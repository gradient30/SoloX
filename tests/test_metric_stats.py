# -*- coding: utf-8 -*-
"""Tests for PerfDog-style metric statistics."""

import unittest

from solox.public.metric_stats import (
    build_scene_segments,
    build_scene_tag_stats,
    compute_fps_stats,
    compute_jank_stats,
    compute_metric_stats,
    filter_chart_by_range,
)


class TestComputeMetricStats(unittest.TestCase):

    def test_basic_stats(self):
        s = compute_metric_stats([10, 20, 30, 40])
        self.assertEqual(s['avg'], 25.0)
        self.assertEqual(s['max'], 40.0)
        self.assertEqual(s['min'], 10.0)
        self.assertEqual(s['count'], 4)

    def test_empty(self):
        s = compute_metric_stats([])
        self.assertEqual(s['count'], 0)


class TestJankStats(unittest.TestCase):

    def test_stutter_rate(self):
        s = compute_jank_stats([0, 1, 0, 2, 0])
        self.assertEqual(s['sum'], 3)
        self.assertEqual(s['stutter_samples'], 2)
        self.assertEqual(s['stutter_rate'], 40.0)


class TestFpsStats(unittest.TestCase):

    def test_active_fps_excludes_zeros(self):
        s = compute_fps_stats([0, 0, 58, 60, 59])
        self.assertEqual(s['min'], 0)
        self.assertEqual(s['min_active'], 58.0)
        self.assertEqual(s['avg_active'], 59.0)


class TestSceneTags(unittest.TestCase):

    def test_segments_without_tags(self):
        segs = build_scene_segments([])
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]['label'], '全时段')

    def test_per_scene_stats(self):
        tags = [
            {'time': '10:00:00.000000', 'label': 'Lobby'},
            {'time': '10:00:05.000000', 'label': 'Battle'},
        ]
        charts = {
            'cpu_app': [
                {'x': '09:59:58.000000', 'y': 10},
                {'x': '10:00:02.000000', 'y': 30},
                {'x': '10:00:06.000000', 'y': 50},
            ],
            'mem_total': [
                {'x': '10:00:02.000000', 'y': 200},
                {'x': '10:00:06.000000', 'y': 400},
            ],
            'fps': [
                {'x': '10:00:02.000000', 'y': 60},
                {'x': '10:00:06.000000', 'y': 45},
            ],
            'jank': [
                {'x': '10:00:02.000000', 'y': 0},
                {'x': '10:00:06.000000', 'y': 2},
            ],
            'big_jank': [
                {'x': '10:00:02.000000', 'y': 0},
                {'x': '10:00:06.000000', 'y': 1},
            ],
        }
        result = build_scene_tag_stats(tags, charts)
        self.assertEqual(len(result['scenes']), 3)
        battle = [s for s in result['scenes'] if s['label'] == 'Battle'][0]
        self.assertEqual(battle['metrics']['cpu_app']['avg'], 50.0)
        self.assertEqual(battle['metrics']['fps']['min'], 45.0)
        self.assertEqual(battle['metrics']['big_jank']['sum'], 1.0)

    def test_big_jank_stats(self):
        s = compute_jank_stats([0, 0, 2, 1])
        self.assertEqual(s['sum'], 3)
        self.assertEqual(s['stutter_samples'], 2)

    def test_filter_by_range(self):
        chart = [
            {'x': '10:00:01.000000', 'y': 1},
            {'x': '10:00:03.000000', 'y': 2},
            {'x': '10:00:05.000000', 'y': 3},
        ]
        vals = filter_chart_by_range(chart, '10:00:02.000000', '10:00:04.000000')
        self.assertEqual(vals, [2])


if __name__ == '__main__':
    unittest.main()
