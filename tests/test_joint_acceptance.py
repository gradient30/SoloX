# -*- coding: utf-8 -*-
"""Joint acceptance tests — R&D / PM / QA cross-cutting release criteria."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from solox.public.common import File, Platform
from tests.matrix_loader import (
    load_matrix,
    validate_docs_consistency,
    validate_release_readiness,
)

_TESTS_DIR = os.path.dirname(__file__)
_DOCS_PATH = os.path.join(_TESTS_DIR, '..', 'docs', 'compatibility-matrix.md')


class TestReleaseReadinessGate(unittest.TestCase):
    """Single entry point mirroring scripts/validate_compatibility_matrix.py."""

    def test_full_release_readiness(self):
        errors = validate_release_readiness()
        self.assertEqual(errors, [], f'Release readiness failed: {errors}')

    def test_docs_yaml_consistency(self):
        errors = validate_docs_consistency(load_matrix())
        self.assertEqual(errors, [], f'Docs/matrix mismatch: {errors}')

    def test_perfdog_metrics_in_matrix(self):
        """PM: jank / big_jank / scene_tags must be traceable in compatibility matrix."""
        metrics = load_matrix()['metrics']
        for key in ('jank', 'big_jank', 'scene_tags'):
            self.assertIn(key, metrics, f'metrics.{key} missing from matrix')


class TestGpuCollectRealCodePath(unittest.TestCase):
    """Regression: /apm/collect?target=gpu must invoke GPU with correct kwargs."""

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('solox.public.apm.adb.shell')
    def test_gpu_collect_end_to_end(self, mock_shell):
        mock_shell.return_value = '5000 10000'

        resp = self.client.get(
            '/apm/collect',
            query_string={
                'platform': 'Android',
                'deviceid': 'test_device',
                'pkgname': 'com.test.app',
                'target': 'gpu',
            },
        )
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['gpu'], 50.0)
        mock_shell.assert_called_with(
            cmd='cat /sys/class/kgsl/kgsl-3d0/gpubusy',
            deviceId='test_device',
        )


class TestPerfDogAcceptanceFlow(unittest.TestCase):
    """R&D + QA: scene tags, big_jank stats, and Excel export end-to-end (no device)."""

    def _write_min_logs(self, report_dir):
        logs = {
            'fps.log': '10:00:01.000000=60\n',
            'jank.log': '10:00:01.000000=2\n10:00:02.000000=0\n',
            'big_jank.log': '10:00:01.000000=1\n10:00:02.000000=0\n',
            'cpu_app.log': '10:00:01.000000=25\n',
            'cpu_sys.log': '10:00:01.000000=40\n',
            'mem_total.log': '10:00:01.000000=200\n',
            'mem_swap.log': '10:00:01.000000=10\n',
        }
        for name, content in logs.items():
            with open(os.path.join(report_dir, name), 'w', encoding='utf-8') as fh:
                fh.write(content)

    def test_make_report_preserves_scene_tags_and_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = File()
            f.report_dir = tmp
            self._write_min_logs(tmp)
            f.add_scene_tag('Lobby')
            f.add_scene_tag('Battle')
            scene = f.make_report('com.test.app', 'test_device', False, Platform.Android)
            scene_dir = os.path.join(tmp, scene)
            self.assertTrue(os.path.isfile(os.path.join(scene_dir, 'scene_tags.json')))
            self.assertTrue(os.path.isfile(os.path.join(scene_dir, 'perf_stats.json')))
            self.assertTrue(os.path.isfile(os.path.join(scene_dir, 'scene_tag_stats.json')))
            perf = json.load(open(os.path.join(scene_dir, 'perf_stats.json'), encoding='utf-8'))
            self.assertIn('big_jank', perf)
            self.assertEqual(perf['big_jank']['sum'], 1.0)
            tag_stats = json.load(
                open(os.path.join(scene_dir, 'scene_tag_stats.json'), encoding='utf-8'))
            self.assertGreaterEqual(len(tag_stats['scenes']), 2)

    def test_export_excel_includes_jank_and_scene_sheets(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = File()
            f.report_dir = tmp
            scene = 'apm_export_test'
            scene_dir = os.path.join(tmp, scene)
            os.makedirs(scene_dir)
            self._write_min_logs(scene_dir)
            with open(os.path.join(scene_dir, 'scene_tags.json'), 'w', encoding='utf-8') as fh:
                json.dump([
                    {'time': '10:00:01.000000', 'label': 'Lobby'},
                    {'time': '10:00:02.000000', 'label': 'Battle'},
                ], fh)
            with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                json.dump({'app': 'com.test.app', 'platform': 'Android'}, fh)
            xls_path = f.export_excel('Android', scene)
            self.assertTrue(os.path.isfile(xls_path))
            self.assertGreater(os.path.getsize(xls_path), 200)
            with open(xls_path, 'rb') as fh:
                blob = fh.read()
            for marker in (b'jank', b'big_jank', b'scene_tags', b'scene_stats'):
                self.assertIn(marker, blob, f'missing sheet marker {marker!r} in xls')

    def test_scene_tag_api(self):
        from solox.web import app
        app.config['TESTING'] = True
        client = app.test_client()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(File, '__init__', lambda self, fileroot='.': None):
                inst = File()
                inst.report_dir = tmp
                with patch('solox.view.apis.f', inst):
                    resp = client.post('/apm/scene/tag', data={'label': 'Boss Fight'})
                    self.assertEqual(resp.get_json()['status'], 1)
                    tags = client.get('/apm/scene/tags').get_json()['tags']
                    self.assertEqual(len(tags), 1)
                    self.assertEqual(tags[0]['label'], 'Boss Fight')


class TestReportManagementAcceptance(unittest.TestCase):
    """PM/QA: report list duration_label + chart downsample API."""

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_report_list_returns_duration_label(self):
        import json as _json
        with tempfile.TemporaryDirectory() as tmp:
            report_root = os.path.join(tmp, 'report', 'apm_test_run')
            os.makedirs(report_root)
            with open(os.path.join(report_root, 'result.json'), 'w', encoding='utf-8') as fh:
                _json.dump({
                    'app': 'com.test.app',
                    'platform': 'Android',
                    'model': 'normal',
                    'devices': 'device1',
                    'ctime': '2026-03-15-16-31-18',
                    'video': 0,
                    'duration': '05:32',
                    'duration_label': 'apm_05:32',
                    'duration_seconds': 332,
                }, fh)
            with patch('solox.view.apis.os.getcwd', return_value=tmp):
                resp = self.client.get('/apm/report/list', query_string={'page': 1, 'size': 20})
            data = resp.get_json()
            self.assertEqual(data['status'], 1)
            self.assertEqual(len(data['data']), 1)
            self.assertEqual(data['data'][0]['duration_label'], 'apm_05:32')
            self.assertEqual(data['data'][0]['scene'], 'apm_test_run')

    def test_log_api_downsample(self):
        with tempfile.TemporaryDirectory() as tmp:
            inst = File()
            inst.report_dir = os.path.join(tmp, 'report')
            scene = 'apm_ds'
            scene_dir = os.path.join(inst.report_dir, scene)
            os.makedirs(scene_dir)
            with open(os.path.join(scene_dir, 'cpu_app.log'), 'w', encoding='utf-8') as fh:
                for i in range(3000):
                    fh.write(f'10:00:{i % 60:02d}.000000={i % 100}\n')
            with open(os.path.join(scene_dir, 'cpu_sys.log'), 'w', encoding='utf-8') as fh:
                fh.write('10:00:00.000000=10\n')
            with open(os.path.join(scene_dir, 'result.json'), 'w', encoding='utf-8') as fh:
                import json as _json
                _json.dump({'cores': 0}, fh)
            with patch('solox.view.apis.f', inst):
                resp = self.client.get('/apm/log', query_string={
                    'scene': scene,
                    'target': 'cpu',
                    'platform': 'Android',
                    'max_points': 200,
                })
            data = resp.get_json()
            self.assertEqual(data['status'], 1)
            self.assertLessEqual(len(data['cpuAppData']), 200)
            self.assertTrue(data.get('downsampled'))


class TestRecordPlayerAcceptance(unittest.TestCase):
    """PM/QA: hybrid video player — browser mp4 + system mkv fallback."""

    def setUp(self):
        from solox.web import app
        from solox.view import apis
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.apis = apis
        self._orig_report_dir = apis.f.report_dir
        self.tmp = tempfile.mkdtemp()
        apis.f.report_dir = self.tmp
        self.scene = 'apm_video_accept'
        os.makedirs(os.path.join(self.tmp, self.scene))

    def tearDown(self):
        self.apis.f.report_dir = self._orig_report_dir

    def test_pm_mp4_browser_playable_with_stream(self):
        mp4 = os.path.join(self.tmp, self.scene, 'record.mp4')
        with open(mp4, 'wb') as fh:
            fh.write(b'\x00' * 512)
        info = self.client.get('/apm/record/info', query_string={'scene': self.scene}).get_json()
        self.assertEqual(info['status'], 1)
        self.assertTrue(info['browser_playable'])
        stream = self.client.get('/apm/record/stream', query_string={'scene': self.scene})
        self.assertEqual(stream.status_code, 200)
        self.assertIn('video/mp4', stream.content_type)

    def test_qa_mkv_not_browser_playable(self):
        with open(os.path.join(self.tmp, self.scene, 'record.mkv'), 'wb') as fh:
            fh.write(b'\x00' * 64)
        info = self.client.get('/apm/record/info', query_string={'scene': self.scene}).get_json()
        self.assertEqual(info['status'], 1)
        self.assertEqual(info['format'], 'mkv')
        self.assertFalse(info['browser_playable'])

    @patch('solox.view.apis.Scrcpy.play_video')
    def test_qa_system_player_fallback(self, mock_play):
        mp4 = os.path.join(self.tmp, self.scene, 'record.mp4')
        with open(mp4, 'wb') as fh:
            fh.write(b'\x00' * 32)
        resp = self.client.get('/apm/record/play', query_string={'scene': self.scene})
        self.assertEqual(resp.get_json()['status'], 1)
        mock_play.assert_called_once_with(mp4)


class TestWeakNetAcceptance(unittest.TestCase):
    """R&D + PM + QA: weak network presets, probe, apply/clear API (PerfDog-style)."""

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.device_patcher = patch(
            'solox.view.apis.d.getIdbyDevice', return_value='test_device')
        self.device_patcher.start()

    def tearDown(self):
        self.device_patcher.stop()

    def test_pm_presets_api_cn_labels(self):
        resp = self.client.get('/apm/weaknet/presets', query_string={'lan': 'cn'})
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        ids = {p['id'] for p in data['presets']}
        self.assertIn('lte_weak', ids)
        self.assertIn('3g', ids)
        lte = next(p for p in data['presets'] if p['id'] == 'lte_weak')
        self.assertIn('4G', lte['label'])

    @patch('solox.public.weak_network.WeakNetworkManager._has_root', return_value=False)
    @patch('solox.public.weak_network.WeakNetworkManager._detect_interface_no_root',
           return_value='wlan0')
    def test_qa_capabilities_probe_only_without_root(self, *_mocks):
        resp = self.client.get('/apm/weaknet/capabilities', query_string={
            'platform': 'Android',
            'device': 'Pixel [test_device]',
        })
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertFalse(data['simulation_supported'])
        self.assertEqual(data['interface'], 'wlan0')
        self.assertEqual(data['mode'], 'probe_only')

    @patch('solox.public.weak_network.adb.shell')
    def test_qa_probe_api_parses_rtt(self, mock_shell):
        mock_shell.return_value = (
            '10 packets transmitted, 10 received, 0% packet loss\n'
            'rtt min/avg/max/mdev = 40.0/45.0/50.0/2.5 ms'
        )
        resp = self.client.get('/apm/weaknet/probe', query_string={
            'platform': 'Android',
            'device': 'dev',
            'host': '8.8.8.8',
            'count': 10,
        })
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertAlmostEqual(data['probe']['rtt_avg_ms'], 45.0)
        self.assertEqual(data['probe']['loss_pct'], 0.0)

    @patch('solox.public.weak_network.WeakNetworkManager.apply_preset')
    def test_rd_apply_preset_api(self, mock_apply):
        mock_apply.return_value = {
            'status': 1,
            'preset': '3g',
            'interface': 'wlan0',
            'params': {'delay_ms': 300},
        }
        resp = self.client.get('/apm/weaknet/apply', query_string={
            'platform': 'Android',
            'device': 'dev',
            'preset': '3g',
        })
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['preset'], '3g')
        mock_apply.assert_called_once_with('test_device', '3g')

    @patch('solox.public.weak_network.WeakNetworkManager.clear')
    def test_rd_clear_on_stop_lifecycle(self, mock_clear):
        mock_clear.return_value = {'status': 1, 'msg': 'weak network cleared', 'cleared': True}
        resp = self.client.get('/apm/weaknet/clear', query_string={
            'platform': 'Android',
            'device': 'dev',
        })
        self.assertEqual(resp.get_json()['status'], 1)
        mock_clear.assert_called_once_with('test_device')

    def test_pm_ios_simulation_unsupported(self):
        resp = self.client.get('/apm/weaknet/capabilities', query_string={
            'platform': 'iOS',
            'device': '00008030-001',
        })
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertFalse(data['simulation_supported'])
        self.assertIn('Android-only', data['msg'])


class TestL1CoverageCompleteness(unittest.TestCase):
    """QA: every metric marked l3_p0_required must have L1 or L3 path documented."""

    def test_fps_has_l1_mock_coverage(self):
        matrix = load_matrix()
        fps_apis = set(matrix['metrics']['fps']['l1_mock_apis'])
        self.assertTrue({28, 30, 31, 34, 36}.issubset(fps_apis))

    def test_big_jank_has_l1_mock_coverage(self):
        matrix = load_matrix()
        apis = set(matrix['metrics']['big_jank']['l1_mock_apis'])
        self.assertTrue({34, 36}.issubset(apis))

    def test_p0_android_count_matches_acceptance_doc(self):
        matrix = load_matrix()
        p0_count = len(matrix['android']['P0']['entries'])
        with open(
            os.path.join(_TESTS_DIR, '..', 'docs', 'acceptance',
                         'joint-review-2026-compatibility.md'),
            encoding='utf-8',
        ) as fh:
            content = fh.read()
        self.assertIn(str(p0_count), content)

    def test_minimum_automated_case_count(self):
        """PM acceptance: L1/L2 suite must cover at least 85 automated cases."""
        loader = unittest.TestLoader()
        suite = loader.discover(_TESTS_DIR, pattern='test_*.py')
        count = suite.countTestCases()
        self.assertGreaterEqual(
            count, 123,
            f'Expected >= 123 tests (health endpoint), found {count}',
        )

    def test_weaknet_in_l1_modules(self):
        """QA: weak network module must be in L1 release gate list."""
        from tests.matrix_loader import _L1_TEST_MODULES
        self.assertIn('test_weak_network.py', _L1_TEST_MODULES)


if __name__ == '__main__':
    unittest.main()
