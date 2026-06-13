# -*- coding: utf-8 -*-
"""Weak network: presets, ping parsing, apply/clear with mocked adb."""

import unittest
from unittest.mock import patch

from solox.public.weak_network import ProbeResult, WeakNetworkManager, WEAKNET_PRESETS


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


class TestWeakNetApplyClear(unittest.TestCase):

    def setUp(self):
        WeakNetworkManager.clear('dev1')

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
            WeakNetworkManager.apply_preset('dev1', '3g')
        self.assertIn('root', str(ctx.exception).lower())

    @patch.object(WeakNetworkManager, '_has_root', return_value=True)
    @patch.object(WeakNetworkManager, '_detect_interface', return_value='wlan0')
    @patch.object(WeakNetworkManager, '_run_root', return_value='cleared')
    def test_clear(self, mock_run, *_mocks):
        import solox.public.weak_network as wn
        wn._active['dev1'] = {'preset': '3g', 'interface': 'wlan0', 'params': {}}
        out = WeakNetworkManager.clear('dev1')
        self.assertEqual(out['status'], 1)
        self.assertNotIn('dev1', wn._active)
        mock_run.assert_called()

    @patch('solox.public.weak_network.adb.shell')
    def test_probe(self, mock_shell):
        mock_shell.return_value = SAMPLE_PING
        r = WeakNetworkManager.probe('dev1', host='8.8.8.8', count=10)
        self.assertEqual(r.loss_pct, 10.0)
        mock_shell.assert_called_once()
        self.assertIn('ping -c 10', mock_shell.call_args[1]['cmd'])


if __name__ == '__main__':
    unittest.main()
