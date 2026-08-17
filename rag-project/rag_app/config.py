from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("RAG_APP_NAME", "DeepSeek 知识库")
    data_dir: Path = Path(os.getenv("RAG_DATA_DIR", "runtime")).resolve()
    llm_base_url: str = os.getenv("RAG_LLM_BASE_URL", "http://127.0.0.1:8001/v1").rstrip("/")
    llm_api_key: str = os.getenv("RAG_LLM_API_KEY", "local-not-required")
    llm_model: str = os.getenv("RAG_LLM_MODEL", "deepseek-local")
    llm_mode: str = os.getenv("RAG_LLM_MODE", "openai")
    embedding_url: str = os.getenv("RAG_EMBEDDING_URL", "http://127.0.0.1:8002").rstrip("/")
    embedding_mode: str = os.getenv("RAG_EMBEDDING_MODE", "tei")
    embedding_model: str = os.getenv("RAG_EMBEDDING_MODEL", "bge-m3")
    embedding_batch_size: int = _int("RAG_EMBEDDING_BATCH_SIZE", 32)
    chunk_size: int = _int("RAG_CHUNK_SIZE", 700)
    chunk_overlap: int = _int("RAG_CHUNK_OVERLAP", 100)
    default_top_k: int = _int("RAG_TOP_K", 6)
    score_threshold: float = _float("RAG_SCORE_THRESHOLD", 0.2)
    max_context_chars: int = _int("RAG_MAX_CONTEXT_CHARS", 12000)
    max_history_messages: int = _int("RAG_MAX_HISTORY_MESSAGES", 10)
    max_upload_mb: int = _int("RAG_MAX_UPLOAD_MB", 50)
    request_timeout: float = _float("RAG_REQUEST_TIMEOUT", 300.0)
    system_prompt: str = os.getenv(
        "RAG_SYSTEM_PROMPT",
        "你是严谨的中文知识库助手。优先依据给出的检索资料回答；"
        "资料不足时明确说明，不得编造来源。引用资料时使用 [1]、[2] 这样的编号。",
    )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "rag.sqlite3"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
