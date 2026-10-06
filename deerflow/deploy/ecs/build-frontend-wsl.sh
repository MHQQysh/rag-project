#!/bin/bash
# Run in Linux/WSL with Node and the repository's pinned pnpm available.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
cd "$repo/frontend"
pnpm install --frozen-lockfile
NEXT_CONFIG_BUILD_OUTPUT=standalone SKIP_ENV_VALIDATION=1 NODE_OPTIONS=--max-old-space-size=2048 pnpm exec next build --webpack
