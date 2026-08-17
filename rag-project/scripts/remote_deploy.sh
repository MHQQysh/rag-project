#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p runtime/uploads model-cache
chmod -R a+rwX runtime
mkdir -p model-cache/modelscope

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "Docker Compose is required" >&2
  exit 1
fi

DOCKER_BUILDKIT=0 "${compose[@]}" build app

modelscope_image="modelscope-registry.cn-beijing.cr.aliyuncs.com/modelscope-repo/modelscope:ubuntu22.04-cuda12.8.1-py311-torch2.10.0-vllm0.17.0-modelscope1.34.0-swift4.0.1"
download_model() {
  local model_id="$1"
  local target="$2"
  if [[ -f "model-cache/modelscope/${target}/config.json" ]] && find "model-cache/modelscope/${target}" -name '*.safetensors' -print -quit | grep -q .; then
    echo "Model already present: ${target}"
    return
  fi
  docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e MODELSCOPE_CACHE=/tmp/modelscope \
    -e XDG_CACHE_HOME=/tmp/cache \
    -v "$PWD/model-cache/modelscope:/models" \
    "$modelscope_image" \
    bash -lc "modelscope download --model '${model_id}' --local_dir '/models/${target}' --max-workers 4"
}

download_model deepseek-ai/DeepSeek-R1-Distill-Qwen-14B deepseek-14b
download_model BAAI/bge-m3 bge-m3
python3 scripts/fix_deepseek_tokenizer.py model-cache/modelscope/deepseek-14b

"${compose[@]}" up -d
"${compose[@]}" ps

echo "模型首次启动需要下载权重。查看进度："
echo "  ${compose[*]} logs -f llm embeddings"
