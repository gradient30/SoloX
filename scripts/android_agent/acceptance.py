"""Connected-device acceptance harness for Android Agent weak-network preview."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from solox.public.weak_network import WEAKNET_PRESETS
from solox.public.weaknet.agent import AndroidAgentController
from solox.public.weaknet.models import WeakNetworkProfile


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AcceptanceThresholds:
    max_baseline_rtt_overhead_ms: float = 5.0
    max_bandwidth_error_pct: float = 10.0
    min_udp_packets: int = 1000
    udp_loss_tolerance_pct: float = 1.0


@dataclass(frozen=True)
class AcceptanceDecision:
    passed: bool
    checks: dict[str, bool]
    details: dict[str, Any]


def evaluate_measurements(
    measurements: dict[str, Any],
    thresholds: AcceptanceThresholds,
) -> AcceptanceDecision:
    target_kbps = float(measurements.get('bandwidth_target_kbps') or 0)
    observed_kbps = float(measurements.get('bandwidth_observed_kbps') or 0)
    bandwidth_error = (
        abs(observed_kbps - target_kbps) / target_kbps * 100
        if target_kbps > 0
        else 0
    )
    udp_target = float(measurements.get('udp_loss_target_pct') or 0)
    udp_observed = float(measurements.get('udp_loss_observed_pct') or 0)
    udp_packets = int(measurements.get('udp_packets') or 0)
    checks = {
        'baseline_rtt_overhead': (
            float(measurements.get('baseline_rtt_overhead_ms') or 0)
            <= thresholds.max_baseline_rtt_overhead_ms
        ),
        'bandwidth_accuracy': bandwidth_error <= thresholds.max_bandwidth_error_pct,
        'udp_loss_confidence': (
            udp_packets >= thresholds.min_udp_packets
            and abs(udp_observed - udp_target) <= thresholds.udp_loss_tolerance_pct
        ),
        'tcp_retransmission_evidence': int(measurements.get('tcp_retransmissions') or 0) > 0,
        'ipv6_leak_detection': int(measurements.get('ipv6_leaks') or 0) == 0,
        'usb_recovery': bool(measurements.get('usb_disconnect_recovered')),
    }
    return AcceptanceDecision(
        passed=all(checks.values()),
        checks=checks,
        details={
            'bandwidth_error_pct': bandwidth_error,
            'udp_loss_delta_pct': abs(udp_observed - udp_target),
        },
    )


def profile_from_name(profile_name: str) -> WeakNetworkProfile:
    if profile_name not in WEAKNET_PRESETS:
        raise ValueError(f'unknown weak-network profile: {profile_name}')
    cfg = dict(WEAKNET_PRESETS[profile_name])
    cfg.pop('label_cn', None)
    cfg.pop('label_en', None)
    return WeakNetworkProfile.from_legacy(
        delay_ms=int(cfg.get('delay_ms') or 0),
        jitter_ms=int(cfg.get('jitter_ms') or 0),
        loss_pct=float(cfg.get('loss_pct') or 0),
        rate=cfg.get('rate'),
    )


def default_measurements_provider() -> dict[str, Any]:
    raise RuntimeError(
        'real traffic measurement is not wired yet; provide a measurements provider '
        'or run this harness after implementing TCP/UDP probes'
    )


def run_acceptance(
    *,
    device: str,
    package: str,
    profile_name: str,
    smoke: bool,
    output_root: Path | str = ROOT / 'report',
    controller: AndroidAgentController | None = None,
    measurements_provider: Callable[[], dict[str, Any]] = default_measurements_provider,
) -> dict[str, Any]:
    if not device:
        raise ValueError('device is required')
    if not package:
        raise ValueError('package is required')
    controller = controller or AndroidAgentController()
    profile = profile_from_name(profile_name)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    report_dir = Path(output_root) / f'weaknet-acceptance-{timestamp}'
    report_dir.mkdir(parents=True, exist_ok=True)

    evidence: dict[str, Any] = {}
    try:
        evidence['capabilities'] = controller.capabilities(device)
        evidence['prepare'] = controller.prepare(device)
        evidence['apply'] = controller.apply(device, package, profile)
        evidence['status'] = controller.status(device)
        measurements = measurements_provider()
        decision = evaluate_measurements(measurements, AcceptanceThresholds())
        report = {
            'device': device,
            'package': package,
            'profile': profile_name,
            'smoke': smoke,
            'engine': 'agent',
            'report_dir': str(report_dir),
            'measurements': measurements,
            'decision': {
                'passed': decision.passed,
                'checks': decision.checks,
                'details': decision.details,
            },
            'evidence': evidence,
        }
        return report
    finally:
        evidence['clear'] = controller.clear(device)
        (report_dir / 'result.json').write_text(
            json.dumps(
                {
                    'device': device,
                    'package': package,
                    'profile': profile_name,
                    'smoke': smoke,
                    'engine': 'agent',
                    'evidence': evidence,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding='utf-8',
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True, help='ADB serial to test')
    parser.add_argument('--package', required=True, help='Android package under test')
    parser.add_argument('--profile', default='lte_weak', help='SoloX weak-network preset')
    parser.add_argument('--smoke', action='store_true', help='Run a short smoke profile')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_acceptance(
        device=args.device,
        package=args.package,
        profile_name=args.profile,
        smoke=args.smoke,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report['decision']['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
