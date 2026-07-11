# -*- coding: utf-8 -*-
"""报告规则引擎分析与多报告回归 diff（平台无关，仅处理已采集数据）。

设计目标：
- 对齐 2026 头部工具（如 PerfDog AI 的"单报告智能分析""对比上次是否改善"）的**结论性输出**，
  但采用**离线规则引擎**，不依赖任何云端 LLM Key —— SoloX 是内网/本地工具，不能假设有外网。
- 核心为纯函数（`evaluate_metrics`/`diff_metrics`/`detect_memory_growth`），便于单测；
  I/O 由薄封装 `analyze_report`/`compare_reports` 负责，复用 `File` 读取 `perf_stats.json`。

阈值来源：结合 PerfDog 公开的卡顿/流畅度口径与常见工程经验，全部可通过参数覆盖。
"""

from __future__ import annotations

from typing import Any, Optional

# 默认阈值（可经 analyze_report(thresholds=...) 覆盖）。
DEFAULT_THRESHOLDS: dict[str, Any] = {
    'fps_active_critical': 30.0,   # 活跃平均帧率低于此值：严重
    'fps_active_warning': 50.0,    # 低于此值：警告
    'jank_stutter_warning': 10.0,  # 卡顿率(%)高于此值：警告
    'jank_stutter_critical': 20.0,  # 高于此值：严重
    'cpu_app_warning': 60.0,       # 应用 CPU 平均高于此值：警告
    'cpu_app_critical': 85.0,      # 高于此值：严重
    'mem_growth_ratio': 1.30,      # 末段/首段内存均值比高于此值 + 绝对增量达标：疑似泄漏
    'mem_growth_abs_mb': 150.0,    # 内存绝对增量(MB)阈值
}

_LEVEL_ORDER = {'critical': 3, 'warning': 2, 'info': 1, 'ok': 0}


def _finding(metric: str, level: str, message: str,
             value: Any = None, threshold: Any = None) -> dict[str, Any]:
    return {
        'metric': metric,
        'level': level,
        'message': message,
        'value': value,
        'threshold': threshold,
    }


def detect_memory_growth(values: list[float | int],
                         ratio: float = 1.30,
                         abs_mb: float = 150.0) -> Optional[dict[str, Any]]:
    """基于内存时序检测疑似持续增长（泄漏）。

    以首/末各 1/4 段的均值比较：末段均值同时满足
    ``末段/首段 >= ratio`` 且 ``末段-首段 >= abs_mb`` 时判为疑似增长。

    :param values: 按时间顺序的内存占用序列（MB）。
    :return: 命中时返回 {'first_avg','last_avg','delta','ratio'}，否则 None。
    """
    nums = [float(v) for v in values if v is not None]
    if len(nums) < 8:  # 样本过少无法判断趋势
        return None
    q = max(1, len(nums) // 4)
    first_avg = sum(nums[:q]) / q
    last_avg = sum(nums[-q:]) / q
    if first_avg <= 0:
        return None
    delta = last_avg - first_avg
    if last_avg / first_avg >= ratio and delta >= abs_mb:
        return {
            'first_avg': round(first_avg, 2),
            'last_avg': round(last_avg, 2),
            'delta': round(delta, 2),
            'ratio': round(last_avg / first_avg, 3),
        }
    return None


def evaluate_metrics(perf_stats: dict[str, Any],
                     platform: str = 'Android',
                     thresholds: Optional[dict[str, Any]] = None,
                     mem_series: Optional[list[float | int]] = None
                     ) -> list[dict[str, Any]]:
    """基于 perf_stats 生成结构化结论列表。

    :param perf_stats: `perf_stats.json` 反序列化结果（指标名 -> 统计字典）。
    :param platform: 'Android' 或 'iOS'，用于跳过平台不适用项。
    :param thresholds: 覆盖默认阈值。
    :param mem_series: 可选内存时序，用于泄漏趋势判断（无则跳过该项）。
    :return: findings 列表，每项含 metric/level/message/value/threshold。
    """
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    findings: list[dict[str, Any]] = []

    fps = perf_stats.get('fps') or {}
    if fps:
        active = fps.get('avg_active', fps.get('avg', 0)) or 0
        if active and active < th['fps_active_critical']:
            findings.append(_finding(
                'fps', 'critical',
                f'活跃平均帧率仅 {active}Hz，明显卡顿',
                active, th['fps_active_critical']))
        elif active and active < th['fps_active_warning']:
            findings.append(_finding(
                'fps', 'warning',
                f'活跃平均帧率 {active}Hz，偏低',
                active, th['fps_active_warning']))
        elif active:
            findings.append(_finding(
                'fps', 'ok', f'帧率良好（活跃均值 {active}Hz）', active))

    # Jank/Stutter 仅 Android 有真实测量（iOS 不支持，perf_stats 中通常无此项）
    jank = perf_stats.get('jank') or {}
    if jank and jank.get('count'):
        stutter = jank.get('stutter_rate', 0) or 0
        if stutter > th['jank_stutter_critical']:
            findings.append(_finding(
                'jank', 'critical',
                f'卡顿率 {stutter}% 偏高，体验受损明显',
                stutter, th['jank_stutter_critical']))
        elif stutter > th['jank_stutter_warning']:
            findings.append(_finding(
                'jank', 'warning',
                f'卡顿率 {stutter}% 偏高',
                stutter, th['jank_stutter_warning']))

    big_jank = perf_stats.get('big_jank') or {}
    if big_jank and big_jank.get('sum'):
        findings.append(_finding(
            'big_jank', 'warning',
            f'出现严重卡顿(BigJank) {int(big_jank["sum"])} 次',
            int(big_jank['sum'])))

    cpu = perf_stats.get('cpu_app') or {}
    if cpu and cpu.get('count'):
        avg = cpu.get('avg', 0) or 0
        if avg > th['cpu_app_critical']:
            findings.append(_finding(
                'cpu_app', 'critical',
                f'应用 CPU 均值 {avg}% 过高',
                avg, th['cpu_app_critical']))
        elif avg > th['cpu_app_warning']:
            findings.append(_finding(
                'cpu_app', 'warning',
                f'应用 CPU 均值 {avg}% 偏高',
                avg, th['cpu_app_warning']))

    if mem_series is not None:
        growth = detect_memory_growth(
            mem_series, th['mem_growth_ratio'], th['mem_growth_abs_mb'])
        if growth:
            findings.append(_finding(
                'mem_total', 'warning',
                (f'内存从约 {growth["first_avg"]}MB 增长到 {growth["last_avg"]}MB'
                 f'（+{growth["delta"]}MB），疑似泄漏或缓存持续增长'),
                growth))

    if not findings:
        findings.append(_finding('overall', 'ok', '各项指标未见明显异常'))
    return findings


def overall_level(findings: list[dict[str, Any]]) -> str:
    """取 findings 中的最高严重级别。"""
    if not findings:
        return 'ok'
    return max(findings, key=lambda f: _LEVEL_ORDER.get(f['level'], 0))['level']


# 指标方向：True 表示"数值越大越好"（如 fps），False 表示"越大越差"。
_HIGHER_IS_BETTER = {'fps': True}


def _direction_for(metric: str) -> bool:
    return _HIGHER_IS_BETTER.get(metric, False)


def diff_metrics(base_stats: dict[str, Any],
                 target_stats: dict[str, Any],
                 field: str = 'avg') -> dict[str, Any]:
    """对比两份 perf_stats，输出每个共有指标的量化差值与改善/恶化判定。

    :param base_stats: 基准报告的 perf_stats。
    :param target_stats: 目标报告的 perf_stats。
    :param field: 参与对比的统计字段（默认 avg；fps 建议用 avg_active）。
    :return: {'metrics': {metric: {base,target,delta,percent,verdict}}, 'summary': {...}}
    """
    metrics: dict[str, Any] = {}
    improved = regressed = 0
    for metric in sorted(set(base_stats) & set(target_stats)):
        b = base_stats.get(metric) or {}
        t = target_stats.get(metric) or {}
        use_field = 'avg_active' if (metric == 'fps' and 'avg_active' in b and 'avg_active' in t) else field
        bv = b.get(use_field)
        tv = t.get(use_field)
        if not isinstance(bv, (int, float)) or not isinstance(tv, (int, float)):
            continue
        delta = round(tv - bv, 2)
        percent = round((delta / bv * 100), 2) if bv else None
        higher_better = _direction_for(metric)
        if delta == 0:
            verdict = 'same'
        elif (delta > 0) == higher_better:
            verdict = 'improved'
            improved += 1
        else:
            verdict = 'regressed'
            regressed += 1
        metrics[metric] = {
            'field': use_field,
            'base': bv,
            'target': tv,
            'delta': delta,
            'percent': percent,
            'verdict': verdict,
        }
    return {
        'metrics': metrics,
        'summary': {
            'improved': improved,
            'regressed': regressed,
            'unchanged': len(metrics) - improved - regressed,
        },
    }


# --------------------------------------------------------------------------
# I/O 薄封装（依赖 File；导入置于函数内避免与 common 循环依赖）
# --------------------------------------------------------------------------

def _get_file():
    from solox.public.common import File
    return File()


def _load_perf_stats(file, scene: str) -> dict[str, Any]:
    stats = file._read_scene_json(scene, 'perf_stats.json')
    if stats:
        return stats
    # 兼容早期报告：无 perf_stats.json 时按平台即时构建
    try:
        meta = file.readJson(scene)
        platform = meta.get('platform', 'Android')
    except Exception:
        platform = 'Android'
    return file.build_perf_stats(scene, platform)


def _load_mem_series(file, scene: str) -> Optional[list[float]]:
    try:
        data = file.readLog(scene=scene, filename='mem_total.log')[1]
        return data or None
    except Exception:
        return None


def analyze_report(scene: str, thresholds: Optional[dict[str, Any]] = None,
                   file=None) -> dict[str, Any]:
    """分析单个报告，返回结构化结论。

    :param scene: 报告目录名（report/ 下的 apm_* 目录）。
    :return: {'scene','platform','app','findings','level','perf_stats'}
    """
    file = file or _get_file()
    try:
        meta = file.readJson(scene)
    except Exception:
        meta = {}
    platform = meta.get('platform', 'Android')
    perf_stats = _load_perf_stats(file, scene)
    mem_series = _load_mem_series(file, scene)
    findings = evaluate_metrics(perf_stats, platform, thresholds, mem_series)
    return {
        'scene': scene,
        'platform': platform,
        'app': meta.get('app', ''),
        'ctime': meta.get('ctime', ''),
        'findings': findings,
        'level': overall_level(findings),
        'perf_stats': perf_stats,
    }


def compare_reports(base_scene: str, target_scene: str,
                    file=None) -> dict[str, Any]:
    """对比两个报告，输出回归 diff 量化表。

    :param base_scene: 基准报告（通常为较早/上一版本）。
    :param target_scene: 目标报告（通常为当前版本）。
    """
    file = file or _get_file()
    base_stats = _load_perf_stats(file, base_scene)
    target_stats = _load_perf_stats(file, target_scene)
    diff = diff_metrics(base_stats, target_stats)
    return {
        'base_scene': base_scene,
        'target_scene': target_scene,
        'diff': diff,
    }
