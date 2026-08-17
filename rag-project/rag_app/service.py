from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from .clients import EmbeddingClient, LLMClient
from .config import Settings
from .database import Database
from .text_analysis import analyze_text


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class RAGService:
    def __init__(self, settings: Settings, database: Database, embeddings: EmbeddingClient, llm: LLMClient):
        self.settings = settings
        self.database = database
        self.embeddings = embeddings
        self.llm = llm

    async def retrieve(self, query: str, top_k: int, threshold: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        analysis = analyze_text(query)
        vector = (await self.embeddings.embed([query]))[0]
        matches = self.database.search(
            vector,
            analysis["lexical_terms"],
            [entity["text"] for entity in analysis["entities"]],
            top_k,
            threshold,
        )
        sources = [
            {
                "document_id": item["document_id"],
                "document_name": item["name"],
                "chunk_index": item["chunk_index"],
                "locator": item["locator"],
                "score": round(item["score"], 4),
                "dense_score": round(item["dense_score"], 4),
                "lexical_score": round(item["lexical_score"], 4),
                "entity_score": round(item["entity_score"], 4),
                "content": item["content"],
            }
            for item in matches
        ]
        return sources, analysis

    def _messages(
        self,
        query: str,
        sources: list[dict[str, Any]],
        history: list[dict[str, Any]],
        analysis: dict[str, Any],
    ) -> list[dict[str, str]]:
        blocks = []
        used = 0
        for number, source in enumerate(sources, 1):
            header = f"[{number}] 文件：{source['document_name']}；位置：{source['locator'] or '未标注'}；相关度：{source['score']}"
            block = f"{header}\n{source['content']}"
            if used + len(block) > self.settings.max_context_chars:
                break
            blocks.append(block)
            used += len(block)
        context = "\n\n".join(blocks) if blocks else "（当前没有检索到达到阈值的知识片段）"
        keyword_text = "、".join(item["text"] for item in analysis["keywords"]) or "无"
        entity_text = "、".join(item["text"] for item in analysis["entities"]) or "无"
        system = (
            f"{self.settings.system_prompt}\n\n"
            f"检索侧识别的关键词：{keyword_text}\n检索侧识别的实体：{entity_text}\n"
            f"以下是本轮混合检索资料：\n{context}"
        )
        messages = [{"role": "system", "content": system}]
        messages.extend({"role": item["role"], "content": item["content"]} for item in history if item["role"] in {"user", "assistant"})
        messages.append({"role": "user", "content": query})
        return messages

    async def chat(self, query: str, conversation_id: str | None, top_k: int, threshold: float) -> AsyncIterator[str]:
        conversation = self.database.get_conversation(conversation_id) if conversation_id else None
        if not conversation:
            conversation = self.database.create_conversation(query.strip()[:36] or "新对话")
        conversation_id = conversation["id"]
        history = self.database.list_messages(conversation_id, self.settings.max_history_messages)
        sources, analysis = await self.retrieve(query, top_k, threshold)
        self.database.add_message(conversation_id, "user", query)

        public_sources = [
            {**source, "content": source["content"][:600] + ("…" if len(source["content"]) > 600 else "")}
            for source in sources
        ]
        yield sse("meta", {"conversation_id": conversation_id, "sources": public_sources, "analysis": analysis})

        answer_parts: list[str] = []
        try:
            async for token in self.llm.stream(self._messages(query, sources, history, analysis)):
                answer_parts.append(token)
                yield sse("token", {"content": token})
            answer = "".join(answer_parts).strip()
            self.database.add_message(conversation_id, "assistant", answer, public_sources, analysis)
            yield sse("done", {"conversation_id": conversation_id})
        except Exception as error:
            yield sse("error", {"message": str(error)})
