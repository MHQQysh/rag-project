from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator

import httpx
import numpy as np

from .config import Settings


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


class EmbeddingClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _hash_embedding(text: str, dimensions: int = 256) -> np.ndarray:
        vector = np.zeros(dimensions, dtype=np.float32)
        normalized = "".join(text.lower().split())
        tokens = [normalized[i : i + 2] for i in range(max(1, len(normalized) - 1))]
        for token in tokens or [normalized]:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = np.linalg.norm(vector)
        return vector / max(float(norm), 1e-12)

    async def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        if self.settings.embedding_mode == "hash":
            return np.stack([self._hash_embedding(text) for text in texts])

        vectors: list[list[float]] = []
        timeout = httpx.Timeout(self.settings.request_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for offset in range(0, len(texts), self.settings.embedding_batch_size):
                batch = texts[offset : offset + self.settings.embedding_batch_size]
                if self.settings.embedding_mode == "openai":
                    response = await client.post(
                        f"{self.settings.embedding_url}/embeddings",
                        json={"model": self.settings.embedding_model, "input": batch, "encoding_format": "float"},
                        headers={"Authorization": "Bearer local-not-required"},
                    )
                else:
                    response = await client.post(
                        f"{self.settings.embedding_url}/embed",
                        json={"inputs": batch, "truncate": True},
                    )
                response.raise_for_status()
                payload = response.json()
                if self.settings.embedding_mode == "openai":
                    vectors.extend(item["embedding"] for item in sorted(payload["data"], key=lambda item: item["index"]))
                else:
                    vectors.extend(payload)
        return _normalize(np.asarray(vectors, dtype=np.float32))

    async def healthy(self) -> bool:
        if self.settings.embedding_mode == "hash":
            return True
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                endpoint = "/models" if self.settings.embedding_mode == "openai" else "/health"
                response = await client.get(f"{self.settings.embedding_url}{endpoint}")
            return response.status_code == 200
        except Exception:
            return False


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        if self.settings.llm_mode == "mock":
            answer = "这是测试模式回答。我已依据检索到的知识片段进行处理。[1]"
            for token in answer:
                yield token
                await asyncio.sleep(0)
            return

        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "stream": True,
            "temperature": 0.6,
            "top_p": 0.95,
            "max_tokens": 4096,
        }
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}", "Content-Type": "application/json"}
        timeout = httpx.Timeout(self.settings.request_timeout, connect=20)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{self.settings.llm_base_url}/chat/completions", json=payload, headers=headers) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    raise RuntimeError(f"模型服务返回 {response.status_code}: {body[:500]}")
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    event = json.loads(data)
                    choices = event.get("choices") or []
                    if choices:
                        content = (choices[0].get("delta") or {}).get("content")
                        if content:
                            yield content

    async def healthy(self) -> bool:
        if self.settings.llm_mode == "mock":
            return True
        try:
            headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.settings.llm_base_url}/models", headers=headers)
            return response.status_code == 200
        except Exception:
            return False
