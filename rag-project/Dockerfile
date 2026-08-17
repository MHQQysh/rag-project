FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

COPY requirements-app.txt ./
RUN pip install --upgrade pip && pip install -r requirements-app.txt

COPY rag_app ./rag_app
COPY startup.py ./

RUN mkdir -p /app/runtime/uploads && useradd --create-home --uid 10001 rag && chown -R rag:rag /app
USER rag

EXPOSE 6006
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:6006/api/config', timeout=3)"

CMD ["python", "startup.py"]
