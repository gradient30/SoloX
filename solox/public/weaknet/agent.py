"""Host-side lifecycle and control for the Android weak-network Agent."""

from __future__ import annotations

import hashlib
import json
import re
import socket
import subprocess
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from solox.public.adb import _windows_hidden_process_kwargs, adb

from .agent_protocol import (
    MAX_MESSAGE_BYTES,
    AgentProtocolError,
    build_request,
    decode_response,
    encode_message,
)
from .models import WeakNetworkProfile

AGENT_PACKAGE = 'io.solox.networkagent'
AGENT_ACTIVITY = f'{AGENT_PACKAGE}/.MainActivity'
AGENT_SOCKET = 'solox.networkagent.control'
AGENT_PUBLIC_DIR = Path(__file__).resolve().parents[1] / 'android_agent'


@dataclass(frozen=True)
class AgentCommandResult:
    returncode: int
    stdout: str
    stderr: str


class AgentAdbClient(Protocol):
    def run(
        self,
        device_id: str,
        args: Sequence[str],
        timeout: int = 30,
    ) -> AgentCommandResult:
        """Run an ADB command for one device."""


class SubprocessAgentAdbClient:
    """ADB adapter with structured arguments and hidden Windows processes."""

    def __init__(self, adb_path: str | None = None) -> None:
        self.adb_path = adb_path or adb.adb_path

    def run(
        self,
        device_id: str,
        args: Sequence[str],
        timeout: int = 30,
    ) -> AgentCommandResult:
        command = [self.adb_path, '-s', device_id, *args]
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            check=False,
            **_windows_hidden_process_kwargs(),
        )
        return AgentCommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )


def _allocate_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        return int(listener.getsockname()[1])


class AgentSocketTransport:
    """Send one request through a temporary ADB-forwarded local socket."""

    def __init__(
        self,
        adb_client: AgentAdbClient,
        *,
        port_allocator: Callable[[], int] = _allocate_local_port,
        timeout: float = 5.0,
    ) -> None:
        self._adb = adb_client
        self._port_allocator = port_allocator
        self._timeout = timeout

    def send(
        self,
        device_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        port = self._port_allocator()
        local = f'tcp:{port}'
        forward = self._adb.run(
            device_id,
            ('forward', local, f'localabstract:{AGENT_SOCKET}'),
        )
        if forward.returncode != 0:
            detail = forward.stderr or forward.stdout or 'unknown adb error'
            raise RuntimeError(f'cannot forward Agent control socket: {detail}')

        try:
            with socket.create_connection(
                ('127.0.0.1', port),
                timeout=self._timeout,
            ) as connection:
                connection.sendall(encode_message(request))
                reader = connection.makefile('r', encoding='utf-8', newline='\n')
                try:
                    raw = reader.readline(MAX_MESSAGE_BYTES + 1)
                finally:
                    reader.close()
                if not raw:
                    raise AgentProtocolError('Agent closed the control socket')
                if len(raw.encode('utf-8')) > MAX_MESSAGE_BYTES:
                    raise AgentProtocolError('Agent response exceeds size limit')
                if not raw.endswith('\n'):
                    raise AgentProtocolError('Agent response is not newline terminated')
                return decode_response(
                    raw,
                    expected_request_id=request['request_id'],
                )
        finally:
            self._adb.run(device_id, ('forward', '--remove', local))


RequestSender = Callable[[str, dict[str, Any]], dict[str, Any]]


class AndroidAgentController:
    """Explicitly install, authorize and control the Android Agent."""

    def __init__(
        self,
        adb_client: AgentAdbClient | None = None,
        apk_path: str | Path | None = None,
        request_sender: RequestSender | None = None,
    ) -> None:
        self._adb = adb_client or SubprocessAgentAdbClient()
        self.apk_path = Path(apk_path) if apk_path else self.default_apk_path()
        self._transport = AgentSocketTransport(self._adb)
        self._request_sender = request_sender or self._transport.send

    @staticmethod
    def default_apk_path() -> Path:
        metadata_path = AGENT_PUBLIC_DIR / 'checksums.json'
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                apk_name = metadata.get('apk')
                if isinstance(apk_name, str) and apk_name:
                    return AGENT_PUBLIC_DIR / apk_name
            except (OSError, ValueError, TypeError):
                pass
        return AGENT_PUBLIC_DIR / 'qas-network-agent.apk'

    def capabilities(self, device_id: str) -> dict[str, Any]:
        package = self._package_info(device_id)
        result = {
            'apk_available': self.apk_path.is_file(),
            'apk_path': str(self.apk_path),
            'installed': package['installed'],
            'installed_version': package['version_name'],
            'installed_version_code': package['version_code'],
            'reachable': False,
            'state': 'not_installed' if not package['installed'] else 'unreachable',
            'protocol_version': None,
            'simulation_supported': False,
        }
        if not package['installed']:
            return result
        try:
            status = self.status(device_id)
        except (OSError, RuntimeError, TimeoutError, AgentProtocolError):
            return result
        result.update({
            'reachable': True,
            'state': status.get('state', 'unknown'),
            'protocol_version': status.get('protocol_version'),
            'simulation_supported': status.get('state') not in (
                'permission_required',
                'error',
            ),
        })
        return result

    def install(self, device_id: str) -> dict[str, Any]:
        if not self.apk_path.is_file():
            raise FileNotFoundError(f'Android Agent APK not found: {self.apk_path}')
        self._verify_apk_checksum()
        result = self._adb.run(
            device_id,
            ('install', '-r', str(self.apk_path)),
            timeout=120,
        )
        if result.returncode == 0 and 'success' in result.stdout.lower():
            return {'installed': True, 'msg': result.stdout}

        detail = result.stderr or result.stdout or 'unknown adb error'
        if 'INSTALL_FAILED_ABORTED' not in detail:
            raise RuntimeError(f'Agent installation failed: {detail}')
        return self._install_via_shell_pm(device_id, detail)

    def _install_via_shell_pm(self, device_id: str, original_error: str) -> dict[str, Any]:
        remote_apk = '/data/local/tmp/solox-network-agent.apk'
        push = self._adb.run(
            device_id,
            ('push', str(self.apk_path), remote_apk),
            timeout=120,
        )
        if push.returncode != 0:
            detail = push.stderr or push.stdout or original_error
            raise RuntimeError(f'Agent installation failed: {detail}')
        install = self._adb.run(
            device_id,
            ('shell', 'pm', 'install', '-r', remote_apk),
            timeout=120,
        )
        if install.returncode != 0 or 'success' not in install.stdout.lower():
            detail = install.stderr or install.stdout or original_error
            raise RuntimeError(f'Agent installation failed: {detail}')
        return {'installed': True, 'msg': install.stdout, 'fallback': 'pm_install'}

    def _verify_apk_checksum(self) -> None:
        metadata_path = self.apk_path.parent / 'checksums.json'
        if not metadata_path.is_file():
            return
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        if metadata.get('apk') != self.apk_path.name:
            return
        expected = str(metadata.get('sha256', '')).lower()
        if not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise RuntimeError('Agent APK checksum metadata is invalid')
        actual = hashlib.sha256(self.apk_path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(
                f'Agent APK checksum mismatch: expected {expected}, got {actual}'
            )

    def prepare(self, device_id: str) -> dict[str, Any]:
        result = self._adb.run(
            device_id,
            (
                'shell',
                'am',
                'start',
                '-n',
                AGENT_ACTIVITY,
                '--ez',
                'request_vpn',
                'true',
            ),
        )
        output = '\n'.join(item for item in (result.stdout, result.stderr) if item)
        if result.returncode != 0 or re.search(
            r'(?im)^(?:error|exception)|does not exist',
            output,
        ):
            detail = result.stderr or result.stdout or 'unknown adb error'
            raise RuntimeError(f'cannot start Agent authorization: {detail}')
        return {'started': True, 'msg': result.stdout}

    def apply(
        self,
        device_id: str,
        target_package: str,
        profile: WeakNetworkProfile,
    ) -> dict[str, Any]:
        target_package = target_package.strip()
        if not target_package:
            raise ValueError('target package is required for Agent mode')
        session_id = str(uuid.uuid4())
        profile_data = profile.to_dict()
        digest = self.profile_digest(profile_data)
        request = build_request(
            'start',
            {
                'session_id': session_id,
                'target_package': target_package,
                'profile': profile_data,
                'profile_digest': digest,
            },
        )
        try:
            response = self._send(device_id, request)
        except Exception as exc:
            self._best_effort_stop(device_id)
            raise RuntimeError(f'Agent start failed: {exc}') from exc

        payload = response['payload']
        if payload.get('state') != 'active':
            self._best_effort_stop(device_id)
            raise RuntimeError(
                f'Agent did not become active: {payload.get("state", "unknown")}'
            )
        if payload.get('session_id') != session_id:
            self._best_effort_stop(device_id)
            raise RuntimeError('Agent session id does not match start request')
        if payload.get('profile_digest') != digest:
            self._best_effort_stop(device_id)
            raise RuntimeError('Agent profile digest does not match start request')
        return {
            'status': 1,
            'engine': 'agent',
            'active': True,
            'session_id': session_id,
            'target_package': target_package,
            'profile': profile_data,
            **payload,
        }

    def status(self, device_id: str) -> dict[str, Any]:
        response = self._send(device_id, build_request('status'))
        return response['payload']

    def clear(self, device_id: str) -> dict[str, Any]:
        response = self._send(device_id, build_request('stop'))
        return {'status': 1, 'engine': 'agent', **response['payload']}

    def _best_effort_stop(self, device_id: str) -> None:
        try:
            self.clear(device_id)
        except Exception:
            pass

    def _send(
        self,
        device_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        raw = self._request_sender(device_id, request)
        response = decode_response(
            json.dumps(raw) if isinstance(raw, dict) else raw,
            expected_request_id=request['request_id'],
        )
        if not response['ok']:
            raise RuntimeError(response.get('error') or 'Agent request failed')
        return response

    def _package_info(self, device_id: str) -> dict[str, Any]:
        result = self._adb.run(
            device_id,
            ('shell', 'dumpsys', 'package', AGENT_PACKAGE),
        )
        output = result.stdout
        installed = result.returncode == 0 and bool(
            re.search(r'\bversionCode=\d+', output)
        )
        version_name = None
        version_code = None
        if installed:
            version_match = re.search(r'\bversionName=([^\s]+)', output)
            code_match = re.search(r'\bversionCode=(\d+)', output)
            if version_match:
                version_name = version_match.group(1)
            if code_match:
                version_code = int(code_match.group(1))
        return {
            'installed': installed,
            'version_name': version_name,
            'version_code': version_code,
        }

    @staticmethod
    def profile_digest(profile: dict[str, Any]) -> str:
        encoded = json.dumps(
            profile,
            ensure_ascii=True,
            separators=(',', ':'),
            sort_keys=True,
        ).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()
