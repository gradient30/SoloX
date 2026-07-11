# -*- coding: utf-8 -*-
"""Flask integration tests for /apm/collect — mocked APM backends, no device."""

import unittest
from unittest.mock import patch, MagicMock

from solox.public.apm import Target


COLLECT_URL = '/apm/collect'
BASE_PARAMS = {
    'platform': 'Android',
    'deviceid': 'test_device',
    'pkgname': 'com.test.app',
}


class TestApmCollectApi(unittest.TestCase):
    """Integration tests via Flask test client."""

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def _get(self, target, **extra):
        params = {**BASE_PARAMS, 'target': target, **extra}
        return self.client.get(COLLECT_URL, query_string=params)

    @patch('solox.view.apis.CPU')
    def test_collect_cpu_success(self, mock_cpu_cls):
        inst = MagicMock()
        inst.getCpuRate.return_value = (12.5, 45.0)
        mock_cpu_cls.return_value = inst

        resp = self._get(Target.CPU)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['appCpuRate'], 12.5)
        self.assertEqual(data['systemCpuRate'], 45.0)
        inst.getCpuRate.assert_called_once_with(noLog=True)

    @patch('solox.view.apis.Memory')
    def test_collect_memory_success(self, mock_mem_cls):
        inst = MagicMock()
        inst.getProcessMemory.return_value = (256.0, 1.5)
        mock_mem_cls.return_value = inst

        resp = self._get(Target.Memory)
        data = resp.get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['totalPass'], 256.0)
        self.assertEqual(data['swapPass'], 1.5)

    @patch('solox.view.apis.Memory')
    def test_collect_memory_detail_android(self, mock_mem_cls):
        detail = {
            'java_heap': 50.0,
            'native_heap': 100.0,
            'code_pss': 8.0,
            'stack_pss': 0.5,
            'graphics_pss': 40.0,
            'private_pss': 2.0,
            'system_pss': 1.0,
        }
        inst = MagicMock()
        inst.getAndroidMemoryDetail.return_value = detail
        mock_mem_cls.return_value = inst

        resp = self._get(Target.MemoryDetail)
        data = resp.get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['data']['java_heap'], 50.0)

    def test_collect_memory_detail_ios_not_supported(self):
        resp = self._get(
            Target.MemoryDetail,
            platform='iOS',
        )
        data = resp.get_json()
        self.assertEqual(data['status'], 0)
        self.assertIn('not support', data['msg'])

    @patch('solox.view.apis.Network')
    def test_collect_network_success(self, mock_net_cls):
        inst = MagicMock()
        inst.getNetWorkData.return_value = (10.5, 20.3)
        mock_net_cls.return_value = inst

        resp = self._get(Target.Network)
        data = resp.get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['upflow'], 10.5)
        self.assertEqual(data['downflow'], 20.3)

    @patch('solox.view.apis.FPS')
    def test_collect_fps_includes_meta(self, mock_fps_cls):
        inst = MagicMock()
        inst.getFPS.return_value = (60, 2)
        inst.fps_meta = {
            'source': 'surfaceflinger_latency',
            'fps': 60,
            'confidence': 'high',
            'verified': True,
            'fresh_frame_count': 58,
        }
        inst.big_jank = 1
        mock_fps_cls.return_value = inst

        resp = self._get(Target.FPS)
        data = resp.get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['fps'], 60)
        self.assertEqual(data['jank'], 2)
        self.assertEqual(data['big_jank'], 1)
        self.assertEqual(data['fps_meta']['confidence'], 'high')

    @patch('solox.view.apis.Battery')
    def test_collect_battery_android(self, mock_bat_cls):
        inst = MagicMock()
        inst.getBattery.return_value = (85, 32.5)
        mock_bat_cls.return_value = inst

        resp = self._get(Target.Battery)
        data = resp.get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['level'], 85)
        self.assertEqual(data['temperature'], 32.5)

    @patch('solox.view.apis.Battery')
    def test_collect_battery_ios(self, mock_bat_cls):
        inst = MagicMock()
        inst.getBattery.return_value = (33.0, 500.0, 4.1, 2.05)
        mock_bat_cls.return_value = inst

        resp = self._get(
            Target.Battery,
            platform='iOS',
            deviceid='00008030-001',
        )
        data = resp.get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['temperature'], 33.0)
        self.assertEqual(data['power'], 2.05)

    @patch('solox.view.apis.GPU')
    def test_collect_gpu_success(self, mock_gpu_cls):
        inst = MagicMock()
        inst.getGPU.return_value = 55.5
        mock_gpu_cls.return_value = inst

        resp = self._get(Target.GPU)
        data = resp.get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['gpu'], 55.5)
        mock_gpu_cls.assert_called_once()
        call_kwargs = mock_gpu_cls.call_args[1]
        self.assertEqual(call_kwargs['pkgName'], BASE_PARAMS['pkgname'])
        self.assertEqual(call_kwargs['deviceId'], BASE_PARAMS['deviceid'])

    def test_collect_unknown_target(self):
        resp = self._get('invalid_metric')
        data = resp.get_json()
        self.assertEqual(data['status'], 0)
        self.assertEqual(data['msg'], 'no this target')

    @patch('solox.view.apis.CPU')
    def test_collect_exception_returns_error_json(self, mock_cpu_cls):
        mock_cpu_cls.side_effect = RuntimeError('device offline')

        resp = self._get(Target.CPU)
        data = resp.get_json()

        self.assertEqual(data['status'], 0)
        self.assertIn('device offline', data['msg'])


class TestApmIosMetricHonesty(unittest.TestCase):
    """iOS 指标可信度：不支持的项返回 null + *_supported=false，而非伪造 0。"""

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def _get(self, target, **extra):
        params = {**BASE_PARAMS, 'target': target, **extra}
        return self.client.get(COLLECT_URL, query_string=params)

    @patch('solox.view.apis.FPS')
    def test_collect_fps_ios_jank_not_supported(self, mock_fps_cls):
        inst = MagicMock()
        inst.getFPS.return_value = (60, None)  # iOS: jank 无法测量
        inst.big_jank = None
        inst.fps_meta = None
        mock_fps_cls.return_value = inst

        data = self._get(
            Target.FPS, platform='iOS', deviceid='00008030-001',
        ).get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['fps'], 60)
        self.assertIsNone(data['jank'])
        self.assertIsNone(data['big_jank'])
        self.assertFalse(data['jank_supported'])

    @patch('solox.view.apis.Memory')
    def test_collect_memory_ios_swap_not_supported(self, mock_mem_cls):
        inst = MagicMock()
        inst.getProcessMemory.return_value = (256.0, None)  # iOS: 无 Swap
        mock_mem_cls.return_value = inst

        data = self._get(
            Target.Memory, platform='iOS', deviceid='00008030-001',
        ).get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['totalPass'], 256.0)
        self.assertIsNone(data['swapPass'])
        self.assertFalse(data['swap_supported'])

    @patch('solox.view.apis.FPS')
    def test_collect_fps_android_jank_supported_flag(self, mock_fps_cls):
        inst = MagicMock()
        inst.getFPS.return_value = (60, 2)
        inst.big_jank = 1
        inst.fps_meta = None
        mock_fps_cls.return_value = inst

        data = self._get(Target.FPS).get_json()  # 默认 Android

        self.assertEqual(data['jank'], 2)
        self.assertEqual(data['big_jank'], 1)
        self.assertTrue(data['jank_supported'])

    @patch('solox.view.apis.Memory')
    def test_collect_memory_android_swap_supported_flag(self, mock_mem_cls):
        inst = MagicMock()
        inst.getProcessMemory.return_value = (256.0, 1.5)
        mock_mem_cls.return_value = inst

        data = self._get(Target.Memory).get_json()  # 默认 Android

        self.assertEqual(data['swapPass'], 1.5)
        self.assertTrue(data['swap_supported'])

    @patch('solox.view.apis.GPU')
    def test_collect_gpu_ios_exposes_renderer_tiler(self, mock_gpu_cls):
        inst = MagicMock()
        inst.getGPU.return_value = 62.0
        inst.renderer = 40.0
        inst.tiler = 25.0
        mock_gpu_cls.return_value = inst

        data = self._get(
            Target.GPU, platform='iOS', deviceid='00008030-001',
        ).get_json()

        self.assertEqual(data['status'], 1)
        self.assertEqual(data['gpu'], 62.0)
        self.assertEqual(data['renderer'], 40.0)
        self.assertEqual(data['tiler'], 25.0)
        self.assertTrue(data['gpu_detail_supported'])

    @patch('solox.view.apis.GPU')
    def test_collect_gpu_android_has_no_gpu_detail(self, mock_gpu_cls):
        inst = MagicMock()
        inst.getGPU.return_value = 55.5
        inst.renderer = None  # 真实 Android GPU 对象即为 None
        inst.tiler = None
        mock_gpu_cls.return_value = inst

        data = self._get(Target.GPU).get_json()  # 默认 Android

        self.assertEqual(data['gpu'], 55.5)
        self.assertNotIn('renderer', data)
        self.assertNotIn('gpu_detail_supported', data)


class TestMetricSupportHelpers(unittest.TestCase):
    """纯函数：Jank/Swap 平台能力标注辅助。"""

    def test_fps_jank_support_none_marks_unsupported(self):
        from solox.view import apis
        monitor = MagicMock()
        monitor.big_jank = None
        result = apis._apply_fps_jank_support({'status': 1, 'fps': 60}, monitor, None)
        self.assertIsNone(result['jank'])
        self.assertIsNone(result['big_jank'])
        self.assertFalse(result['jank_supported'])

    def test_fps_jank_support_value_marks_supported(self):
        from solox.view import apis
        monitor = MagicMock()
        monitor.big_jank = 3
        result = apis._apply_fps_jank_support({'status': 1, 'fps': 60}, monitor, 5)
        self.assertEqual(result['jank'], 5)
        self.assertEqual(result['big_jank'], 3)
        self.assertTrue(result['jank_supported'])

    def test_mem_swap_support_none_marks_unsupported(self):
        from solox.view import apis
        result = apis._apply_mem_swap_support({'status': 1, 'totalPass': 256.0}, None)
        self.assertIsNone(result['swapPass'])
        self.assertFalse(result['swap_supported'])

    def test_mem_swap_support_value_marks_supported(self):
        from solox.view import apis
        result = apis._apply_mem_swap_support({'status': 1, 'totalPass': 256.0}, 1.5)
        self.assertEqual(result['swapPass'], 1.5)
        self.assertTrue(result['swap_supported'])

    def test_gpu_detail_numeric_values_exposed(self):
        from solox.view import apis
        monitor = MagicMock()
        monitor.renderer = 40.0
        monitor.tiler = 25.0
        result = apis._apply_gpu_detail({'status': 1, 'gpu': 62.0}, monitor)
        self.assertEqual(result['renderer'], 40.0)
        self.assertEqual(result['tiler'], 25.0)
        self.assertTrue(result['gpu_detail_supported'])

    def test_gpu_detail_none_not_exposed(self):
        from solox.view import apis

        class _Bare:
            renderer = None
            tiler = None

        result = apis._apply_gpu_detail({'status': 1, 'gpu': 55.5}, _Bare())
        self.assertNotIn('renderer', result)
        self.assertNotIn('gpu_detail_supported', result)


class TestApmCollectApiMethods(unittest.TestCase):
    """Endpoint accepts GET and POST."""

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('solox.view.apis.CPU')
    def test_post_collect_cpu(self, mock_cpu_cls):
        inst = MagicMock()
        inst.getCpuRate.return_value = (5.0, 30.0)
        mock_cpu_cls.return_value = inst

        resp = self.client.post(
            COLLECT_URL,
            data={**BASE_PARAMS, 'target': Target.CPU},
        )
        self.assertEqual(resp.get_json()['status'], 1)


class TestHealthEndpoint(unittest.TestCase):
    """Docker / dev.sh / nginx healthcheck."""

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_health_returns_ok_and_version(self):
        resp = self.client.get('/health')
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['msg'], 'ok')
        self.assertIn('version', data)


if __name__ == '__main__':
    unittest.main()
