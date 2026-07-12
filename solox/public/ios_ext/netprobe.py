# -*- coding: utf-8 -*-
"""iOS 被动网络 RTT 采样：基于 Instruments ``NetworkMonitor``。

技术来源（借鉴，允许直接使用）：
    - pymobiledevice3 ``services.dvt.instruments.network_monitor``
      （``com.apple.instruments.server.services.networking`` DTX 通道）。
      其 ``ConnectionUpdateEvent`` 携带每条 TCP 连接的内核统计，其中
      ``min_rtt`` / ``avg_rtt`` 即为**真实往返时延**（非主动 ping，读取现有
      连接的内核测量值）。

诚实边界：
    - iOS 非越狱设备**没有 shell**，无法主动 ``ping``；本模块提供的是**被动**
      RTT——只反映采样窗口内设备上已存在连接的内核 RTT。无活跃连接时样本为空。
    - ``min_rtt`` / ``avg_rtt`` 为内核原始整数；其单位随 iOS 版本/字段口径可能
      为微秒或毫秒。本模块输出 ``*_raw`` 原值并附 ``unit='raw'``，**单位标定属
      真机待验收项**，绝不臆造换算后的"毫秒"值误导用户。
    - ``pymobiledevice3`` 为可选依赖（``solox[ios]``），所有导入均惰性完成。

聚合函数 :func:`aggregate_rtt` 为纯函数，可离线单测，不依赖 pymobiledevice3。
"""

from __future__ import annotations

from typing import Any

from solox.public.ios_ext import _aio
from solox.public.ios_ext import device as _dev

_DEFAULT_DURATION = 5.0


def aggregate_rtt(updates: list[Any]) -> dict[str, Any]:
    """把若干 ConnectionUpdate 记录聚合为稳定的对外结构（纯函数）。

    Args:
        updates: 每项为具备 ``min_rtt`` / ``avg_rtt`` / ``rx_bytes`` /
            ``tx_bytes`` 属性的对象，或含同名键的 dict。

    Returns:
        Dict[str, Any]: 含连接数、RTT 原值聚合、收发字节合计与诚实说明。
    """
    def _get(item: Any, key: str) -> Any:
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    min_rtts = [
        v for v in (_get(u, 'min_rtt') for u in updates)
        if isinstance(v, (int, float)) and v > 0
    ]
    avg_rtts = [
        v for v in (_get(u, 'avg_rtt') for u in updates)
        if isinstance(v, (int, float)) and v > 0
    ]
    rx_bytes = sum(
        v for v in (_get(u, 'rx_bytes') for u in updates)
        if isinstance(v, (int, float))
    )
    tx_bytes = sum(
        v for v in (_get(u, 'tx_bytes') for u in updates)
        if isinstance(v, (int, float))
    )

    return {
        'mode': 'passive_networkmonitor',
        'connections_sampled': len(updates),
        'rtt_samples': len(avg_rtts),
        'min_rtt_raw': min(min_rtts) if min_rtts else None,
        'avg_rtt_raw': (
            round(sum(avg_rtts) / len(avg_rtts), 2) if avg_rtts else None
        ),
        'max_rtt_raw': max(avg_rtts) if avg_rtts else None,
        'rx_bytes': rx_bytes,
        'tx_bytes': tx_bytes,
        'unit': 'raw',
        'note': (
            '被动内核 RTT（非主动 ping）；min_rtt/avg_rtt 为原始整数，单位标定'
            '属真机待验收项，未换算为毫秒以免误导'
        ),
    }


def sample_rtt(
    udid: str,
    duration: float = _DEFAULT_DURATION,
    ios_major: int | None = None,
) -> dict[str, Any]:
    """采样一段时间内设备现有连接的被动 RTT（同步阻塞）。

    Args:
        udid: 设备标识。
        duration: 采样窗口秒数。
        ios_major: 已知 iOS 主版本；``None`` 时自动探测。

    Returns:
        Dict[str, Any]: :func:`aggregate_rtt` 的结果，附 ``duration``。

    Raises:
        IOSBackendUnavailable: 未安装 pymobiledevice3。
        Exception: 底层 DVT/隧道错误原样上报（由调用方降级为诚实不支持）。
    """
    _dev._require_pmd3()
    window = max(1.0, float(duration))
    # 采样窗口之外预留 30s 供 DVT/隧道建连与关闭。
    updates = _aio.run(_sample_async(udid, window, ios_major), timeout=window + 30.0)
    result = aggregate_rtt(updates)
    result['duration'] = window
    return result


async def _sample_async(
    udid: str,
    duration: float,
    ios_major: int | None,
) -> list[Any]:
    """在 DVT 会话上采集 ``duration`` 秒的 ConnectionUpdate 事件。"""
    import asyncio

    from pymobiledevice3.services.dvt.instruments.network_monitor import (
        ConnectionUpdateEvent,
        NetworkMonitor,
    )

    collected: list[Any] = []
    async with _dev.dvt_session_async(udid, ios_major=ios_major) as dvt:
        monitor = NetworkMonitor(dvt)
        async with monitor:
            loop = asyncio.get_event_loop()
            deadline = loop.time() + duration
            iterator = monitor.__aiter__()
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    event = await asyncio.wait_for(
                        iterator.__anext__(), timeout=remaining
                    )
                except (asyncio.TimeoutError, StopAsyncIteration):
                    break
                if isinstance(event, ConnectionUpdateEvent):
                    collected.append(event)
    return collected
