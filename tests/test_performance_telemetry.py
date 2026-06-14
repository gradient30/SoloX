# -*- coding: utf-8 -*-
"""Runtime performance telemetry acceptance tests."""

import subprocess
from unittest.mock import MagicMock, patch


def test_apm_request_records_latency_and_concurrency():
    from solox.public.performance_telemetry import telemetry
    from solox.view import apis
    from solox.web import app

    app.config['TESTING'] = True
    client = app.test_client()
    telemetry.reset()

    with patch.object(apis.f, 'getCpuLog', return_value={'status': 1}):
        response = client.get('/apm/log', query_string={
            'scene': 'apm_perf',
            'target': 'cpu',
            'platform': 'Android',
            'max_points': 20,
        })

    assert response.status_code == 200
    assert float(response.headers['X-SoloX-Response-Time-Ms']) >= 0

    snapshot = client.get('/apm/telemetry').get_json()
    assert snapshot['status'] == 1
    assert snapshot['api']['count'] == 1
    assert snapshot['api']['active'] == 0
    assert snapshot['api']['max_active'] >= 1
    assert snapshot['api']['routes']['/apm/log']['count'] == 1
    assert '/apm/telemetry' not in snapshot['api']['routes']


def test_telemetry_reset_clears_previous_samples():
    from solox.public.performance_telemetry import telemetry
    from solox.web import app

    app.config['TESTING'] = True
    client = app.test_client()
    telemetry.reset()
    started = telemetry.begin_api('/apm/test')
    telemetry.end_api('/apm/test', started)

    snapshot = client.get('/apm/telemetry', query_string={'reset': 1}).get_json()

    assert snapshot['api']['count'] == 0
    assert snapshot['api']['routes'] == {}
    assert snapshot['adb']['count'] == 0


def test_telemetry_reset_ignores_pre_reset_inflight_request():
    from solox.public.performance_telemetry import telemetry

    telemetry.reset()
    stale = telemetry.begin_api('/apm/slow')
    telemetry.reset()
    fresh = telemetry.begin_api('/apm/fresh')
    telemetry.end_api('/apm/fresh', fresh)
    telemetry.end_api('/apm/slow', stale)

    snapshot = telemetry.snapshot()
    assert snapshot['api']['count'] == 1
    assert snapshot['api']['active'] == 0
    assert snapshot['api']['routes']['/apm/fresh']['count'] == 1
    assert '/apm/slow' not in snapshot['api']['routes']


def test_adb_shell_records_command_duration():
    from solox.public.adb import ADB
    from solox.public.performance_telemetry import telemetry

    telemetry.reset()
    adb = ADB.__new__(ADB)
    adb.adb_path = 'adb'
    process = MagicMock()
    process.communicate.return_value = (b'ok', b'')

    with patch('solox.public.adb.subprocess.Popen', return_value=process):
        assert adb.shell('getprop ro.product.model', 'device-1') == 'ok'

    snapshot = telemetry.snapshot()
    assert snapshot['adb']['count'] == 1
    assert snapshot['adb']['active'] == 0
    assert snapshot['adb']['max_active'] == 1
    assert snapshot['adb']['max_ms'] >= 0


def test_adb_shell_hides_windows_console():
    from solox.public.adb import ADB

    adb = ADB.__new__(ADB)
    adb.adb_path = 'adb'
    process = MagicMock()
    process.communicate.return_value = (b'ok', b'')

    with (
        patch('solox.public.adb.platform.system', return_value='Windows'),
        patch('solox.public.adb.subprocess.Popen', return_value=process) as popen,
    ):
        assert adb.shell('getprop ro.product.model', 'device-1') == 'ok'

    kwargs = popen.call_args.kwargs
    assert kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW
    assert kwargs['startupinfo'].dwFlags & subprocess.STARTF_USESHOWWINDOW
    assert kwargs['startupinfo'].wShowWindow == 0


def test_adb_device_discovery_records_command_duration():
    from solox.public.common import Devices
    from solox.public.performance_telemetry import telemetry

    telemetry.reset()
    devices = Devices.__new__(Devices)
    devices.adb = 'adb'
    process = MagicMock()
    process.communicate.return_value = (b'List of devices attached\ndevice-1\tdevice\n\n', b'')

    with patch('solox.public.adb.subprocess.Popen', return_value=process):
        assert devices.getDeviceIds() == ['device-1']

    snapshot = telemetry.snapshot()
    assert snapshot['adb']['count'] == 1
    assert snapshot['adb']['active'] == 0


def test_adb_popen_readlines_hides_windows_console_and_avoids_os_popen():
    from solox.public.adb import ADB

    adb = ADB.__new__(ADB)
    adb.adb_path = 'adb'
    process = MagicMock()
    process.communicate.return_value = (b'line-1\nline-2\n', b'')

    with (
        patch('solox.public.adb.platform.system', return_value='Windows'),
        patch('solox.public.adb.os.popen', side_effect=AssertionError('os.popen should not be used')),
        patch('solox.public.adb.subprocess.Popen', return_value=process) as popen,
    ):
        assert adb.popen_readlines('adb devices') == ['line-1\n', 'line-2\n']

    kwargs = popen.call_args.kwargs
    assert kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW
    assert kwargs['startupinfo'].dwFlags & subprocess.STARTF_USESHOWWINDOW
    assert kwargs['startupinfo'].wShowWindow == 0


def test_api_route_dimensions_are_bounded():
    from solox.public.performance_telemetry import PerformanceTelemetry

    local = PerformanceTelemetry(sample_limit=5, route_limit=3)
    for route in ('/apm/one', '/apm/two', '/apm/three'):
        started = local.begin_api(route)
        local.end_api(route, started)

    routes = local.snapshot()['api']['routes']
    assert len(routes) == 3
    assert routes['/apm/one']['count'] == 1
    assert routes['/apm/two']['count'] == 1
    assert routes['__other__']['count'] == 1
