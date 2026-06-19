# -*- coding: utf-8 -*-
"""Executable contracts for the Android Agent protocol and state model."""

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'android-agent' / 'app' / 'src' / 'main' / 'java'
JAVAC = ROOT / 'runtime' / 'android-toolchain' / 'jdk-stage' / 'jdk-17.0.19+10' / 'bin' / 'javac.exe'
JAVA = ROOT / 'runtime' / 'android-toolchain' / 'jdk-stage' / 'jdk-17.0.19+10' / 'bin' / 'java.exe'


def test_agent_protocol_and_state_machine_contracts(tmp_path):
    harness = tmp_path / 'AgentProtocolHarness.java'
    harness.write_text(
        r'''
import io.solox.networkagent.model.WeakNetworkProfile;
import io.solox.networkagent.protocol.AgentCommand;
import io.solox.networkagent.protocol.AgentResponse;
import io.solox.networkagent.state.AgentState;
import io.solox.networkagent.state.AgentStateStore;

public final class AgentProtocolHarness {
    public static void main(String[] args) {
        WeakNetworkProfile profile = WeakNetworkProfile.of(100, 20, 1.5, 1024, 200, 30, 2.0, 2048, "all");
        AgentCommand start = AgentCommand.start("req-1", "com.example.app", "session-1", profile);
        AgentCommand parsed = AgentCommand.fromJson(start.toJson());
        check(parsed.schemaVersion() == 1, "schema version");
        check("req-1".equals(parsed.requestId()), "request id");
        check("start".equals(parsed.command()), "command");
        check("com.example.app".equals(parsed.targetPackage()), "target package");
        check(parsed.profile().uplinkDelayMs() == 100, "profile uplink delay");
        check(parsed.profile().downlinkBandwidthKbps() == 2048, "profile downlink bandwidth");

        expectFailure(() -> AgentCommand.fromJson("{\"schema_version\":2,\"request_id\":\"x\",\"command\":\"status\"}"), "schema");
        expectFailure(() -> WeakNetworkProfile.of(0, 0, 101.0, 0, 0, 0, 0.0, 0, "all"), "loss");

        AgentResponse ok = AgentResponse.ok("req-1", "active");
        AgentResponse okParsed = AgentResponse.fromJson(ok.toJson());
        check(okParsed.ok(), "response ok");
        check("active".equals(okParsed.state()), "response state");

        AgentStateStore store = new AgentStateStore(10_000L);
        check(store.state() == AgentState.IDLE, "initial state");
        store.transitionTo(AgentState.PERMISSION_REQUIRED, 1_000L);
        store.transitionTo(AgentState.STARTING, 1_100L);
        store.activate("session-1", "com.example.app", profile, 1_200L);
        check(store.state() == AgentState.ACTIVE, "active state");
        expectFailure(() -> store.transitionTo(AgentState.IDLE, 1_300L), "transition");
        store.markStaleIfNeeded(20_000L);
        check(store.state() == AgentState.STOPPING, "stale heartbeat stops");
        store.transitionTo(AgentState.IDLE, 20_100L);
        String snapshot = store.persistedSnapshot();
        check(!snapshot.contains("packet"), "snapshot omits packet payloads");
        check(snapshot.contains("\"state\":\"idle\""), "snapshot state");
    }

    private static void check(boolean condition, String label) {
        if (!condition) {
            throw new AssertionError(label);
        }
    }

    private static void expectFailure(Runnable action, String messagePart) {
        try {
            action.run();
        } catch (IllegalArgumentException expected) {
            if (expected.getMessage() != null && expected.getMessage().contains(messagePart)) {
                return;
            }
            throw new AssertionError("wrong failure: " + expected.getMessage());
        }
        throw new AssertionError("expected failure containing " + messagePart);
    }
}
''',
        encoding='utf-8',
    )

    sources = [
        SRC / 'io/solox/networkagent/model/Json.java',
        SRC / 'io/solox/networkagent/model/WeakNetworkProfile.java',
        SRC / 'io/solox/networkagent/protocol/AgentCommand.java',
        SRC / 'io/solox/networkagent/protocol/AgentResponse.java',
        SRC / 'io/solox/networkagent/state/AgentState.java',
        SRC / 'io/solox/networkagent/state/AgentStateStore.java',
        harness,
    ]
    out_dir = tmp_path / 'classes'
    out_dir.mkdir()
    subprocess.run(
        [str(JAVAC), '-encoding', 'UTF-8', '-d', str(out_dir), *map(str, sources)],
        check=True,
        cwd=ROOT,
    )
    subprocess.run(
        [str(JAVA), '-cp', str(out_dir), 'AgentProtocolHarness'],
        check=True,
        cwd=ROOT,
    )
