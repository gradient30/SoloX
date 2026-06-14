"""Weak-network engine interface."""

from __future__ import annotations

from typing import Any, Protocol

from .models import WeakNetworkProfile


class WeakNetworkEngine(Protocol):
    def capabilities(self, device_id: str) -> dict[str, Any]:
        """Return engine support and current capability details."""

    def apply(
        self,
        device_id: str,
        profile: WeakNetworkProfile,
        *,
        preset_id: str = 'custom',
        **options: Any,
    ) -> dict[str, Any]:
        """Apply a validated profile."""

    def status(self, device_id: str) -> dict[str, Any]:
        """Return normalized current state."""

    def clear(self, device_id: str) -> dict[str, Any]:
        """Remove active impairment."""
