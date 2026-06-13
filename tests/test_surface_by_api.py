# -*- coding: utf-8 -*-
"""API-tiered Surface / FPS tests aligned with compatibility_matrix.yaml fixtures."""

import unittest
from unittest.mock import patch, MagicMock

from tests.matrix_loader import get_surface_fixtures, load_matrix
from solox.public.android_fps import GameSurfaceDetector, SurfaceStatsCollector


PKG = 'com.test.game'
DEVICE = 'test_device'


def _detector(sdk: int) -> GameSurfaceDetector:
    d = GameSurfaceDetector(DEVICE, PKG)
    d._sdk_version = sdk
    return d


def _mock_surfaces(detector, surfaces):
    return patch.object(detector, 'get_all_surfaces', return_value=surfaces)


class TestGameSurfaceDetectorByApi(unittest.TestCase):
    """Surface discovery behaviour per Android API tier."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures = get_surface_fixtures(load_matrix())

    def test_api_28_30_prefers_legacy_surfaceview_format(self):
        sdk = self.fixtures['api_28_30']['sdk']
        surfaces = self.fixtures['api_28_30']['surfaces']
        det = _detector(sdk)
        with _mock_surfaces(det, surfaces):
            candidates = det.get_candidate_surfaces()
        self.assertTrue(candidates[0].startswith('SurfaceView'))
        self.assertIn('UnityPlayerActivity', candidates[0])

    def test_api_31_33_supports_blast_format(self):
        sdk = self.fixtures['api_31_33']['sdk']
        surfaces = self.fixtures['api_31_33']['surfaces']
        det = _detector(sdk)
        with _mock_surfaces(det, surfaces):
            candidates = det.get_candidate_surfaces()
        self.assertTrue(any('BLAST' in s for s in candidates))

    def test_api_34_36_activity_level_surface_ranked(self):
        sdk = self.fixtures['api_34_36']['sdk']
        surfaces = self.fixtures['api_34_36']['surfaces']
        det = _detector(sdk)
        with _mock_surfaces(det, surfaces):
            candidates = det.get_candidate_surfaces()
        self.assertTrue(any(PKG in s and 'Activity' in s for s in candidates))

    def test_unity_surface_detected_as_game(self):
        det = _detector(35)
        surface = (
            'SurfaceView - com.test.game/com.unity3d.player.UnityPlayerActivity#0'
        )
        self.assertTrue(det.is_game_surface(surface))
        self.assertEqual(det.detect_game_engine(surface), 'unity')

    def test_unreal_surface_detected(self):
        det = _detector(35)
        surface = 'com.test.game/com.epicgames.unreal.GameActivity#0'
        self.assertEqual(det.detect_game_engine(surface), 'unreal')

    def test_cocos_surface_detected(self):
        det = _detector(31)
        surface = 'SurfaceView - com.test.game/org.cocos2dx.lib.Cocos2dxActivity#0'
        self.assertEqual(det.detect_game_engine(surface), 'cocos')

    @patch('solox.public.android_fps.adb.shell')
    def test_sdk_version_read_from_device(self, mock_shell):
        mock_shell.return_value = '35'
        det = GameSurfaceDetector(DEVICE, PKG)
        self.assertEqual(det.get_sdk_version(), 35)
        mock_shell.assert_called_with(
            cmd='getprop ro.build.version.sdk', deviceId=DEVICE
        )

    def test_page_flip_preferred_api_26_27_only(self):
        for sdk in (26, 27):
            det = _detector(sdk)
            self.assertTrue(
                det.should_prefer_page_flip(),
                f'API {sdk} should prefer page flip',
            )
        for sdk in (28, 30, 31, 35, 36):
            det = _detector(sdk)
            self.assertFalse(
                det.should_prefer_page_flip(),
                f'API {sdk} should not force page flip',
            )

    def test_game_surface_priority_over_normal(self):
        det = _detector(31)
        surfaces = [
            'SurfaceView - com.test.game/com.test.game.MainActivity#1',
            'SurfaceView - com.test.game/com.unity3d.player.UnityPlayerActivity#0',
        ]
        with _mock_surfaces(det, surfaces):
            candidates = det.get_candidate_surfaces()
        self.assertIn('UnityPlayerActivity', candidates[0])


class TestSurfaceActivityParsingByApi(unittest.TestCase):
    """get_surfaceview_activity must parse all matrix surface formats."""

    def _collector(self):
        return SurfaceStatsCollector(
            device=DEVICE,
            frequency=1,
            package_name=PKG,
            fps_queue=None,
            jank_threshold=166,
            surfaceview=True,
        )

    @patch('solox.public.android_fps.adb.shell')
    def test_parse_legacy_surfaceview_dash_format(self, mock_shell):
        line = f'SurfaceView - {PKG}/com.unity3d.player.UnityPlayerActivity#0'
        mock_shell.return_value = line
        c = self._collector()
        activity = c.get_surfaceview_activity()
        self.assertEqual(activity, f'{PKG}/com.unity3d.player.UnityPlayerActivity')

    @patch('solox.public.android_fps.adb.shell')
    def test_parse_blast_format(self, mock_shell):
        line = f'SurfaceView[{PKG}](BLAST)#0'
        mock_shell.return_value = line
        c = self._collector()
        activity = c.get_surfaceview_activity()
        self.assertEqual(activity, PKG)

    @patch('solox.public.android_fps.adb.shell')
    def test_parse_activity_level_format(self, mock_shell):
        line = f'{PKG}/com.unity3d.player.UnityPlayerActivity#0'
        mock_shell.return_value = line
        c = self._collector()
        activity = c.get_surfaceview_activity()
        self.assertEqual(activity, f'{PKG}/com.unity3d.player.UnityPlayerActivity')


class TestMatrixDrivenApiCoverage(unittest.TestCase):
    """Every API in metrics.fps.l1_mock_apis must have page_flip policy defined."""

    def test_l1_mock_apis_have_documented_policy(self):
        matrix = load_matrix()
        mock_apis = matrix['metrics']['fps']['l1_mock_apis']
        for api in mock_apis:
            det = _detector(api)
            # Policy must be deterministic (bool), not raise
            self.assertIsInstance(det.should_prefer_page_flip(), bool)


if __name__ == '__main__':
    unittest.main()
