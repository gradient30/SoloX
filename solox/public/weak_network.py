# -*- coding: utf-8 -*-
"""Weak-network simulation (tc netem) and quality probing for Android devices."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any

from logzero import logger

from solox.public.adb import adb

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
    def get_capabilities(cls, device_id: str) -> dict[str, Any]:
        rooted = cls._has_root(device_id)
        iface = cls._detect_interface(device_id) if rooted else cls._detect_interface_no_root(device_id)
        tc_ok = False
        if rooted and iface:
            tc_ok = cls._tc_available(device_id)
        with _lock:
            active = _active.get(device_id)
        return {
            'root_available': rooted,
            'tc_available': tc_ok,
            'simulation_supported': bool(rooted and iface and tc_ok),
            'interface': iface,
            'active_preset': active.get('preset') if active else None,
            'active_params': active.get('params') if active else None,
            'mode': 'simulation' if active else ('probe_only' if not rooted else 'idle'),
        }

    @classmethod
    def get_status(cls, device_id: str) -> dict[str, Any]:
        cap = cls.get_capabilities(device_id)
        with _lock:
            active = _active.get(device_id)
        cap['active'] = active is not None
        if active:
            cap['applied_at'] = active.get('applied_at')
            cap['interface'] = active.get('interface', cap.get('interface'))
        return cap

    @classmethod
    def apply_preset(cls, device_id: str, preset_id: str) -> dict[str, Any]:
        if preset_id == 'off':
            return cls.clear(device_id)
        if preset_id not in WEAKNET_PRESETS:
            raise ValueError(f'unknown preset: {preset_id}')
        cfg = dict(WEAKNET_PRESETS[preset_id])
        cfg.pop('label_cn', None)
        cfg.pop('label_en', None)
        return cls.apply_custom(device_id, preset_id=preset_id, **cfg)

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
    ) -> dict[str, Any]:
        if not cls._has_root(device_id):
            raise RuntimeError(
                'simulation requires root (su). Use network probe mode or root your test device.'
            )
        iface = interface or cls._detect_interface(device_id)
        if not iface:
            raise RuntimeError('cannot detect active network interface (wlan0/rmnet*)')
        if not cls._tc_available(device_id):
            raise RuntimeError('tc/netem not available on device kernel')

        netem = cls._build_netem_args(delay_ms, jitter_ms, loss_pct, rate)
        if not netem:
            return cls.clear(device_id)

        cls._run_root(device_id, f'tc qdisc replace dev {iface} root netem {netem}')
        verify = cls._run_root(device_id, f'tc qdisc show dev {iface}')
        if 'netem' not in verify.lower():
            raise RuntimeError(f'tc apply failed: {verify[:200]}')

        import time as _time
        state = {
            'preset': preset_id,
            'interface': iface,
            'params': {
                'delay_ms': delay_ms,
                'jitter_ms': jitter_ms,
                'loss_pct': loss_pct,
                'rate': rate,
            },
            'applied_at': _time.time(),
        }
        with _lock:
            _active[device_id] = state
        logger.info('[WeakNet] applied %s on %s dev=%s', preset_id, device_id, iface)
        return {'status': 1, 'msg': 'weak network applied', **state}

    @classmethod
    def clear(cls, device_id: str) -> dict[str, Any]:
        with _lock:
            prev = _active.pop(device_id, None)
        iface = (prev or {}).get('interface') or cls._detect_interface(device_id)
        cleared = False
        if iface and cls._has_root(device_id):
            out = cls._run_root(
                device_id,
                f'tc qdisc del dev {iface} root 2>/dev/null; echo cleared',
            )
            cleared = 'cleared' in out or 'Cannot find' in out or 'RTNETLINK' in out
        logger.info('[WeakNet] cleared %s iface=%s', device_id, iface)
        return {'status': 1, 'msg': 'weak network cleared', 'cleared': cleared, 'interface': iface}

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
        parts = []
        delay_ms = max(0, int(delay_ms or 0))
        jitter_ms = max(0, int(jitter_ms or 0))
        loss_pct = max(0.0, min(float(loss_pct or 0), 100.0))
        if delay_ms:
            if jitter_ms:
                parts.append(f'delay {delay_ms}ms {jitter_ms}ms')
            else:
                parts.append(f'delay {delay_ms}ms')
        if loss_pct:
            parts.append(f'loss {loss_pct:g}%')
        if rate:
            parts.append(f'rate {rate}')
        return ' '.join(parts)

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
