# -*- coding: utf-8 -*-
"""SoloX MCP 工具（纯函数，返回 JSON 可序列化结果）。

对齐 2026 头部工具（PerfDog MCP 15 工具）中复用成本最低、价值最高的一组：
报告列举、指标查询、异常检测、回归对比。所有函数只读已采集数据，无副作用、
不依赖设备连接，因而可离线单测。MCP server 层仅做协议封装、转调这些函数。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from solox.public import report_analysis


def _file():
    from solox.public.common import File
    return File()


def list_reports(limit: int = 20, file=None) -> dict[str, Any]:
    """列出最近的性能报告（按修改时间倒序）。

    :param limit: 返回条数上限。
    :return: {'count', 'reports': [{scene, app, platform, ctime}]}
    """
    import json
    file = file or _file()
    report_dir = file.report_dir
    entries = []
    if os.path.isdir(report_dir):
        for name in os.listdir(report_dir):
            full = os.path.join(report_dir, name)
            result_path = os.path.join(full, 'result.json')
            if not (os.path.isdir(full) and os.path.isfile(result_path)):
                continue
            try:
                entries.append((os.path.getmtime(full), name, result_path))
            except OSError:
                continue
    entries.sort(reverse=True)
    reports = []
    for _mtime, name, result_path in entries[:max(0, limit)]:
        meta = {}
        try:
            with open(result_path, encoding='utf-8') as fh:
                meta = json.load(fh)
        except Exception:
            meta = {}
        reports.append({
            'scene': name,
            'app': meta.get('app', ''),
            'platform': meta.get('platform', ''),
            'ctime': meta.get('ctime', ''),
            'duration': meta.get('duration', ''),
        })
    return {'count': len(reports), 'reports': reports}


def get_report_metrics(scene: str, file=None) -> dict[str, Any]:
    """返回指定报告的 perf_stats（min/max/avg 等汇总）。"""
    file = file or _file()
    stats = report_analysis._load_perf_stats(file, scene)
    return {'scene': scene, 'perf_stats': stats}


def detect_issues(scene: str, file=None) -> dict[str, Any]:
    """对指定报告运行规则引擎，返回结构化结论（严重度分级）。"""
    file = file or _file()
    return report_analysis.analyze_report(scene, file=file)


def compare_reports(base: str, target: str, file=None) -> dict[str, Any]:
    """对比两个报告，返回指标量化差值与改善/恶化判定。"""
    file = file or _file()
    return report_analysis.compare_reports(base, target, file=file)


# 工具清单：供 MCP server 注册，也便于测试遍历。
TOOL_SPECS = [
    {
        'name': 'list_reports',
        'description': '列出最近的 SoloX 性能报告',
        'func': list_reports,
    },
    {
        'name': 'get_report_metrics',
        'description': '获取某个报告的 min/max/avg 指标汇总',
        'func': get_report_metrics,
    },
    {
        'name': 'detect_issues',
        'description': '对某个报告运行规则引擎，输出性能问题结论',
        'func': detect_issues,
    },
    {
        'name': 'compare_reports',
        'description': '对比两个报告，输出回归 diff（改善/恶化）',
        'func': compare_reports,
    },
]
