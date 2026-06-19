package io.solox.networkagent.logging;

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
                + escapeJsonString(source)
                + "\",\"message\":\""
                + escapeJsonString(message)
                + "\"}";
    }

    private static String escapeJsonString(String value) {
        StringBuilder builder = new StringBuilder(value.length());
        for (int i = 0; i < value.length(); i++) {
            char current = value.charAt(i);
            switch (current) {
                case '"':
                    builder.append("\\\"");
                    break;
                case '\\':
                    builder.append("\\\\");
                    break;
                case '\n':
                    builder.append("\\n");
                    break;
                case '\r':
                    builder.append("\\r");
                    break;
                case '\t':
                    builder.append("\\t");
                    break;
                case '\b':
                    builder.append("\\b");
                    break;
                case '\f':
                    builder.append("\\f");
                    break;
                default:
                    if (current < 0x20) {
                        builder.append("\\u");
                        String hex = Integer.toHexString(current);
                        for (int pad = hex.length(); pad < 4; pad++) {
                            builder.append('0');
                        }
                        builder.append(hex);
                    } else {
                        builder.append(current);
                    }
                    break;
            }
        }
        return builder.toString();
    }
}
