# -*- coding: utf-8 -*-
"""Static regression contracts for performance-sensitive template JavaScript."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _template(name):
    return (ROOT / 'solox' / 'templates' / name).read_text(encoding='utf-8')


def _run_node(script):
    node = shutil.which('node')
    if not node:
        pytest.skip('node is required for executable frontend timing tests')
    subprocess.run(
        [node, '-e', script],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def test_live_collection_uses_isolated_delayed_timers():
    source = _template('index.html')

    assert 'var metricTimers = {};' in source
    assert 'function scheduleMetricPoll(' in source
    assert 'document.hidden' in source
    assert 'clearAllMetricTimers();' in source
    assert 'var timerQ' not in source
    assert not re.search(r'setTimeout\s*\(\s*get[A-Za-z]+\s*\(', source)

    for key in (
        'cpu',
        'cpu_core',
        'gpu',
        'battery',
        'mem',
        'mem_detail',
        'network',
        'fps',
        'disk',
        'energy',
    ):
        assert "scheduleMetricPoll('{}'".format(key) in source


def test_live_collection_passes_callbacks_to_chart_load_events():
    source = _template('index.html')

    assert not re.search(
        r"collectPers\([^;\n]+,\s*get[A-Za-z]+\([^;\n]*\)\s*\);",
        source,
    )
    assert source.count('function () { get') >= 10


def test_live_collection_timer_runtime_behavior():
    _run_node(r"""
const fs = require('fs');
const source = fs.readFileSync('solox/templates/index.html', 'utf8');
const block = source.match(/var metricTimers = \{\};[\s\S]*?\n\s*var liveStats = /)[0].replace(/\n\s*var liveStats = $/, '');
function assert(cond, msg) { if (!cond) { throw new Error(msg); } }
let nextId = 0;
const timers = new Map();
global.window = {
  setTimeout: (fn, delay) => {
    const id = ++nextId;
    timers.set(id, { fn, delay });
    return id;
  },
  clearTimeout: (id) => timers.delete(id)
};
global.document = { hidden: false };
global.stop = false;
eval(block);
let calls = [];
scheduleMetricPoll('cpu', () => calls.push('cpu'), 1000);
scheduleMetricPoll('mem', () => calls.push('mem'), 1000);
assert(Object.keys(metricTimers).length === 2, 'metrics should keep independent timers');
const cpuTimer = metricTimers.cpu;
clearMetricTimer('cpu');
assert(!metricTimers.cpu, 'cpu timer should clear independently');
assert(metricTimers.mem, 'mem timer should remain after cpu clear');
document.hidden = true;
timers.get(metricTimers.mem).fn();
assert(calls.length === 0, 'hidden page should not call metric callback');
assert(metricTimers.mem, 'hidden page should reschedule metric');
document.hidden = false;
timers.get(metricTimers.mem).fn();
assert(calls.join(',') === 'mem', 'visible page should run rescheduled callback');
scheduleMetricPoll('cpu', () => calls.push('cpu'), 1000);
scheduleMetricPoll('disk', () => calls.push('disk'), 3000);
clearAllMetricTimers();
assert(Object.keys(metricTimers).length === 0, 'clearAllMetricTimers should clear registry');
assert(!timers.has(cpuTimer), 'cleared timer should be removed from host timers');
""")


def test_analysis_page_limits_initial_chart_request_concurrency():
    source = _template('analysis.html')

    assert 'var chartLoadMaxConcurrency = 3;' in source
    assert 'function enqueueChartLoad(' in source
    assert 'function drainChartLoadQueue(' in source
    assert 'enqueueChartLoad(initCpuCharts);' in source
    assert 'enqueueChartLoad(initMemoryCharts);' in source
    assert 'enqueueChartLoad(initFpsCharts);' in source
    assert 'setTimeout(initMemoryCharts' not in source
    assert 'setTimeout(initFpsCharts' not in source
    assert 'onclick="init' not in source
    assert 'onclick="enqueueChartLoad(initCpuCoreCharts)"' in source

    for function_name in (
        'initCpuCharts',
        'initBatteryCharts',
        'initFpsCharts',
        'initGpuCharts',
        'initMemoryCharts',
        'initMemoryDetailCharts',
        'initCpuCoreCharts',
        'initNetworkCharts',
        'initDiskCharts',
    ):
        match = re.search(
            r'function {}\(\)\s*\{{(?P<body>.*?)\n\s*\}}'.format(function_name),
            source,
            re.DOTALL,
        )
        assert match, function_name
        assert 'return $.ajax({' in match.group('body'), function_name


def test_analysis_chart_queue_runtime_behavior():
    _run_node(r"""
const fs = require('fs');
const source = fs.readFileSync('solox/templates/analysis.html', 'utf8');
const block = source.match(/var chartLoadQueue = \[\];[\s\S]*?\n\s*\$\(document\)\.ready/)[0].replace(/\n\s*\$\(document\)\.ready$/, '');
function assert(cond, msg) { if (!cond) { throw new Error(msg); } }
global.$ = {
  when: (request) => ({
    always: (callback) => Promise.resolve(request).then(callback, callback)
  })
};
eval(block);
let active = 0;
let peak = 0;
let done = 0;
for (let i = 0; i < 9; i += 1) {
  enqueueChartLoad(() => new Promise((resolve, reject) => {
    active += 1;
    peak = Math.max(peak, active);
    setTimeout(() => {
      active -= 1;
      done += 1;
      if (i === 4) {
        reject(new Error('expected failure'));
      } else {
        resolve();
      }
    }, 5);
  }));
}
setTimeout(() => {
  assert(peak === 3, 'queue peak concurrency should be 3');
  assert(done === 9, 'queue should drain all tasks including failures');
  assert(chartLoadsActive === 0, 'active counter should return to zero');
  assert(chartLoadQueue.length === 0, 'queue should be empty');
}, 80);
setTimeout(() => {}, 100);
""")


def test_compare_and_pk_pages_send_chart_point_limit():
    compare_source = _template('analysis_compare.html')
    pk_source = _template('analysis_pk.html')

    assert 'var chartMaxPoints = {{ chart_max_points|default(1500) }};' in compare_source
    assert compare_source.count('max_points: chartMaxPoints') == 7
    assert 'var chartMaxPoints = {{ chart_max_points|default(1500) }};' in pk_source
    assert pk_source.count('max_points: chartMaxPoints') == 4
