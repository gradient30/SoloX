"""Validated weak-network configuration models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

ProtocolName = Literal['all', 'tcp', 'udp']
_RATE_RE = re.compile(r'^(\d+(?:\.\d+)?)\s*(kbit|mbit)?$', re.I)


def parse_rate_kbps(rate: str | int | float | None) -> int | None:
    """Convert legacy tc rate values to integer kilobits per second."""
    if rate is None or rate == '':
        return None
    if isinstance(rate, bool):
        raise ValueError('bandwidth must be a number or tc rate string')
    if isinstance(rate, (int, float)):
        value = int(rate)
    else:
        match = _RATE_RE.fullmatch(str(rate).strip())
        if not match:
            raise ValueError(f'invalid bandwidth rate: {rate}')
        unit = (match.group(2) or 'kbit').lower()
        value = int(float(match.group(1)) * (1000 if unit == 'mbit' else 1))
    if value <= 0:
        raise ValueError('bandwidth must be greater than zero')
    return value


@dataclass(frozen=True)
class DirectionProfile:
    delay_ms: int = 0
    jitter_ms: int = 0
    loss_pct: float = 0.0
    bandwidth_kbps: int | None = None
    burst_loss_pct: float = 0.0

    def __post_init__(self) -> None:
        if self.delay_ms < 0:
            raise ValueError('delay must be greater than or equal to zero')
        if self.jitter_ms < 0:
            raise ValueError('jitter must be greater than or equal to zero')
        if not 0 <= self.loss_pct <= 100:
            raise ValueError('loss must be between 0 and 100')
        if not 0 <= self.burst_loss_pct <= 100:
            raise ValueError('burst loss must be between 0 and 100')
        if self.bandwidth_kbps is not None and self.bandwidth_kbps <= 0:
            raise ValueError('bandwidth must be greater than zero')

    def to_dict(self) -> dict[str, Any]:
        return {
            'delay_ms': self.delay_ms,
            'jitter_ms': self.jitter_ms,
            'loss_pct': self.loss_pct,
            'bandwidth_kbps': self.bandwidth_kbps,
            'burst_loss_pct': self.burst_loss_pct,
        }

    def to_tc_rate(self) -> str | None:
        if self.bandwidth_kbps is None:
            return None
        if self.bandwidth_kbps % 1000 == 0:
            return f'{self.bandwidth_kbps // 1000}mbit'
        return f'{self.bandwidth_kbps}kbit'


@dataclass(frozen=True)
class WeakNetworkProfile:
    uplink: DirectionProfile
    downlink: DirectionProfile
    protocol: ProtocolName = 'all'
    ip_filter: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.protocol not in ('all', 'tcp', 'udp'):
            raise ValueError(f'unsupported protocol: {self.protocol}')
        object.__setattr__(self, 'ip_filter', tuple(self.ip_filter))

    @classmethod
    def from_legacy(
        cls,
        delay_ms: int = 0,
        jitter_ms: int = 0,
        loss_pct: float = 0,
        rate: str | int | float | None = None,
    ) -> WeakNetworkProfile:
        direction = DirectionProfile(
            delay_ms=int(delay_ms or 0),
            jitter_ms=int(jitter_ms or 0),
            loss_pct=float(loss_pct or 0),
            bandwidth_kbps=parse_rate_kbps(rate),
        )
        return cls(uplink=direction, downlink=direction)

    def to_dict(self) -> dict[str, Any]:
        return {
            'uplink': self.uplink.to_dict(),
            'downlink': self.downlink.to_dict(),
            'protocol': self.protocol,
            'ip_filter': list(self.ip_filter),
        }
