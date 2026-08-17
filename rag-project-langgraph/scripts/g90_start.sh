#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/test/test06/apps/rag-project-langgraph"
cd "$PROJECT_DIR"
mkdir -p logs runtime

export PYTHONUTF8=1
export RAG_LLM_BASE_URL="http://127.0.0.1:8001/v1"
export RAG_LLM_MODEL="deepseek-local"
export RAG_EMBEDDING_BASE_URL="http://127.0.0.1:8002/v1"
export RAG_EMBEDDING_MODEL="bge-m3"
export RAG_LOCAL_API_KEY="EMPTY"

.venv/bin/python g90_runtime.py --build-index

if ! tmux has-session -t rag-graph1 2>/dev/null; then
  tmux new-session -d -s rag-graph1 \
    "cd '$PROJECT_DIR' && exec env PYTHONUTF8=1 RAG_LLM_BASE_URL='$RAG_LLM_BASE_URL' RAG_LLM_MODEL='$RAG_LLM_MODEL' RAG_EMBEDDING_BASE_URL='$RAG_EMBEDDING_BASE_URL' RAG_EMBEDDING_MODEL='$RAG_EMBEDDING_MODEL' RAG_LOCAL_API_KEY='$RAG_LOCAL_API_KEY' .venv/bin/python -u g90_runtime.py basic 2>&1 | tee -a logs/graph1.log"
fi

if ! tmux has-session -t rag-graph2 2>/dev/null; then
  tmux new-session -d -s rag-graph2 \
    "cd '$PROJECT_DIR' && exec env PYTHONUTF8=1 RAG_LLM_BASE_URL='$RAG_LLM_BASE_URL' RAG_LLM_MODEL='$RAG_LLM_MODEL' RAG_EMBEDDING_BASE_URL='$RAG_EMBEDDING_BASE_URL' RAG_EMBEDDING_MODEL='$RAG_EMBEDDING_MODEL' RAG_LOCAL_API_KEY='$RAG_LOCAL_API_KEY' .venv/bin/python -u g90_runtime.py adaptive 2>&1 | tee -a logs/graph2.log"
fi

tmux list-sessions | grep -E '^rag-graph(1|2):'
