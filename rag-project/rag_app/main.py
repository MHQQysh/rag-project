from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .chunking import chunk_units
from .clients import EmbeddingClient, LLMClient
from .config import get_settings
from .database import Database
from .parsers import SUPPORTED_EXTENSIONS, extract_units
from .schemas import AnalyzeRequest, ChatRequest, ConversationCreate, RenameRequest
from .service import RAGService
from .text_analysis import analyze_text, index_terms

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("deepseek-rag")

settings = get_settings()
database = Database(settings.database_path)
embeddings = EmbeddingClient(settings)
llm = LLMClient(settings)
rag = RAGService(settings, database, embeddings, llm)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    database.init()
    backfilled = await asyncio.to_thread(database.backfill_lexical_tokens, index_terms)
    if backfilled:
        logger.info("Backfilled lexical terms for %s existing chunks", backfilled)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)


@app.get("/api/health")
async def health():
    llm_ok, embedding_ok = await asyncio.gather(llm.healthy(), embeddings.healthy())
    return {
        "status": "ok" if llm_ok and embedding_ok else "degraded",
        "llm": {"ready": llm_ok, "model": settings.llm_model},
        "embedding": {"ready": embedding_ok},
        "database": {"ready": settings.database_path.exists()},
    }


@app.get("/api/config")
def config():
    return {
        "app_name": settings.app_name,
        "model": settings.llm_model,
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "max_upload_mb": settings.max_upload_mb,
        "default_top_k": settings.default_top_k,
        "score_threshold": settings.score_threshold,
    }


@app.get("/api/stats")
def stats():
    return database.stats()


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest):
    """展示查询进入混合检索前的各项文本理解结果。"""
    return analyze_text(payload.text.strip())


@app.get("/api/documents")
def list_documents():
    return database.list_documents()


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)):
    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型：{extension or '无扩展名'}")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"文件不能超过 {settings.max_upload_mb} MB")
    if not content:
        raise HTTPException(400, "文件为空")

    sha256 = hashlib.sha256(content).hexdigest()
    existing = database.get_document_by_sha(sha256)
    if existing:
        return {**existing, "duplicate": True}

    document = database.create_document(original_name, extension, len(content), sha256)
    safe_name = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", original_name)
    stored_path = settings.upload_dir / f"{document['id']}_{safe_name}"
    stored_path.write_bytes(content)
    try:
        units = await asyncio.to_thread(extract_units, stored_path, original_name)
        chunks = chunk_units(units, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise ValueError("没有从文件中提取到可索引文本；扫描版 PDF 请先进行 OCR")
        vectors = await embeddings.embed([chunk.text for chunk in chunks])
        database.finish_document(
            document["id"],
            [
                {
                    "index": chunk.index,
                    "locator": chunk.locator,
                    "text": chunk.text,
                    "lexical_tokens": index_terms(chunk.text),
                }
                for chunk in chunks
            ],
            vectors,
        )
        return database.get_document(document["id"])
    except Exception as error:
        logger.exception("Failed to index %s", original_name)
        database.fail_document(document["id"], str(error))
        raise HTTPException(500, f"文档处理失败：{error}") from error


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str):
    document = database.get_document(document_id)
    if not document:
        raise HTTPException(404, "文档不存在")
    deleted = database.delete_document(document_id)
    for path in settings.upload_dir.glob(f"{document_id}_*"):
        path.unlink(missing_ok=True)
    return {"deleted": deleted}


@app.get("/api/conversations")
def list_conversations():
    return database.list_conversations()


@app.post("/api/conversations")
def create_conversation(payload: ConversationCreate):
    return database.create_conversation(payload.title.strip() or "新对话")


@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(conversation_id: str, payload: RenameRequest):
    if not database.get_conversation(conversation_id):
        raise HTTPException(404, "会话不存在")
    database.rename_conversation(conversation_id, payload.title.strip())
    return database.get_conversation(conversation_id)


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    if not database.delete_conversation(conversation_id):
        raise HTTPException(404, "会话不存在")
    return {"deleted": True}


@app.get("/api/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str):
    if not database.get_conversation(conversation_id):
        raise HTTPException(404, "会话不存在")
    return database.list_messages(conversation_id)


@app.post("/api/chat")
async def chat(payload: ChatRequest):
    top_k = payload.top_k or settings.default_top_k
    threshold = settings.score_threshold if payload.score_threshold is None else payload.score_threshold
    return StreamingResponse(
        rag.chat(payload.query.strip(), payload.conversation_id, top_k, threshold),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


static_dir = Path(__file__).with_name("static")
app.mount("/assets", StaticFiles(directory=static_dir), name="assets")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(static_dir / "index.html")
