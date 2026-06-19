# -*- coding: utf-8 -*-
"""Contracts for Linux gateway weak-network calibration scripts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts' / 'weaknet_gateway'


def read(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding='utf-8')


def test_apply_dry_run_generates_bidirectional_netem_and_ifb_commands():
    script = read('apply.sh')

    assert '--dry-run' in script
    assert 'sysctl -w net.ipv4.ip_forward=1' in script
    assert 'sysctl -w net.ipv6.conf.all.forwarding=1' in script
    assert 'tc qdisc replace dev "$IFACE" root handle 1: netem' in script
    assert 'delay "${DELAY_MS}ms" "${JITTER_MS}ms"' in script
    assert 'loss "${LOSS_PCT}%"' in script
    assert 'rate "$RATE"' in script
    assert 'modprobe ifb' in script
    assert 'ip link add "$IFB" type ifb' in script
    assert 'tc qdisc replace dev "$IFACE" ingress' in script
    assert 'mirred egress redirect dev "$IFB"' in script
    assert 'tc qdisc replace dev "$IFB" root handle 1: netem' in script


def test_apply_refuses_empty_or_loopback_interface():
    script = read('apply.sh')

    assert 'validate_iface' in script
    assert 'interface is required' in script
    assert '"lo"|"loopback"' in script
    assert 'loopback interface is not allowed' in script


def test_clear_is_idempotent_and_removes_ifb_without_eval():
    out = read('clear.sh')

    assert 'tc qdisc del dev "$IFACE" root || true' in out
    assert 'tc qdisc del dev "$IFACE" ingress || true' in out
    assert 'tc qdisc del dev "$IFB" root || true' in out
    assert 'ip link del "$IFB" || true' in out
    for script in ('apply.sh', 'clear.sh', 'status.sh'):
        assert 'eval ' not in read(script)


def test_status_reports_gateway_state_commands():
    out = read('status.sh')

    assert 'tc qdisc show dev "$IFACE"' in out
    assert 'tc filter show dev "$IFACE" parent ffff:' in out
    assert 'tc qdisc show dev "$IFB"' in out
    assert 'sysctl net.ipv4.ip_forward' in out
    assert 'sysctl net.ipv6.conf.all.forwarding' in out


def test_gateway_readme_documents_calibration_boundary():
    readme = read('README.md')

    assert 'Linux gateway' in readme
    assert 'IFB' in readme
    assert 'dry-run' in readme
    assert 'calibration' in readme.lower()
