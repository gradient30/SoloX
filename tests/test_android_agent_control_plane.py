# -*- coding: utf-8 -*-
"""Contracts for the Android Agent control dispatcher and service entrypoints."""

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'android-agent' / 'app' / 'src' / 'main' / 'java'
JAVAC = ROOT / 'runtime' / 'android-toolchain' / 'jdk-stage' / 'jdk-17.0.19+10' / 'bin' / 'javac.exe'
JAVA = ROOT / 'runtime' / 'android-toolchain' / 'jdk-stage' / 'jdk-17.0.19+10' / 'bin' / 'java.exe'


def test_dispatcher_refuses_to_report_active_without_native_runtime(tmp_path):
    harness = tmp_path / 'CommandDispatcherHarness.java'
    harness.write_text(
        r'''
import io.solox.networkagent.control.CommandDispatcher;
import io.solox.networkagent.state.AgentStateStore;
import io.solox.networkagent.model.WeakNetworkProfile;

public final class CommandDispatcherHarness {
    private static final CommandDispatcher.TunnelController UNAUTHORIZED_TUNNEL = new CommandDispatcher.TunnelController() {
        public boolean isAuthorized() {
            return false;
        }

        public CommandDispatcher.TunnelStartResult start(String targetPackage, WeakNetworkProfile profile) {
            return CommandDispatcher.TunnelStartResult.error("unexpected start");
        }

        public void stop() {
        }
    };

    private static final CommandDispatcher.TunnelController MISSING_NATIVE_TUNNEL = new CommandDispatcher.TunnelController() {
        public boolean isAuthorized() {
            return true;
        }

        public CommandDispatcher.TunnelStartResult start(String targetPackage, WeakNetworkProfile profile) {
            return CommandDispatcher.TunnelStartResult.error("native data plane unavailable");
        }

        public void stop() {
        }
    };

    public static void main(String[] args) {
        AgentStateStore store = new AgentStateStore(10_000L);
        CommandDispatcher dispatcher = new CommandDispatcher(store, UNAUTHORIZED_TUNNEL, pkg -> true);

        String status = dispatcher.dispatch("{\"schema_version\":1,\"request_id\":\"r1\",\"command\":\"status\",\"payload\":{}}", 100L);
        check(status.contains("\"ok\":true"), "status ok");
        check(status.contains("\"state\":\"idle\""), "status idle");
        check(store.state().wireName().equals("idle"), "status does not mutate state");

        String missingTarget = dispatcher.dispatch("{\"schema_version\":1,\"request_id\":\"r2\",\"command\":\"start\",\"payload\":{}}", 200L);
        check(missingTarget.contains("\"ok\":false"), "missing target rejected");
        check(store.state().wireName().equals("idle"), "missing target does not mutate state");

        String permission = dispatcher.dispatch("{\"schema_version\":1,\"request_id\":\"r3\",\"command\":\"start\",\"payload\":{\"target_package\":\"com.example.app\",\"session_id\":\"s1\",\"profile\":{},\"profile_digest\":\"d1\"}}", 300L);
        check(permission.contains("\"ok\":true"), "permission response ok");
        check(permission.contains("\"state\":\"permission_required\""), "permission required state");

        CommandDispatcher nativeMissing = new CommandDispatcher(new AgentStateStore(10_000L), MISSING_NATIVE_TUNNEL, pkg -> true);
        String nativeError = nativeMissing.dispatch("{\"schema_version\":1,\"request_id\":\"r4\",\"command\":\"start\",\"payload\":{\"target_package\":\"com.example.app\",\"session_id\":\"s1\",\"profile\":{},\"profile_digest\":\"d1\"}}", 400L);
        check(nativeError.contains("\"ok\":false"), "native unavailable rejected");
        check(nativeError.contains("native data plane unavailable"), "native unavailable reason");
        check(!nativeError.contains("\"state\":\"active\""), "must not report active");

        String stop = nativeMissing.dispatch("{\"schema_version\":1,\"request_id\":\"r5\",\"command\":\"stop\",\"payload\":{}}", 500L);
        check(stop.contains("\"ok\":true"), "stop ok");
        check(stop.contains("\"state\":\"idle\""), "stop idle");

        String unknown = nativeMissing.dispatch("{\"schema_version\":1,\"request_id\":\"r6\",\"command\":\"unknown\",\"payload\":{}}", 600L);
        check(unknown.contains("\"ok\":false"), "unknown rejected");
        check(nativeMissing.state().wireName().equals("idle"), "unknown does not mutate state");
    }

    private static void check(boolean condition, String label) {
        if (!condition) {
            throw new AssertionError(label);
        }
    }
}
''',
        encoding='utf-8',
    )
    sources = [
        SRC / 'io/solox/networkagent/model/Json.java',
        SRC / 'io/solox/networkagent/model/WeakNetworkProfile.java',
        SRC / 'io/solox/networkagent/logging/AgentLogLevel.java',
        SRC / 'io/solox/networkagent/logging/AgentLogEntry.java',
        SRC / 'io/solox/networkagent/logging/AgentLogStore.java',
        SRC / 'io/solox/networkagent/runtime/AgentRuntime.java',
        SRC / 'io/solox/networkagent/protocol/AgentResponse.java',
        SRC / 'io/solox/networkagent/state/AgentState.java',
        SRC / 'io/solox/networkagent/state/AgentStateStore.java',
        SRC / 'io/solox/networkagent/control/CommandDispatcher.java',
        harness,
    ]
    out_dir = tmp_path / 'classes'
    out_dir.mkdir()
    subprocess.run(
        [str(JAVAC), '-encoding', 'UTF-8', '-d', str(out_dir), *map(str, sources)],
        check=True,
        cwd=ROOT,
    )
    subprocess.run([str(JAVA), '-cp', str(out_dir), 'CommandDispatcherHarness'], check=True, cwd=ROOT)


def test_agent_log_store_keeps_bounded_latest_entries_and_filters_by_exact_level(tmp_path):
    harness = tmp_path / 'AgentLogStoreHarness.java'
    harness.write_text(
        r'''
import java.util.List;

import io.solox.networkagent.logging.AgentLogEntry;
import io.solox.networkagent.logging.AgentLogLevel;
import io.solox.networkagent.logging.AgentLogStore;

public final class AgentLogStoreHarness {
    public static void main(String[] args) {
        AgentLogStore store = new AgentLogStore(3);

        AgentLogEntry first = store.record(AgentLogLevel.INFO, "service", "created", 100L);
        AgentLogEntry second = store.record(AgentLogLevel.WARN, "dispatcher", "permission required", 200L);
        AgentLogEntry third = store.record(AgentLogLevel.ERROR, "native", "native data plane unavailable", 300L);
        AgentLogEntry fourth = store.record(AgentLogLevel.INFO, "socket", "request handled", 400L);

        check(first.sequence() == 1L, "first sequence");
        check(second.sequence() == 2L, "second sequence");
        check(third.sequence() == 3L, "third sequence");
        check(fourth.sequence() == 4L, "fourth sequence");

        List<AgentLogEntry> latest = store.latest();
        check(latest.size() == 3, "bounded latest size");
        check(latest.get(0).sequence() == 2L, "oldest entry evicted");
        check(latest.get(2).message().equals("request handled"), "latest keeps newest");

        List<AgentLogEntry> info = store.filter(AgentLogLevel.INFO);
        check(info.size() == 1, "exact INFO filtering");
        check(info.get(0).source().equals("socket"), "INFO filter excludes evicted INFO");

        List<AgentLogEntry> error = store.filter(AgentLogLevel.ERROR);
        check(error.size() == 1, "exact ERROR filtering");
        check(error.get(0).message().contains("native data plane unavailable"), "ERROR message retained");

        String json = fourth.toJson();
        check(json.contains("\"level\":\"INFO\""), "json includes level");
        check(json.contains("\"source\":\"socket\""), "json includes source");
        check(json.contains("\"message\":\"request handled\""), "json includes message");
    }

    private static void check(boolean condition, String label) {
        if (!condition) {
            throw new AssertionError(label);
        }
    }
}
''',
        encoding='utf-8',
    )
    sources = [
        SRC / 'io/solox/networkagent/model/Json.java',
        SRC / 'io/solox/networkagent/logging/AgentLogLevel.java',
        SRC / 'io/solox/networkagent/logging/AgentLogEntry.java',
        SRC / 'io/solox/networkagent/logging/AgentLogStore.java',
        harness,
    ]
    out_dir = tmp_path / 'classes'
    out_dir.mkdir()
    subprocess.run(
        [str(JAVAC), '-encoding', 'UTF-8', '-d', str(out_dir), *map(str, sources)],
        check=True,
        cwd=ROOT,
    )
    subprocess.run([str(JAVA), '-cp', str(out_dir), 'AgentLogStoreHarness'], check=True, cwd=ROOT)


def test_android_agent_has_authorization_service_and_control_socket_files():
    expected = [
        SRC / 'io/solox/networkagent/MainActivity.java',
        SRC / 'io/solox/networkagent/vpn/SoloXVpnService.java',
        SRC / 'io/solox/networkagent/control/ControlSocketServer.java',
        SRC / 'io/solox/networkagent/control/CommandDispatcher.java',
        SRC / 'io/solox/networkagent/notification/AgentNotification.java',
    ]
    for path in expected:
        assert path.is_file(), path

    service = (SRC / 'io/solox/networkagent/vpn/SoloXVpnService.java').read_text(encoding='utf-8')
    socket = (SRC / 'io/solox/networkagent/control/ControlSocketServer.java').read_text(encoding='utf-8')
    activity = (SRC / 'io/solox/networkagent/MainActivity.java').read_text(encoding='utf-8')

    assert 'VpnService.prepare' in activity
    assert 'onNewIntent' in activity
    assert 'setIntent(intent)' in activity
    assert 'startForeground' in service
    assert 'solox.networkagent.control' in socket
    assert 'MAX_REQUEST_BYTES' in socket
    assert 'REQUEST_TIMEOUT_MS' in socket
    assert 'new Thread(() -> handle(socket)' in socket
    assert 'setSoTimeout(REQUEST_TIMEOUT_MS)' in socket
    assert 'native data plane unavailable' in service


def test_android_agent_lifecycle_events_are_recorded_for_local_display():
    runtime = SRC / 'io/solox/networkagent/runtime/AgentRuntime.java'
    assert runtime.is_file(), runtime

    service = (SRC / 'io/solox/networkagent/vpn/SoloXVpnService.java').read_text(encoding='utf-8')
    dispatcher = (SRC / 'io/solox/networkagent/control/CommandDispatcher.java').read_text(encoding='utf-8')
    socket = (SRC / 'io/solox/networkagent/control/ControlSocketServer.java').read_text(encoding='utf-8')
    activity = (SRC / 'io/solox/networkagent/MainActivity.java').read_text(encoding='utf-8')
    runtime_text = runtime.read_text(encoding='utf-8')

    assert 'AgentLogStore' in runtime_text
    assert 'AgentLogLevel.INFO' in runtime_text
    assert 'AgentLogLevel.WARN' in runtime_text
    assert 'AgentLogLevel.ERROR' in runtime_text

    assert 'AgentRuntime.info("service"' in service
    assert 'AgentRuntime.warn("service"' in service
    assert 'AgentRuntime.error("service"' in service
    assert 'created' in service
    assert 'destroyed' in service
    assert 'VPN start success' in service
    assert 'VPN cleanup' in service

    assert 'AgentRuntime.info("dispatcher"' in dispatcher
    assert 'AgentRuntime.warn("dispatcher"' in dispatcher
    assert 'AgentRuntime.error("dispatcher"' in dispatcher
    assert 'permission' in dispatcher
    assert 'target package is not installed' in dispatcher
    assert 'native data plane unavailable' in dispatcher

    assert 'AgentRuntime.info("socket"' in socket
    assert 'AgentRuntime.warn("socket"' in socket
    assert 'AgentRuntime.error("socket"' in socket
    assert 'started' in socket
    assert 'request' in socket

    assert 'renderLogs()' in activity
    assert 'AgentRuntime.latestLogs()' in activity


def test_vpn_service_builds_tun_and_starts_native_before_reporting_active():
    service = (SRC / 'io/solox/networkagent/vpn/SoloXVpnService.java').read_text(encoding='utf-8')
    dispatcher = (SRC / 'io/solox/networkagent/control/CommandDispatcher.java').read_text(encoding='utf-8')

    assert 'new Builder()' in service
    assert '.addAddress(' in service
    assert '.addRoute(' in service
    assert '.addAllowedApplication(targetPackage)' in service
    assert 'getPackageName().equals(targetPackage)' in service
    assert 'NativeTunnel.start(' in service
    assert 'NativeTunnel.stop(' in service
    assert 'ParcelFileDescriptor' in service
    assert 'detachFd()' in service

    assert 'interface TunnelController' in dispatcher
    assert 'tunnelController.start(' in dispatcher
    assert 'nativeAvailable' not in dispatcher
