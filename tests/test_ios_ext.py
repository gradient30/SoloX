# -*- coding: utf-8 -*-
"""iOS 扩展后端（solox.public.ios_ext）单元测试。

pymobiledevice3 9.x 为异步 API，本套测试以 AsyncMock/异步上下文管理器 mock 验证
逻辑与调用契约，不依赖真机；真机联通性属"待验收"，见
docs/plans/2026-07-11-ios-pmd3-backend.md。
"""

from __future__ import annotations

import contextlib
import time
from types import SimpleNamespace
from unittest import mock

import pytest

# 本套测试通过 mock.patch 直接替换 pymobiledevice3.* 子模块，需要该可选依赖
# 可导入；CI/未安装 solox[ios] 的环境无此包，整体跳过（核心功能不受影响）。
pytest.importorskip(
    "pymobiledevice3",
    reason="未安装可选依赖 pymobiledevice3（solox[ios]），跳过 iOS 扩展后端测试",
)

from solox.public import ios_ext  # noqa: E402
from solox.public.ios_ext import device, frametime, screen, weaknet  # noqa: E402


@contextlib.asynccontextmanager
async def _fake_dvt(*_args, **_kwargs):
    """伪造的 DVT 异步上下文管理器。"""
    yield mock.MagicMock(name="dvt")


def _async_inducer(**kwargs):
    """构造一个 connect/list/set/clear 均为 AsyncMock 的 ConditionInducer。"""
    inducer = mock.MagicMock(name="ConditionInducer")
    inducer.connect = mock.AsyncMock()
    inducer.list = mock.AsyncMock(return_value=kwargs.get("list", []))
    inducer.set = mock.AsyncMock()
    inducer.clear = mock.AsyncMock()
    return inducer


def _patch_inducer(instance):
    return mock.patch(
        "pymobiledevice3.services.dvt.instruments."
        "condition_inducer.ConditionInducer",
        return_value=instance,
    )


# ---------------------------------------------------------------------------
# 能力探测
# ---------------------------------------------------------------------------
def test_capabilities_structure():
    caps = ios_ext.capabilities()
    assert caps["backend"] == "pymobiledevice3"
    assert set(caps["features"]) == {
        "device_link",
        "weaknet",
        "screenshot",
        "frametime",
    }
    assert all(v is caps["available"] for v in caps["features"].values())


def test_is_available_when_missing():
    with mock.patch("importlib.util.find_spec", return_value=None):
        assert ios_ext.is_available() is False


# ---------------------------------------------------------------------------
# A: device
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "version,expected",
    [("17.4.1", 17), ("16.0", 16), ("18", 18), (None, None), ("x", None)],
)
def test_parse_major(version, expected):
    assert device._parse_major(version) == expected


def test_needs_rsd():
    assert device.needs_rsd(17) is True
    assert device.needs_rsd(16) is False
    assert device.needs_rsd(None) is False


def test_list_devices_mocked():
    fake = [
        SimpleNamespace(serial="UDID-1", connection_type="USB"),
        SimpleNamespace(serial=None, connection_type="USB"),  # 应被跳过
    ]
    with mock.patch(
        "pymobiledevice3.usbmux.list_devices",
        new=mock.AsyncMock(return_value=fake),
    ):
        result = device.list_devices()
    assert result == [{"udid": "UDID-1", "connection_type": "USB"}]


def test_get_device_info_mocked():
    client = mock.MagicMock(spec=["all_values", "close"])
    client.all_values = {
        "ProductVersion": "17.5",
        "ProductType": "iPhone15,2",
        "DeviceName": "demo",
    }
    with mock.patch(
        "pymobiledevice3.lockdown.create_using_usbmux",
        new=mock.AsyncMock(return_value=client),
    ):
        info = device.get_device_info("UDID-1")
    assert info["product_version"] == "17.5"
    assert info["ios_major"] == 17
    assert info["product_type"] == "iPhone15,2"
    client.close.assert_called_once()


def test_require_pmd3_raises_when_unavailable():
    with mock.patch.object(ios_ext, "is_available", return_value=False):
        with pytest.raises(device.IOSBackendUnavailable):
            device._require_pmd3()


# ---------------------------------------------------------------------------
# B: weaknet（Condition Inducer）
# ---------------------------------------------------------------------------
def test_weaknet_list_profiles_filters_network():
    raw = [
        {
            "identifier": "SlowNetworkCondition",
            "name": "Network Link Conditioner",
            "isDestructive": False,
            "profiles": [
                {
                    "identifier": "3G-GoodNetwork",
                    "name": "3G, Good",
                    "description": "d",
                }
            ],
        },
        {
            "identifier": "ThermalCondition",
            "name": "Thermal State",
            "profiles": [],
        },
    ]
    inducer = _async_inducer(list=raw)
    with mock.patch.object(device, "dvt_session_async", _fake_dvt), \
            _patch_inducer(inducer):
        profiles = weaknet.IOSWeakNetManager.list_profiles("UDID-1")
    assert len(profiles) == 1
    assert profiles[0]["identifier"] == "SlowNetworkCondition"
    assert profiles[0]["profiles"][0]["identifier"] == "3G-GoodNetwork"


def test_weaknet_apply_and_clear_lifecycle():
    inducer = _async_inducer()
    with mock.patch.object(device, "dvt_session_async", _fake_dvt), \
            _patch_inducer(inducer):
        result = weaknet.IOSWeakNetManager.apply("UDID-2", "3G-GoodNetwork")
        assert result["active"] is True
        assert result["profile_identifier"] == "3G-GoodNetwork"
        status = weaknet.IOSWeakNetManager.status("UDID-2")
        assert status["active"] is True

        cleared = weaknet.IOSWeakNetManager.clear("UDID-2")
        assert cleared["active"] is False
    inducer.set.assert_awaited_once_with("3G-GoodNetwork")
    inducer.clear.assert_awaited_once()
    assert weaknet.IOSWeakNetManager.status("UDID-2")["active"] is False


def test_weaknet_apply_reports_worker_error():
    def _boom(*_a, **_k):
        raise RuntimeError("boom")

    with mock.patch.object(device, "dvt_session_async", _boom):
        with pytest.raises(RuntimeError, match="boom"):
            weaknet.IOSWeakNetManager.apply("UDID-3", "3G-GoodNetwork")
    assert weaknet.IOSWeakNetManager.status("UDID-3")["active"] is False


# ---------------------------------------------------------------------------
# C: screen
# ---------------------------------------------------------------------------
def test_take_screenshot_mocked():
    client = mock.MagicMock()
    service = mock.MagicMock()
    service.take_screenshot = mock.AsyncMock(return_value=b"PNGDATA")
    with mock.patch(
        "pymobiledevice3.lockdown.create_using_usbmux",
        new=mock.AsyncMock(return_value=client),
    ), mock.patch(
        "pymobiledevice3.services.screenshot.ScreenshotService",
        return_value=service,
    ):
        data = screen.take_screenshot("UDID-1")
    assert data == b"PNGDATA"
    service.take_screenshot.assert_awaited_once()


def test_save_screenshot(tmp_path):
    out = tmp_path / "shot.png"
    with mock.patch.object(
        screen, "take_screenshot", return_value=b"PNGDATA"
    ):
        path = screen.save_screenshot("UDID-1", str(out))
    assert path == str(out)
    assert out.read_bytes() == b"PNGDATA"


def _fake_open_service():
    service = mock.MagicMock()
    service.take_screenshot = mock.AsyncMock(return_value=b"PNGDATA")
    lockdown = mock.MagicMock()
    return mock.AsyncMock(return_value=(service, lockdown))


def test_screen_recorder_capture_and_assemble(tmp_path):
    out = tmp_path / "rec.mp4"
    frames_dir = tmp_path / "frames"
    calls = {"ffmpeg": 0}

    def _fake_run(cmd, **_kwargs):
        calls["ffmpeg"] += 1
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    with mock.patch.object(
        screen, "_open_screenshot_service", _fake_open_service()
    ), mock.patch.object(
        screen, "_find_ffmpeg", return_value="ffmpeg"
    ), mock.patch.object(screen.subprocess, "run", _fake_run):
        rec = screen.ScreenRecorder(
            "UDID-1", str(out), fps=20, frames_dir=str(frames_dir)
        )
        rec.start()
        time.sleep(0.3)
        result = rec.stop()

    assert result["frames"] >= 1
    assert result["assembled"] is True
    assert result["output"] == str(out)
    assert calls["ffmpeg"] == 1


def test_screen_recorder_no_ffmpeg(tmp_path):
    out = tmp_path / "rec.mp4"
    with mock.patch.object(
        screen, "_open_screenshot_service", _fake_open_service()
    ), mock.patch.object(screen, "_find_ffmpeg", return_value=""):
        rec = screen.ScreenRecorder(
            "UDID-1", str(out), fps=20,
            frames_dir=str(tmp_path / "f"),
        )
        rec.start()
        time.sleep(0.15)
        result = rec.stop()
    assert result["assembled"] is False
    assert "ffmpeg" in (result["error"] or "")


# ---------------------------------------------------------------------------
# D: frametime / Jank
# ---------------------------------------------------------------------------
def test_calculate_jank_smooth_60hz():
    rp = 1.0 / 60
    present = [i * rp for i in range(60)]
    result = frametime.calculate_jank(present, refresh_period=rp)
    assert result["jank"] == 0
    assert result["big_jank"] == 0
    assert result["fps"] == 60


def test_calculate_jank_detects_dropped_frames():
    rp = 1.0 / 60
    present = [i * rp for i in range(10)]
    present += [present[-1] + rp * 4]
    present += [present[-1] + rp * (j + 1) for j in range(10)]
    result = frametime.calculate_jank(present, refresh_period=rp)
    assert result["jank"] >= 1
    assert result["big_jank"] >= 1
    assert 0 <= result["stutter_rate"] <= 1


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_jank_parity_with_android(seed):
    """iOS 抖动算法须与 Android _calculate_jank_ex 完全一致。"""
    from solox.public.android_fps import SurfaceStatsCollector

    rp = 1.0 / 60
    import random

    rng = random.Random(seed)
    present = [0.0]
    for _ in range(40):
        step = rp * rng.choice([1, 1, 1, 2, 3, 4])
        present.append(present[-1] + step)

    triples = [[0.0, t, 0.0] for t in present]
    a_jank, a_big = SurfaceStatsCollector._calculate_jank_ex(
        None, triples, rp
    )
    i_jank, i_big = frametime._jank_ex(present, rp)
    assert (i_jank, i_big) == (a_jank, a_big)


def test_extract_present_times_with_matcher():
    events = [
        SimpleNamespace(name="CoreAnimation commit", timestamp=1.0),
        SimpleNamespace(name="unrelated", timestamp=1.5),
        SimpleNamespace(name="RenderServer present", timestamp=2.0),
    ]
    times = frametime.extract_present_times(events)
    assert times == [1.0, 2.0]


def test_extract_present_times_custom_matcher():
    events = [
        SimpleNamespace(debug_id=0xAA, timestamp=3.0),
        SimpleNamespace(debug_id=0xBB, timestamp=1.0),
    ]
    times = frametime.extract_present_times(
        events, matcher=lambda e: e.debug_id == 0xAA
    )
    assert times == [3.0]


def _patch_core_profile(events):
    tap = mock.MagicMock()
    tap.get_kdbuf_stream.return_value = iter(events)
    tap_cls = mock.MagicMock(return_value=tap)
    tap_cls.get_time_config = mock.AsyncMock(return_value={})
    return mock.patch(
        "pymobiledevice3.services.dvt.instruments."
        "core_profile_session_tap.CoreProfileSessionTap",
        tap_cls,
    )


def test_measure_jank_mocked():
    events = [
        SimpleNamespace(name="CoreAnimation", timestamp=i * (1.0 / 60))
        for i in range(30)
    ]
    with mock.patch.object(device, "dvt_session_async", _fake_dvt), \
            _patch_core_profile(events):
        result = frametime.measure_jank("UDID-1", duration=0.1)
    assert result["supported"] is True
    assert result["frames"] == 30
    assert result["raw_events"] == 30


def test_measure_jank_no_frames_reports_note():
    events = [SimpleNamespace(name="unrelated", timestamp=1.0)]
    with mock.patch.object(device, "dvt_session_async", _fake_dvt), \
            _patch_core_profile(events):
        result = frametime.measure_jank("UDID-1", duration=0.1)
    assert result["supported"] is False
    assert "matcher" in result["note"]
