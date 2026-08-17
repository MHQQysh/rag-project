from __future__ import annotations

import json
import math
import sqlite3
import threading
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._write_lock = threading.Lock()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    locator TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    lexical_tokens TEXT NOT NULL DEFAULT '[]',
                    embedding BLOB NOT NULL,
                    embedding_dim INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    analysis_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
                """
            )
            chunk_columns = {row["name"] for row in db.execute("PRAGMA table_info(chunks)")}
            if "lexical_tokens" not in chunk_columns:
                db.execute("ALTER TABLE chunks ADD COLUMN lexical_tokens TEXT NOT NULL DEFAULT '[]'")
            message_columns = {row["name"] for row in db.execute("PRAGMA table_info(messages)")}
            if "analysis_json" not in message_columns:
                db.execute("ALTER TABLE messages ADD COLUMN analysis_json TEXT NOT NULL DEFAULT '{}'")

    def create_document(self, name: str, extension: str, size_bytes: int, sha256: str) -> dict[str, Any]:
        document_id = str(uuid.uuid4())
        created_at = utc_now()
        with self._write_lock, self.connect() as db:
            db.execute(
                "INSERT INTO documents(id,name,extension,size_bytes,sha256,status,created_at) VALUES(?,?,?,?,?,'processing',?)",
                (document_id, name, extension, size_bytes, sha256, created_at),
            )
        return self.get_document(document_id)

    def get_document_by_sha(self, sha256: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE sha256=?", (sha256,)).fetchone()
        return dict(row) if row else None

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        return dict(row) if row else None

    def finish_document(self, document_id: str, chunks: list[dict[str, Any]], embeddings: np.ndarray) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunk and embedding counts differ")
        with self._write_lock, self.connect() as db:
            db.executemany(
                "INSERT INTO chunks(document_id,chunk_index,locator,content,lexical_tokens,embedding,embedding_dim) VALUES(?,?,?,?,?,?,?)",
                [
                    (
                        document_id,
                        chunk["index"],
                        chunk["locator"],
                        chunk["text"],
                        json.dumps(chunk.get("lexical_tokens", []), ensure_ascii=False),
                        np.asarray(vector, dtype=np.float32).tobytes(),
                        len(vector),
                    )
                    for chunk, vector in zip(chunks, embeddings)
                ],
            )
            db.execute("UPDATE documents SET status='ready', chunk_count=?, error=NULL WHERE id=?", (len(chunks), document_id))

    def fail_document(self, document_id: str, error: str) -> None:
        with self._write_lock, self.connect() as db:
            db.execute("UPDATE documents SET status='failed', error=? WHERE id=?", (error[:1000], document_id))

    def list_documents(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        with self._write_lock, self.connect() as db:
            cursor = db.execute("DELETE FROM documents WHERE id=?", (document_id,))
        return cursor.rowcount > 0

    def backfill_lexical_tokens(self, analyzer) -> int:
        with self.connect() as db:
            rows = db.execute("SELECT id,content FROM chunks WHERE lexical_tokens='' OR lexical_tokens='[]'").fetchall()
        if not rows:
            return 0
        updates = [(json.dumps(analyzer(row["content"]), ensure_ascii=False), row["id"]) for row in rows]
        with self._write_lock, self.connect() as db:
            db.executemany("UPDATE chunks SET lexical_tokens=? WHERE id=?", updates)
        return len(updates)

    def search(
        self,
        query_embedding: np.ndarray,
        query_terms: list[str],
        entities: list[str],
        top_k: int,
        threshold: float,
    ) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """SELECT c.id,c.document_id,c.chunk_index,c.locator,c.content,c.lexical_tokens,c.embedding,c.embedding_dim,d.name
                   FROM chunks c JOIN documents d ON d.id=c.document_id WHERE d.status='ready'"""
            ).fetchall()
        if not rows:
            return []
        query = np.asarray(query_embedding, dtype=np.float32)
        documents = []
        for row in rows:
            try:
                terms = json.loads(row["lexical_tokens"] or "[]")
            except json.JSONDecodeError:
                terms = []
            documents.append([str(term).lower() for term in terms])

        normalized_query = [term.lower() for term in query_terms if term]
        query_counts = Counter(normalized_query)
        document_frequencies = {
            term: sum(1 for document in documents if term in set(document)) for term in query_counts
        }
        average_length = sum(len(document) for document in documents) / max(len(documents), 1)
        raw_bm25: list[float] = []
        for document in documents:
            frequencies = Counter(document)
            score = 0.0
            for term, query_frequency in query_counts.items():
                df = document_frequencies[term]
                idf = math.log(1 + (len(documents) - df + 0.5) / (df + 0.5))
                tf = frequencies[term]
                denominator = tf + 1.5 * (1 - 0.75 + 0.75 * len(document) / max(average_length, 1))
                score += idf * ((tf * 2.5) / denominator if denominator else 0) * query_frequency
            raw_bm25.append(score)
        max_bm25 = max(raw_bm25, default=0.0)
        query_entities = {entity.lower() for entity in entities if entity}

        scored: list[dict[str, Any]] = []
        for row, document_terms, bm25 in zip(rows, documents, raw_bm25):
            vector = np.frombuffer(row["embedding"], dtype=np.float32, count=row["embedding_dim"])
            if vector.shape != query.shape:
                continue
            dense_score = float(np.dot(query, vector))
            lexical_score = bm25 / max_bm25 if max_bm25 else 0.0
            content_lower = row["content"].lower()
            entity_score = (
                sum(1 for entity in query_entities if entity in content_lower) / len(query_entities)
                if query_entities else 0.0
            )
            if normalized_query:
                score = 0.72 * dense_score + 0.23 * lexical_score + 0.05 * entity_score
            else:
                score = dense_score
            if score >= threshold:
                item = {key: row[key] for key in ("id", "document_id", "chunk_index", "locator", "content", "name")}
                item["score"] = score
                item["dense_score"] = dense_score
                item["lexical_score"] = lexical_score
                item["entity_score"] = entity_score
                scored.append(item)
        ranked = sorted(scored, key=lambda item: item["score"], reverse=True)
        if not ranked:
            return []
        # Top-K 不是强行凑满：相对最佳结果过低的尾部通常只是语义噪声。
        relative_threshold = max(threshold, ranked[0]["score"] * 0.42)
        return [item for item in ranked if item["score"] >= relative_threshold][:top_k]

    def create_conversation(self, title: str = "新对话") -> dict[str, Any]:
        conversation_id = str(uuid.uuid4())
        now = utc_now()
        with self._write_lock, self.connect() as db:
            db.execute("INSERT INTO conversations(id,title,created_at,updated_at) VALUES(?,?,?,?)", (conversation_id, title, now, now))
        return self.get_conversation(conversation_id)

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        return dict(row) if row else None

    def list_conversations(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """SELECT c.*, COUNT(m.id) AS message_count FROM conversations c
                   LEFT JOIN messages m ON m.conversation_id=c.id GROUP BY c.id ORDER BY c.updated_at DESC"""
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._write_lock, self.connect() as db:
            cursor = db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
        return cursor.rowcount > 0

    def rename_conversation(self, conversation_id: str, title: str) -> None:
        with self._write_lock, self.connect() as db:
            db.execute("UPDATE conversations SET title=?,updated_at=? WHERE id=?", (title, utc_now(), conversation_id))

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())
        now = utc_now()
        with self._write_lock, self.connect() as db:
            db.execute(
                "INSERT INTO messages(id,conversation_id,role,content,sources_json,analysis_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (message_id, conversation_id, role, content, json.dumps(sources or [], ensure_ascii=False), json.dumps(analysis or {}, ensure_ascii=False), now),
            )
            db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
        return {"id": message_id, "conversation_id": conversation_id, "role": role, "content": content, "sources": sources or [], "analysis": analysis or {}, "created_at": now}

    def list_messages(self, conversation_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC"
        params: tuple[Any, ...] = (conversation_id,)
        if limit:
            sql = "SELECT * FROM (SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT ?) ORDER BY created_at ASC"
            params = (conversation_id, limit)
        with self.connect() as db:
            rows = db.execute(sql, params).fetchall()
        return [
            {
                "id": row["id"],
                "conversation_id": row["conversation_id"],
                "role": row["role"],
                "content": row["content"],
                "sources": json.loads(row["sources_json"]),
                "analysis": json.loads(row["analysis_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def stats(self) -> dict[str, int]:
        with self.connect() as db:
            documents = db.execute("SELECT COUNT(*) FROM documents WHERE status='ready'").fetchone()[0]
            chunks = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            conversations = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        return {"documents": documents, "chunks": chunks, "conversations": conversations}
