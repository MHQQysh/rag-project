"""g90 runtime for the repository's two LangGraph RAG examples.

This adapter uses the OpenAI-compatible DeepSeek and BGE-M3 services already
running on g90.  It replaces the upstream hard dependency on an external API
gateway, Tavily, and Milvus with a persisted NumPy cosine index built from the
repository's own ``datas/md`` knowledge base.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Literal, TypedDict

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.constants import END, START
from langgraph.graph import StateGraph


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "datas" / "md"
RUNTIME_DIR = ROOT / "runtime"
INDEX_PATH = RUNTIME_DIR / "g90-bge-m3-index.npz"
META_PATH = RUNTIME_DIR / "g90-bge-m3-metadata.json"

LLM_BASE_URL = os.getenv("RAG_LLM_BASE_URL", "http://127.0.0.1:8001/v1")
LLM_MODEL = os.getenv("RAG_LLM_MODEL", "deepseek-local")
EMBEDDING_BASE_URL = os.getenv(
    "RAG_EMBEDDING_BASE_URL", "http://127.0.0.1:8002/v1"
)
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "bge-m3")
API_KEY = os.getenv("RAG_LOCAL_API_KEY", "EMPTY")


class RAGState(TypedDict, total=False):
    question: str
    documents: list[dict[str, object]]
    confidence: float
    route_decision: str
    answer: str


def _embedding_client() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=API_KEY,
        openai_api_base=EMBEDDING_BASE_URL,
        check_embedding_ctx_length=False,
    )


def _llm_client() -> ChatOpenAI:
    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=API_KEY,
        base_url=LLM_BASE_URL,
        temperature=0,
        max_tokens=900,
        timeout=180,
    )


def _split_markdown(text: str, max_chars: int = 1_400, overlap: int = 180) -> list[str]:
    sections = re.split(r"\n(?=#{1,4}\s)", text)
    chunks: list[str] = []
    for section in sections:
        section = section.strip()
        if not section or section == "---":
            continue
        start = 0
        while start < len(section):
            end = min(len(section), start + max_chars)
            chunk = section[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(section):
                break
            start = max(start + 1, end - overlap)
    return chunks


def _knowledge_chunks() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for chunk_id, text_chunk in enumerate(_split_markdown(text)):
            records.append(
                {"source": path.name, "chunk": chunk_id, "text": text_chunk}
            )
    if not records:
        raise RuntimeError(f"No Markdown files found under {DATA_DIR}")
    return records


def build_index(force: bool = False) -> tuple[np.ndarray, list[dict[str, object]]]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if INDEX_PATH.exists() and META_PATH.exists() and not force:
        matrix = np.load(INDEX_PATH)["embeddings"]
        metadata = json.loads(META_PATH.read_text(encoding="utf-8"))
        return matrix, metadata

    metadata = _knowledge_chunks()
    texts = [str(item["text"]) for item in metadata]
    print(f"[index] embedding {len(texts)} chunks with {EMBEDDING_MODEL}", flush=True)
    client = _embedding_client()
    vectors: list[list[float]] = []
    batch_size = 32
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        vectors.extend(client.embed_documents(batch))
        print(f"[index] {min(start + batch_size, len(texts))}/{len(texts)}", flush=True)

    matrix = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.clip(norms, 1e-12, None)

    index_tmp = INDEX_PATH.with_suffix(".tmp")
    meta_tmp = META_PATH.with_suffix(".tmp")
    with index_tmp.open("wb") as handle:
        np.savez_compressed(handle, embeddings=matrix)
    meta_tmp.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    os.replace(index_tmp, INDEX_PATH)
    os.replace(meta_tmp, META_PATH)
    print(f"[index] saved {INDEX_PATH} shape={matrix.shape}", flush=True)
    return matrix, metadata


class LocalVectorIndex:
    def __init__(self) -> None:
        self.matrix, self.metadata = build_index()
        self.embeddings = _embedding_client()

    def search(self, question: str, top_k: int = 4) -> list[dict[str, object]]:
        query = np.asarray(self.embeddings.embed_query(question), dtype=np.float32)
        query /= max(float(np.linalg.norm(query)), 1e-12)
        scores = self.matrix @ query
        indices = np.argsort(scores)[::-1][:top_k]
        results: list[dict[str, object]] = []
        for index in indices:
            record = dict(self.metadata[int(index)])
            record["score"] = round(float(scores[int(index)]), 4)
            results.append(record)
        return results


_index: LocalVectorIndex | None = None


def _get_index() -> LocalVectorIndex:
    global _index
    if _index is None:
        _index = LocalVectorIndex()
    return _index


def retrieve(state: RAGState) -> RAGState:
    documents = _get_index().search(state["question"])
    confidence = float(documents[0]["score"]) if documents else 0.0
    print(f"[retrieve] hits={len(documents)} top_score={confidence:.4f}", flush=True)
    return {"documents": documents, "confidence": confidence}


def route_node(state: RAGState) -> RAGState:
    result = retrieve(state)
    confidence = float(result.get("confidence", 0.0))
    selected = "vectorstore" if confidence >= 0.28 else "fallback"
    print(f"[route] {selected}", flush=True)
    return {**result, "route_decision": selected}


def route_next(state: RAGState) -> Literal["generate", "fallback"]:
    return "generate" if state.get("route_decision") == "vectorstore" else "fallback"


def generate(state: RAGState) -> RAGState:
    context_parts = []
    for document in state.get("documents", []):
        citation = f"[{document['source']}#chunk-{document['chunk']}]"
        context_parts.append(f"{citation}\n{document['text']}")
    context = "\n\n".join(context_parts)
    system = SystemMessage(
        content=(
            "你是企业知识库 RAG 助手。只能依据提供的资料回答；资料不足时必须明确说不知道。"
            "回答使用中文，结论后保留形如 [文件名#chunk-N] 的引用，不要编造引用。"
        )
    )
    human = HumanMessage(content=f"资料：\n{context}\n\n用户问题：{state['question']}")
    response = _llm_client().invoke([system, human])
    answer = response.content if isinstance(response.content, str) else str(response.content)
    if not answer:
        answer = str(response.additional_kwargs.get("reasoning_content", ""))
    if "</think>" in answer:
        answer = answer.split("</think>", 1)[1].strip()
    print("[generate] DeepSeek response received", flush=True)
    return {"answer": answer}


def fallback(state: RAGState) -> RAGState:
    return {
        "answer": (
            "知识库检索置信度不足，当前自适应流程拒绝生成答案。"
            "请询问 Milvus、向量检索、索引、部署或仓库文档相关问题。"
        )
    }


def build_basic_graph():
    workflow = StateGraph(RAGState)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile()


def build_adaptive_graph():
    workflow = StateGraph(RAGState)
    workflow.add_node("router", route_node)
    workflow.add_node("generate", generate)
    workflow.add_node("fallback", fallback)
    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router", route_next, {"generate": "generate", "fallback": "fallback"}
    )
    workflow.add_edge("generate", END)
    workflow.add_edge("fallback", END)
    return workflow.compile()


def answer_once(flow: Literal["basic", "adaptive"], question: str) -> str:
    graph = build_basic_graph() if flow == "basic" else build_adaptive_graph()
    result = graph.invoke({"question": question})
    return str(result["answer"])


def interactive(flow: Literal["basic", "adaptive"]) -> None:
    label = "graph1 基础 RAG" if flow == "basic" else "graph2 自适应 RAG"
    print(f"{label} 已在 g90 启动；输入 q / exit / quit 退出。", flush=True)
    while True:
        try:
            question = input("用户：").strip()
        except EOFError:
            break
        if question.lower() in {"q", "exit", "quit"}:
            break
        if question:
            try:
                print(f"回答：{answer_once(flow, question)}\n", flush=True)
            except Exception as exc:
                print(f"运行错误：{type(exc).__name__}: {exc}\n", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("flow", nargs="?", choices=["basic", "adaptive"])
    parser.add_argument("--question")
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.build_index:
        build_index(force=args.force)
        return
    if not args.flow:
        parser.error("flow is required unless --build-index is used")
    if args.question:
        print(answer_once(args.flow, args.question))
    else:
        interactive(args.flow)


if __name__ == "__main__":
    main()
