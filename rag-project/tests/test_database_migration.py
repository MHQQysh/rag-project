import sqlite3

from rag_app.database import Database
from rag_app.text_analysis import index_terms


def test_existing_database_is_migrated_and_backfilled(tmp_path):
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE documents (id TEXT PRIMARY KEY, name TEXT, extension TEXT, size_bytes INTEGER,
                sha256 TEXT UNIQUE, status TEXT, chunk_count INTEGER, error TEXT, created_at TEXT);
            CREATE TABLE chunks (id INTEGER PRIMARY KEY, document_id TEXT, chunk_index INTEGER,
                locator TEXT, content TEXT, embedding BLOB, embedding_dim INTEGER);
            CREATE TABLE conversations (id TEXT PRIMARY KEY, title TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE messages (id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT,
                sources_json TEXT DEFAULT '[]', created_at TEXT);
            INSERT INTO chunks VALUES (1, 'doc', 0, '', '北斗计划负责人是林舟', X'00000000', 1);
            """
        )

    database = Database(path)
    database.init()
    assert database.backfill_lexical_tokens(index_terms) == 1

    with database.connect() as db:
        terms = db.execute("SELECT lexical_tokens FROM chunks WHERE id=1").fetchone()[0]
        message_columns = {row["name"] for row in db.execute("PRAGMA table_info(messages)")}
    assert "北斗" in terms
    assert "analysis_json" in message_columns
