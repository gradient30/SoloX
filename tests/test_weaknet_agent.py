import json
import socket
from pathlib import Path

import pytest

from solox.public.weaknet.agent import (
    AgentCommandResult,
    AgentSocketTransport,
    AndroidAgentController,
)
from solox.public.weaknet.agent_protocol import (
    AgentProtocolError,
    decode_response,
)
from solox.public.weaknet.models import WeakNetworkProfile


class FakeAdbClient:

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def run(self, device_id, args, timeout=30):
        self.calls.append((device_id, tuple(args), timeout))
        if self.responses:
            return self.responses.pop(0)
        return AgentCommandResult(returncode=0, stdout='', stderr='')


class FakeRequestSender:

    def __init__(self, handler):
        self.handler = handler
        self.requests = []

    def __call__(self, device_id, request):
        self.requests.append((device_id, request))
        return self.handler(device_id, request)


def test_capabilities_reports_missing_apk_without_installing(tmp_path):
    adb_client = FakeAdbClient([
        AgentCommandResult(returncode=0, stdout='', stderr=''),
    ])
    controller = AndroidAgentController(
        adb_client=adb_client,
        apk_path=tmp_path / 'missing.apk',
        request_sender=lambda *_args: pytest.fail('status socket must not be queried'),
    )

    result = controller.capabilities('device-1')

    assert result['apk_available'] is False
    assert result['installed'] is False
    assert all(call[1][0] != 'install' for call in adb_client.calls)


def test_capabilities_parses_installed_version(tmp_path):
    apk_path = tmp_path / 'agent.apk'
    apk_path.write_bytes(b'apk')
    adb_client = FakeAdbClient([
        AgentCommandResult(
            returncode=0,
            stdout='versionCode=12 minSdk=21 targetSdk=36\nversionName=1.2.0',
            stderr='',
        ),
    ])
    sender = FakeRequestSender(
        lambda _device, request: {
            'schema_version': 1,
            'request_id': request['request_id'],
            'ok': True,
            'payload': {'state': 'idle', 'protocol_version': 1},
            'error': None,
        }
    )
    controller = AndroidAgentController(adb_client, apk_path, sender)

    result = controller.capabilities('device-1')

    assert result['installed'] is True
    assert result['installed_version'] == '1.2.0'
    assert result['installed_version_code'] == 12
    assert result['reachable'] is True


def test_install_is_explicit_and_uses_replace_flag(tmp_path):
    apk_path = tmp_path / 'agent.apk'
    apk_path.write_bytes(b'apk')
    adb_client = FakeAdbClient([
        AgentCommandResult(returncode=0, stdout='Success', stderr=''),
    ])
    controller = AndroidAgentController(adb_client, apk_path)

    result = controller.install('device-1')

    assert result['installed'] is True
    assert adb_client.calls == [
        ('device-1', ('install', '-r', str(apk_path)), 120),
    ]


def test_install_rejects_apk_when_checksum_metadata_does_not_match(tmp_path):
    apk_path = tmp_path / 'qas-network-agent-0.1.0.apk'
    apk_path.write_bytes(b'tampered-apk')
    (tmp_path / 'checksums.json').write_text(
        json.dumps({
            'apk': apk_path.name,
            'sha256': '0' * 64,
            'version': '0.1.0',
            'version_code': 1,
            'package_id': 'io.solox.networkagent',
            'min_protocol_version': 1,
        }),
        encoding='utf-8',
    )
    adb_client = FakeAdbClient([
        AgentCommandResult(returncode=0, stdout='Success', stderr=''),
    ])
    controller = AndroidAgentController(adb_client, apk_path)

    with pytest.raises(RuntimeError, match='checksum'):
        controller.install('device-1')

    assert adb_client.calls == []

def test_install_falls_back_to_shell_pm_install_when_streamed_install_is_aborted(tmp_path):
    apk_path = tmp_path / 'agent.apk'
    apk_path.write_bytes(b'apk')
    adb_client = FakeAdbClient([
        AgentCommandResult(
            returncode=1,
            stdout='',
            stderr='Failure [INSTALL_FAILED_ABORTED: User rejected permissions]',
        ),
        AgentCommandResult(returncode=0, stdout='1 file pushed', stderr=''),
        AgentCommandResult(returncode=0, stdout='Success', stderr=''),
    ])
    controller = AndroidAgentController(adb_client, apk_path)

    result = controller.install('device-1')

    assert result['installed'] is True
    assert adb_client.calls == [
        ('device-1', ('install', '-r', str(apk_path)), 120),
        ('device-1', ('push', str(apk_path), '/data/local/tmp/solox-network-agent.apk'), 120),
        ('device-1', ('shell', 'pm', 'install', '-r', '/data/local/tmp/solox-network-agent.apk'), 120),
    ]


def test_prepare_starts_visible_permission_activity(tmp_path):
    apk_path = tmp_path / 'agent.apk'
    apk_path.write_bytes(b'apk')
    adb_client = FakeAdbClient([
        AgentCommandResult(returncode=0, stdout='Starting: Intent', stderr=''),
    ])
    controller = AndroidAgentController(adb_client, apk_path)

    result = controller.prepare('device-1')

    assert result['started'] is True
    assert adb_client.calls[0][1] == (
        'shell',
        'am',
        'start',
        '-n',
        'io.solox.networkagent/.MainActivity',
        '--ez',
        'request_vpn',
        'true',
    )


def test_prepare_rejects_adb_activity_error_with_zero_exit_code(tmp_path):
    apk_path = tmp_path / 'agent.apk'
    apk_path.write_bytes(b'apk')
    adb_client = FakeAdbClient([
        AgentCommandResult(
            returncode=0,
            stdout='Error type 3\nActivity class does not exist.',
            stderr='',
        ),
    ])
    controller = AndroidAgentController(adb_client, apk_path)

    with pytest.raises(RuntimeError, match='does not exist'):
        controller.prepare('device-1')


def test_decode_response_rejects_unknown_schema():
    raw = json.dumps({
        'schema_version': 2,
        'request_id': 'request-1',
        'ok': True,
        'payload': {},
        'error': None,
    })

    with pytest.raises(AgentProtocolError, match='schema'):
        decode_response(raw, expected_request_id='request-1')


def test_decode_response_wraps_invalid_utf8():
    with pytest.raises(AgentProtocolError, match='UTF-8'):
        decode_response(b'\xff', expected_request_id='request-1')


def test_apply_requires_matching_active_session_and_digest(tmp_path):
    apk_path = tmp_path / 'agent.apk'
    apk_path.write_bytes(b'apk')
    adb_client = FakeAdbClient()

    def respond(_device, request):
        if request['command'] == 'stop':
            return {
                'schema_version': 1,
                'request_id': request['request_id'],
                'ok': True,
                'payload': {'state': 'idle'},
                'error': None,
            }
        return {
            'schema_version': 1,
            'request_id': request['request_id'],
            'ok': True,
            'payload': {
                'state': 'active',
                'session_id': request['payload']['session_id'],
                'profile_digest': 'wrong-digest',
            },
            'error': None,
        }

    sender = FakeRequestSender(respond)
    controller = AndroidAgentController(adb_client, apk_path, sender)

    with pytest.raises(RuntimeError, match='profile digest'):
        controller.apply(
            'device-1',
            'com.example.app',
            WeakNetworkProfile.from_legacy(delay_ms=100),
        )

    assert [item[1]['command'] for item in sender.requests] == ['start', 'stop']


def test_apply_timeout_attempts_stop_and_preserves_failure(tmp_path):
    apk_path = tmp_path / 'agent.apk'
    apk_path.write_bytes(b'apk')
    adb_client = FakeAdbClient()

    def respond(_device, request):
        if request['command'] == 'start':
            raise TimeoutError('agent timeout')
        return {
            'schema_version': 1,
            'request_id': request['request_id'],
            'ok': True,
            'payload': {'state': 'idle'},
            'error': None,
        }

    sender = FakeRequestSender(respond)
    controller = AndroidAgentController(adb_client, apk_path, sender)

    with pytest.raises(RuntimeError, match='agent timeout'):
        controller.apply(
            'device-1',
            'com.example.app',
            WeakNetworkProfile.from_legacy(loss_pct=1),
        )

    assert [item[1]['command'] for item in sender.requests] == ['start', 'stop']


class FakeSocket:

    def __init__(self, response):
        self.response = response
        self.sent = b''
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True

    def sendall(self, data):
        self.sent += data

    def makefile(self, _mode, encoding=None, newline=None):
        class Reader:
            def __init__(self, response):
                self.response = response

            def readline(self, _limit):
                return self.response

            def close(self):
                return None

        return Reader(self.response)


def test_socket_transport_creates_and_removes_adb_forward(monkeypatch):
    adb_client = FakeAdbClient([
        AgentCommandResult(returncode=0, stdout='', stderr=''),
        AgentCommandResult(returncode=0, stdout='', stderr=''),
    ])
    response = json.dumps({
        'schema_version': 1,
        'request_id': 'request-1',
        'ok': True,
        'payload': {'state': 'idle'},
        'error': None,
    }) + '\n'
    fake_socket = FakeSocket(response)
    monkeypatch.setattr(
        socket,
        'create_connection',
        lambda address, timeout: fake_socket,
    )
    transport = AgentSocketTransport(
        adb_client,
        port_allocator=lambda: 43123,
    )
    request = {
        'schema_version': 1,
        'request_id': 'request-1',
        'command': 'status',
        'payload': {},
    }

    result = transport.send('device-1', request)

    assert result['payload']['state'] == 'idle'
    assert adb_client.calls[0][1] == (
        'forward',
        'tcp:43123',
        'localabstract:solox.networkagent.control',
    )
    assert adb_client.calls[1][1] == (
        'forward',
        '--remove',
        'tcp:43123',
    )
    assert fake_socket.sent.endswith(b'\n')
