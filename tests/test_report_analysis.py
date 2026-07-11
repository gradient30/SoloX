# -*- coding: utf-8 -*-
"""report_analysis 规则引擎与回归 diff 的单元测试（无设备、无磁盘依赖）。"""

import unittest

from solox.public import report_analysis as ra


class FakeFile:
    """最小 File 替身：仅实现 report_analysis 所需读取接口。"""

    def __init__(self, perf_stats=None, meta=None, mem_series=None,
                 report_dir='/tmp/report'):
        self._perf = perf_stats or {}
        self._meta = meta or {}
        self._mem = mem_series or []
        self.report_dir = report_dir

    def _read_scene_json(self, scene, filename):
        if filename == 'perf_stats.json':
            return self._perf or None
        return None

    def readJson(self, scene):
        return self._meta

    def readLog(self, scene, filename, max_points=None):
        if filename == 'mem_total.log':
            return ([], list(self._mem))
        return ([], [])

    def build_perf_stats(self, scene, platform='Android'):
        return self._perf


class TestEvaluateMetrics(unittest.TestCase):

    def test_low_fps_is_critical(self):
        stats = {'fps': {'avg': 20, 'avg_active': 22, 'count': 60}}
        findings = ra.evaluate_metrics(stats)
        fps = [f for f in findings if f['metric'] == 'fps'][0]
        self.assertEqual(fps['level'], 'critical')

    def test_mid_fps_is_warning(self):
        stats = {'fps': {'avg': 45, 'avg_active': 45, 'count': 60}}
        findings = ra.evaluate_metrics(stats)
        fps = [f for f in findings if f['metric'] == 'fps'][0]
        self.assertEqual(fps['level'], 'warning')

    def test_high_stutter_is_critical(self):
        stats = {
            'fps': {'avg': 58, 'avg_active': 58, 'count': 60},
            'jank': {'count': 60, 'stutter_rate': 25.0, 'sum': 30},
        }
        findings = ra.evaluate_metrics(stats)
        jank = [f for f in findings if f['metric'] == 'jank'][0]
        self.assertEqual(jank['level'], 'critical')

    def test_big_jank_reported(self):
        stats = {'big_jank': {'count': 60, 'sum': 5}}
        findings = ra.evaluate_metrics(stats)
        bj = [f for f in findings if f['metric'] == 'big_jank'][0]
        self.assertEqual(bj['level'], 'warning')
        self.assertEqual(bj['value'], 5)

    def test_high_cpu_is_critical(self):
        stats = {'cpu_app': {'avg': 90, 'count': 60}}
        findings = ra.evaluate_metrics(stats)
        cpu = [f for f in findings if f['metric'] == 'cpu_app'][0]
        self.assertEqual(cpu['level'], 'critical')

    def test_healthy_report_is_ok(self):
        stats = {
            'fps': {'avg': 59, 'avg_active': 59, 'count': 60},
            'cpu_app': {'avg': 20, 'count': 60},
        }
        findings = ra.evaluate_metrics(stats)
        self.assertEqual(ra.overall_level(findings), 'ok')

    def test_ios_without_jank_has_no_jank_finding(self):
        stats = {'fps': {'avg': 59, 'avg_active': 59, 'count': 60}}
        findings = ra.evaluate_metrics(stats, platform='iOS')
        self.assertFalse(any(f['metric'] == 'jank' for f in findings))


class TestMemoryGrowth(unittest.TestCase):

    def test_detects_growth(self):
        series = [100] * 8 + [400] * 8
        result = ra.detect_memory_growth(series, ratio=1.3, abs_mb=150)
        self.assertIsNotNone(result)
        self.assertGreater(result['delta'], 150)

    def test_flat_series_no_growth(self):
        series = [200] * 16
        self.assertIsNone(ra.detect_memory_growth(series))

    def test_short_series_returns_none(self):
        self.assertIsNone(ra.detect_memory_growth([100, 400]))


class TestDiffMetrics(unittest.TestCase):

    def test_fps_increase_is_improvement(self):
        base = {'fps': {'avg': 50, 'avg_active': 50}}
        target = {'fps': {'avg': 58, 'avg_active': 58}}
        diff = ra.diff_metrics(base, target)
        self.assertEqual(diff['metrics']['fps']['verdict'], 'improved')
        self.assertEqual(diff['summary']['improved'], 1)

    def test_cpu_increase_is_regression(self):
        base = {'cpu_app': {'avg': 30}}
        target = {'cpu_app': {'avg': 45}}
        diff = ra.diff_metrics(base, target)
        self.assertEqual(diff['metrics']['cpu_app']['verdict'], 'regressed')
        self.assertEqual(diff['metrics']['cpu_app']['delta'], 15)

    def test_memory_increase_is_regression(self):
        base = {'mem_total': {'avg': 200}}
        target = {'mem_total': {'avg': 380}}
        diff = ra.diff_metrics(base, target)
        self.assertEqual(diff['metrics']['mem_total']['verdict'], 'regressed')

    def test_non_numeric_skipped(self):
        base = {'fps': {'avg': None}}
        target = {'fps': {'avg': None}}
        diff = ra.diff_metrics(base, target)
        self.assertNotIn('fps', diff['metrics'])


class TestAnalyzeAndCompareWrappers(unittest.TestCase):

    def test_analyze_report_uses_perf_stats_and_mem(self):
        file = FakeFile(
            perf_stats={
                'fps': {'avg': 20, 'avg_active': 22, 'count': 60},
                'cpu_app': {'avg': 20, 'count': 60},
            },
            meta={'platform': 'Android', 'app': 'com.demo', 'ctime': 't'},
            mem_series=[100] * 8 + [400] * 8,
        )
        result = ra.analyze_report('scene_x', file=file)
        self.assertEqual(result['scene'], 'scene_x')
        self.assertEqual(result['platform'], 'Android')
        self.assertEqual(result['level'], 'critical')  # 低 fps
        self.assertTrue(any(f['metric'] == 'mem_total'
                            for f in result['findings']))

    def test_compare_reports_wrapper(self):
        base = FakeFile(perf_stats={'fps': {'avg': 50, 'avg_active': 50}})
        # 单一 FakeFile 对 base/target 返回相同 stats；改用两次不同实例
        target = FakeFile(perf_stats={'fps': {'avg': 58, 'avg_active': 58}})

        # compare_reports 只接受一个 file，这里验证 diff_metrics 已在上组覆盖，
        # 此处验证 wrapper 装配结构。
        class DualFile(FakeFile):
            def _read_scene_json(self, scene, filename):
                if filename != 'perf_stats.json':
                    return None
                return ({'fps': {'avg': 50, 'avg_active': 50}}
                        if scene == 'a' else {'fps': {'avg': 58, 'avg_active': 58}})

        result = ra.compare_reports('a', 'b', file=DualFile())
        self.assertEqual(result['base_scene'], 'a')
        self.assertEqual(result['target_scene'], 'b')
        self.assertEqual(result['diff']['metrics']['fps']['verdict'], 'improved')


if __name__ == '__main__':
    unittest.main()
