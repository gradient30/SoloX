# -*- coding: utf-8 -*-
"""Report screen recording: resolve path, info API, stream with Range."""

import os
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from solox.public.common import File, Scrcpy


def _fake_mp4_payload(extra=b''):
    """Minimal bytes that pass finalize validation (ftyp + moov)."""
    body = b'\x00' * 4 + b'ftyp' + b'isom' + b'\x00' * 4 + extra
    body += b'\x00' * 2000 + b'moov' + b'\x00' * 64
    return body


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
            fh.write(_fake_mp4_payload())
        info = self.f.resolve_record_video(scene)
        self.assertIsNotNone(info)
        self.assertEqual(info['format'], 'mp4')
        self.assertTrue(info['browser_playable'])
        self.assertGreater(info['size'], 128)

    def test_mkv_system_player_fallback(self):
        scene = 'apm_mkv'
        self._scene_dir(scene)
        with open(os.path.join(self.tmp, scene, 'record.mkv'), 'wb') as fh:
            fh.write(b'\x1aE\xdf\xa3' + b'\x00' * 3000)
        info = self.f.resolve_record_video(scene)
        self.assertEqual(info['format'], 'mkv')
        self.assertFalse(info['browser_playable'])

    def test_mp4_preferred_over_mkv(self):
        scene = 'apm_both'
        d = self._scene_dir(scene)
        with open(os.path.join(d, 'record.mkv'), 'wb') as fh:
            fh.write(b'mkv')
        with open(os.path.join(d, 'record.mp4'), 'wb') as fh:
            fh.write(_fake_mp4_payload(b'mp4'))
        info = self.f.resolve_record_video(scene)
        self.assertEqual(info['format'], 'mp4')

    def test_rejects_path_traversal(self):
        self.assertIsNone(self.f.resolve_record_video('../etc/passwd'))
        self.assertIsNone(self.f.resolve_record_video('foo/bar'))

    def test_missing_scene(self):
        self.assertIsNone(self.f.resolve_record_video('apm_no_such_scene'))

    def test_truncated_mp4_rejected(self):
        scene = 'apm_bad_mp4'
        self._scene_dir(scene)
        path = os.path.join(self.tmp, scene, 'record.mp4')
        with open(path, 'wb') as fh:
            fh.write(b'\x00' * 4 + b'ftyp' + b'isom' + b'\x00' * 100)
        self.assertIsNone(self.f.resolve_record_video(scene))

    def test_faststart_mp4_with_moov_near_head_is_valid(self):
        scene = 'apm_faststart_mp4'
        self._scene_dir(scene)
        path = os.path.join(self.tmp, scene, 'record.mp4')
        with open(path, 'wb') as fh:
            fh.write(b'\x00' * 4 + b'ftyp' + b'isom' + b'\x00' * 128 + b'moov')
            fh.seek(3 * 1024 * 1024)
            fh.write(b'\x00')

        info = self.f.resolve_record_video(scene)

        self.assertIsNotNone(info)
        self.assertEqual(info['format'], 'mp4')


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
            fh.write(_fake_mp4_payload(b'\x00' * 128))

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
        self.assertEqual(resp.data, _fake_mp4_payload(b'\x00' * 128))

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

    @patch('solox.view.apis.Scrcpy.record_status')
    def test_record_status_api(self, mock_status):
        mock_status.return_value = {
            'status': 1,
            'recording': True,
            'elapsed_seconds': 42,
            'elapsed_label': '00:00:42',
            'risk_level': 'normal',
            'healthy': True,
        }

        resp = self.client.get('/apm/record/status')
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['status'], 1)
        self.assertTrue(data['recording'])
        self.assertEqual(data['elapsed_label'], '00:00:42')
        mock_status.assert_called_once_with()


class _FakeProcess:
    """subprocess.Popen 的完整测试替身。

    补齐 poll/wait/terminate/kill/send_signal/communicate 与上下文管理协议，
    使其在任意平台的启动/清理路径下（如非 Windows 走 send_signal(SIGINT) →
    terminate → kill 的优雅停止链）都不会因缺少属性抛 AttributeError/TypeError。
    """

    pid = 12345
    returncode = None

    def poll(self):
        return None

    def wait(self, timeout=None):
        return 0

    def send_signal(self, _sig):
        return None

    def terminate(self):
        return None

    def kill(self):
        return None

    def communicate(self, input=None, timeout=None):
        return (b'', b'')

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _ExitedProcess:

    pid = 12345
    returncode = 1

    def poll(self):
        return 1

    def wait(self, timeout=None):
        return 1

    def send_signal(self, _sig):
        return None

    def terminate(self):
        return None

    def kill(self):
        return None

    def communicate(self, input=None, timeout=None):
        return (b'', b'')

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class TestScrcpyRecordPipeline(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        Scrcpy._record_process = None
        Scrcpy._record_stderr = None
        Scrcpy._record_error = ''
        Scrcpy._record_report_error = ''
        Scrcpy._record_started_at = None
        Scrcpy._record_file = ''
        Scrcpy._record_device = ''
        Scrcpy._record_quality = ''

    def tearDown(self):
        Scrcpy._record_process = None
        Scrcpy._close_record_stderr()
        Scrcpy._record_error = ''
        Scrcpy._record_report_error = ''
        Scrcpy._record_started_at = None
        Scrcpy._record_file = ''
        Scrcpy._record_device = ''
        Scrcpy._record_quality = ''

    def test_find_ffmpeg_binary_ignores_missing_configured_path(self):
        missing = os.path.join(self.tmp, 'missing', 'ffmpeg.exe')

        with (
            patch.dict(os.environ, {'SOLOX_FFMPEG': missing}),
            patch.object(Scrcpy, 'STATICPATH', self.tmp),
            patch('solox.public.common.shutil.which', return_value=None),
        ):
            self.assertEqual(Scrcpy._find_ffmpeg_binary(), '')

    def test_find_ffmpeg_binary_uses_existing_configured_path(self):
        ffmpeg = os.path.join(self.tmp, 'ffmpeg.exe')
        with open(ffmpeg, 'wb') as fh:
            fh.write(b'')

        with (
            patch.dict(os.environ, {'SOLOX_FFMPEG': ffmpeg}),
            patch('solox.public.common.shutil.which', return_value=None),
        ):
            self.assertEqual(Scrcpy._find_ffmpeg_binary(), ffmpeg)

    def test_start_record_requires_ffmpeg_before_launch(self):
        with (
            patch.object(Scrcpy, '_find_ffmpeg_binary', return_value=''),
            patch('solox.public.common.subprocess.Popen') as mock_popen,
        ):
            result = Scrcpy.start_record('device-1', quality='720p')

        self.assertEqual(result, 1)
        self.assertIn('ffmpeg', Scrcpy.last_record_error().lower())
        mock_popen.assert_not_called()

    def test_start_record_uses_mkv_container_before_remux(self):
        popen_calls = []

        def fake_popen(args, **kwargs):
            popen_calls.append(args)
            return _FakeProcess()

        with (
            patch.object(File, 'get_repordir', return_value=self.tmp),
            patch.object(Scrcpy, '_find_ffmpeg_binary', return_value='ffmpeg'),
            patch('solox.public.common.subprocess.Popen', side_effect=fake_popen),
            patch('solox.public.common.time.sleep', return_value=None),
        ):
            result = Scrcpy.start_record('device-1', quality='720p')

        self.assertEqual(result, 0)
        args = popen_calls[0]
        self.assertIn('--record={}'.format(os.path.join(self.tmp, 'record.mkv')), args)
        self.assertIn('--record-format=mkv', args)
        self.assertNotIn('--record={}'.format(os.path.join(self.tmp, 'record.mp4')), args)

    def test_record_presets_use_game_friendly_bitrates(self):
        self.assertEqual(Scrcpy.RECORD_PRESETS['1080p']['bitrate'], '16M')
        self.assertEqual(Scrcpy.RECORD_PRESETS['720p']['bitrate'], '8M')
        self.assertEqual(Scrcpy.RECORD_PRESETS['480p']['bitrate'], '4M')

    def test_remux_recording_to_mp4_uses_ffmpeg_copy_and_validates_output(self):
        mkv = os.path.join(self.tmp, 'record.mkv')
        mp4 = os.path.join(self.tmp, 'record.mp4')
        with open(mkv, 'wb') as fh:
            fh.write(b'\x1aE\xdf\xa3' + b'\x00' * 3000)

        def fake_run(args, **kwargs):
            self.assertEqual(args[0], 'ffmpeg')
            self.assertIn('-c', args)
            self.assertIn('copy', args)
            self.assertNotIn('capture_output', kwargs)
            self.assertNotEqual(kwargs.get('stdout'), subprocess.PIPE)
            self.assertNotEqual(kwargs.get('stderr'), subprocess.PIPE)
            self.assertIsNotNone(kwargs.get('stdout'))
            self.assertIs(kwargs.get('stdout'), kwargs.get('stderr'))
            tmp_output = args[-1]
            self.assertTrue(tmp_output.endswith('.mp4'))
            self.assertNotEqual(os.path.basename(tmp_output), 'record.mp4')
            with open(tmp_output, 'wb') as fh:
                fh.write(_fake_mp4_payload())
            return subprocess.CompletedProcess(args, 0, stdout='', stderr='')

        with (
            patch.object(Scrcpy, '_find_ffmpeg_binary', return_value='ffmpeg'),
            patch('solox.public.common.subprocess.run', side_effect=fake_run),
        ):
            result = Scrcpy._remux_recording_to_mp4(self.tmp)

        self.assertEqual(result, mp4)
        self.assertTrue(File._is_valid_record_file(mp4, 'mp4'))

    def test_record_status_reports_elapsed_size_and_warning_level(self):
        record_path = os.path.join(self.tmp, 'record.mkv')
        with open(record_path, 'wb') as fh:
            fh.write(b'\x00' * 4096)
        Scrcpy._record_process = _FakeProcess()
        Scrcpy._record_started_at = 100.0
        Scrcpy._record_file = record_path
        Scrcpy._record_device = 'device-1'
        Scrcpy._record_quality = '720p'

        with patch('solox.public.common.time.time', return_value=1060.0):
            status = Scrcpy.record_status()

        self.assertEqual(status['status'], 1)
        self.assertTrue(status['recording'])
        self.assertTrue(status['healthy'])
        self.assertEqual(status['elapsed_seconds'], 960)
        self.assertEqual(status['elapsed_label'], '00:16:00')
        self.assertEqual(status['risk_level'], 'warning')
        self.assertEqual(status['file_size'], 4096)
        self.assertEqual(status['device'], 'device-1')
        self.assertEqual(status['quality'], '720p')

    def test_record_status_reports_exited_process_without_valid_video(self):
        record_path = os.path.join(self.tmp, 'record.mkv')
        with open(record_path, 'wb') as fh:
            fh.write(b'')
        Scrcpy._record_process = _ExitedProcess()
        Scrcpy._record_started_at = 100.0
        Scrcpy._record_file = record_path

        with patch('solox.public.common.time.time', return_value=130.0):
            status = Scrcpy.record_status()

        self.assertEqual(status['status'], 1)
        self.assertFalse(status['recording'])
        self.assertFalse(status['healthy'])
        self.assertIn('no valid recording', status['error'])

    def test_stop_record_uses_long_finalize_wait_and_records_empty_file_error(self):
        record_path = os.path.join(self.tmp, 'record.mkv')
        with open(record_path, 'wb') as fh:
            fh.write(b'')
        Scrcpy._record_process = _ExitedProcess()
        Scrcpy._record_started_at = 100.0
        Scrcpy._record_file = record_path

        with (
            patch.object(File, 'get_repordir', return_value=self.tmp),
            patch.object(File, 'wait_for_record_file', return_value=None) as mock_wait,
            patch('solox.public.common.time.time', return_value=1180.0),
        ):
            Scrcpy.stop_record()

        self.assertGreaterEqual(mock_wait.call_args.kwargs['timeout'], 90.0)
        self.assertIn('empty', Scrcpy.last_record_error())
        self.assertEqual(Scrcpy.record_result_error(), Scrcpy.last_record_error())

    def test_make_report_persists_record_error_when_video_missing(self):
        Scrcpy._record_report_error = 'recording source file is empty'

        with patch.object(File, 'get_repordir', return_value=self.tmp):
            f = File()
            scene = f.make_report(
                app='com.example',
                devices='device-1',
                video=0,
                platform='Android',
            )

        result_path = os.path.join(self.tmp, scene, 'result.json')
        with open(result_path, encoding='utf-8') as fh:
            result = json.load(fh)

        self.assertEqual(result['video'], 0)
        self.assertEqual(result['record_error'], 'recording source file is empty')


if __name__ == '__main__':
    unittest.main()
