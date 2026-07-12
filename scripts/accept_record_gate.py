#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Android 录屏发版门禁核心逻辑（P2-T2）。

供 ``accept_record_e2e.py``、``accept_record.sh`` / ``accept_record.ps1`` 及
``release_gate`` 可选第 4 步调用。纯校验函数可单测；完整 E2E 需 SoloX 服务 +
adb 真机。

环境变量（可选）::

    SOLOX_BASE          SoloX URL，默认 http://127.0.0.1:50003
    SOLOX_DEVICE_ID     设备 serial；未设则取 adb 第一台
    SOLOX_RECORD_PKG    验收包名
    SOLOX_RECORD_DURATION  录屏秒数，默认 65
    SOLOX_RECORD_MIN_DURATION  validate-only 最小时长，默认 55
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PKG = "com.lyjz.chqsy.vivo"
DEFAULT_BASE = "http://127.0.0.1:50003"


def configure_utf8_stdout() -> None:
    """避免 Windows CP1252 输出中文失败。"""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass


def list_android_device_ids(adb_cmd: list[str] | None = None) -> list[str]:
    """返回 ``adb devices`` 中状态为 device 的 serial 列表。"""
    cmd = adb_cmd or ["adb", "devices"]
    out = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    device_ids: list[str] = []
    for line in out.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            device_ids.append(parts[0])
    return device_ids


def resolve_device_id(device_id: str | None) -> str:
    """解析设备 ID；``auto`` 或空则取第一台已连接设备。"""
    if device_id and device_id not in ("auto", ""):
        return device_id
    devices = list_android_device_ids()
    if not devices:
        raise RuntimeError("无已连接的 Android 设备（adb devices）")
    return devices[0]


def ffprobe_duration(path: Path) -> float | None:
    """返回视频时长（秒）；无 ffprobe 时返回 None。"""
    candidates: list[list[str]] = [
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
    ]
    bundled = ROOT / "solox" / "public" / "ffmpeg" / "bin" / "ffprobe.exe"
    if bundled.is_file():
        candidates.append(
            [
                str(bundled), "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
        )
    for cmd in candidates:
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30,
            )
            if out.returncode == 0 and out.stdout.strip():
                return float(out.stdout.strip())
        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            continue
    return None


def validate_record_file(
    path: str | Path,
    min_duration_sec: float = 55.0,
) -> dict[str, Any]:
    """校验录屏文件是否可用于发版（moov + 可选 ffprobe 时长）。

    :param path: ``record.mp4`` 或 ``record.mkv`` 路径。
    :param min_duration_sec: ffprobe 可用时的最短 acceptable 时长。
    :return: 含 ``passed`` / ``valid`` / ``format`` / ``duration_sec`` 等。
    """
    from solox.public.common import File

    video_path = Path(path)
    if not video_path.is_file():
        return {
            "passed": False,
            "valid": False,
            "path": str(video_path),
            "format": None,
            "duration_sec": None,
            "reason": "file_not_found",
        }

    fmt = video_path.suffix.lstrip(".").lower() or "mp4"
    if fmt not in ("mp4", "mkv"):
        fmt = "mp4"
    valid = File._is_valid_record_file(str(video_path), fmt)
    duration_sec = ffprobe_duration(video_path) if valid else None

    passed = valid
    reason = "ok" if valid else "invalid_container"
    if passed and duration_sec is not None:
        if duration_sec < min_duration_sec:
            passed = False
            reason = "duration_too_short"

    return {
        "passed": passed,
        "valid": valid,
        "path": str(video_path.resolve()),
        "format": fmt,
        "duration_sec": duration_sec,
        "min_duration_sec": min_duration_sec,
        "reason": reason,
    }


def http_get(
    base: str,
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """GET JSON API。"""
    query = urllib.parse.urlencode(params or {})
    url = f"{base.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_health(base: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data = http_get(base, "/health")
            if data.get("status") == 1:
                return
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"SoloX 未在 {base} 就绪")


def adb(*args: str, device_id: str) -> str:
    cmd = ["adb", "-s", device_id, *args]
    out = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if out.returncode != 0:
        raise RuntimeError(f"adb 失败: {' '.join(cmd)}\n{out.stderr}")
    return out.stdout.strip()


def launch_app(device_id: str, package: str) -> None:
    adb(
        "shell", "monkey", "-p", package,
        "-c", "android.intent.category.LAUNCHER", "1",
        device_id=device_id,
    )


def device_label(device_id: str) -> str:
    model = adb("shell", "getprop", "ro.product.model", device_id=device_id)
    return f"{device_id}({model})"


def find_latest_report_scene(report_dir: Path) -> str | None:
    candidates = [
        p for p in report_dir.iterdir()
        if p.is_dir() and p.name.startswith("apm_")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime).name


def run_acceptance(
    base: str,
    device_id: str,
    package: str,
    duration: int,
    quality: str,
) -> dict[str, Any]:
    """执行录屏 E2E（与 Web UI 相同 REST 路径）。"""
    from solox.public.common import File

    wait_health(base)
    devices_resp = http_get(base, "/device/info", {"platform": "Android"})
    if devices_resp.get("status") != 1:
        raise RuntimeError(f"无 Android 设备: {devices_resp}")

    device = device_label(device_id)
    android_release = adb(
        "shell", "getprop", "ro.build.version.release", device_id=device_id,
    )

    print(f"▶ 设备: {device}  Android {android_release}")
    print(f"▶ 包名: {package}  画质: {quality}  时长: {duration}s")

    http_get(base, "/apm/initialize")
    launch_app(device_id, package)
    time.sleep(3)

    start = http_get(
        base, "/apm/record/start",
        {"platform": "Android", "device": device, "quality": quality},
    )
    if start.get("status") != 1:
        raise RuntimeError(f"录屏启动失败: {start}")

    print("▶ 录屏中…")
    t0 = time.time()
    while time.time() - t0 < duration:
        st = http_get(base, "/apm/record/status")
        print(
            f"   … {st.get('elapsed_seconds', 0)}s  "
            f"healthy={st.get('healthy', False)}",
            flush=True,
        )
        time.sleep(5)

    report_dir_before = set(Path(File().report_dir).glob("apm_*"))
    save = http_get(
        base, "/apm/create/report",
        {
            "platform": "Android",
            "model": "normal",
            "app": package,
            "devices": device,
            "wifi_switch": "false",
            "process": "",
            "record_switch": "true",
            "thermal_switch": "false",
            "cores": "8",
        },
        timeout=max(180.0, duration + 120.0),
    )
    if save.get("status") != 1:
        raise RuntimeError(f"保存报告失败: {save}")

    report_root = Path(File().report_dir)
    new_dirs = [p for p in report_root.glob("apm_*") if p not in report_dir_before]
    scene = new_dirs[0].name if new_dirs else find_latest_report_scene(report_root)
    if not scene:
        raise RuntimeError("未找到新报告目录")

    report_path = report_root / scene
    mp4 = report_path / "record.mp4"
    mkv = report_path / "record.mkv"
    video_info = File().resolve_record_video(scene)

    check = validate_record_file(
        mp4 if mp4.is_file() else mkv,
        min_duration_sec=max(55.0, duration - 10),
    )
    stream_ok = False
    if check["valid"] and mp4.is_file():
        try:
            info = http_get(base, "/apm/record/info", {"scene": scene})
            stream_ok = info.get("status") == 1
        except urllib.error.HTTPError:
            stream_ok = False

    result_meta: dict[str, Any] = {}
    result_path = report_path / "result.json"
    if result_path.is_file():
        result_meta = json.loads(result_path.read_text(encoding="utf-8"))

    return {
        "passed": check["passed"] and stream_ok,
        "device_id": device_id,
        "device": device,
        "android_release": android_release,
        "package": package,
        "quality": quality,
        "requested_duration_sec": duration,
        "scene": scene,
        "video_path": check.get("path"),
        "video_format": video_info.get("format") if video_info else check.get("format"),
        "valid": check["valid"],
        "ffprobe_duration_sec": check.get("duration_sec"),
        "stream_api_ok": stream_ok,
        "result_video_flag": result_meta.get("video"),
        "record_error": result_meta.get("record_error", ""),
        "base_url": base,
        "reason": check.get("reason"),
    }


def should_run_record_accept(env: dict[str, str] | None = None) -> bool:
    """release gate 是否在环境变量启用录屏验收。"""
    env = env or os.environ
    return env.get("SOLOX_RECORD_ACCEPT", "").strip() == "1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Android 录屏发版门禁")
    parser.add_argument(
        "--validate-only",
        metavar="PATH",
        help="仅校验已有 record.mp4/mkv（不发 E2E）",
    )
    parser.add_argument(
        "--min-duration", type=float,
        default=float(os.environ.get("SOLOX_RECORD_MIN_DURATION", "55")),
    )
    parser.add_argument("--base", default=os.environ.get("SOLOX_BASE", DEFAULT_BASE))
    parser.add_argument(
        "--device-id",
        default=os.environ.get("SOLOX_DEVICE_ID", "auto"),
    )
    parser.add_argument(
        "--package",
        default=os.environ.get("SOLOX_RECORD_PKG", DEFAULT_PKG),
    )
    parser.add_argument(
        "--duration", type=int,
        default=int(os.environ.get("SOLOX_RECORD_DURATION", "65")),
    )
    parser.add_argument(
        "--quality", default="720p", choices=["1080p", "720p", "480p"],
    )
    parser.add_argument("--json-out", help="将结果写入 JSON 文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdout()
    args = build_parser().parse_args(argv)

    try:
        if args.validate_only:
            result = validate_record_file(
                args.validate_only, min_duration_sec=args.min_duration,
            )
        else:
            device_id = resolve_device_id(args.device_id)
            result = run_acceptance(
                args.base, device_id, args.package, args.duration, args.quality,
            )
    except Exception as exc:
        print(f"❌ 录屏验收失败: {exc}")
        return 1

    print("\n========== 验收结果 ==========")
    for key, val in result.items():
        print(f"  {key}: {val}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if result.get("passed"):
        print("\n✅ Android 录屏验收通过")
        return 0
    print("\n❌ Android 录屏验收未通过")
    return 1


if __name__ == "__main__":
    sys.exit(main())
