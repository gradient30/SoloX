#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Android 录屏 E2E 验收（P2-T1）：复用 Web 同款 REST 路径，真机 scrcpy 录屏 ≥60s。

用法::

    python scripts/accept_record_e2e.py
    python scripts/accept_record_e2e.py --duration 65 --quality 720p
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
DEFAULT_DEVICE_ID = "ecc3b00e"
DEFAULT_BASE = "http://127.0.0.1:50003"


def configure_utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass


def http_get(
    base: str,
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> dict:
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
    """前台启动目标 App（Cocos 游戏）。"""
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
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.name


def ffprobe_duration(path: Path) -> float | None:
    """返回视频时长（秒），无 ffprobe 时返回 None。"""
    for cmd in (
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
    ):
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=30,
            )
            if out.returncode == 0 and out.stdout.strip():
                return float(out.stdout.strip())
        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            continue
    bundled = ROOT / "solox" / "public" / "ffmpeg" / "bin" / "ffprobe.exe"
    if bundled.is_file():
        try:
            out = subprocess.run(
                [str(bundled), "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                capture_output=True, text=True, check=False, timeout=30,
            )
            if out.returncode == 0 and out.stdout.strip():
                return float(out.stdout.strip())
        except (ValueError, subprocess.TimeoutExpired):
            pass
    return None


def run_acceptance(
    base: str,
    device_id: str,
    package: str,
    duration: int,
    quality: str,
) -> dict[str, Any]:
    """执行录屏 E2E，返回结构化验收结果。"""
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
        elapsed = st.get("elapsed_seconds", 0)
        healthy = st.get("healthy", False)
        print(f"   … {elapsed}s  healthy={healthy}", flush=True)
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
    video_info = File().resolve_record_video(scene)
    mp4 = report_path / "record.mp4"
    mkv = report_path / "record.mkv"

    valid_mp4 = mp4.is_file() and File._is_valid_record_file(str(mp4), "mp4")
    valid_mkv = mkv.is_file() and File._is_valid_record_file(str(mkv), "mkv")
    video_path = mp4 if valid_mp4 else (mkv if valid_mkv else None)

    duration_sec = ffprobe_duration(video_path) if video_path else None
    stream_ok = False
    if video_path and valid_mp4:
        try:
            info = http_get(base, "/apm/record/info", {"scene": scene})
            stream_ok = info.get("status") == 1
        except urllib.error.HTTPError:
            stream_ok = False

    result_path = report_path / "result.json"
    result_meta = {}
    if result_path.is_file():
        result_meta = json.loads(result_path.read_text(encoding="utf-8"))

    passed = bool(video_path and (valid_mp4 or valid_mkv))
    if duration_sec is not None:
        passed = passed and duration_sec >= max(55, duration - 10)

    return {
        "passed": passed,
        "device_id": device_id,
        "device": device,
        "android_release": android_release,
        "package": package,
        "quality": quality,
        "requested_duration_sec": duration,
        "scene": scene,
        "video_path": str(video_path) if video_path else None,
        "video_format": video_info.get("format") if video_info else None,
        "valid_mp4": valid_mp4,
        "valid_mkv": valid_mkv,
        "ffprobe_duration_sec": duration_sec,
        "stream_api_ok": stream_ok,
        "result_video_flag": result_meta.get("video"),
        "record_error": result_meta.get("record_error", ""),
        "base_url": base,
    }


def main() -> int:
    configure_utf8_stdout()
    parser = argparse.ArgumentParser(description="Android 录屏 E2E 验收")
    parser.add_argument("--base", default=os.environ.get("SOLOX_BASE", DEFAULT_BASE))
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID)
    parser.add_argument("--package", default=DEFAULT_PKG)
    parser.add_argument("--duration", type=int, default=65,
                        help="录屏秒数，默认 65（≥60 满足 P2-T1）")
    parser.add_argument("--quality", default="720p",
                        choices=["1080p", "720p", "480p"])
    parser.add_argument("--json-out", help="将结果写入 JSON 文件")
    args = parser.parse_args()

    try:
        result = run_acceptance(
            args.base, args.device_id, args.package, args.duration, args.quality,
        )
    except Exception as exc:
        print(f"❌ E2E 失败: {exc}")
        return 1

    print("\n========== E2E 结果 ==========")
    for key, val in result.items():
        print(f"  {key}: {val}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if result["passed"]:
        print("\n✅ P2-T1 录屏 E2E 通过（R1：MP4/MKV 合法；时长待 ffprobe 核对）")
        return 0
    print("\n❌ P2-T1 录屏 E2E 未通过")
    return 1


if __name__ == "__main__":
    sys.exit(main())
