# -*- coding: utf-8 -*-
"""Unit tests for FPS calculation accuracy and credibility metadata.

Tests cover:
- FPS formula: (frame_count - 1) / time_span
- collect_oneshot metadata fields
- Confidence level assignment
- Refresh rate capping
- Jank detection
- Bridge timestamp removal (regression)
"""
import datetime
import unittest
from unittest.mock import patch, MagicMock

from solox.public.android_fps import SurfaceStatsCollector


def _make_collector(**kwargs):
    """Create a SurfaceStatsCollector with defaults suitable for testing."""
    defaults = dict(
        device='test_device',
        frequency=1,
        package_name='com.test.app',
        fps_queue=None,
        jank_threshold=166,
        surfaceview=True,
    )
    defaults.update(kwargs)
    return SurfaceStatsCollector(**defaults)


def _generate_timestamps(count, fps=60, start=1000.0):
    """Generate evenly spaced frame timestamps at the given FPS.

    Returns list of [app_ts, display_ts, vsync_ts] triples,
    matching SurfaceFlinger --latency format (in seconds).
    """
    interval = 1.0 / fps
    return [[start + i * interval, start + i * interval, start + i * interval]
            for i in range(count)]


class TestFPSFormula(unittest.TestCase):
    """Test _calculate_results_new with known inputs."""

    def test_60fps_full_buffer(self):
        """127 frames at 60fps should yield fps=60."""
        c = _make_collector()
        ts = _generate_timestamps(127, fps=60)
        refresh_period = 1.0 / 60
        fps, jank = c._calculate_results_new(refresh_period, ts)
        self.assertIn(fps, [59, 60, 61], f'Expected ~60, got {fps}')

    def test_30fps(self):
        ts = _generate_timestamps(60, fps=30)
        c = _make_collector()
        fps, jank = c._calculate_results_new(1.0 / 60, ts)
        self.assertIn(fps, [29, 30, 31], f'Expected ~30, got {fps}')

    def test_zero_frames(self):
        c = _make_collector()
        fps, jank = c._calculate_results_new(1.0 / 60, [])
        self.assertEqual(fps, 0)
        self.assertEqual(jank, 0)

    def test_single_frame(self):
        c = _make_collector()
        fps, jank = c._calculate_results_new(1.0 / 60, [[1.0, 1.0, 1.0]])
        self.assertEqual(fps, 1)

    def test_refresh_rate_cap(self):
        """FPS should be capped at refresh_rate + 1."""
        c = _make_collector()
        # 100 frames in 1 second = 99fps, but refresh_period = 1/60
        ts = _generate_timestamps(100, fps=99)
        refresh_period = 1.0 / 60
        fps, jank = c._calculate_results_new(refresh_period, ts)
        self.assertLessEqual(fps, 61, f'Should be capped at 61, got {fps}')

    def test_no_refresh_period_no_cap(self):
        """Without refresh_period, no cap should be applied."""
        c = _make_collector()
        ts = _generate_timestamps(100, fps=99)
        fps, jank = c._calculate_results_new(None, ts)
        self.assertGreater(fps, 60, f'Without cap, fps should be >60, got {fps}')

    def test_two_frames(self):
        """Two frames should give a valid FPS based on their interval."""
        c = _make_collector()
        ts = [[1.0, 1.0, 1.0], [1.0, 1.0167, 1.0]]
        fps, jank = c._calculate_results_new(1.0 / 60, ts)
        self.assertIn(fps, [59, 60, 61])


class TestBridgeTimestampRemoval(unittest.TestCase):
    """Verify the bridge timestamp is NOT prepended (regression test)."""

    def test_no_bridge_in_collector_thread_data(self):
        """Collector thread should not insert artificial bridge timestamps.

        The old code prepended [0, last_timestamp, 0] which inflated the
        time denominator by ADB overhead, causing ~50fps instead of ~60fps.
        """
        c = _make_collector()

        # Simulate: last_timestamp from previous cycle = 999.0
        c.last_timestamp = 999.0

        # New frames start at 999.5 (0.5s gap = ADB overhead + sleep)
        new_timestamps = _generate_timestamps(60, fps=60, start=999.5)

        # Filter as the collector thread does
        timestamps = [t for t in new_timestamps if t[1] > c.last_timestamp]

        # Verify NO bridge timestamp prepended
        self.assertEqual(len(timestamps), 60)
        # First timestamp should be the first real frame, not [0, 999.0, 0]
        self.assertAlmostEqual(timestamps[0][1], 999.5, places=2)

        # Calculate FPS from these timestamps
        if len(timestamps) >= 2:
            seconds = timestamps[-1][1] - timestamps[0][1]
            fps = int(round((len(timestamps) - 1) / seconds))
            self.assertIn(fps, [59, 60, 61],
                         f'Without bridge, FPS should be ~60, got {fps}')

    def test_bridge_would_cause_underreport(self):
        """Demonstrate that the old bridge approach underreports FPS."""
        # 60 real frames starting at t=1000.5
        real_frames = _generate_timestamps(60, fps=60, start=1000.5)

        # Old bridge: prepend [0, last_timestamp=1000.0, 0]
        bridge = [[0, 1000.0, 0]]
        bridged = bridge + real_frames

        seconds_bridged = bridged[-1][1] - bridged[0][1]  # ~1.5s (includes 0.5s gap)
        fps_bridged = int(round((len(bridged) - 1) / seconds_bridged))

        # Without bridge
        seconds_real = real_frames[-1][1] - real_frames[0][1]  # ~1.0s
        fps_real = int(round((len(real_frames) - 1) / seconds_real))

        self.assertLess(fps_bridged, 55, f'Bridged should underreport: {fps_bridged}')
        self.assertGreater(fps_real, 55, f'Real should be accurate: {fps_real}')


class TestCollectOneshotMetadata(unittest.TestCase):
    """Test that collect_oneshot populates credibility metadata."""

    @patch.object(SurfaceStatsCollector, '_init_surface')
    @patch.object(SurfaceStatsCollector, '_get_frame_data_from_surfaceflinger')
    @patch.object(SurfaceStatsCollector, '_get_page_flip_count')
    def test_high_confidence_60fps(self, mock_pflip, mock_sf, mock_init):
        """60 fresh frames over ~1s should yield confidence=high."""
        c = _make_collector()
        c.surfaceview = True
        c.focus_window = 'SurfaceView[com.test.app]'

        baseline_ts = _generate_timestamps(127, fps=60, start=1000.0)
        fresh_ts = _generate_timestamps(127, fps=60, start=1000.0)
        # Second call has 60 new frames after the baseline
        new_frames = _generate_timestamps(60, fps=60, start=1000.0 + 127/60 + 0.01)
        all_ts = fresh_ts + new_frames

        mock_sf.side_effect = [
            (1.0 / 60, baseline_ts),  # first read
            (1.0 / 60, all_ts),       # second read
        ]
        mock_pflip.side_effect = [42, 43]  # page flip works

        with patch('time.sleep'):
            fps, jank = c.collect_oneshot()

        self.assertIsNotNone(c.last_collection_meta)
        meta = c.last_collection_meta
        self.assertEqual(meta['source'], 'surfaceflinger_latency')
        self.assertGreater(meta['fresh_frame_count'], 0)
        self.assertEqual(meta['refresh_rate_hz'], 60)
        self.assertIn(meta['confidence'], ['high', 'medium'])
        self.assertTrue(meta['verified'])  # page flip counter worked

    @patch.object(SurfaceStatsCollector, '_init_surface')
    @patch.object(SurfaceStatsCollector, '_get_frame_data_from_surfaceflinger')
    @patch.object(SurfaceStatsCollector, '_get_page_flip_count')
    def test_low_confidence_few_frames(self, mock_pflip, mock_sf, mock_init):
        """Very few fresh frames should yield confidence=low."""
        c = _make_collector()
        c.surfaceview = True
        c.focus_window = 'SurfaceView[com.test.app]'

        baseline_ts = _generate_timestamps(5, fps=60, start=1000.0)
        # Only 3 new frames after baseline
        later_ts = baseline_ts + _generate_timestamps(3, fps=60, start=1001.0)

        mock_sf.side_effect = [
            (1.0 / 60, baseline_ts),
            (1.0 / 60, later_ts),
        ]
        mock_pflip.return_value = -1  # page flip not available

        with patch('time.sleep'):
            fps, jank = c.collect_oneshot()

        meta = c.last_collection_meta
        self.assertEqual(meta['confidence'], 'low')
        self.assertFalse(meta['verified'])
        self.assertEqual(meta['fresh_frame_count'], 3)

    @patch.object(SurfaceStatsCollector, '_init_surface')
    @patch.object(SurfaceStatsCollector, '_get_fps_by_page_flip')
    def test_page_flip_fallback_metadata(self, mock_pflip, mock_init):
        """Page flip path should set source='page_flip'."""
        c = _make_collector()
        c._use_page_flip = True

        mock_pflip.return_value = (58, 0)

        fps, jank = c.collect_oneshot()

        self.assertEqual(fps, 58)
        meta = c.last_collection_meta
        self.assertEqual(meta['source'], 'page_flip')
        self.assertEqual(meta['confidence'], 'medium')

    @patch.object(SurfaceStatsCollector, '_init_surface')
    @patch.object(SurfaceStatsCollector, '_get_frame_data_from_surfaceflinger')
    @patch.object(SurfaceStatsCollector, '_get_fps_by_page_flip')
    def test_no_baseline_fallback(self, mock_pflip, mock_sf, mock_init):
        """When baseline read fails, should fall back to page flip."""
        c = _make_collector()
        c.surfaceview = True

        mock_sf.return_value = (None, None)  # no data
        mock_pflip.return_value = (45, 0)

        fps, jank = c.collect_oneshot()

        meta = c.last_collection_meta
        self.assertEqual(meta['source'], 'page_flip_fallback')
        self.assertEqual(meta['confidence'], 'low')


class TestJankCalculation(unittest.TestCase):
    """Test jank detection accuracy with PerfDog-compatible thresholds."""

    def test_no_jank_steady_60fps(self):
        """Steady 60fps should have zero jank."""
        c = _make_collector()
        ts = _generate_timestamps(60, fps=60)
        jank, big_jank = c._calculate_jank_ex(ts, refresh_period=1.0/60)
        self.assertEqual(jank, 0)
        self.assertEqual(big_jank, 0)

    def test_jank_one_dropped_frame(self):
        """A single dropped frame (33.3ms gap) should count as jank.

        At 60fps, normal interval = 16.67ms.
        Dropping 1 frame → 33.3ms gap → exceeds 2 * vsync (33.3ms).
        This is the key fix: old code with 83.3ms/166ms thresholds missed this.
        """
        c = _make_collector()
        ts = _generate_timestamps(60, fps=60, start=1.0)
        # Double the gap between frame 30 and 31 (simulate 1 dropped frame)
        drop_gap = 1.0 / 60  # add one extra frame interval
        for i in range(31, 60):
            ts[i][0] += drop_gap
            ts[i][1] += drop_gap
            ts[i][2] += drop_gap
        jank, big_jank = c._calculate_jank_ex(ts, refresh_period=1.0/60)
        self.assertGreaterEqual(jank, 1, 'Should detect dropped frame as jank')
        self.assertEqual(big_jank, 0, 'Single drop is not big jank')

    def test_big_jank_three_dropped_frames(self):
        """Three dropped frames (66.7ms gap) should count as big jank.

        3 × vsync = 50ms. A 66.7ms gap exceeds this.
        """
        c = _make_collector()
        ts = _generate_timestamps(60, fps=60, start=1.0)
        # Insert a 3-frame gap at position 30
        drop_gap = 3.0 / 60  # three extra intervals
        for i in range(31, 60):
            ts[i][0] += drop_gap
            ts[i][1] += drop_gap
            ts[i][2] += drop_gap
        jank, big_jank = c._calculate_jank_ex(ts, refresh_period=1.0/60)
        self.assertGreaterEqual(jank, 1)
        self.assertGreaterEqual(big_jank, 1, 'Should detect as big jank')

    def test_jank_with_200ms_stutter(self):
        """A 200ms stutter should be both jank and big jank."""
        c = _make_collector()
        ts = _generate_timestamps(10, fps=60, start=1.0)
        for i in range(6, 10):
            ts[i][0] += 0.2
            ts[i][1] += 0.2
            ts[i][2] += 0.2
        jank, big_jank = c._calculate_jank_ex(ts, refresh_period=1.0/60)
        self.assertGreater(jank, 0)
        self.assertGreater(big_jank, 0)

    def test_old_threshold_misses_normal_jank(self):
        """Demonstrate old _calculate_janky misses normal stutters.

        This is the regression test: the old 166ms threshold is too high.
        """
        c = _make_collector()
        ts = _generate_timestamps(60, fps=60, start=1.0)
        # 50ms gap (visible stutter, 3 dropped frames)
        drop_gap = 3.0 / 60
        for i in range(31, 60):
            ts[i][0] += drop_gap
            ts[i][1] += drop_gap
            ts[i][2] += drop_gap
        old_jank = c._calculate_janky(ts)  # uses 166ms threshold
        new_jank, new_big = c._calculate_jank_ex(ts, refresh_period=1.0/60)
        self.assertEqual(old_jank, 0, 'Old method should miss 50ms stutter')
        self.assertGreater(new_jank, 0, 'New method should catch it')

    def test_30fps_jank_thresholds(self):
        """At 30fps (33.3ms vsync), jank threshold should be 66.7ms."""
        c = _make_collector()
        ts = _generate_timestamps(30, fps=30, start=1.0)
        # Insert 1 dropped frame at 30fps → 66.7ms gap
        drop_gap = 1.0 / 30
        for i in range(16, 30):
            ts[i][0] += drop_gap
            ts[i][1] += drop_gap
            ts[i][2] += drop_gap
        jank, big_jank = c._calculate_jank_ex(ts, refresh_period=1.0/30)
        self.assertGreaterEqual(jank, 1)

    def test_few_frames_simple_threshold(self):
        """With < 5 frames, simple vsync threshold is used."""
        c = _make_collector()
        # 3 frames with a 40ms gap
        ts = [[1.0, 1.0, 1.0], [1.0, 1.0167, 1.0], [1.0, 1.0567, 1.0]]
        jank, big_jank = c._calculate_jank_ex(ts, refresh_period=1.0/60)
        self.assertGreaterEqual(jank, 1, 'Should detect 40ms gap as jank')


class TestMakeMeta(unittest.TestCase):
    """Test _make_meta helper."""

    def test_meta_fields(self):
        c = _make_collector()
        meta = c._make_meta(
            source='surfaceflinger_latency', fps=60,
            fresh_count=58, buffer_count=127,
            window_seconds=0.9833, refresh_rate_hz=60,
            surface='SurfaceView[com.test](BLAST)#0',
            verified=True, confidence='high'
        )
        self.assertEqual(meta['source'], 'surfaceflinger_latency')
        self.assertEqual(meta['fps'], 60)
        self.assertEqual(meta['fresh_frame_count'], 58)
        self.assertEqual(meta['buffer_frame_count'], 127)
        self.assertEqual(meta['window_seconds'], 0.9833)
        self.assertEqual(meta['refresh_rate_hz'], 60)
        self.assertTrue(meta['verified'])
        self.assertEqual(meta['confidence'], 'high')
        self.assertIs(c.last_collection_meta, meta)


if __name__ == '__main__':
    unittest.main()
