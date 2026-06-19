package io.solox.networkagent.logging;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;

public final class AgentLogStore {
    public static final int MAX_SOURCE_LENGTH = 96;
    public static final int MAX_MESSAGE_LENGTH = 2048;
    private static final String TRUNCATION_SUFFIX = "...";

    private final int capacity;
    private final ArrayDeque<AgentLogEntry> entries;
    private long nextSequence = 1L;

    public AgentLogStore(int capacity) {
        if (capacity <= 0) {
            throw new IllegalArgumentException("capacity must be positive");
        }
        this.capacity = capacity;
        this.entries = new ArrayDeque<>(capacity);
    }

    public synchronized AgentLogEntry record(AgentLogLevel level, String source, String message, long timestampMs) {
        AgentLogEntry entry = new AgentLogEntry(
                nextSequence++,
                timestampMs,
                level,
                truncate(source, MAX_SOURCE_LENGTH),
                truncate(message, MAX_MESSAGE_LENGTH));
        if (entries.size() == capacity) {
            entries.removeFirst();
        }
        entries.addLast(entry);
        return entry;
    }

    public synchronized List<AgentLogEntry> latest() {
        return new ArrayList<>(entries);
    }

    public synchronized List<AgentLogEntry> filter(AgentLogLevel level) {
        ArrayList<AgentLogEntry> matches = new ArrayList<>();
        for (AgentLogEntry entry : entries) {
            if (entry.level() == level) {
                matches.add(entry);
            }
        }
        return matches;
    }

    private static String truncate(String value, int maxLength) {
        if (value == null) {
            return "";
        }
        if (value.length() <= maxLength) {
            return value;
        }
        return value.substring(0, maxLength - TRUNCATION_SUFFIX.length()) + TRUNCATION_SUFFIX;
    }
}
