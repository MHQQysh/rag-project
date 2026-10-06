#!/bin/bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
base="$repo/frontend"
stage="$base/.next/standalone"
test -f "$stage/server.js"
mkdir -p "$stage/.next" "$stage/bin"
cp -a "$base/.next/static" "$stage/.next/"
cp -a "$base/public" "$stage/"
cp "$(command -v node)" "$stage/bin/node"
tar -czf "$repo/deerflow-frontend-linux.tar.gz" -C "$stage" .
