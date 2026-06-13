"""Reproduce the /apm/log eager-versus-lazy report loading benchmark."""

import argparse
import gc
import json
import os
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from solox.public.common import File, Platform  # noqa: E402


LOG_NAMES = (
    'cpu_app',
    'cpu_sys',
    'mem_total',
    'mem_swap',
    'mem_java_heap',
    'mem_native_heap',
    'mem_code_pss',
    'mem_stack_pss',
    'mem_graphics_pss',
    'mem_private_pss',
    'mem_system_pss',
    'battery_level',
    'battery_tem',
    'upflow',
    'downflow',
    'fps',
    'jank',
    'gpu',
    'disk_used',
    'disk_free',
    'cpu0',
    'cpu1',
    'cpu2',
    'cpu3',
)


def _measure(operation, repeats):
    elapsed = []
    peaks = []
    result = None
    for _ in range(repeats):
        gc.collect()
        tracemalloc.start()
        started = time.perf_counter()
        result = operation()
        elapsed.append(time.perf_counter() - started)
        peaks.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
    return result, statistics.median(elapsed), max(peaks)


def run_benchmark(lines, repeats, max_points):
    with tempfile.TemporaryDirectory() as temp_dir:
        scene = 'apm_benchmark'
        scene_dir = os.path.join(temp_dir, scene)
        os.makedirs(scene_dir)
        payload = ''.join(
            f'10:00:{index % 60:02d}.000000={index % 100}\n'
            for index in range(lines)
        )
        for name in LOG_NAMES:
            with open(
                os.path.join(scene_dir, f'{name}.log'),
                'w',
                encoding='utf-8',
            ) as log_file:
                log_file.write(payload)
        with open(
            os.path.join(scene_dir, 'result.json'),
            'w',
            encoding='utf-8',
        ) as result_file:
            json.dump({'cores': 4}, result_file)

        report_file = File()
        report_file.report_dir = temp_dir

        def eager_load():
            results = {
                'cpu': report_file.getCpuLog(
                    Platform.Android, scene, max_points),
                'mem': report_file.getMemLog(
                    Platform.Android, scene, max_points),
                'mem_detail': report_file.getMemDetailLog(
                    Platform.Android, scene, max_points),
                'battery': report_file.getBatteryLog(
                    Platform.Android, scene, max_points),
                'flow': report_file.getFlowLog(
                    Platform.Android, scene, max_points),
                'fps': report_file.getFpsLog(
                    Platform.Android, scene, max_points),
                'gpu': report_file.getGpuLog(
                    Platform.Android, scene, max_points),
                'disk': report_file.getDiskLog(
                    Platform.Android, scene, max_points),
                'cpu_core': report_file.getCpuCoreLog(
                    Platform.Android, scene, max_points),
            }
            return results['cpu']

        def lazy_load():
            return report_file.getCpuLog(
                Platform.Android,
                scene,
                max_points,
            )

        eager_result, eager_seconds, eager_peak = _measure(
            eager_load,
            repeats,
        )
        lazy_result, lazy_seconds, lazy_peak = _measure(
            lazy_load,
            repeats,
        )
        return {
            'lines_per_log': lines,
            'log_files': len(LOG_NAMES),
            'repeats': repeats,
            'max_points': max_points,
            'response_equal': eager_result == lazy_result,
            'eager_seconds_median': round(eager_seconds, 4),
            'lazy_seconds_median': round(lazy_seconds, 4),
            'latency_reduction_pct': round(
                (1 - lazy_seconds / eager_seconds) * 100,
                1,
            ),
            'eager_peak_mb': round(eager_peak / 1024 / 1024, 2),
            'lazy_peak_mb': round(lazy_peak / 1024 / 1024, 2),
            'peak_memory_reduction_pct': round(
                (1 - lazy_peak / eager_peak) * 100,
                1,
            ),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lines', type=int, default=20000)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--max-points', type=int, default=1500)
    args = parser.parse_args()
    result = run_benchmark(
        max(args.lines, 1),
        max(args.repeats, 1),
        max(args.max_points, 1),
    )
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
