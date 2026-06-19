package io.solox.networkagent.state;

import io.solox.networkagent.model.Json;
import io.solox.networkagent.model.WeakNetworkProfile;

public final class AgentStateStore {
    private final long heartbeatTimeoutMs;
    private AgentState state = AgentState.IDLE;
    private String sessionId;
    private String targetPackage;
    private WeakNetworkProfile profile;
    private long heartbeatAtMs;
    private String lastError;

    public AgentStateStore(long heartbeatTimeoutMs) {
        if (heartbeatTimeoutMs <= 0) {
            throw new IllegalArgumentException("heartbeat timeout must be positive");
        }
        this.heartbeatTimeoutMs = heartbeatTimeoutMs;
    }

    public synchronized AgentState state() {
        return state;
    }

    public synchronized void transitionTo(AgentState next, long nowMs) {
        if (!isLegalTransition(state, next)) {
            throw new IllegalArgumentException("illegal transition from " + state.wireName() + " to " + next.wireName());
        }
        state = next;
        heartbeatAtMs = nowMs;
        if (next == AgentState.IDLE) {
            sessionId = null;
            targetPackage = null;
            profile = null;
            lastError = null;
        }
    }

    public synchronized void activate(String sessionId, String targetPackage, WeakNetworkProfile profile, long nowMs) {
        if (state != AgentState.STARTING) {
            throw new IllegalArgumentException("transition to active requires starting state");
        }
        if (sessionId == null || sessionId.isBlank()) {
            throw new IllegalArgumentException("session id is required");
        }
        if (targetPackage == null || targetPackage.isBlank()) {
            throw new IllegalArgumentException("target package is required");
        }
        if (profile == null) {
            throw new IllegalArgumentException("profile is required");
        }
        this.sessionId = sessionId;
        this.targetPackage = targetPackage;
        this.profile = profile;
        transitionTo(AgentState.ACTIVE, nowMs);
    }

    public synchronized void heartbeat(long nowMs) {
        if (state == AgentState.ACTIVE) {
            heartbeatAtMs = nowMs;
        }
    }

    public synchronized void markStaleIfNeeded(long nowMs) {
        if (state == AgentState.ACTIVE && nowMs - heartbeatAtMs > heartbeatTimeoutMs) {
            state = AgentState.STOPPING;
            heartbeatAtMs = nowMs;
        }
    }

    public synchronized void fail(String message, long nowMs) {
        state = AgentState.ERROR;
        lastError = message;
        heartbeatAtMs = nowMs;
    }

    public synchronized String persistedSnapshot() {
        StringBuilder builder = new StringBuilder();
        builder.append("{")
                .append("\"state\":\"").append(state.wireName()).append("\",")
                .append("\"heartbeat_at\":").append(heartbeatAtMs);
        if (sessionId != null) {
            builder.append(",\"session_id\":\"").append(Json.escape(sessionId)).append("\"");
        }
        if (targetPackage != null) {
            builder.append(",\"target_package\":\"").append(Json.escape(targetPackage)).append("\"");
        }
        if (profile != null) {
            builder.append(",\"profile\":").append(profile.toJson());
        }
        if (lastError != null) {
            builder.append(",\"last_error\":\"").append(Json.escape(lastError)).append("\"");
        }
        builder.append("}");
        return builder.toString();
    }

    private static boolean isLegalTransition(AgentState current, AgentState next) {
        if (next == AgentState.ERROR) {
            return true;
        }
        return (current == AgentState.IDLE && next == AgentState.PERMISSION_REQUIRED)
                || (current == AgentState.PERMISSION_REQUIRED && next == AgentState.STARTING)
                || (current == AgentState.STARTING && next == AgentState.ACTIVE)
                || (current == AgentState.ACTIVE && next == AgentState.STOPPING)
                || (current == AgentState.STOPPING && next == AgentState.IDLE);
    }
}
