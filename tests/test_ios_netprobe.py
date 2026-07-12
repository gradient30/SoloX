# -*- coding: utf-8 -*-
"""iOS 被动 RTT 聚合（netprobe.aggregate_rtt）纯函数单测。

aggregate_rtt 不依赖 pymobiledevice3，可在无 solox[ios] 的 CI 环境运行。
"""

from __future__ import annotations

from types import SimpleNamespace

from solox.public.ios_ext import netprobe


def test_aggregate_rtt_empty():
    result = netprobe.aggregate_rtt([])
    assert result['connections_sampled'] == 0
    assert result['rtt_samples'] == 0
    assert result['avg_rtt_raw'] is None
    assert result['min_rtt_raw'] is None
    assert result['unit'] == 'raw'


def test_aggregate_rtt_from_objects():
    updates = [
        SimpleNamespace(min_rtt=10, avg_rtt=20, rx_bytes=100, tx_bytes=50),
        SimpleNamespace(min_rtt=30, avg_rtt=40, rx_bytes=200, tx_bytes=60),
    ]
    result = netprobe.aggregate_rtt(updates)
    assert result['connections_sampled'] == 2
    assert result['rtt_samples'] == 2
    assert result['min_rtt_raw'] == 10
    assert result['avg_rtt_raw'] == 30.0
    assert result['max_rtt_raw'] == 40
    assert result['rx_bytes'] == 300
    assert result['tx_bytes'] == 110


def test_aggregate_rtt_ignores_nonpositive_and_dicts():
    updates = [
        {'min_rtt': 0, 'avg_rtt': 0, 'rx_bytes': 10, 'tx_bytes': 5},
        {'min_rtt': 15, 'avg_rtt': 25, 'rx_bytes': 20, 'tx_bytes': 8},
    ]
    result = netprobe.aggregate_rtt(updates)
    # 只有第二条 RTT 为正，参与聚合
    assert result['rtt_samples'] == 1
    assert result['avg_rtt_raw'] == 25.0
    assert result['min_rtt_raw'] == 15
    assert result['rx_bytes'] == 30
    assert result['mode'] == 'passive_networkmonitor'
    assert 'note' in result
