# -*- coding: utf-8 -*-
"""Weak-network simulation (tc netem) and quality probing for Android devices."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any

from solox.public.adb import adb
from solox.public.weaknet.agent import AndroidAgentController
from solox.public.weaknet.models import (
    DirectionProfile,
    WeakNetworkProfile,
    parse_rate_kbps,
)
from solox.public.weaknet.root_tc import RootTcWeakNetworkEngine

# PerfDog-style presets: delay / jitter / loss / egress rate limit
WEAKNET_PRESETS: dict[str, dict[str, Any]] = {
    'off': {
        'label_cn': '关闭',
        'label_en': 'Off',
        'delay_ms': 0,
        'jitter_ms': 0,
        'loss_pct': 0,
    },
    'wifi_good': {
        'label_cn': 'WiFi 良好',
        'label_en': 'WiFi Good',
        'delay_ms': 20,
        'jitter_ms': 5,
        'loss_pct': 0,
    },
    'lte_good': {
        'label_cn': '4G 良好',
        'label_en': 'LTE Good',
        'delay_ms': 50,
        'jitter_ms': 10,
        'loss_pct': 0,
    },
    'lte_weak': {
        'label_cn': '4G 弱网',
        'label_en': 'LTE Weak',
        'delay_ms': 200,
        'jitter_ms': 50,
        'loss_pct': 2,
        'rate': '5mbit',
    },
    '3g': {
        'label_cn': '3G',
        'label_en': '3G',
        'delay_ms': 300,
        'jitter_ms': 80,
        'loss_pct': 1,
        'rate': '1500kbit',
    },
    '2g': {
        'label_cn': '2G',
        'label_en': '2G',
        'delay_ms': 600,
        'jitter_ms': 100,
        'loss_pct': 3,
        'rate': '256kbit',
    },
    'high_latency': {
        'label_cn': '高延迟',
        'label_en': 'High Latency',
        'delay_ms': 500,
        'jitter_ms': 0,
        'loss_pct': 0,
    },
    'high_loss': {
        'label_cn': '高丢包',
        'label_en': 'High Packet Loss',
        'delay_ms': 100,
        'jitter_ms': 0,
        'loss_pct': 10,
    },
    'very_weak': {
        'label_cn': '极差网络',
        'label_en': 'Very Weak',
        'delay_ms': 800,
        'jitter_ms': 200,
        'loss_pct': 5,
        'rate': '128kbit',
    },
}

_lock = threading.Lock()
_active: dict[str, dict[str, Any]] = {}
_active_engines: dict[str, str] = {}


@dataclass
class ProbeResult:
    host: str
    sent: int = 0
    received: int = 0
    loss_pct: float = 0.0
    rtt_min_ms: float = 0.0
    rtt_avg_ms: float = 0.0
    rtt_max_ms: float = 0.0
    jitter_ms: float = 0.0
    raw: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'host': self.host,
            'sent': self.sent,
            'received': self.received,
            'loss_pct': self.loss_pct,
            'rtt_min_ms': self.rtt_min_ms,
            'rtt_avg_ms': self.rtt_avg_ms,
            'rtt_max_ms': self.rtt_max_ms,
            'jitter_ms': self.jitter_ms,
        }


class WeakNetworkManager:
    """Apply Linux tc/netem on device (root) or run latency probes (all devices)."""

    DEFAULT_PROBE_HOST = '8.8.8.8'
    _agent_controller: AndroidAgentController | None = None

    @classmethod
    def _agent(cls) -> AndroidAgentController:
        if cls._agent_controller is None:
            cls._agent_controller = AndroidAgentController()
        return cls._agent_controller

    @classmethod
    def _root_engine(cls) -> RootTcWeakNetworkEngine:
        return RootTcWeakNetworkEngine(
            has_root=cls._has_root,
            tc_available=cls._tc_available,
            detect_interface=cls._detect_interface,
            detect_interface_no_root=cls._detect_interface_no_root,
            run_root=cls._run_root,
            active=_active,
            lock=_lock,
        )

    @classmethod
    def list_presets(cls, lan: str = 'cn') -> list[dict[str, Any]]:
        label_key = 'label_cn' if lan == 'cn' else 'label_en'
        items = []
        for key, cfg in WEAKNET_PRESETS.items():
            if key == 'off':
                continue
            items.append({
                'id': key,
                'label': cfg.get(label_key, key),
                'delay_ms': cfg.get('delay_ms', 0),
                'jitter_ms': cfg.get('jitter_ms', 0),
                'loss_pct': cfg.get('loss_pct', 0),
                'rate': cfg.get('rate'),
            })
        return items

    @classmethod
    def get_capabilities(
        cls,
        device_id: str,
        engine: str = 'auto',
    ) -> dict[str, Any]:
        cls._validate_engine(engine)
        root = cls._root_engine().capabilities(device_id)
        agent = cls._agent_capabilities(device_id)
        with _lock:
            active_engine = _active_engines.get(device_id)
        result = {
            **root,
            'simulation_supported': bool(
                root.get('simulation_supported')
                or agent.get('simulation_supported')
            ),
            'agent': agent,
            'available_engines': [
                name
                for name, supported in (
                    ('agent', agent.get('simulation_supported')),
                    ('root_tc', root.get('simulation_supported')),
                )
                if supported
            ],
            'active_engine': active_engine,
        }
        if active_engine == 'agent':
            result['mode'] = 'simulation'
            result['engine'] = 'agent'
        elif root.get('mode') == 'simulation':
            result['engine'] = 'root_tc'
        return result

    @classmethod
    def get_status(cls, device_id: str) -> dict[str, Any]:
        with _lock:
            active_engine = _active_engines.get(device_id)
        if active_engine == 'agent':
            status = cls._agent().status(device_id)
            return {
                **status,
                'engine': 'agent',
                'active_engine': 'agent',
                'active': status.get('state') == 'active',
            }
        status = cls._root_engine().status(device_id)
        if status.get('active'):
            status['engine'] = 'root_tc'
            status['active_engine'] = 'root_tc'
        return status

    @classmethod
    def apply_preset(
        cls,
        device_id: str,
        preset_id: str,
        *,
        engine: str = 'auto',
        target_package: str | None = None,
    ) -> dict[str, Any]:
        if preset_id == 'off':
            return cls.clear(device_id, engine=engine)
        if preset_id not in WEAKNET_PRESETS:
            raise ValueError(f'unknown preset: {preset_id}')
        cfg = dict(WEAKNET_PRESETS[preset_id])
        cfg.pop('label_cn', None)
        cfg.pop('label_en', None)
        return cls.apply_custom(
            device_id,
            preset_id=preset_id,
            engine=engine,
            target_package=target_package,
            **cfg,
        )

    @classmethod
    def apply_custom(
        cls,
        device_id: str,
        preset_id: str = 'custom',
        delay_ms: int = 0,
        jitter_ms: int = 0,
        loss_pct: float = 0,
        rate: str | None = None,
        interface: str | None = None,
        engine: str = 'auto',
        target_package: str | None = None,
        uplink_delay_ms: int | None = None,
        uplink_jitter_ms: int | None = None,
        uplink_loss_pct: float | None = None,
        uplink_rate: str | int | float | None = None,
        uplink_burst_loss_pct: float = 0,
        downlink_delay_ms: int | None = None,
        downlink_jitter_ms: int | None = None,
        downlink_loss_pct: float | None = None,
        downlink_rate: str | int | float | None = None,
        downlink_burst_loss_pct: float = 0,
        protocol: str = 'all',
        ip_filter: tuple[str, ...] | list[str] | None = None,
    ) -> dict[str, Any]:
        cls._validate_engine(engine)
        profile = cls._build_profile(
            delay_ms=delay_ms,
            jitter_ms=jitter_ms,
            loss_pct=loss_pct,
            rate=rate,
            uplink_delay_ms=uplink_delay_ms,
            uplink_jitter_ms=uplink_jitter_ms,
            uplink_loss_pct=uplink_loss_pct,
            uplink_rate=uplink_rate,
            uplink_burst_loss_pct=uplink_burst_loss_pct,
            downlink_delay_ms=downlink_delay_ms,
            downlink_jitter_ms=downlink_jitter_ms,
            downlink_loss_pct=downlink_loss_pct,
            downlink_rate=downlink_rate,
            downlink_burst_loss_pct=downlink_burst_loss_pct,
            protocol=protocol,
            ip_filter=ip_filter,
        )
        selected = engine
        if selected == 'auto':
            agent = cls._agent_capabilities(device_id)
            if agent.get('simulation_supported') and target_package:
                selected = 'agent'
            else:
                root = cls._root_engine().capabilities(device_id)
                if root.get('simulation_supported'):
                    selected = 'root_tc'
                elif agent.get('simulation_supported'):
                    raise ValueError('target package is required for Agent mode')
                elif agent.get('installed') and agent.get('state') == 'permission_required':
                    raise RuntimeError('Android Agent VPN authorization is required')
                else:
                    raise RuntimeError(
                        'weak network simulation requires an authorized Android Agent '
                        'or root tc/netem support'
                    )

        if selected == 'agent':
            if not target_package or not target_package.strip():
                raise ValueError('target package is required for Agent mode')
            capabilities = cls._agent_capabilities(device_id)
            if not capabilities.get('installed'):
                raise RuntimeError('Android Agent is not installed')
            if not capabilities.get('reachable'):
                raise RuntimeError('Android Agent is not reachable')
            if not capabilities.get('simulation_supported'):
                if capabilities.get('state') == 'permission_required':
                    raise RuntimeError('Android Agent VPN authorization is required')
                raise RuntimeError('Android Agent is not ready')
            result = cls._agent().apply(
                device_id,
                target_package.strip(),
                profile,
            )
        else:
            result = cls._root_engine().apply(
                device_id,
                profile,
                preset_id=preset_id,
                interface=interface,
            )
            result.update({
                'engine': 'root_tc',
                'active': True,
                'profile': profile.to_dict(),
            })

        with _lock:
            _active_engines[device_id] = selected
        return result

    @classmethod
    def clear(
        cls,
        device_id: str,
        *,
        engine: str = 'auto',
    ) -> dict[str, Any]:
        cls._validate_engine(engine)
        with _lock:
            active_engine = _active_engines.get(device_id)
        selected = active_engine if engine == 'auto' and active_engine else engine
        if selected == 'agent':
            result = cls._agent().clear(device_id)
        else:
            result = cls._root_engine().clear(device_id)
            result['engine'] = 'root_tc'
        with _lock:
            _active_engines.pop(device_id, None)
        return result

    @classmethod
    def agent_status(cls, device_id: str) -> dict[str, Any]:
        return cls._agent().capabilities(device_id)

    @classmethod
    def agent_install(cls, device_id: str) -> dict[str, Any]:
        return cls._agent().install(device_id)

    @classmethod
    def agent_prepare(cls, device_id: str) -> dict[str, Any]:
        return cls._agent().prepare(device_id)

    @classmethod
    def _agent_capabilities(cls, device_id: str) -> dict[str, Any]:
        try:
            return cls._agent().capabilities(device_id)
        except Exception as exc:
            return {
                'apk_available': False,
                'installed': False,
                'reachable': False,
                'simulation_supported': False,
                'state': 'error',
                'error': str(exc),
            }

    @staticmethod
    def _validate_engine(engine: str) -> None:
        if engine not in ('auto', 'agent', 'root_tc'):
            raise ValueError(f'unsupported weak network engine: {engine}')

    @staticmethod
    def _build_profile(
        *,
        delay_ms: int,
        jitter_ms: int,
        loss_pct: float,
        rate: str | int | float | None,
        uplink_delay_ms: int | None,
        uplink_jitter_ms: int | None,
        uplink_loss_pct: float | None,
        uplink_rate: str | int | float | None,
        uplink_burst_loss_pct: float,
        downlink_delay_ms: int | None,
        downlink_jitter_ms: int | None,
        downlink_loss_pct: float | None,
        downlink_rate: str | int | float | None,
        downlink_burst_loss_pct: float,
        protocol: str,
        ip_filter: tuple[str, ...] | list[str] | None,
    ) -> WeakNetworkProfile:
        uplink = DirectionProfile(
            delay_ms=delay_ms if uplink_delay_ms is None else uplink_delay_ms,
            jitter_ms=jitter_ms if uplink_jitter_ms is None else uplink_jitter_ms,
            loss_pct=loss_pct if uplink_loss_pct is None else uplink_loss_pct,
            bandwidth_kbps=parse_rate_kbps(
                rate if uplink_rate is None else uplink_rate
            ),
            burst_loss_pct=uplink_burst_loss_pct,
        )
        downlink = DirectionProfile(
            delay_ms=delay_ms if downlink_delay_ms is None else downlink_delay_ms,
            jitter_ms=jitter_ms if downlink_jitter_ms is None else downlink_jitter_ms,
            loss_pct=loss_pct if downlink_loss_pct is None else downlink_loss_pct,
            bandwidth_kbps=parse_rate_kbps(
                rate if downlink_rate is None else downlink_rate
            ),
            burst_loss_pct=downlink_burst_loss_pct,
        )
        return WeakNetworkProfile(
            uplink=uplink,
            downlink=downlink,
            protocol=protocol,
            ip_filter=tuple(ip_filter or ()),
        )

    @classmethod
    def probe(cls, device_id: str, host: str | None = None, count: int = 10) -> ProbeResult:
        host = (host or cls.DEFAULT_PROBE_HOST).strip()
        count = max(1, min(int(count), 30))
        cmd = f'ping -c {count} -W 2 {host}'
        raw = adb.shell(cmd=cmd, deviceId=device_id)
        return cls._parse_ping(raw, host)

    @classmethod
    def _parse_ping(cls, raw: str, host: str) -> ProbeResult:
        result = ProbeResult(host=host, raw=raw)
        if not raw:
            return result
        m_loss = re.search(r'(\d+)% packet loss', raw, re.I)
        if not m_loss:
            m_loss = re.search(r'(\d+)%\s*loss', raw, re.I)
        if m_loss:
            result.loss_pct = float(m_loss.group(1))
        m_tx = re.search(r'(\d+)\s+packets transmitted,\s*(\d+)\s+received', raw, re.I)
        if m_tx:
            result.sent = int(m_tx.group(1))
            result.received = int(m_tx.group(2))
        m_rtt = re.search(
            r'rtt min/avg/max/(?:mdev|stddev)\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)(?:/([\d.]+))?',
            raw,
            re.I,
        )
        if m_rtt:
            result.rtt_min_ms = float(m_rtt.group(1))
            result.rtt_avg_ms = float(m_rtt.group(2))
            result.rtt_max_ms = float(m_rtt.group(3))
            if m_rtt.group(4):
                result.jitter_ms = float(m_rtt.group(4))
        return result

    @classmethod
    def _build_netem_args(
        cls,
        delay_ms: int,
        jitter_ms: int,
        loss_pct: float,
        rate: str | None,
    ) -> str:
        profile = WeakNetworkProfile.from_legacy(
            delay_ms=max(0, int(delay_ms or 0)),
            jitter_ms=max(0, int(jitter_ms or 0)),
            loss_pct=max(0.0, min(float(loss_pct or 0), 100.0)),
            rate=rate,
        )
        return RootTcWeakNetworkEngine.build_netem_args(profile)

    @classmethod
    def _has_root(cls, device_id: str) -> bool:
        for su_cmd in ('su -c id', 'su 0 id'):
            out = adb.shell(cmd=su_cmd, deviceId=device_id)
            if 'uid=0' in out:
                return True
        return False

    @classmethod
    def _tc_available(cls, device_id: str) -> bool:
        out = cls._run_root(device_id, 'tc qdisc help 2>&1 | head -1')
        return 'usage' in out.lower() or 'qdisc' in out.lower()

    @classmethod
    def _detect_interface(cls, device_id: str) -> str | None:
        out = cls._run_root(device_id, 'ip route show default 2>/dev/null')
        if not out:
            out = adb.shell(cmd='ip route show default', deviceId=device_id)
        m = re.search(r'dev\s+(\S+)', out)
        if m:
            return m.group(1)
        return cls._detect_interface_no_root(device_id)

    @classmethod
    def _detect_interface_no_root(cls, device_id: str) -> str | None:
        for iface in ('wlan0', 'rmnet_data0', 'rmnet0', 'ccmni0', 'eth0'):
            out = adb.shell(cmd=f'ip link show {iface}', deviceId=device_id)
            if out and 'state UP' in out:
                return iface
        return None

    @classmethod
    def _run_root(cls, device_id: str, cmd: str) -> str:
        escaped = cmd.replace('\\', '\\\\').replace('"', '\\"')
        for su_cmd in (f'su -c "{escaped}"', f'su 0 sh -c "{escaped}"'):
            out = adb.shell(cmd=su_cmd, deviceId=device_id)
            if out and 'permission denied' not in out.lower():
                return out
        return adb.shell(cmd=f'su -c "{escaped}"', deviceId=device_id)
