package io.solox.networkagent.logging;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;

public final class AgentLogStore {
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
        AgentLogEntry entry = new AgentLogEntry(nextSequence++, timestampMs, level, source, message);
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
}
