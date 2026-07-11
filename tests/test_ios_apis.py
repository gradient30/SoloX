# -*- coding: utf-8 -*-
"""iOS 扩展后端 Web 端点集成测试（mocked，无真机）。

验证 apis.py 中 iOS 平台的弱网路由与新增 iOS 端点的接线正确性。
"""

import unittest
from unittest.mock import patch


class TestIOSApis(unittest.TestCase):
    """经 Flask 测试客户端验证 iOS 端点。"""

    def setUp(self):
        from solox.web import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_ios_backend_capabilities(self):
        resp = self.client.get('/apm/ios/backend')
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['backend'], 'pymobiledevice3')
        self.assertIn('features', data)

    @patch('solox.view.apis.d.getIdbyDevice', return_value='UDID')
    @patch(
        'solox.public.ios_ext.weaknet.IOSWeakNetManager.list_profiles'
    )
    def test_weaknet_ios_profiles(self, mock_list, _mock_id):
        mock_list.return_value = [
            {'identifier': 'SlowNetworkCondition', 'name': 'NLC',
             'is_destructive': False, 'profiles': []}
        ]
        resp = self.client.get(
            '/apm/weaknet/ios/profiles', query_string={'device': 'x'}
        )
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertEqual(len(data['profiles']), 1)
        mock_list.assert_called_once_with('UDID')

    @patch('solox.view.apis.d.getIdbyDevice', return_value='UDID')
    @patch('solox.public.ios_ext.weaknet.IOSWeakNetManager.apply')
    def test_weaknet_apply_routes_ios(self, mock_apply, _mock_id):
        mock_apply.return_value = {
            'engine': 'ios_condition_inducer',
            'active': True,
            'profile_identifier': '3G-GoodNetwork',
        }
        resp = self.client.get(
            '/apm/weaknet/apply',
            query_string={
                'platform': 'iOS',
                'device': 'x',
                'preset': '3G-GoodNetwork',
            },
        )
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertTrue(data['active'])
        mock_apply.assert_called_once_with('UDID', '3G-GoodNetwork')

    @patch('solox.view.apis.d.getIdbyDevice', return_value='UDID')
    @patch('solox.public.ios_ext.weaknet.IOSWeakNetManager.clear')
    def test_weaknet_clear_routes_ios(self, mock_clear, _mock_id):
        mock_clear.return_value = {
            'engine': 'ios_condition_inducer', 'active': False
        }
        resp = self.client.get(
            '/apm/weaknet/clear',
            query_string={'platform': 'iOS', 'device': 'x'},
        )
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertFalse(data['active'])
        mock_clear.assert_called_once_with('UDID')

    @patch('solox.view.apis.d.getIdbyDevice', return_value='UDID')
    @patch('solox.public.ios_ext.weaknet.IOSWeakNetManager.apply')
    def test_weaknet_apply_off_clears(self, mock_apply, _mock_id):
        with patch(
            'solox.public.ios_ext.weaknet.IOSWeakNetManager.clear'
        ) as mock_clear:
            mock_clear.return_value = {
                'engine': 'ios_condition_inducer', 'active': False
            }
            resp = self.client.get(
                '/apm/weaknet/apply',
                query_string={
                    'platform': 'iOS', 'device': 'x', 'preset': 'off'
                },
            )
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertFalse(data['active'])
        mock_apply.assert_not_called()

    @patch('solox.view.apis.d.getIdbyDevice', return_value='UDID')
    @patch('solox.public.ios_ext.screen.take_screenshot')
    def test_ios_screenshot(self, mock_shot, _mock_id):
        mock_shot.return_value = b'\x89PNG\r\n\x1a\n'
        resp = self.client.get(
            '/apm/ios/screenshot', query_string={'device': 'x'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['Content-Type'], 'image/png')
        self.assertEqual(resp.data, b'\x89PNG\r\n\x1a\n')

    @patch('solox.view.apis.d.getIdbyDevice', return_value='UDID')
    @patch('solox.public.ios_ext.frametime.measure_jank')
    def test_ios_jank(self, mock_measure, _mock_id):
        mock_measure.return_value = {
            'frames': 300, 'fps': 60, 'jank': 2, 'big_jank': 0,
            'stutter_rate': 0.0067, 'big_stutter_rate': 0.0,
            'raw_events': 1200, 'supported': True,
        }
        resp = self.client.get(
            '/apm/ios/jank',
            query_string={'device': 'x', 'duration': '5'},
        )
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['jank'], 2)
        self.assertTrue(data['supported'])
        mock_measure.assert_called_once()


if __name__ == '__main__':
    unittest.main()
