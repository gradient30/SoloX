# -*- coding: utf-8 -*-
"""Contracts for Android native weak-network runtime integration."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'android-agent' / 'native'
APP_SRC = ROOT / 'android-agent' / 'app' / 'src' / 'main' / 'java'

TUN2PROXY_REV = 'eed123fbbec06295bf83f9be36d5a0f64ed9a8cb'


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_native_runtime_pins_tun2proxy_supply_chain_and_safe_arguments():
    cargo = read(NATIVE / 'Cargo.toml')
    lock = read(NATIVE / 'Cargo.lock')
    runtime = read(NATIVE / 'src' / 'runtime.rs')
    docs = read(ROOT / 'docs' / '06-engineering' / 'android-agent-third-party.md')
    vendor_cargo = read(NATIVE / 'third_party' / 'tun2proxy' / 'Cargo.toml')
    vendor_license = read(NATIVE / 'third_party' / 'tun2proxy' / 'LICENSE')
    vendor_lib = read(NATIVE / 'third_party' / 'tun2proxy' / 'src' / 'lib.rs')

    assert TUN2PROXY_REV in cargo
    assert 'name = "solox-network-agent-native"' in lock
    assert 'tun2proxy' in cargo
    assert 'path = "third_party/tun2proxy"' in cargo
    assert 'tokio' in cargo
    assert 'name = "tun2proxy"' in vendor_cargo
    assert 'version = "0.8.2"' in vendor_cargo
    assert 'license = "MIT"' in vendor_cargo
    assert 'MIT License' in vendor_license
    assert 'pub async fn run<D>' in vendor_lib
    assert 'D: AsyncRead + AsyncWrite + Unpin + Send + \'static' in vendor_lib
    assert '--tun-fd' in runtime
    assert '--proxy=socks5://' in runtime
    assert '--dns=over-tcp' in runtime
    assert '--ipv6-enabled' in runtime
    assert '--max-sessions=256' in runtime
    assert '--close-fd-on-drop=true' in runtime
    assert 'run_socks5_proxy' in runtime
    assert 'tun2proxy::general_run_async' in runtime
    assert 'CancellationToken' in runtime
    assert TUN2PROXY_REV in docs
    assert 'MIT' in docs
    assert 'https://github.com/tun2proxy/tun2proxy' in docs
    assert 'android-agent/native/third_party/tun2proxy' in docs
    assert 'AsyncRead/AsyncWrite' in docs


def test_java_native_bridge_uses_bounded_arguments_without_shell_paths():
    bridge = read(APP_SRC / 'io/solox/networkagent/nativebridge/NativeTunnel.java')
    service = read(APP_SRC / 'io/solox/networkagent/vpn/SoloXVpnService.java')

    assert 'System.loadLibrary("solox_network_agent_native")' in bridge
    assert '--tun-fd' in bridge
    assert '--proxy=socks5://' in bridge
    assert '--dns=over-tcp' in bridge
    assert '--ipv6-enabled' in bridge
    assert '--max-sessions=256' in bridge
    assert 'String filePath' not in bridge
    assert 'Runtime.getRuntime' not in bridge
    assert 'WeakNetworkProfile profile' in bridge
    assert 'profile.uplinkDelayMs()' in bridge
    assert 'profile.downlinkLossPct()' in bridge
    assert 'NativeTunnel.start(detachedFd, true, profile)' in service


def test_build_script_cross_compiles_android_native_libraries_from_workspace_sysroot():
    build = read(ROOT / 'scripts' / 'android_agent' / 'build.ps1')

    assert 'rust-sysroot' in build
    assert 'aarch64-linux-android' in build
    assert 'x86_64-linux-android' in build
    assert 'cargo build' in build
    assert 'jniLibs' in build
    assert 'solox_network_agent_native' in build
    assert 'android-toolchain\\downloads\\rust' in build or 'downloads\\rust' in build
