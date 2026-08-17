"""Deterministic, local-only runners for the two LangGraph examples.

The upstream examples require an OpenAI-compatible API, Tavily, and a running
Milvus server.  This module keeps their graph-shaped execution available on a
fresh machine by using the Markdown files in ``datas/md`` as a small local
knowledge base.  It is intentionally extractive: it never pretends that a
local language model produced the answer.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.constants import END, START
from langgraph.graph import StateGraph


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "datas" / "md"
MAX_FILES = 500
MAX_CHUNK_CHARS = 1_800


class OfflineState(TypedDict, total=False):
    question: str
    search_query: str
    documents: list[dict[str, object]]
    answer: str
    route: str
    attempts: int
    grounded: bool


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    latin = set(re.findall(r"[a-z0-9][a-z0-9_.+-]{1,}", lowered))
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", lowered)
    chinese = {
        run[index : index + 2]
        for run in chinese_runs
        for index in range(max(0, len(run) - 1))
    }
    return latin | chinese


def _split_markdown(text: str) -> list[str]:
    pieces = re.split(r"\n(?=#{1,4}\s)|\n{2,}", text)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece or piece.startswith("---"):
            continue
        if piece.startswith("#") and current:
            chunks.append(current)
            current = ""
        if len(current) + len(piece) + 2 <= MAX_CHUNK_CHARS:
            current = f"{current}\n\n{piece}".strip()
        else:
            if current:
                chunks.append(current)
            current = piece[:MAX_CHUNK_CHARS]
    if current:
        chunks.append(current)
    return chunks


@lru_cache(maxsize=1)
def _corpus() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(DATA_DIR.glob("*.md"))[:MAX_FILES]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, chunk in enumerate(_split_markdown(text)):
            records.append(
                {
                    "source": path.name,
                    "chunk": index,
                    "text": chunk,
                    "tokens": _tokens(chunk),
                }
            )
    if not records:
        raise RuntimeError(f"No Markdown knowledge files found in {DATA_DIR}")
    return records


def _search(query: str, limit: int = 3) -> list[dict[str, object]]:
    query_tokens = _tokens(query)
    synonym_map = {
        "是什么": {"what", "is", "introduction", "overview"},
        "向量": {"vector", "vectors", "embedding"},
        "索引": {"index", "indexes", "hnsw", "flat", "ivf_flat"},
        "支持": {"support", "supported"},
        "价格": {"cost", "price", "free"},
        "费用": {"cost", "price", "free"},
        "部署": {"deploy", "deployment", "docker", "install"},
        "安装": {"install", "installation", "docker"},
        "召回": {"recall", "nprobe", "search"},
    }
    for phrase, expansions in synonym_map.items():
        if phrase in query:
            query_tokens.update(expansions)
    if not query_tokens:
        return []

    ranked: list[tuple[float, dict[str, object]]] = []
    query_lower = query.lower().strip()
    for record in _corpus():
        record_tokens = record["tokens"]
        overlap = query_tokens.intersection(record_tokens)  # type: ignore[union-attr]
        if not overlap:
            continue
        text = str(record["text"])
        text_lower = text.lower()
        score = sum(1.0 + math.log1p(len(token)) for token in overlap)
        score /= 1.0 + 0.03 * math.sqrt(max(1, len(record_tokens)))  # type: ignore[arg-type]
        if query_lower and query_lower in text_lower:
            score += 4.0
        if "overview" in query_tokens and record["source"] == "overview.md":
            score += 2.0
        if "索引" in query and any(term in text_lower for term in ("index types", "hnsw", "ivf_flat")):
            score += 12.0
        if "是什么" in query and "what is milvus" in text_lower:
            score += 12.0
        ranked.append((score, record))

    ranked.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, object]] = []
    for score, record in ranked[:limit]:
        results.append(
            {
                "source": record["source"],
                "chunk": record["chunk"],
                "text": record["text"],
                "score": round(score, 4),
            }
        )
    return results


def _question(state: OfflineState) -> str:
    return state.get("search_query") or state["question"]


def retrieve(state: OfflineState) -> OfflineState:
    query = _question(state)
    documents = _search(query)
    print(f"[retrieve] query={query!r}, hits={len(documents)}")
    return {"documents": documents}


def relevant_or_rewrite(state: OfflineState) -> Literal["generate", "rewrite"]:
    documents = state.get("documents", [])
    relevant = bool(documents and float(documents[0]["score"]) >= 0.2)
    print(f"[grade_documents] relevant={relevant}")
    return "generate" if relevant else "rewrite"


def rewrite(state: OfflineState) -> OfflineState:
    attempts = state.get("attempts", 0) + 1
    rewritten = f"{state['question']} Milvus vector database"
    print(f"[rewrite] attempt={attempts}, query={rewritten!r}")
    return {"search_query": rewritten, "attempts": attempts}


def after_rewrite(state: OfflineState) -> Literal["retrieve", "fallback"]:
    return "fallback" if state.get("attempts", 0) > 1 else "retrieve"


def _clean_excerpt(text: str, limit: int = 520) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
        and not line.lstrip().startswith(("---", "![", "<!--", "{{"))
    ]
    excerpt = " ".join(lines)
    excerpt = re.sub(r"\s+", " ", excerpt)
    return excerpt[:limit].rstrip() + ("…" if len(excerpt) > limit else "")


def generate(state: OfflineState) -> OfflineState:
    documents = state.get("documents", [])
    if not documents:
        return fallback(state)
    citations = []
    for doc in documents[:2]:
        citations.append(
            f"- [{doc['source']}#chunk-{doc['chunk']}] "
            f"{_clean_excerpt(str(doc['text']))}"
        )
    answer = "根据仓库内的本地知识库，检索到以下依据：\n" + "\n".join(citations)
    print(f"[generate] citations={len(citations)}")
    return {"answer": answer, "grounded": True}


def fallback(state: OfflineState) -> OfflineState:
    answer = (
        "本地离线知识库中没有找到足够相关的内容。"
        "请换一个与 Milvus、向量检索、索引或运维有关的问题；"
        "联网模式可配置 OPENAI_API_KEY、TAVILY_API_KEY 和 Milvus 后使用。"
    )
    print("[fallback] no grounded local answer")
    return {"answer": answer, "grounded": False}


def route_question(state: OfflineState) -> Literal["vectorstore", "fallback"]:
    known_terms = {
        "milvus",
        "vector",
        "向量",
        "索引",
        "embedding",
        "docker",
        "检索",
        "collection",
        "partition",
    }
    tokens = _tokens(state["question"])
    route = "vectorstore" if tokens.intersection(known_terms) else "fallback"
    print(f"[route_question] route={route}")
    return route


def quality_gate(state: OfflineState) -> Literal["useful", "fallback"]:
    useful = bool(state.get("grounded") and state.get("answer"))
    print(f"[quality_gate] useful={useful}")
    return "useful" if useful else "fallback"


def build_basic_graph():
    workflow = StateGraph(OfflineState)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("rewrite", rewrite)
    workflow.add_node("generate", generate)
    workflow.add_node("fallback", fallback)
    workflow.add_edge(START, "retrieve")
    workflow.add_conditional_edges("retrieve", relevant_or_rewrite)
    workflow.add_conditional_edges("rewrite", after_rewrite)
    workflow.add_edge("generate", END)
    workflow.add_edge("fallback", END)
    return workflow.compile()


def build_adaptive_graph():
    workflow = StateGraph(OfflineState)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)
    workflow.add_node("fallback", fallback)
    workflow.add_conditional_edges(
        START,
        route_question,
        {"vectorstore": "retrieve", "fallback": "fallback"},
    )
    workflow.add_edge("retrieve", "generate")
    workflow.add_conditional_edges(
        "generate", quality_gate, {"useful": END, "fallback": "fallback"}
    )
    workflow.add_edge("fallback", END)
    return workflow.compile()


def run_cli(flow: Literal["basic", "adaptive"]) -> None:
    graph = build_basic_graph() if flow == "basic" else build_adaptive_graph()
    label = "基础 RAG" if flow == "basic" else "自适应 RAG"
    print(f"{label} 已以本地离线模式启动。输入 q / exit / quit 退出。")
    while True:
        try:
            question = input("用户：").strip()
        except EOFError:
            break
        if question.lower() in {"q", "exit", "quit"}:
            print("对话结束。")
            break
        if not question:
            continue
        result = graph.invoke({"question": question, "attempts": 0})
        print(f"\n回答：\n{result['answer']}\n")
