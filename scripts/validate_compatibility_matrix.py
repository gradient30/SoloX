#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate compatibility matrix before release. Exit 0 = pass, 1 = fail."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tests.matrix_loader import _L1_TEST_MODULES, load_matrix, validate_release_readiness  # noqa: E402


def configure_utf8_stdout() -> None:
    """将可重配置的标准输出切换为 UTF-8，避免旧 Windows 代码页编码失败。

    GitHub Actions 的 Windows Python runner 可能以 CP1252 编码标准输出，
    而本脚本输出中文和状态图标。统一使用 UTF-8 可避免在校验逻辑执行前触发
    :class:`UnicodeEncodeError`；无法重配置的自定义输出流保持原状。
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass


def main() -> int:
    """校验兼容矩阵并返回适用于 CI 的退出码。"""
    configure_utf8_stdout()
    print('正在校验兼容矩阵（结构 + 文档 + L1 测试映射）…')
    try:
        data = load_matrix()
    except Exception as exc:
        print(f'❌ 无法加载矩阵: {exc}')
        return 1

    errors = validate_release_readiness(data)
    if errors:
        print('❌ 兼容矩阵校验失败:')
        for err in errors:
            print(f'  - {err}')
        return 1

    print('✅ 兼容矩阵校验通过')
    print(f'  发版门禁: {data["release_gate"]}')
    print(f'  Android P0 API: {[e["api"] for e in data["android"]["P0"]["entries"]]}')
    print(f'  iOS P0 版本: {[e["version"] for e in data["ios"]["P0"]["entries"]]}')
    print(f'  L1 测试模块: {len(_L1_TEST_MODULES)} 个（见 tests/test_joint_acceptance.py）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
