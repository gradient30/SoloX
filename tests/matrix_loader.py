# -*- coding: utf-8 -*-
"""Load and validate tests/compatibility_matrix.yaml for CI and release gate checks."""

from __future__ import annotations

import os
from typing import Any

_MATRIX_PATH = os.path.join(os.path.dirname(__file__), 'compatibility_matrix.yaml')

_REQUIRED_ROOT_KEYS = (
    'schema_version',
    'release_gate',
    'google_play',
    'android',
    'ios',
    'metrics',
    'surface_fixtures',
)

_ANDROID_PRIORITIES = ('P0', 'P1', 'P2', 'P3')
_IOS_PRIORITIES = ('P0', 'P1', 'P2', 'P3')

_P0_ANDROID_APIS = {33, 34, 35, 36}
_P0_IOS_VERSIONS = {'18', '26'}


def _load_yaml(path: str) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(
            'PyYAML is required to load compatibility_matrix.yaml. '
            'Install with: pip install pyyaml'
        ) from exc
    with open(path, encoding='utf-8') as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError('compatibility_matrix.yaml root must be a mapping')
    return data


def load_matrix(path: str | None = None) -> dict[str, Any]:
    """Load compatibility matrix from YAML."""
    return _load_yaml(path or _MATRIX_PATH)


def _validate_platform_block(block: dict[str, Any], platform: str) -> list[str]:
    errors: list[str] = []
    priorities = _ANDROID_PRIORITIES if platform == 'android' else _IOS_PRIORITIES
    for priority in priorities:
        if priority not in block:
            errors.append(f'{platform}.{priority} is missing')
            continue
        tier_block = block[priority]
        if 'entries' not in tier_block or not tier_block['entries']:
            errors.append(f'{platform}.{priority}.entries must be non-empty')
            continue
        for idx, entry in enumerate(tier_block['entries']):
            prefix = f'{platform}.{priority}.entries[{idx}]'
            if platform == 'android':
                if 'api' not in entry:
                    errors.append(f'{prefix} missing api')
                if 'release' not in entry:
                    errors.append(f'{prefix} missing release')
            else:
                if 'version' not in entry:
                    errors.append(f'{prefix} missing version')
                if 'device' not in entry:
                    errors.append(f'{prefix} missing device')
            if 'tier' not in entry:
                errors.append(f'{prefix} missing tier')
    return errors


def validate_matrix(data: dict[str, Any] | None = None) -> list[str]:
    """Return list of validation errors; empty list means valid."""
    if data is None:
        data = load_matrix()
    errors: list[str] = []

    for key in _REQUIRED_ROOT_KEYS:
        if key not in data:
            errors.append(f'missing root key: {key}')

    if errors:
        return errors

    if data['release_gate'] != 'P0_all_pass':
        errors.append('release_gate must be P0_all_pass')

    gp = data.get('google_play', {})
    if gp.get('target_api_min') != 35:
        errors.append('google_play.target_api_min must be 35 for 2026 Play policy')

    errors.extend(_validate_platform_block(data['android'], 'android'))
    errors.extend(_validate_platform_block(data['ios'], 'ios'))

    p0_android_apis = {
        e['api'] for e in data['android']['P0']['entries']
    }
    missing_p0 = _P0_ANDROID_APIS - p0_android_apis
    if missing_p0:
        errors.append(f'android.P0 missing required APIs: {sorted(missing_p0)}')

    p0_ios_versions = {
        str(e['version']) for e in data['ios']['P0']['entries']
    }
    missing_ios = _P0_IOS_VERSIONS - p0_ios_versions
    if missing_ios:
        errors.append(f'ios.P0 missing required versions: {sorted(missing_ios)}')

    fixtures = data.get('surface_fixtures', {})
    for name in ('api_28_30', 'api_31_33', 'api_34_36'):
        if name not in fixtures:
            errors.append(f'surface_fixtures.{name} is missing')
        elif not fixtures[name].get('surfaces'):
            errors.append(f'surface_fixtures.{name}.surfaces must be non-empty')

    fps_apis = set(data.get('metrics', {}).get('fps', {}).get('l1_mock_apis', []))
    if not {28, 30, 31, 34, 36}.issubset(fps_apis):
        errors.append('metrics.fps.l1_mock_apis must cover 28, 30, 31, 34, 36')

    return errors


def get_android_entries(priority: str, data: dict[str, Any] | None = None) -> list[dict]:
    matrix = data or load_matrix()
    return list(matrix['android'][priority]['entries'])


def get_ios_entries(priority: str, data: dict[str, Any] | None = None) -> list[dict]:
    matrix = data or load_matrix()
    return list(matrix['ios'][priority]['entries'])


def get_surface_fixtures(data: dict[str, Any] | None = None) -> dict[str, Any]:
    matrix = data or load_matrix()
    return dict(matrix['surface_fixtures'])


_DOCS_PATH = os.path.join(os.path.dirname(__file__), '..', 'docs', 'compatibility-matrix.md')

_L1_TEST_MODULES = (
    'test_fps_calculation.py',
    'test_surface_by_api.py',
    'test_apm_cpu_memory.py',
    'test_apm_collect_api.py',
    'test_compatibility_matrix.py',
    'test_metric_stats.py',
    'test_report_management.py',
    'test_record_player.py',
    'test_weak_network.py',
    'test_joint_acceptance.py',
)


def validate_docs_consistency(
    data: dict[str, Any] | None = None,
    docs_path: str | None = None,
) -> list[str]:
    """Cross-check docs/compatibility-matrix.md against matrix YAML."""
    if data is None:
        data = load_matrix()
    path = docs_path or _DOCS_PATH
    errors: list[str] = []

    if not os.path.isfile(path):
        return [f'missing docs file: {path}']

    with open(path, encoding='utf-8') as fh:
        content = fh.read()

    if data['release_gate'] not in content:
        errors.append(f'docs missing release_gate: {data["release_gate"]}')

    target_api = data['google_play'].get('target_api_min')
    if str(target_api) not in content:
        errors.append(f'docs must mention Google Play target API {target_api}')

    for entry in data['android']['P0']['entries']:
        api = entry['api']
        if str(api) not in content:
            errors.append(f'docs missing android P0 API {api}')

    for entry in data['ios']['P0']['entries']:
        version = str(entry['version'])
        if f'iOS {version}' not in content and f'**{version}**' not in content:
            errors.append(f'docs missing ios P0 version {version}')

    tests_dir = os.path.dirname(__file__)
    for mod in _L1_TEST_MODULES:
        if not os.path.isfile(os.path.join(tests_dir, mod)):
            errors.append(f'missing L1 test module: tests/{mod}')

    return errors


def validate_release_readiness(data: dict[str, Any] | None = None) -> list[str]:
    """Full release-gate validation: schema + docs + L1 test modules."""
    if data is None:
        data = load_matrix()
    errors = validate_matrix(data)
    errors.extend(validate_docs_consistency(data))
    return errors
