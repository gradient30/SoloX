# -*- coding: utf-8 -*-
"""Helpers for resolving Android/Rust toolchain paths in tests."""

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def project_toolchain_root() -> Path:
    return ROOT / 'runtime' / 'android-toolchain'


def default_shared_toolchain_root() -> Path | None:
    local_appdata = os.environ.get('LOCALAPPDATA')
    if not local_appdata:
        return None
    return Path(local_appdata) / 'SoloX' / 'toolchains' / 'android-rust'


def configured_shared_toolchain_root() -> Path | None:
    override = os.environ.get('SOLOX_SHARED_TOOLROOT')
    if override:
        return Path(override)
    return default_shared_toolchain_root()


def toolchain_has_required_layout(tool_root: Path | None) -> bool:
    if tool_root is None:
        return False
    java_executable = 'java.exe' if os.name == 'nt' else 'java'
    required = (
        tool_root / 'jdk-stage' / 'jdk-17.0.19+10' / 'bin' / java_executable,
        tool_root / 'android-sdk' / 'build-tools' / '36.0.0',
    )
    return all(path.exists() for path in required)


def resolve_test_toolchain_root() -> Path:
    shared_root = configured_shared_toolchain_root()
    if toolchain_has_required_layout(shared_root):
        return shared_root
    return project_toolchain_root()


def resolve_test_java_executable(name: str) -> Path:
    executable = f'{name}.exe' if os.name == 'nt' else name
    return (
        resolve_test_toolchain_root()
        / 'jdk-stage'
        / 'jdk-17.0.19+10'
        / 'bin'
        / executable
    )


def java_test_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault('JAVA_TOOL_OPTIONS', '-Xms32m -Xmx128m')
    return env