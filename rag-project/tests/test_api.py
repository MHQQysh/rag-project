import importlib
import json

from fastapi.testclient import TestClient


def _events(text: str):
    result = []
    for block in text.strip().split("\n\n"):
        event = next(line[6:].strip() for line in block.splitlines() if line.startswith("event:"))
        data = next(line[5:].strip() for line in block.splitlines() if line.startswith("data:"))
        result.append((event, json.loads(data)))
    return result


def test_document_chat_and_conversation_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RAG_EMBEDDING_MODE", "hash")
    monkeypatch.setenv("RAG_LLM_MODE", "mock")
    monkeypatch.setenv("RAG_SCORE_THRESHOLD", "-1")

    import rag_app.config
    rag_app.config.get_settings.cache_clear()
    import rag_app.main
    app_module = importlib.reload(rag_app.main)

    with TestClient(app_module.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        analysis = client.post("/api/analyze", json={"text": "我想知道这个项目的代号"})
        assert analysis.status_code == 200
        assert "项目" in analysis.json()["filtered_tokens"]
        assert analysis.json()["semantic_query"] == "我想知道这个项目的代号"

        uploaded = client.post(
            "/api/documents",
            files={"file": ("规则.txt", "项目代号是北斗。交付日期是十月一日。", "text/plain")},
        )
        assert uploaded.status_code == 200, uploaded.text
        assert uploaded.json()["status"] == "ready"
        assert uploaded.json()["chunk_count"] >= 1

        response = client.post("/api/chat", json={"query": "项目代号是什么？", "top_k": 4})
        assert response.status_code == 200
        events = _events(response.text)
        meta = next(data for event, data in events if event == "meta")
        assert meta["sources"][0]["document_name"] == "规则.txt"
        assert "analysis" in meta
        assert {"dense_score", "lexical_score", "entity_score"}.issubset(meta["sources"][0])
        assert any(event == "token" for event, _ in events)
        assert any(event == "done" for event, _ in events)

        messages = client.get(f"/api/conversations/{meta['conversation_id']}/messages")
        assert [item["role"] for item in messages.json()] == ["user", "assistant"]
        assert messages.json()[1]["analysis"]["semantic_query"] == "项目代号是什么？"

        stats = client.get("/api/stats").json()
        assert stats == {"documents": 1, "chunks": uploaded.json()["chunk_count"], "conversations": 1}
