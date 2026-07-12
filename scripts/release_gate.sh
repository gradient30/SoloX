#!/usr/bin/env bash
# SoloX 发版门禁 — 与 CI 核心步骤对齐（setup 校验 + 兼容矩阵 + 全量测试）
# 可选第 4 步：SOLOX_RECORD_ACCEPT=1 时跑 Android 录屏真机验收
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON="${SOLOX_PYTHON:-python}"
RECORD_ACCEPT="${SOLOX_RECORD_ACCEPT:-0}"
TOTAL=3
if [[ "$RECORD_ACCEPT" == "1" ]]; then
  TOTAL=4
fi

echo "========================================"
echo " SoloX 发版门禁"
echo "========================================"

echo ""
echo "▶ [1/${TOTAL}] 校验 pyproject.toml 依赖版本"
"$PYTHON" scripts/verify_setup.py

echo ""
echo "▶ [2/${TOTAL}] 校验兼容矩阵"
"$PYTHON" scripts/validate_compatibility_matrix.py

echo ""
echo "▶ [3/${TOTAL}] 运行全量测试"
"$PYTHON" -m pytest tests/ -q --disable-warnings --tb=short

if [[ "$RECORD_ACCEPT" == "1" ]]; then
  echo ""
  echo "▶ [4/${TOTAL}] Android 录屏真机验收（SOLOX_RECORD_ACCEPT=1）"
  bash scripts/accept_record.sh
else
  echo ""
  echo "ℹ️  跳过录屏真机验收（动过录屏链路时请: SOLOX_RECORD_ACCEPT=1 bash scripts/release_gate.sh）"
fi

echo ""
echo "✅ 发版门禁通过"
