# -*- coding: utf-8 -*-
"""iOS 真实 Jank（D）：CoreProfileSessionTap 帧时序 → PerfDog 抖动定义。

背景：Instruments 的 opengl 采样器只给聚合帧率标量，**无逐帧时戳**，故无法算
Jank。``CoreProfileSessionTap`` 是内核 kdebug 追踪通道，可拿到带内核时间戳的事
件流；从中提取 CoreAnimation "帧呈现" 事件即得逐帧呈现时间序列，再复用与
Android 完全一致的 PerfDog 抖动定义（见
:func:`calculate_jank`，与 ``android_fps._calculate_jank_ex`` 保持同义）。

诚实边界（真机待标定）：
    kdebug 中"帧呈现"对应的 trace code（debugid）随 iOS 版本/图形栈变化，需在
    真机上用 ``CoreProfileSessionTap.get_trace_codes()`` 核对后确定。本模块把
    匹配器设计为**可注入/可配置**，默认给出候选集合但不保证覆盖所有机型；未命
    中时如实返回 0 帧并给出"需标定"提示，绝不臆造帧数据。
"""

from __future__ import annotations

import queue
from typing import Any, Callable, Iterable

# CoreAnimation / RenderServer 相关 trace class 候选（需真机核对）。
# 这些是"帧呈现/提交"事件常见所属的 kdebug class/subclass 关键字，仅作默认猜
# 测，真机标定后应替换为确切 debugid 集合。
DEFAULT_FRAME_TRACE_HINTS = (
    "coreanimation",
    "renderserver",
    "ca::render",
    "backboard",
)

# 默认刷新周期（60Hz）。高刷机型应据实传入（如 120Hz → 1/120）。
DEFAULT_REFRESH_PERIOD = 1.0 / 60


def calculate_jank(
    present_times: list[float],
    refresh_period: float | None = None,
) -> dict[str, Any]:
    """由逐帧呈现时间序列计算 Jank / BigJank / 卡顿率。

    该实现与 ``android_fps.SurfaceStatsCollector._calculate_jank_ex`` 采用**完
    全相同**的 PerfDog 抖动判定（滑动窗口 2×近三帧均值，且分别超过 2×/3× vsync
    周期），以保证 Android/iOS 口径一致（由 parity 测试守护）。

    Args:
        present_times: 逐帧呈现时间戳（秒，单调递增）。
        refresh_period: 屏幕刷新周期（秒）；``None`` 默认 60Hz。

    Returns:
        Dict[str, Any]: 含 ``frames`` / ``fps`` / ``jank`` / ``big_jank`` /
        ``stutter_rate`` / ``big_stutter_rate``。
    """
    if not refresh_period or refresh_period <= 0:
        refresh_period = DEFAULT_REFRESH_PERIOD

    frames = len(present_times)
    result = {
        "frames": frames,
        "fps": 0,
        "jank": 0,
        "big_jank": 0,
        "stutter_rate": 0.0,
        "big_stutter_rate": 0.0,
    }
    if frames < 2:
        return result

    seconds = present_times[-1] - present_times[0]
    if seconds > 0:
        result["fps"] = int(round((frames - 1) / seconds))

    jank, big_jank = _jank_ex(present_times, refresh_period)
    result["jank"] = jank
    result["big_jank"] = big_jank
    # 卡顿率 = 抖动帧数 / 总帧数（与 Android stutterRate 口径一致）
    result["stutter_rate"] = round(jank / frames, 4)
    result["big_stutter_rate"] = round(big_jank / frames, 4)
    return result


def _jank_ex(
    present_times: list[float],
    refresh_period: float,
) -> tuple[int, int]:
    """PerfDog 抖动核心算法（与 Android 版逐行同义）。

    Args:
        present_times: 逐帧呈现时间戳（秒）。
        refresh_period: 刷新周期（秒）。

    Returns:
        Tuple[int, int]: ``(jank, big_jank)``。
    """
    eps = 1e-6
    vsync_2x = refresh_period * 2 - eps
    vsync_3x = refresh_period * 3 - eps

    jank = 0
    big_jank = 0
    frame_count = len(present_times)

    if frame_count < 5:
        prev = None
        for ts in present_times:
            if prev is None:
                prev = ts
                continue
            ft = ts - prev
            if ft > vsync_2x:
                jank += 1
            if ft > vsync_3x:
                big_jank += 1
            prev = ts
        return jank, big_jank

    for i in range(4, frame_count):
        cur = present_times[i]
        prev = present_times[i - 1]
        p2 = present_times[i - 2]
        p3 = present_times[i - 3]
        p4 = present_times[i - 4]
        avg3 = ((p3 - p4) + (p2 - p3) + (prev - p2)) / 3.0
        threshold_dynamic = avg3 * 2 - eps
        current_ft = cur - prev
        if current_ft > threshold_dynamic and current_ft > vsync_2x:
            jank += 1
        if current_ft > threshold_dynamic and current_ft > vsync_3x:
            big_jank += 1

    for i in range(1, min(4, frame_count)):
        ft = present_times[i] - present_times[i - 1]
        if ft > vsync_2x:
            jank += 1
        if ft > vsync_3x:
            big_jank += 1

    return jank, big_jank


def extract_present_times(
    events: Iterable[Any],
    time_config: dict[str, Any] | None = None,
    matcher: Callable[[Any], bool] | None = None,
) -> list[float]:
    """从 kdebug 事件流中提取"帧呈现"时间序列（秒）。

    Args:
        events: kdebug 事件对象可迭代序列。
        time_config: ``CoreProfileSessionTap.get_time_config()`` 结果，用于把
            内核 mach 时间换算为秒。
        matcher: 判定某事件是否为"帧呈现"的谓词；``None`` 时使用基于
            :data:`DEFAULT_FRAME_TRACE_HINTS` 的默认猜测（**需真机标定**）。

    Returns:
        List[float]: 单调递增的呈现时间戳（秒）。
    """
    if matcher is None:
        matcher = _default_frame_matcher
    times: list[float] = []
    for event in events:
        try:
            if not matcher(event):
                continue
            seconds = _event_seconds(event, time_config)
        except Exception:  # noqa: BLE001 - 单个事件解析失败不影响整体
            continue
        if seconds is not None:
            times.append(seconds)
    times.sort()
    return times


def _default_frame_matcher(event: Any) -> bool:
    """默认帧事件匹配器：按 class/subclass 名称关键字猜测（需真机标定）。"""
    text = ""
    for attr in ("name", "class_name", "subclass_name", "debug_id"):
        value = getattr(event, attr, None)
        if value is not None:
            text += " " + str(value).lower()
    return any(hint in text for hint in DEFAULT_FRAME_TRACE_HINTS)


def _event_seconds(
    event: Any,
    time_config: dict[str, Any] | None,
) -> float | None:
    """将事件时间戳换算为秒。

    优先使用已是秒/纳秒的字段；否则用 mach timebase（numer/denom）换算。
    """
    ts = getattr(event, "timestamp", None)
    if ts is None:
        ts = getattr(event, "time", None)
    if ts is None:
        return None
    ts = float(ts)
    if not time_config:
        return ts
    numer = time_config.get("numer") or time_config.get("numerator")
    denom = time_config.get("denom") or time_config.get("denominator")
    if numer and denom:
        # mach ticks → 纳秒 → 秒
        return ts * (float(numer) / float(denom)) / 1e9
    return ts


def measure_jank(
    udid: str,
    duration: float = 10.0,
    refresh_period: float | None = None,
    ios_major: int | None = None,
    matcher: Callable[[Any], bool] | None = None,
) -> dict[str, Any]:
    """采集一段时间的帧时序并计算 Jank（真机 + tunneld 环境，同步门面）。

    Args:
        udid: 设备标识。
        duration: 采集时长（秒）。
        refresh_period: 刷新周期（秒）；高刷机型请据实传入。
        ios_major: 已知 iOS 主版本；``None`` 时自动探测。
        matcher: 自定义帧事件匹配器（真机标定后传入确切 debugid 判定）。

    Returns:
        Dict[str, Any]: :func:`calculate_jank` 结果，并附加 ``raw_events`` /
        ``supported``（提取到帧则 ``True``）/ ``note``。

    Raises:
        IOSBackendUnavailable: pymobiledevice3 未安装时。
        TunnelUnavailable: iOS 17+ 但 tunneld 不可用时。
    """
    from solox.public.ios_ext import _aio, device as _dev

    _dev._require_pmd3()
    events, time_config = _aio.run(
        _collect_events_async(udid, duration, ios_major),
        timeout=duration + 30,
    )
    present_times = extract_present_times(
        events, time_config=time_config, matcher=matcher
    )
    result = calculate_jank(present_times, refresh_period=refresh_period)
    result["raw_events"] = len(events)
    result["supported"] = result["frames"] >= 2
    if not result["supported"]:
        result["note"] = (
            "未从 kdebug 提取到帧呈现事件：需在真机上用 get_trace_codes() "
            "核对 CoreAnimation 帧事件 debugid 并传入自定义 matcher"
        )
    return result


async def _collect_events_async(
    udid: str,
    duration: float,
    ios_major: int | None,
) -> tuple[list[Any], dict[str, Any]]:
    """在 DVT 会话内采集 kdebug 事件并返回 ``(events, time_config)``。"""
    from solox.public.ios_ext import device as _dev
    from pymobiledevice3.services.dvt.instruments.core_profile_session_tap \
        import CoreProfileSessionTap

    async with _dev.dvt_session_async(udid, ios_major=ios_major) as dvt:
        time_config = await CoreProfileSessionTap.get_time_config(dvt)
        tap = CoreProfileSessionTap(dvt, time_config)
        events = await _drain_events_async(tap, duration)
    return events, time_config or {}


async def _drain_events_async(
    tap: Any,
    duration: float,
) -> list[Any]:
    """在给定时长内从 tap 抽取 kdebug 事件（兼容同步/异步事件流）。"""
    import asyncio

    events: list[Any] = []
    chunk_queue: "queue.Queue[Any]" = queue.Queue()
    stream = tap.get_kdbuf_stream(chunk_queue)
    loop = asyncio.get_event_loop()
    deadline = loop.time() + max(0.0, duration)

    if hasattr(stream, "__aiter__"):
        async for event in stream:
            events.append(event)
            if loop.time() >= deadline:
                break
    else:
        for event in stream:
            events.append(event)
            if loop.time() >= deadline:
                break
    return events
