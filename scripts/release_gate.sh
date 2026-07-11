#!/usr/bin/env bash
# SoloX 发版门禁 — 与 CI 核心步骤对齐（setup 校验 + 兼容矩阵 + 全量测试）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON="${SOLOX_PYTHON:-python}"

echo "========================================"
echo " SoloX 发版门禁"
echo "========================================"

echo ""
echo "▶ [1/3] 校验 setup.py 依赖版本"
"$PYTHON" scripts/verify_setup.py

echo ""
echo "▶ [2/3] 校验兼容矩阵"
"$PYTHON" scripts/validate_compatibility_matrix.py

echo ""
echo "▶ [3/3] 运行全量测试"
"$PYTHON" -m pytest tests/ -q --disable-warnings --tb=short

echo ""
echo "✅ 发版门禁通过"
