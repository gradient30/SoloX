#!/usr/bin/env bash
# SoloX release gate — matrix validation + full pytest (local CI mirror)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON="${SOLOX_PYTHON:-python}"

echo "==> [1/2] validate_compatibility_matrix"
"$PYTHON" scripts/validate_compatibility_matrix.py

echo "==> [2/2] pytest tests/"
"$PYTHON" -m pytest tests/ -q --disable-warnings --tb=short

echo "OK: release gate passed"
