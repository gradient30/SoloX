# -*- coding: utf-8 -*-
"""Weak network: presets, ping parsing, apply/clear with mocked adb."""

import unittest
from unittest.mock import patch

import pytest

from solox.public.weak_network import ProbeResult, WeakNetworkManager, WEAKNET_PRESETS
from solox.public.weaknet.models import DirectionProfile, WeakNetworkProfile


SAMPLE_PING = """
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=45.2 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=118 time=48.1 ms

--- 8.8.8.8 ping statistics ---
10 packets transmitted, 9 received, 10% packet loss, time 9012ms
rtt min/avg/max/mdev = 42.100/46.500/52.300/3.200 ms
"""


class TestWeakNetPresets(unittest.TestCase):

    def test_list_presets_cn(self):
        items = WeakNetworkManager.list_presets(lan='cn')
        self.assertGreater(len(items), 5)
        self.assertNotIn('off', [x['id'] for x in items])
        ids = {x['id'] for x in items}
        self.assertIn('lte_weak', ids)
        self.assertIn('3g', ids)

    def test_preset_labels(self):
        for key, cfg in WEAKNET_PRESETS.items():
            if key == 'off':
                continue
            self.assertIn('label_cn', cfg)
            self.assertIn('label_en', cfg)


class TestPingParse(unittest.TestCase):

    def test_parse_standard_ping(self):
        r = WeakNetworkManager._parse_ping(SAMPLE_PING, '8.8.8.8')
        self.assertEqual(r.host, '8.8.8.8')
        self.assertEqual(r.sent, 10)
        self.assertEqual(r.received, 9)
        self.assertEqual(r.loss_pct, 10.0)
        self.assertAlmostEqual(r.rtt_min_ms, 42.1)
        self.assertAlmostEqual(r.rtt_avg_ms, 46.5)
        self.assertAlmostEqual(r.rtt_max_ms, 52.3)
        self.assertAlmostEqual(r.jitter_ms, 3.2)

    def test_parse_empty(self):
        r = WeakNetworkManager._parse_ping('', '1.1.1.1')
        self.assertIsInstance(r, ProbeResult)
        self.assertEqual(r.sent, 0)

    def test_to_dict(self):
        r = ProbeResult(host='h', sent=5, received=5, rtt_avg_ms=10.0)
        d = r.to_dict()
        self.assertEqual(d['host'], 'h')
        self.assertEqual(d['rtt_avg_ms'], 10.0)


class TestNetemArgs(unittest.TestCase):

    def test_build_full(self):
        s = WeakNetworkManager._build_netem_args(200, 50, 2.5, '5mbit')
        self.assertIn('delay 200ms 50ms', s)
        self.assertIn('loss 2.5%', s)
        self.assertIn('rate 5mbit', s)

    def test_build_empty_returns_empty(self):
        self.assertEqual(WeakNetworkManager._build_netem_args(0, 0, 0, None), '')


class TestWeakNetworkProfile:

    def test_legacy_profile_maps_to_both_directions(self):
        profile = WeakNetworkProfile.from_legacy(
            delay_ms=200,
            jitter_ms=50,
            loss_pct=2,
            rate='5mbit',
        )

        assert profile.uplink.delay_ms == 200
        assert profile.downlink.delay_ms == 200
        assert profile.uplink.jitter_ms == 50
        assert profile.downlink.loss_pct == 2
        assert profile.uplink.bandwidth_kbps == 5000
        assert profile.downlink.bandwidth_kbps == 5000

    @pytest.mark.parametrize(
        ('rate', 'expected'),
        [
            (None, None),
            ('', None),
            ('1500kbit', 1500),
            ('5mbit', 5000),
            ('2048', 2048),
            (2048, 2048),
        ],
    )
    def test_legacy_rate_parsing(self, rate, expected):
        profile = WeakNetworkProfile.from_legacy(rate=rate)
        assert profile.uplink.bandwidth_kbps == expected

    def test_profile_rejects_invalid_loss(self):
        with pytest.raises(ValueError, match='loss'):
            DirectionProfile(loss_pct=101)

    def test_profile_rejects_negative_delay(self):
        with pytest.raises(ValueError, match='delay'):
            DirectionProfile(delay_ms=-1)

    def test_profile_serializes_without_legacy_rate_strings(self):
        profile = WeakNetworkProfile.from_legacy(
            delay_ms=100,
            jitter_ms=20,
            loss_pct=1.5,
            rate='256kbit',
        )

        assert profile.to_dict() == {
            'uplink': {
                'delay_ms': 100,
                'jitter_ms': 20,
                'loss_pct': 1.5,
                'bandwidth_kbps': 256,
                'burst_loss_pct': 0.0,
            },
            'downlink': {
                'delay_ms': 100,
                'jitter_ms': 20,
                'loss_pct': 1.5,
                'bandwidth_kbps': 256,
                'burst_loss_pct': 0.0,
            },
            'protocol': 'all',
            'ip_filter': [],
        }


class TestWeakNetApplyClear(unittest.TestCase):

    def setUp(self):
        import solox.public.weak_network as wn

        # 仅重置进程内状态；勿调用 WeakNetworkManager.clear()——在无真机的 CI
        # 上会走 adb shell（ip route / su），subprocess 永久阻塞直至 pytest 超时。
        wn._active.clear()
        wn._active_engines.clear()

    def tearDown(self):
        import solox.public.weak_network as wn

        wn._active.clear()
        wn._active_engines.clear()

    @patch.object(WeakNetworkManager, '_has_root', return_value=True)
    @patch.object(WeakNetworkManager, '_tc_available', return_value=True)
    @patch.object(WeakNetworkManager, '_detect_interface', return_value='wlan0')
    @patch.object(WeakNetworkManager, '_run_root')
    def test_apply_preset(self, mock_run, *_mocks):
        mock_run.side_effect = ['', 'qdisc netem 800ms delay']
        out = WeakNetworkManager.apply_preset('dev1', 'lte_weak')
        self.assertEqual(out['status'], 1)
        self.assertEqual(out['preset'], 'lte_weak')
        self.assertEqual(out['interface'], 'wlan0')
        tc_call = mock_run.call_args_list[0][0][1]
        self.assertIn('tc qdisc replace dev wlan0 root netem', tc_call)
        self.assertIn('delay 200ms', tc_call)

    @patch.object(WeakNetworkManager, '_has_root', return_value=False)
    def test_apply_requires_root(self, *_mocks):
        with self.assertRaises(RuntimeError) as ctx:
            WeakNetworkManager.apply_preset('dev1', '3g', engine='root_tc')
        self.assertIn('root', str(ctx.exception).lower())

    @patch.object(WeakNetworkManager, '_has_root', return_value=True)
    @patch.object(WeakNetworkManager, '_detect_interface', return_value='wlan0')
    @patch.object(WeakNetworkManager, '_run_root', return_value='cleared')
    def test_clear(self, mock_run, *_mocks):
        import solox.public.weak_network as wn

        root_eng = WeakNetworkManager._root_engine()
        root_eng._active['dev1'] = {
            'preset': '3g',
            'interface': 'wlan0',
            'params': {},
        }
        wn._active_engines['dev1'] = 'root_tc'
        out = WeakNetworkManager.clear('dev1')
        self.assertEqual(out['status'], 1)
        self.assertNotIn('dev1', root_eng._active)
        self.assertNotIn('dev1', wn._active_engines)
        mock_run.assert_called()

    @patch('solox.public.weak_network.adb.shell')
    def test_probe(self, mock_shell):
        mock_shell.return_value = SAMPLE_PING
        r = WeakNetworkManager.probe('dev1', host='8.8.8.8', count=10)
        self.assertEqual(r.loss_pct, 10.0)
        mock_shell.assert_called_once()
        self.assertIn('ping -c 10', mock_shell.call_args[1]['cmd'])


class FakeAgentController:

    def __init__(self, capabilities=None, apply_error=None, status=None):
        self.capability_result = capabilities or {
            'installed': True,
            'reachable': True,
            'simulation_supported': True,
            'state': 'idle',
        }
        self.apply_error = apply_error
        self.status_result = status or {'state': 'idle'}
        self.apply_calls = []
        self.clear_calls = []

    def capabilities(self, device_id):
        return dict(self.capability_result)

    def apply(self, device_id, target_package, profile):
        self.apply_calls.append((device_id, target_package, profile))
        if self.apply_error:
            raise self.apply_error
        return {
            'status': 1,
            'engine': 'agent',
            'active': True,
            'session_id': 'session-1',
            'target_package': target_package,
            'profile': profile.to_dict(),
        }

    def status(self, _device_id):
        return dict(self.status_result)

    def clear(self, device_id):
        self.clear_calls.append(device_id)
        return {'status': 1, 'engine': 'agent', 'state': 'idle'}


class TestWeakNetEngineSelection(unittest.TestCase):

    def setUp(self):
        import solox.public.weak_network as weak_network

        self.previous_agent = getattr(WeakNetworkManager, '_agent_controller', None)
        weak_network._active_engines.clear()

    def tearDown(self):
        import solox.public.weak_network as weak_network

        WeakNetworkManager._agent_controller = self.previous_agent
        weak_network._active_engines.clear()

    @patch.object(WeakNetworkManager, '_has_root', return_value=False)
    @patch.object(
        WeakNetworkManager,
        '_detect_interface_no_root',
        return_value='wlan0',
    )
    def test_auto_prefers_healthy_agent(self, *_mocks):
        agent = FakeAgentController()
        WeakNetworkManager._agent_controller = agent

        result = WeakNetworkManager.apply_custom(
            'dev1',
            engine='auto',
            target_package='com.example.app',
            delay_ms=120,
        )

        self.assertEqual(result['engine'], 'agent')
        self.assertEqual(agent.apply_calls[0][1], 'com.example.app')
        self.assertEqual(agent.apply_calls[0][2].uplink.delay_ms, 120)

    @patch.object(WeakNetworkManager, '_has_root', return_value=True)
    @patch.object(WeakNetworkManager, '_tc_available', return_value=True)
    @patch.object(WeakNetworkManager, '_detect_interface', return_value='wlan0')
    @patch.object(WeakNetworkManager, '_run_root')
    def test_auto_falls_back_to_root_before_start(self, mock_run, *_mocks):
        mock_run.side_effect = ['', 'qdisc netem delay 100ms']
        WeakNetworkManager._agent_controller = FakeAgentController({
            'installed': False,
            'reachable': False,
            'simulation_supported': False,
            'state': 'not_installed',
        })

        result = WeakNetworkManager.apply_custom(
            'dev1',
            engine='auto',
            delay_ms=100,
        )

        self.assertEqual(result['engine'], 'root_tc')
        self.assertTrue(result['active'])

    @patch.object(WeakNetworkManager, '_has_root', return_value=True)
    @patch.object(WeakNetworkManager, '_tc_available', return_value=True)
    @patch.object(WeakNetworkManager, '_detect_interface', return_value='wlan0')
    @patch.object(WeakNetworkManager, '_run_root')
    def test_agent_start_failure_does_not_fallback_to_root(self, mock_run, *_mocks):
        WeakNetworkManager._agent_controller = FakeAgentController(
            apply_error=RuntimeError('native start failed'),
        )

        with self.assertRaisesRegex(RuntimeError, 'native start failed'):
            WeakNetworkManager.apply_custom(
                'dev1',
                engine='auto',
                target_package='com.example.app',
                delay_ms=100,
            )

        mock_run.assert_not_called()

    def test_explicit_agent_requires_target_package(self):
        WeakNetworkManager._agent_controller = FakeAgentController()

        with self.assertRaisesRegex(ValueError, 'target package'):
            WeakNetworkManager.apply_custom(
                'dev1',
                engine='agent',
                delay_ms=100,
            )

    def test_agent_receives_independent_direction_profiles(self):
        agent = FakeAgentController()
        WeakNetworkManager._agent_controller = agent

        WeakNetworkManager.apply_custom(
            'dev1',
            engine='agent',
            target_package='com.example.app',
            uplink_delay_ms=20,
            downlink_delay_ms=200,
            uplink_rate='512kbit',
            downlink_rate='5mbit',
        )

        profile = agent.apply_calls[0][2]
        self.assertEqual(profile.uplink.delay_ms, 20)
        self.assertEqual(profile.downlink.delay_ms, 200)
        self.assertEqual(profile.uplink.bandwidth_kbps, 512)
        self.assertEqual(profile.downlink.bandwidth_kbps, 5000)

    def test_agent_status_cannot_override_normalized_activity(self):
        import solox.public.weak_network as weak_network

        WeakNetworkManager._agent_controller = FakeAgentController(status={
            'state': 'idle',
            'engine': 'untrusted',
            'active': True,
        })
        weak_network._active_engines['dev1'] = 'agent'

        result = WeakNetworkManager.get_status('dev1')

        self.assertEqual(result['engine'], 'agent')
        self.assertEqual(result['active_engine'], 'agent')
        self.assertFalse(result['active'])


if __name__ == '__main__':
    unittest.main()
