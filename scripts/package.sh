#!/usr/bin/env bash
# 构建 sdist + wheel（在仓库根目录执行）
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${SOLOX_PYTHON:-python3}"
if ! command -v "$PYTHON" &>/dev/null 2>&1; then
    PYTHON=python
fi

echo "🏗️  SoloX 打包"
echo "项目目录: $ROOT"
echo ""

echo "▶ 清理旧构建产物 …"
rm -rf build dist solox.egg-info

echo "▶ 安装构建工具 …"
"$PYTHON" -m pip install --upgrade pip build twine

echo "▶ 构建 sdist 与 wheel …"
"$PYTHON" -m build

echo ""
echo "✅ 打包完成，产物位于 dist/"
ls -la dist/ 2>/dev/null || dir dist 2>/dev/null || true
