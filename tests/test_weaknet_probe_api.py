# -*- coding: utf-8 -*-
"""/apm/weaknet/probe 平台分支单测（P2-T4）。

要点：
    - iOS 无设备侧主动 ping，端点须返回诚实的 probe_supported=false + 指引，
      **绝不**调用 adb（CI 无真机时不得阻塞）。
    - Android 保持真实 adb ping（此处 mock 底层 probe，不触真机）。
    - setUp/模块级不得触发真实 adb（见 ci-gate-playbook §3.1）。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

import solox.view.apis as apis


def test_probe_ios_without_backend_is_honest_unsupported(client):
    """iOS 未装 solox[ios] 时：probe_supported=false + NLC 指引，不调用 adb。"""
    with mock.patch('solox.public.ios_ext.is_available', return_value=False), \
            mock.patch.object(
                apis.WeakNetworkManager, 'probe',
                side_effect=AssertionError('must not run adb on iOS'),
            ):
        resp = client.get('/apm/weaknet/probe',
                          query_string={'platform': 'iOS', 'device': 'UDID-1'})
    data = resp.get_json()
    assert data['status'] == 1
    assert data['platform'] == 'iOS'
    assert data['probe_supported'] is False
    assert data['passive_rtt_supported'] is False
    assert 'Network Link Conditioner' in data['guide']
    assert 'guide_doc' in data


def test_probe_ios_with_backend_uses_passive_networkmonitor(client):
    """装了 solox[ios] 时：走被动 NetworkMonitor RTT（借鉴 pymobiledevice3）。"""
    fake_probe = {
        'mode': 'passive_networkmonitor',
        'avg_rtt_raw': 25.0,
        'connections_sampled': 2,
        'unit': 'raw',
    }
    with mock.patch('solox.public.ios_ext.is_available', return_value=True), \
            mock.patch.object(apis.d, 'getIdbyDevice', return_value='UDID-1'), \
            mock.patch('solox.public.ios_ext.netprobe.sample_rtt',
                       return_value=fake_probe) as mock_sample:
        resp = client.get('/apm/weaknet/probe',
                          query_string={'platform': 'iOS', 'device': 'UDID-1',
                                        'duration': 3})
    data = resp.get_json()
    assert data['status'] == 1
    assert data['passive_rtt_supported'] is True
    assert data['mode'] == 'passive_networkmonitor'
    assert data['probe']['avg_rtt_raw'] == 25.0
    mock_sample.assert_called_once()


def test_probe_ios_backend_error_degrades_honestly(client):
    """被动采样失败（如无真机/隧道）时：如实报 passive_error，不伪造数据。"""
    with mock.patch('solox.public.ios_ext.is_available', return_value=True), \
            mock.patch.object(apis.d, 'getIdbyDevice', return_value='UDID-1'), \
            mock.patch('solox.public.ios_ext.netprobe.sample_rtt',
                       side_effect=RuntimeError('no tunnel')):
        resp = client.get('/apm/weaknet/probe',
                          query_string={'platform': 'iOS', 'device': 'UDID-1'})
    data = resp.get_json()
    assert data['status'] == 1
    assert data['probe_supported'] is False
    assert 'probe' not in data
    assert 'no tunnel' in data['passive_error']


def test_probe_android_uses_real_ping_path(client):
    """Android 分支：走真实 ping 解析（此处 mock 底层，不触真机）。"""
    fake = SimpleNamespace(to_dict=lambda: {
        'host': '8.8.8.8', 'sent': 10, 'received': 9, 'loss_pct': 10.0,
        'rtt_min_ms': 20.0, 'rtt_avg_ms': 30.0, 'rtt_max_ms': 40.0,
        'jitter_ms': 5.0,
    })
    with mock.patch.object(apis.d, 'getIdbyDevice', return_value='dev1'), \
            mock.patch.object(
                apis.WeakNetworkManager, 'probe', return_value=fake,
            ) as mock_probe:
        resp = client.get('/apm/weaknet/probe',
                          query_string={'platform': 'Android',
                                        'device': 'dev1(model)'})
    data = resp.get_json()
    assert data['status'] == 1
    assert data['platform'] == 'Android'
    assert data['probe_supported'] is True
    assert data['probe']['loss_pct'] == 10.0
    mock_probe.assert_called_once()


def test_probe_unsupported_platform_is_honest(client):
    resp = client.get('/apm/weaknet/probe',
                      query_string={'platform': 'HarmonyOS', 'device': 'x'})
    data = resp.get_json()
    assert data['status'] == 1
    assert data['probe_supported'] is False
