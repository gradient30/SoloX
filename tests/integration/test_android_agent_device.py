# -*- coding: utf-8 -*-
"""Unit contracts for Android Agent real-device acceptance harness."""

from pathlib import Path

import pytest

from scripts.android_agent.acceptance import (
    AcceptanceThresholds,
    evaluate_measurements,
    parse_args,
    run_acceptance,
)


def test_threshold_decision_passes_stable_sample_measurements():
    measurements = {
        'baseline_rtt_overhead_ms': 3.5,
        'bandwidth_target_kbps': 1000,
        'bandwidth_observed_kbps': 940,
        'udp_loss_target_pct': 2.0,
        'udp_loss_observed_pct': 2.2,
        'udp_packets': 1200,
        'tcp_retransmissions': 4,
        'ipv6_leaks': 0,
        'usb_disconnect_recovered': True,
    }

    decision = evaluate_measurements(measurements, AcceptanceThresholds())

    assert decision.passed is True
    assert decision.checks['baseline_rtt_overhead'] is True
    assert decision.checks['bandwidth_accuracy'] is True
    assert decision.checks['udp_loss_confidence'] is True
    assert decision.checks['tcp_retransmission_evidence'] is True
    assert decision.checks['ipv6_leak_detection'] is True
    assert decision.checks['usb_recovery'] is True


def test_threshold_decision_fails_on_ipv6_leak_and_missing_recovery():
    measurements = {
        'baseline_rtt_overhead_ms': 12,
        'bandwidth_target_kbps': 1000,
        'bandwidth_observed_kbps': 700,
        'udp_loss_target_pct': 2.0,
        'udp_loss_observed_pct': 8.0,
        'udp_packets': 200,
        'tcp_retransmissions': 0,
        'ipv6_leaks': 1,
        'usb_disconnect_recovered': False,
    }

    decision = evaluate_measurements(measurements, AcceptanceThresholds())

    assert decision.passed is False
    assert decision.checks['ipv6_leak_detection'] is False
    assert decision.checks['usb_recovery'] is False


def test_cli_requires_explicit_device_and_package():
    with pytest.raises(SystemExit):
        parse_args(['--package', 'com.example.app'])
    with pytest.raises(SystemExit):
        parse_args(['--device', 'abc123'])


class FakeController:
    def __init__(self):
        self.calls = []

    def capabilities(self, device):
        self.calls.append(('capabilities', device))
        return {'installed': True, 'reachable': True, 'state': 'idle'}

    def prepare(self, device):
        self.calls.append(('prepare', device))
        return {'started': True}

    def apply(self, device, package, profile):
        self.calls.append(('apply', device, package, profile.to_dict()))
        return {'status': 1, 'session_id': 's1', 'engine': 'agent'}

    def status(self, device):
        self.calls.append(('status', device))
        return {'state': 'active', 'protocol_version': 1}

    def clear(self, device):
        self.calls.append(('clear', device))
        return {'status': 1, 'state': 'idle'}


def test_run_acceptance_records_report_and_always_clears(tmp_path):
    controller = FakeController()
    report = run_acceptance(
        device='abc123',
        package='com.example.app',
        profile_name='lte_weak',
        smoke=True,
        output_root=tmp_path,
        controller=controller,
        measurements_provider=lambda: {
            'baseline_rtt_overhead_ms': 1,
            'bandwidth_target_kbps': 1000,
            'bandwidth_observed_kbps': 980,
            'udp_loss_target_pct': 2,
            'udp_loss_observed_pct': 2,
            'udp_packets': 1000,
            'tcp_retransmissions': 1,
            'ipv6_leaks': 0,
            'usb_disconnect_recovered': True,
        },
    )

    assert report['decision']['passed'] is True
    assert report['device'] == 'abc123'
    assert report['package'] == 'com.example.app'
    assert Path(report['report_dir']).is_dir()
    assert ('clear', 'abc123') in controller.calls
