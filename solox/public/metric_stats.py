# -*- coding: utf-8 -*-
"""PerfDog-style metric statistics and scene-tag segmentation."""

from __future__ import annotations

from typing import Any


def compute_metric_stats(values: list[float | int]) -> dict[str, Any]:
    """Compute avg/max/min/median/count for a numeric series."""
    if not values:
        return {
            'avg': 0, 'max': 0, 'min': 0, 'median': 0, 'count': 0, 'sum': 0,
        }
    nums = [float(v) for v in values]
    nums_sorted = sorted(nums)
    n = len(nums)
    mid = n // 2
    if n % 2:
        median = nums_sorted[mid]
    else:
        median = (nums_sorted[mid - 1] + nums_sorted[mid]) / 2
    return {
        'avg': round(sum(nums) / n, 2),
        'max': round(max(nums), 2),
        'min': round(min(nums), 2),
        'median': round(median, 2),
        'count': n,
        'sum': round(sum(nums), 2),
    }


def compute_jank_stats(jank_values: list[float | int]) -> dict[str, Any]:
    """Jank stats aligned with PerfDog: total, avg per sample, stutter rate."""
    base = compute_metric_stats(jank_values)
    if not jank_values:
        base['stutter_rate'] = 0
        base['stutter_samples'] = 0
        return base
    stutter_samples = sum(1 for v in jank_values if float(v) > 0)
    base['stutter_samples'] = stutter_samples
    base['stutter_rate'] = round(stutter_samples / len(jank_values) * 100, 2)
    return base


def compute_fps_stats(fps_values: list[float | int]) -> dict[str, Any]:
    """FPS stats; exclude zero-FPS idle samples from avg/min when possible."""
    base = compute_metric_stats(fps_values)
    active = [float(v) for v in fps_values if float(v) > 0]
    if active:
        base['avg_active'] = round(sum(active) / len(active), 2)
        base['min_active'] = round(min(active), 2)
        base['active_count'] = len(active)
    else:
        base['avg_active'] = 0
        base['min_active'] = 0
        base['active_count'] = 0
    return base


def build_scene_segments(tags: list[dict]) -> list[dict]:
    """Build time segments from ordered scene tags (PerfDog scene markers).

    Each tag marks the start of a labelled scene until the next tag.
    """
    if not tags:
        return [{'label': '全时段', 'start': None, 'end': None}]

    segments: list[dict] = []
    if tags[0].get('time'):
        segments.append({
            'label': '默认',
            'start': None,
            'end': tags[0]['time'],
        })
    for i, tag in enumerate(tags):
        end = tags[i + 1]['time'] if i + 1 < len(tags) else None
        segments.append({
            'label': tag.get('label', f'Scene{i + 1}'),
            'start': tag.get('time'),
            'end': end,
        })
    return segments


def _in_time_range(t: str, start: str | None, end: str | None) -> bool:
    if start and t < start:
        return False
    if end and t >= end:
        return False
    return True


def filter_chart_by_range(
    chart: list[dict],
    start: str | None,
    end: str | None,
) -> list[float | int]:
    """Filter log chart points [{x: time, y: value}] by time range."""
    out: list[float | int] = []
    for point in chart:
        t = point.get('x', '')
        if _in_time_range(t, start, end):
            out.append(point['y'])
    return out


def build_scene_tag_stats(
    tags: list[dict],
    metric_charts: dict[str, list[dict]],
) -> dict[str, Any]:
    """Per-scene-tag statistics for all metrics."""
    segments = build_scene_segments(tags)
    scenes = []
    for seg in segments:
        metrics: dict[str, Any] = {}
        for name, chart in metric_charts.items():
            values = filter_chart_by_range(chart, seg['start'], seg['end'])
            if name == 'jank' or name == 'big_jank':
                metrics[name] = compute_jank_stats(values)
            elif name == 'fps':
                metrics[name] = compute_fps_stats(values)
            else:
                metrics[name] = compute_metric_stats(values)
        scenes.append({
            'label': seg['label'],
            'start': seg['start'],
            'end': seg['end'],
            'sample_count': max((m.get('count', 0) for m in metrics.values()), default=0),
            'metrics': metrics,
        })
    return {'tags': tags, 'scenes': scenes}
