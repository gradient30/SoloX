#!/usr/bin/env bash
# Android 录屏真机验收 — 供 release_gate 可选第 4 步或单独执行
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON="${SOLOX_PYTHON:-python}"

echo "========================================"
echo " Android 录屏真机验收"
echo "========================================"

if ! command -v adb >/dev/null 2>&1; then
  echo "❌ 未找到 adb，请先安装 Android platform-tools"
  exit 1
fi

DEVICE_COUNT="$("$PYTHON" -c "
import sys
sys.path.insert(0, 'scripts')
from accept_record_gate import list_android_device_ids
print(len(list_android_device_ids()))
")"

if [[ "$DEVICE_COUNT" -lt 1 ]]; then
  echo "❌ 无已连接的 Android 设备（adb devices）"
  exit 1
fi

echo "▶ 已连接 Android 设备数: $DEVICE_COUNT"
echo "▶ 请确保 SoloX 已启动（默认 http://127.0.0.1:50003）"
echo ""

exec "$PYTHON" scripts/accept_record_gate.py "$@"
