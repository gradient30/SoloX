package io.solox.networkagent.logging;

import io.solox.networkagent.model.Json;

public final class AgentLogEntry {
    private final long sequence;
    private final long timestampMs;
    private final AgentLogLevel level;
    private final String source;
    private final String message;

    AgentLogEntry(long sequence, long timestampMs, AgentLogLevel level, String source, String message) {
        this.sequence = sequence;
        this.timestampMs = timestampMs;
        this.level = level;
        this.source = source == null ? "" : source;
        this.message = message == null ? "" : message;
    }

    public long sequence() {
        return sequence;
    }

    public long timestampMs() {
        return timestampMs;
    }

    public AgentLogLevel level() {
        return level;
    }

    public String source() {
        return source;
    }

    public String message() {
        return message;
    }

    public String toJson() {
        return "{\"sequence\":"
                + sequence
                + ",\"timestamp_ms\":"
                + timestampMs
                + ",\"level\":\""
                + level.name()
                + "\",\"source\":\""
                + Json.escape(source)
                + "\",\"message\":\""
                + Json.escape(message)
                + "\"}";
    }
}
