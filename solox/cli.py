# -*- coding: utf-8 -*-
"""SoloX 命令行采集入口（headless，面向 CI/CD 与脚本化）。

对齐 2026 头部工具（如 PerfDog CLI + Service）的"无界面、可流水线调用"定位：
无需启动 Web UI，即可对指定设备/应用采集一段时间，生成报告并输出规则引擎分析结论。

复用现有 `solox.public.apm.AppPerformanceMonitor` 采集逻辑与
`solox.public.report_analysis` 分析逻辑，不引入新依赖。

用法示例::

    python -m solox.cli collect --platform Android --device <id> \
        --pkg com.example.app --duration 60
    python -m solox.cli analyze --scene apm_2026-07-11-15-30-00
    python -m solox.cli compare --base <sceneA> --target <sceneB>
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from solox import __version__


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器（纯函数，便于单测）。"""
    parser = argparse.ArgumentParser(
        prog='solox.cli',
        description='SoloX headless 性能采集与分析 CLI',
    )
    parser.add_argument('--version', action='version',
                        version=f'SoloX {__version__}')
    sub = parser.add_subparsers(dest='command')

    # collect（默认命令）
    collect = sub.add_parser('collect', help='采集一段时间并生成报告')
    collect.add_argument('--platform', default='Android',
                         choices=['Android', 'iOS'])
    collect.add_argument('--device', required=True, help='设备 ID / UDID')
    collect.add_argument('--pkg', '--pkgname', dest='pkg', required=True,
                         help='包名 / Bundle ID')
    collect.add_argument('--duration', type=int, default=60,
                         help='采集时长（秒），默认 60')
    collect.add_argument('--record', action='store_true',
                         help='Android：同时录屏')
    collect.add_argument('--surfaceview', action='store_true', default=True)
    collect.add_argument('--json', action='store_true',
                         help='以 JSON 输出分析结论')
    collect.add_argument('--no-analysis', dest='analysis',
                         action='store_false', default=True,
                         help='采集后不做规则引擎分析')

    # analyze
    analyze = sub.add_parser('analyze', help='对已存在报告做规则引擎分析')
    analyze.add_argument('--scene', required=True, help='报告目录名')
    analyze.add_argument('--json', action='store_true')

    # compare
    compare = sub.add_parser('compare', help='对比两个报告输出回归 diff')
    compare.add_argument('--base', required=True, help='基准报告目录名')
    compare.add_argument('--target', required=True, help='目标报告目录名')
    compare.add_argument('--json', action='store_true')

    return parser


_LEVEL_ICON = {
    'critical': '[严重]',
    'warning': '[警告]',
    'info': '[提示]',
    'ok': '[正常]',
}


def format_analysis(analysis: dict) -> str:
    """将分析结论格式化为人类可读文本（纯函数，便于单测）。"""
    lines = [
        f"报告: {analysis.get('scene', '')}",
        f"应用: {analysis.get('app', '')}  平台: {analysis.get('platform', '')}",
        f"总体: {_LEVEL_ICON.get(analysis.get('level', 'ok'), '')}",
        '-' * 40,
    ]
    for finding in analysis.get('findings', []):
        icon = _LEVEL_ICON.get(finding.get('level', 'info'), '')
        lines.append(f"{icon} {finding.get('message', '')}")
    return '\n'.join(lines)


def format_compare(compare: dict) -> str:
    """将回归 diff 格式化为人类可读文本（纯函数，便于单测）。"""
    diff = compare.get('diff', {})
    metrics = diff.get('metrics', {})
    summary = diff.get('summary', {})
    lines = [
        f"基准: {compare.get('base_scene', '')}",
        f"目标: {compare.get('target_scene', '')}",
        (f"改善 {summary.get('improved', 0)} · "
         f"恶化 {summary.get('regressed', 0)} · "
         f"持平 {summary.get('unchanged', 0)}"),
        '-' * 40,
    ]
    verdict_label = {'improved': '改善', 'regressed': '恶化', 'same': '持平'}
    for name, m in metrics.items():
        sign = '+' if m['delta'] > 0 else ''
        pct = f" ({sign}{m['percent']}%)" if m.get('percent') is not None else ''
        lines.append(
            f"{name}[{m['field']}]: {m['base']} → {m['target']} "
            f"({sign}{m['delta']}{pct}) {verdict_label.get(m['verdict'], '')}")
    return '\n'.join(lines)


def _cmd_collect(args) -> int:
    from solox.public.apm import AppPerformanceMonitor
    from solox.public import report_analysis
    from solox.public.common import File

    monitor = AppPerformanceMonitor(
        pkgName=args.pkg,
        platform=args.platform,
        deviceId=args.device,
        surfaceview=args.surfaceview,
        noLog=False,
        record=args.record,
        collect_all=True,
        duration=args.duration,
    )
    monitor.collectAll()

    if not args.analysis:
        print('采集完成，报告已生成于 report/ 目录。')
        return 0

    file = File()
    scene = _latest_scene(file)
    if not scene:
        print('采集完成，但未找到报告目录。')
        return 0
    analysis = report_analysis.analyze_report(scene, file=file)
    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    else:
        print(format_analysis(analysis))
    return 0


def _latest_scene(file) -> Optional[str]:
    import os
    report_dir = file.report_dir
    if not os.path.isdir(report_dir):
        return None
    scenes = []
    for name in os.listdir(report_dir):
        full = os.path.join(report_dir, name)
        if os.path.isdir(full) and os.path.isfile(
                os.path.join(full, 'result.json')):
            scenes.append((os.path.getmtime(full), name))
    if not scenes:
        return None
    scenes.sort(reverse=True)
    return scenes[0][1]


def _cmd_analyze(args) -> int:
    from solox.public import report_analysis
    analysis = report_analysis.analyze_report(args.scene)
    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    else:
        print(format_analysis(analysis))
    return 0


def _cmd_compare(args) -> int:
    from solox.public import report_analysis
    compare = report_analysis.compare_reports(args.base, args.target)
    if args.json:
        print(json.dumps(compare, ensure_ascii=False, indent=2))
    else:
        print(format_compare(compare))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == 'collect':
        return _cmd_collect(args)
    if args.command == 'analyze':
        return _cmd_analyze(args)
    if args.command == 'compare':
        return _cmd_compare(args)
    parser.print_help()
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
