#!/usr/bin/env bash
set -euo pipefail
# Run as root after extracting the source bundle into /opt/dbgpt-commerce.
APP=/opt/dbgpt-commerce
UV=/opt/deerflow-tools/bin/uv
export UV_PYTHON_INSTALL_DIR=/opt/dbgpt-python
export UV_CONCURRENT_DOWNLOADS=4 UV_CONCURRENT_BUILDS=1 UV_CONCURRENT_INSTALLS=1
export UV_DEFAULT_INDEX="${UV_DEFAULT_INDEX:-https://mirrors.aliyun.com/pypi/simple}"
"$UV" python install 3.11
if [ ! -x "$APP/.official-venv/bin/python" ]; then
 "$UV" venv --python 3.11 "$APP/.official-venv"
fi
# Linux lock additionally pins the platform-specific uvloop dependency.
"$UV" pip install --python "$APP/.official-venv/bin/python" -r "$APP/official-requirements-linux.lock"
for package in dbgpt-core dbgpt-ext dbgpt-client dbgpt-serve dbgpt-sandbox dbgpt-accelerator/dbgpt-acc-auto dbgpt-app; do
 "$UV" pip install --python "$APP/.official-venv/bin/python" --no-deps "$APP/vendor/DB-GPT/packages/$package"
done
