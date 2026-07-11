#!/usr/bin/env bash
# SoloX 依赖安装 — 调用跨平台 Python 脚本
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${SOLOX_PYTHON:-python3}"
if ! command -v "$PYTHON" &>/dev/null 2>&1; then
    PYTHON=python
fi
exec "$PYTHON" "$SCRIPT_DIR/install_dependencies.py" --user "$@"
