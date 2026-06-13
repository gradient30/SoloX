# -*- coding: utf-8 -*-
"""Report screen recording: resolve path, info API, stream with Range."""

import os
import tempfile
import unittest
from unittest.mock import patch

from solox.public.common import File


class TestResolveRecordVideo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.f = File()
        self.f.report_dir = self.tmp

    def _scene_dir(self, scene):
        path = os.path.join(self.tmp, scene)
        os.makedirs(path, exist_ok=True)
        return path

    def test_mp4_browser_playable(self):
        scene = 'apm_2026_test'
        self._scene_dir(scene)
        mp4 = os.path.join(self.tmp, scene, 'record.mp4')
        with open(mp4, 'wb') as fh:
            fh.write(b'\x00' * 128)
        info = self.f.resolve_record_video(scene)
        self.assertIsNotNone(info)
        self.assertEqual(info['format'], 'mp4')
        self.assertTrue(info['browser_playable'])
        self.assertEqual(info['size'], 128)

    def test_mkv_not_browser_playable(self):
        scene = 'apm_mkv'
        self._scene_dir(scene)
        with open(os.path.join(self.tmp, scene, 'record.mkv'), 'wb') as fh:
            fh.write(b'\x00' * 64)
        info = self.f.resolve_record_video(scene)
        self.assertEqual(info['format'], 'mkv')
        self.assertFalse(info['browser_playable'])

    def test_mp4_preferred_over_mkv(self):
        scene = 'apm_both'
        d = self._scene_dir(scene)
        with open(os.path.join(d, 'record.mkv'), 'wb') as fh:
            fh.write(b'mkv')
        with open(os.path.join(d, 'record.mp4'), 'wb') as fh:
            fh.write(b'mp4')
        info = self.f.resolve_record_video(scene)
        self.assertEqual(info['format'], 'mp4')

    def test_rejects_path_traversal(self):
        self.assertIsNone(self.f.resolve_record_video('../etc/passwd'))
        self.assertIsNone(self.f.resolve_record_video('foo/bar'))

    def test_missing_scene(self):
        self.assertIsNone(self.f.resolve_record_video('apm_no_such_scene'))


class TestRecordPlayerApi(unittest.TestCase):

    def setUp(self):
        from solox.web import app
        from solox.view import apis
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.apis = apis
        self._orig_report_dir = apis.f.report_dir
        self.tmp = tempfile.mkdtemp()
        apis.f.report_dir = self.tmp
        self.scene = 'apm_player_test'
        os.makedirs(os.path.join(self.tmp, self.scene))
        self.mp4 = os.path.join(self.tmp, self.scene, 'record.mp4')
        with open(self.mp4, 'wb') as fh:
            fh.write(b'\x00' * 256)

    def tearDown(self):
        self.apis.f.report_dir = self._orig_report_dir

    def test_record_info_mp4(self):
        resp = self.client.get('/apm/record/info', query_string={'scene': self.scene})
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['status'], 1)
        self.assertEqual(data['format'], 'mp4')
        self.assertTrue(data['browser_playable'])

    def test_record_info_not_found(self):
        resp = self.client.get('/apm/record/info', query_string={'scene': 'missing'})
        self.assertEqual(resp.get_json()['status'], 0)

    def test_record_stream_full(self):
        resp = self.client.get('/apm/record/stream', query_string={'scene': self.scene})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('video/mp4', resp.content_type)
        self.assertEqual(resp.data, b'\x00' * 256)

    def test_record_stream_range(self):
        resp = self.client.get(
            '/apm/record/stream',
            query_string={'scene': self.scene},
            headers={'Range': 'bytes=0-99'},
        )
        self.assertIn(resp.status_code, (200, 206))
        self.assertLessEqual(len(resp.data), 100)

    @patch('solox.view.apis.Scrcpy.play_video')
    def test_record_play_system(self, mock_play):
        resp = self.client.get('/apm/record/play', query_string={'scene': self.scene})
        data = resp.get_json()
        self.assertEqual(data['status'], 1)
        mock_play.assert_called_once_with(self.mp4)


if __name__ == '__main__':
    unittest.main()
