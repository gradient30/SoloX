# -*- coding: utf-8 -*-
"""Android app/process selection: package metadata and foreground selection."""

import json
import os
import subprocess
import time
from unittest.mock import patch

import pytest

from solox.public.common import Devices, _ANDROID_PACKAGE_LABEL_CACHE, _ANDROID_PACKAGE_LIST_CACHE


@pytest.fixture(autouse=True)
def isolate_android_package_label_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        'solox.public.common.ANDROID_PACKAGE_LABEL_CACHE_FILE',
        str(tmp_path / 'android-package-labels.json'),
    )
    _ANDROID_PACKAGE_LABEL_CACHE.clear()
    _ANDROID_PACKAGE_LIST_CACHE.clear()
    yield
    _ANDROID_PACKAGE_LABEL_CACHE.clear()
    _ANDROID_PACKAGE_LIST_CACHE.clear()


def _client():
    from solox.web import app

    app.config['TESTING'] = True
    return app.test_client()


def test_android_package_endpoint_returns_structured_packages_and_legacy_names():
    client = _client()
    packages = [
        {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'type': 'user',
            'display': 'Demo Game (com.demo.game)',
        },
    ]

    with (
        patch('solox.view.apis.d.getIdbyDevice', return_value='device-1'),
        patch('solox.view.apis.d.getAndroidPackages', return_value=packages, create=True) as mock_packages,
    ):
        resp = client.get(
            '/device/package',
            query_string={
                'platform': 'Android',
                'device': 'device-1(model)',
                'type': 'user',
            },
        )

    data = resp.get_json()
    assert resp.status_code == 200
    assert data['status'] == 1
    assert data['pkgnames'] == ['com.demo.game']
    assert data['packages'] == packages
    mock_packages.assert_called_once_with('device-1', 'user')


def test_android_package_label_endpoint_resolves_requested_packages():
    client = _client()
    packages = [
        {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'display': 'Demo Game (com.demo.game)',
            'label_pending': False,
        },
    ]

    with (
        patch('solox.view.apis.d.getIdbyDevice', return_value='device-1'),
        patch('solox.view.apis.d.resolveAndroidPackageLabels', return_value=packages, create=True) as mock_labels,
    ):
        resp = client.get(
            '/device/package/labels',
            query_string={
                'platform': 'Android',
                'device': 'device-1(model)',
                'packages': 'com.demo.game,com.tencent.mm',
            },
        )

    data = resp.get_json()
    assert resp.status_code == 200
    assert data == {'status': 1, 'packages': packages}
    mock_labels.assert_called_once_with('device-1', ['com.demo.game', 'com.tencent.mm'])


def test_android_device_info_preserves_pkgnames_and_adds_user_packages():
    client = _client()
    packages = [
        {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'type': 'user',
            'display': 'Demo Game (com.demo.game)',
        },
    ]

    with (
        patch('solox.view.apis.d.getDeviceIds', return_value=['device-1']),
        patch('solox.view.apis.d.getDevices', return_value=['device-1(model)']),
        patch('solox.view.apis.d.getPkgname', return_value=['com.demo.game', 'android']),
        patch('solox.view.apis.d.getAndroidPackages', return_value=packages, create=True) as mock_packages,
        patch('solox.view.apis.d.getDdeviceDetail', return_value={'brand': 'Demo'}),
    ):
        resp = client.get('/device/info', query_string={'platform': 'Android'})

    data = resp.get_json()
    assert data['status'] == 1
    assert data['pkgnames'] == ['com.demo.game', 'android']
    assert data['packages'] == packages
    mock_packages.assert_called_once_with('device-1', 'user')


def test_android_foreground_endpoint_returns_single_process_auto_select():
    client = _client()
    foreground = {
        'status': 1,
        'pkgname': 'com.demo.game',
        'package': {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'type': 'user',
            'display': 'Demo Game (com.demo.game)',
        },
        'pids': ['1234:com.demo.game'],
        'auto_select_process': True,
    }

    with (
        patch('solox.view.apis.d.getIdbyDevice', return_value='device-1'),
        patch('solox.view.apis.d.getForegroundAndroidApp', return_value=foreground, create=True) as mock_fg,
    ):
        resp = client.get(
            '/package/foreground',
            query_string={'platform': 'Android', 'device': 'device-1(model)'},
        )

    data = resp.get_json()
    assert resp.status_code == 200
    assert data == foreground
    mock_fg.assert_called_once_with('device-1')


def test_android_foreground_endpoint_returns_multiple_processes_for_manual_choice():
    client = _client()
    foreground = {
        'status': 1,
        'pkgname': 'com.demo.game',
        'package': {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'type': 'user',
            'display': 'Demo Game (com.demo.game)',
        },
        'pids': ['1234:com.demo.game', '1235:com.demo.game:remote'],
        'auto_select_process': False,
    }

    with (
        patch('solox.view.apis.d.getIdbyDevice', return_value='device-1'),
        patch('solox.view.apis.d.getForegroundAndroidApp', return_value=foreground, create=True),
    ):
        resp = client.get(
            '/package/foreground',
            query_string={'platform': 'Android', 'device': 'device-1(model)'},
        )

    data = resp.get_json()
    assert data['status'] == 1
    assert data['pkgname'] == 'com.demo.game'
    assert data['pids'] == ['1234:com.demo.game', '1235:com.demo.game:remote']
    assert data['auto_select_process'] is False


def test_android_package_metadata_returns_quick_pending_items_without_slow_label_scan():
    devices = Devices()

    with (
        patch.object(devices, '_get_android_package_names', return_value=['com.demo.game']),
        patch.object(devices, '_get_android_package_labels_batch', side_effect=AssertionError('slow label scan')),
    ):
        _ANDROID_PACKAGE_LABEL_CACHE.clear()
        _ANDROID_PACKAGE_LIST_CACHE.clear()
        user_packages = devices.getAndroidPackages('device-1', 'user')

    assert user_packages == [
        {
            'package': 'com.demo.game',
            'label': 'com.demo.game',
            'type': 'user',
            'display': 'com.demo.game',
            'label_pending': True,
        },
    ]


def test_android_package_metadata_uses_cached_labels_without_device_lookup():
    devices = Devices()

    with patch.object(devices, '_get_android_package_names', return_value=['com.demo.game']):
        _ANDROID_PACKAGE_LABEL_CACHE.clear()
        _ANDROID_PACKAGE_LIST_CACHE.clear()
        _ANDROID_PACKAGE_LABEL_CACHE['device-1'] = (time.monotonic(), {'com.demo.game': 'Demo Game'})
        user_packages = devices.getAndroidPackages('device-1', 'user')

    assert user_packages == [
        {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'type': 'user',
            'display': 'Demo Game (com.demo.game)',
            'label_pending': False,
        },
    ]


def test_android_label_cache_persists_successful_labels(tmp_path):
    devices = Devices()
    cache_file = tmp_path / 'android-package-labels.json'

    with patch('solox.public.common.ANDROID_PACKAGE_LABEL_CACHE_FILE', str(cache_file)):
        _ANDROID_PACKAGE_LABEL_CACHE.clear()
        devices._cache_android_package_labels('device-1', {'com.demo.game': 'Demo Game'})

    payload = json.loads(cache_file.read_text(encoding='utf-8'))
    assert payload['version'] == 1
    assert payload['devices']['device-1']['labels'] == {'com.demo.game': 'Demo Game'}


def test_android_label_cache_is_reused_after_memory_cache_is_cleared(tmp_path):
    devices = Devices()
    cache_file = tmp_path / 'android-package-labels.json'
    cache_file.write_text(
        json.dumps({
            'version': 1,
            'devices': {
                'device-1': {
                    'updated_at': time.time(),
                    'labels': {'com.demo.game': 'Demo Game'},
                },
            },
        }),
        encoding='utf-8',
    )

    with (
        patch('solox.public.common.ANDROID_PACKAGE_LABEL_CACHE_FILE', str(cache_file)),
        patch.object(
            devices,
            '_resolve_android_label_with_aapt',
            side_effect=AssertionError('ADB label extraction should not run'),
        ),
        patch.object(
            devices,
            '_resolve_android_label_from_dumpsys',
            side_effect=AssertionError('dumpsys label extraction should not run'),
        ),
    ):
        _ANDROID_PACKAGE_LABEL_CACHE.clear()
        packages = devices.resolveAndroidPackageLabels('device-1', ['com.demo.game'])

    assert packages == [
        {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'display': 'Demo Game (com.demo.game)',
            'label_pending': False,
        },
    ]


def test_android_label_resolver_uses_dumpsys_before_aapt_pull():
    devices = Devices()

    with (
        patch.object(devices, '_resolve_android_label_from_dumpsys', return_value='Demo Game') as mock_dumpsys,
        patch.object(devices, '_resolve_android_label_with_aapt', side_effect=AssertionError('apk pull should not run')),
    ):
        _ANDROID_PACKAGE_LABEL_CACHE.clear()
        packages = devices.resolveAndroidPackageLabels('device-1', ['com.demo.game'])

    assert packages == [
        {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'display': 'Demo Game (com.demo.game)',
            'label_pending': False,
        },
    ]
    mock_dumpsys.assert_called_once_with('device-1', 'com.demo.game')


def test_android_label_resolver_does_not_pull_apk_by_default_when_dumpsys_missing():
    devices = Devices()

    with (
        patch.object(devices, '_resolve_android_label_from_dumpsys', return_value=''),
        patch.object(devices, '_resolve_android_label_with_aapt', side_effect=AssertionError('apk pull should not run')),
    ):
        _ANDROID_PACKAGE_LABEL_CACHE.clear()
        packages = devices.resolveAndroidPackageLabels('device-1', ['com.demo.game'])

    assert packages == [
        {
            'package': 'com.demo.game',
            'label': 'com.demo.game',
            'display': 'com.demo.game',
            'label_pending': True,
        },
    ]


def test_android_label_resolver_uses_aapt_badging_when_explicitly_enabled():
    devices = Devices()
    calls = []
    timeouts = []

    def fake_run(args, **kwargs):
        calls.append(args)
        timeouts.append(kwargs.get('timeout'))
        assert kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW
        assert kwargs['startupinfo'].dwFlags & subprocess.STARTF_USESHOWWINDOW
        assert kwargs['startupinfo'].wShowWindow == 0
        assert kwargs['stdin'] == subprocess.DEVNULL
        if 'aapt' in args[0]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="package: name='com.demo.game'\napplication-label:'Demo Game'\n",
                stderr='',
            )
        return subprocess.CompletedProcess(args, 0, stdout='', stderr='')

    with (
        patch('solox.public.common.shutil.which', return_value='aapt'),
        patch('solox.public.common.platform.system', return_value='Windows'),
        patch('solox.public.common.adb.popen_readlines', return_value=['package:/data/app/com.demo.game/base.apk\n']),
        patch('solox.public.common.adb.shell', return_value='compat={480dpi} labelRes=0x7f100fe4\n'),
        patch('solox.public.common.subprocess.run', side_effect=fake_run),
        patch.dict(os.environ, {'SOLOX_ANDROID_LABEL_USE_AAPT': '1'}),
    ):
        _ANDROID_PACKAGE_LABEL_CACHE.clear()
        packages = devices.resolveAndroidPackageLabels('device-1', ['com.demo.game'])

    assert packages == [
        {
            'package': 'com.demo.game',
            'label': 'Demo Game',
            'display': 'Demo Game (com.demo.game)',
            'label_pending': False,
        },
    ]
    assert any('pull' in call for call in calls)
    assert any('aapt' in call[0] for call in calls)
    assert max(timeout for timeout in timeouts if timeout is not None) <= 10


def test_android_label_resolver_falls_back_to_package_name_when_aapt_missing():
    devices = Devices()

    with (
        patch('solox.public.common.shutil.which', return_value=None),
        patch('solox.public.common.adb.shell', return_value='compat={480dpi} labelRes=0x7f100fe4\n'),
    ):
        _ANDROID_PACKAGE_LABEL_CACHE.clear()
        packages = devices.resolveAndroidPackageLabels('device-1', ['com.tencent.mm'])

    assert packages == [
        {
            'package': 'com.tencent.mm',
            'label': 'com.tencent.mm',
            'display': 'com.tencent.mm',
            'label_pending': True,
        },
    ]


def test_parse_package_labels_from_dumpsys_supports_application_label():
    devices = Devices()
    output = (
        'Package [com.tencent.tmgp.sgame] (abc):\n'
        '  applicationLabel=王者荣耀\n'
        'Package [com.example.service] (def):\n'
        '  nonLocalizedLabel=Hidden Service labelRes=0x0\n'
    )
    labels = devices._parse_package_labels_from_dumpsys(output)
    assert labels['com.tencent.tmgp.sgame'] == '王者荣耀'
    assert labels['com.example.service'] == 'Hidden Service'


def test_parse_package_labels_from_dumpsys_supports_inline_application_label():
    devices = Devices()
    output = (
        'Package [com.tencent.mm] (abc): applicationLabel=微信 flags=[ HAS_CODE ]\n'
        'Package [com.game.legend] (def): applicationLabel=传奇岁月\n'
    )
    labels = devices._parse_package_labels_from_dumpsys(output)
    assert labels['com.tencent.mm'] == '微信'
    assert labels['com.game.legend'] == '传奇岁月'


def test_fill_missing_android_package_labels_uses_chunked_device_lookup():
    devices = Devices()
    label_map = {'com.tencent.mm': 'com.tencent.mm', 'com.demo.game': 'Demo Game'}

    def fake_shell(cmd, deviceId):
        assert 'for pkg in' in cmd
        assert 'com.tencent.mm' in cmd
        return 'com.tencent.mm|微信\n'

    with patch('solox.public.common.adb.shell', side_effect=fake_shell):
        filled = devices._fill_missing_android_package_labels('device-1', list(label_map), label_map)

    assert filled['com.tencent.mm'] == '微信'
    assert filled['com.demo.game'] == 'Demo Game'


def test_android_foreground_helper_ignores_system_foreground_app():
    devices = Devices()

    with (
        patch.object(devices, 'getCurrentActivity', return_value='com.android.settings/.Settings'),
        patch.object(devices, '_get_android_package_names', return_value=['com.demo.game']),
        patch.object(devices, 'getPid', return_value=['2222:com.android.settings']),
    ):
        result = devices.getForegroundAndroidApp('device-1')

    assert result['status'] == 0
    assert 'foreground app is not a third-party app' in result['msg']
