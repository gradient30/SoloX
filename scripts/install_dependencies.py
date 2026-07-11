#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SoloX 依赖安装（跨平台，供 install_dependencies.sh / .ps1 调用）。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"

CRITICAL_IMPORTS = (
    ("fire", "Fire"),
    ("logzero", "LogZero"),
    ("pyfiglet", "PyFiglet"),
    ("psutil", "PSUtil"),
    ("flask", "Flask"),
    ("werkzeug", "Werkzeug"),
    ("flask_socketio", "Flask-SocketIO"),
    ("tidevice", "tidevice"),
    ("cv2", "OpenCV"),
    ("requests", "Requests"),
)


def _run(cmd: list[str], *, label: str) -> None:
    print(f"▶ {label}")
    print(f"  {' '.join(cmd)}")
    subprocess.check_call(cmd)


def _check_python(min_version: tuple[int, int] = (3, 10)) -> None:
    major, minor = sys.version_info[:2]
    if (major, minor) < min_version:
        need = f"{min_version[0]}.{min_version[1]}"
        got = f"{major}.{minor}"
        print(f"❌ Python 版本过低: {got}（需要 >= {need}）")
        print("   请升级: https://www.python.org/downloads/")
        raise SystemExit(1)
    print(f"✅ Python 版本: {major}.{minor} ({sys.executable})")


def _verify_imports() -> None:
    print("\n🔍 验证已安装依赖 …")
    ok = 0
    for module, name in CRITICAL_IMPORTS:
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "")
            suffix = f" v{version}" if version else ""
            print(f"   ✅ {name}{suffix}")
            ok += 1
        except ImportError:
            print(f"   ❌ {name} — 未安装或导入失败")
    total = len(CRITICAL_IMPORTS)
    print(f"\n依赖检查结果: {ok}/{total} 通过")
    if ok != total:
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="安装 SoloX 项目依赖")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="同时安装开发/测试依赖（pip install -e \".[dev,test]\"）",
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="使用 pip --user 安装（旧脚本兼容）",
    )
    args = parser.parse_args()

    print("🚀 SoloX 依赖安装")
    print("=" * 40)
    _check_python()

    pip = [sys.executable, "-m", "pip"]
    user_flag = ["--user"] if args.user else []

    _run(pip + ["install", "--upgrade", "pip", *user_flag], label="升级 pip")
    if not REQUIREMENTS.is_file():
        print(f"❌ 未找到 {REQUIREMENTS}")
        return 1
    _run(
        pip + ["install", *user_flag, "-r", str(REQUIREMENTS)],
        label="安装 requirements.txt",
    )
    if args.dev:
        _run(
            pip + ["install", *user_flag, "-e", f"{ROOT}[dev,test]"],
            label="安装开发/测试依赖",
        )

    _verify_imports()

    print("\n🎉 依赖安装完成")
    print("\n下一步:")
    print("  1. 连接 Android 设备并开启 USB 调试")
    print("  2. 启动: python -m solox")
    print("     或: .\\scripts\\dev.ps1 start   (Windows)")
    print("     或: bash scripts/dev.sh start")
    print("  3. 打开: http://127.0.0.1:50003/?platform=Android&lan=cn")
    print("\n故障排除: docs/05-issues/troubleshooting.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
