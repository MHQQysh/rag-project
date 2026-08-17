from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", max_length=100)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    conversation_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    score_threshold: float | None = Field(default=None, ge=-1, le=1)


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
