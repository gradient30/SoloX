#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate compatibility matrix before release. Exit 0 = pass, 1 = fail."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tests.matrix_loader import _L1_TEST_MODULES, load_matrix, validate_release_readiness  # noqa: E402


def main() -> int:
    print('Validating compatibility matrix (schema + docs + L1 tests) ...')
    try:
        data = load_matrix()
    except Exception as exc:
        print(f'FAIL: cannot load matrix: {exc}')
        return 1

    errors = validate_release_readiness(data)
    if errors:
        print('FAIL: release readiness validation errors:')
        for err in errors:
            print(f'  - {err}')
        return 1

    print('OK: release readiness validation passed')
    print(f'  release_gate: {data["release_gate"]}')
    print(f'  android P0 APIs: {[e["api"] for e in data["android"]["P0"]["entries"]]}')
    print(f'  ios P0 versions: {[e["version"] for e in data["ios"]["P0"]["entries"]]}')
    print(f'  L1 test modules: {len(_L1_TEST_MODULES)} (see tests/test_joint_acceptance.py)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
