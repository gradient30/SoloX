# -*- coding: utf-8 -*-
"""Cross-platform output tests for the setup dependency verifier."""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_SETUP_SCRIPT = ROOT / "scripts" / "verify_setup.py"
VALIDATE_MATRIX_SCRIPT = ROOT / "scripts" / "validate_compatibility_matrix.py"


def test_verify_setup_supports_legacy_cp1252_stdout() -> None:
    """验证脚本在旧 Windows CP1252 标准输出环境中仍可成功运行。"""
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [sys.executable, str(VERIFY_SETUP_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_matrix_validator_supports_legacy_cp1252_stdout() -> None:
    """兼容矩阵校验脚本在旧 Windows CP1252 输出环境中应可成功运行。"""
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [sys.executable, str(VALIDATE_MATRIX_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
