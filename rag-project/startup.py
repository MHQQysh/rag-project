"""Local launcher for the complete DeepSeek RAG application."""

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "rag_app.main:app",
        host=os.getenv("RAG_HOST", "0.0.0.0"),
        port=int(os.getenv("RAG_PORT", "6006")),
        reload=os.getenv("RAG_RELOAD", "false").lower() == "true",
    )
