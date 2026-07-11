# -*- coding: utf-8 -*-
"""solox.cli 与 solox.mcp 的单元测试（无设备、无 MCP SDK 依赖）。"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from solox import cli
from solox.mcp import tools


class TestCliParser(unittest.TestCase):

    def test_parse_collect(self):
        args = cli.build_parser().parse_args(
            ['collect', '--device', 'dev1', '--pkg', 'com.demo',
             '--duration', '30'])
        self.assertEqual(args.command, 'collect')
        self.assertEqual(args.device, 'dev1')
        self.assertEqual(args.pkg, 'com.demo')
        self.assertEqual(args.duration, 30)

    def test_parse_analyze(self):
        args = cli.build_parser().parse_args(['analyze', '--scene', 's1'])
        self.assertEqual(args.command, 'analyze')
        self.assertEqual(args.scene, 's1')

    def test_parse_compare(self):
        args = cli.build_parser().parse_args(
            ['compare', '--base', 'a', '--target', 'b'])
        self.assertEqual(args.command, 'compare')
        self.assertEqual(args.base, 'a')
        self.assertEqual(args.target, 'b')

    def test_format_analysis_contains_messages(self):
        analysis = {
            'scene': 's1', 'app': 'com.demo', 'platform': 'Android',
            'level': 'critical',
            'findings': [
                {'metric': 'fps', 'level': 'critical', 'message': '帧率过低'},
            ],
        }
        text = cli.format_analysis(analysis)
        self.assertIn('帧率过低', text)
        self.assertIn('[严重]', text)

    def test_format_compare_contains_deltas(self):
        compare = {
            'base_scene': 'a', 'target_scene': 'b',
            'diff': {
                'metrics': {
                    'fps': {'field': 'avg_active', 'base': 50, 'target': 58,
                            'delta': 8, 'percent': 16.0, 'verdict': 'improved'},
                },
                'summary': {'improved': 1, 'regressed': 0, 'unchanged': 0},
            },
        }
        text = cli.format_compare(compare)
        self.assertIn('fps', text)
        self.assertIn('改善', text)

    def test_main_analyze_dispatch(self):
        fake = {'scene': 's1', 'app': '', 'platform': 'Android',
                'level': 'ok', 'findings': []}
        with patch('solox.public.report_analysis.analyze_report',
                   return_value=fake) as mock_analyze:
            rc = cli.main(['analyze', '--scene', 's1', '--json'])
        self.assertEqual(rc, 0)
        mock_analyze.assert_called_once()

    def test_main_no_command_returns_help(self):
        rc = cli.main([])
        self.assertEqual(rc, 1)


class TestMcpTools(unittest.TestCase):

    def test_tool_specs_cover_four_tools(self):
        names = {spec['name'] for spec in tools.TOOL_SPECS}
        self.assertEqual(
            names,
            {'list_reports', 'get_report_metrics',
             'detect_issues', 'compare_reports'})

    def test_list_reports_scans_report_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene_dir = os.path.join(tmp, 'apm_2026-07-11-10-00-00')
            os.makedirs(scene_dir)
            with open(os.path.join(scene_dir, 'result.json'), 'w',
                      encoding='utf-8') as fh:
                json.dump({'app': 'com.demo', 'platform': 'Android',
                           'ctime': 't', 'duration': '00:30'}, fh)

            class _F:
                report_dir = tmp

            result = tools.list_reports(limit=10, file=_F())
            self.assertEqual(result['count'], 1)
            self.assertEqual(result['reports'][0]['app'], 'com.demo')

    def test_detect_issues_delegates_to_analysis(self):
        fake = {'scene': 's1', 'level': 'ok', 'findings': []}
        with patch('solox.public.report_analysis.analyze_report',
                   return_value=fake) as mock_analyze:
            result = tools.detect_issues('s1', file=object())
        self.assertEqual(result['level'], 'ok')
        mock_analyze.assert_called_once()


class TestMcpServerImport(unittest.TestCase):
    """server 模块顶层导入不应要求 MCP SDK。"""

    def test_server_module_imports_without_sdk(self):
        import importlib
        mod = importlib.import_module('solox.mcp.server')
        self.assertTrue(hasattr(mod, 'build_server'))
        self.assertTrue(hasattr(mod, 'main'))


if __name__ == '__main__':
    unittest.main()
