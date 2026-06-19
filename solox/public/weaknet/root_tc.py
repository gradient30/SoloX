"""Root-only Android tc/netem weak-network engine."""

from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock
from typing import Any

from logzero import logger

from .models import WeakNetworkProfile


class RootTcWeakNetworkEngine:
    """Preserve the existing device-side tc/netem behavior behind an engine API."""

    def __init__(
        self,
        *,
        has_root: Callable[[str], bool],
        tc_available: Callable[[str], bool],
        detect_interface: Callable[[str], str | None],
        detect_interface_no_root: Callable[[str], str | None],
        run_root: Callable[[str, str], str],
        active: dict[str, dict[str, Any]],
        lock: Lock,
    ) -> None:
        self._has_root = has_root
        self._tc_available = tc_available
        self._detect_interface = detect_interface
        self._detect_interface_no_root = detect_interface_no_root
        self._run_root = run_root
        self._active = active
        self._lock = lock

    def capabilities(self, device_id: str) -> dict[str, Any]:
        rooted = self._has_root(device_id)
        iface = (
            self._detect_interface(device_id)
            if rooted
            else self._detect_interface_no_root(device_id)
        )
        tc_ok = bool(rooted and iface and self._tc_available(device_id))
        with self._lock:
            active = self._active.get(device_id)
        return {
            'root_available': rooted,
            'tc_available': tc_ok,
            'simulation_supported': tc_ok,
            'interface': iface,
            'active_preset': active.get('preset') if active else None,
            'active_params': active.get('params') if active else None,
            'mode': 'simulation' if active else ('probe_only' if not rooted else 'idle'),
        }

    def status(self, device_id: str) -> dict[str, Any]:
        capabilities = self.capabilities(device_id)
        with self._lock:
            active = self._active.get(device_id)
        capabilities['active'] = active is not None
        if active:
            capabilities['applied_at'] = active.get('applied_at')
            capabilities['interface'] = active.get(
                'interface',
                capabilities.get('interface'),
            )
        return capabilities

    def apply(
        self,
        device_id: str,
        profile: WeakNetworkProfile,
        *,
        preset_id: str = 'custom',
        interface: str | None = None,
        **_options: Any,
    ) -> dict[str, Any]:
        if not self._has_root(device_id):
            raise RuntimeError(
                'simulation requires root (su). Use network probe mode or root your test device.'
            )
        iface = interface or self._detect_interface(device_id)
        if not iface:
            raise RuntimeError('cannot detect active network interface (wlan0/rmnet*)')
        if not self._tc_available(device_id):
            raise RuntimeError('tc/netem not available on device kernel')

        netem = self.build_netem_args(profile)
        if not netem:
            return self.clear(device_id)

        self._run_root(device_id, f'tc qdisc replace dev {iface} root netem {netem}')
        verify = self._run_root(device_id, f'tc qdisc show dev {iface}')
        if 'netem' not in verify.lower():
            raise RuntimeError(f'tc apply failed: {verify[:200]}')

        direction = profile.uplink
        state = {
            'preset': preset_id,
            'interface': iface,
            'params': {
                'delay_ms': direction.delay_ms,
                'jitter_ms': direction.jitter_ms,
                'loss_pct': direction.loss_pct,
                'rate': direction.to_tc_rate(),
            },
            'applied_at': time.time(),
        }
        with self._lock:
            self._active[device_id] = state
        logger.info('[WeakNet] applied %s on %s dev=%s', preset_id, device_id, iface)
        return {'status': 1, 'msg': 'weak network applied', **state}

    def clear(self, device_id: str) -> dict[str, Any]:
        with self._lock:
            previous = self._active.pop(device_id, None)
        iface = (previous or {}).get('interface') or self._detect_interface(device_id)
        cleared = False
        if iface and self._has_root(device_id):
            output = self._run_root(
                device_id,
                f'tc qdisc del dev {iface} root 2>/dev/null; echo cleared',
            )
            cleared = (
                'cleared' in output
                or 'Cannot find' in output
                or 'RTNETLINK' in output
            )
        logger.info('[WeakNet] cleared %s iface=%s', device_id, iface)
        return {
            'status': 1,
            'msg': 'weak network cleared',
            'cleared': cleared,
            'interface': iface,
        }

    @staticmethod
    def build_netem_args(profile: WeakNetworkProfile) -> str:
        direction = profile.uplink
        parts = []
        if direction.delay_ms:
            if direction.jitter_ms:
                parts.append(
                    f'delay {direction.delay_ms}ms {direction.jitter_ms}ms'
                )
            else:
                parts.append(f'delay {direction.delay_ms}ms')
        if direction.loss_pct:
            parts.append(f'loss {direction.loss_pct:g}%')
        rate = direction.to_tc_rate()
        if rate:
            parts.append(f'rate {rate}')
        return ' '.join(parts)
