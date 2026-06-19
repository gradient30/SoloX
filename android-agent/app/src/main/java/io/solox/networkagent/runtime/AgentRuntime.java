package io.solox.networkagent.runtime;

import java.util.List;

import io.solox.networkagent.logging.AgentLogEntry;
import io.solox.networkagent.logging.AgentLogLevel;
import io.solox.networkagent.logging.AgentLogStore;

public final class AgentRuntime {
    private static final AgentLogStore LOGS = new AgentLogStore(500);

    private AgentRuntime() {}

    public static AgentLogEntry info(String source, String message) {
        return record(AgentLogLevel.INFO, source, message);
    }

    public static AgentLogEntry warn(String source, String message) {
        return record(AgentLogLevel.WARN, source, message);
    }

    public static AgentLogEntry error(String source, String message) {
        return record(AgentLogLevel.ERROR, source, message);
    }

    public static List<AgentLogEntry> latestLogs() {
        return LOGS.latest();
    }

    private static AgentLogEntry record(AgentLogLevel level, String source, String message) {
        return LOGS.record(level, source, message, System.currentTimeMillis());
    }
}
