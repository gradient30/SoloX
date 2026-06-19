package io.solox.networkagent.control;

import io.solox.networkagent.model.Json;
import io.solox.networkagent.model.WeakNetworkProfile;
import io.solox.networkagent.state.AgentState;
import io.solox.networkagent.state.AgentStateStore;

public final class CommandDispatcher {
    public interface PackageVerifier {
        boolean isInstalled(String packageName);
    }

    public interface TunnelController {
        boolean isAuthorized();

        TunnelStartResult start(String targetPackage, WeakNetworkProfile profile);

        void stop();
    }

    public static final class TunnelStartResult {
        private final boolean ok;
        private final String error;

        private TunnelStartResult(boolean ok, String error) {
            this.ok = ok;
            this.error = error;
        }

        public static TunnelStartResult ok() {
            return new TunnelStartResult(true, null);
        }

        public static TunnelStartResult error(String error) {
            return new TunnelStartResult(false, error);
        }
    }

    private final AgentStateStore stateStore;
    private final TunnelController tunnelController;
    private final PackageVerifier packageVerifier;

    public CommandDispatcher(
            AgentStateStore stateStore,
            TunnelController tunnelController,
            PackageVerifier packageVerifier) {
        this.stateStore = stateStore;
        this.tunnelController = tunnelController;
        this.packageVerifier = packageVerifier;
    }

    public AgentState state() {
        return stateStore.state();
    }

    public String dispatch(String requestJson, long nowMs) {
        String requestId = Json.stringValue(requestJson, "request_id", "");
        try {
            int schema = Json.intValue(requestJson, "schema_version", -1);
            if (schema != 1) {
                return error(requestId, "unsupported schema version: " + schema, stateStore.state().wireName());
            }
            if (requestId.isBlank()) {
                return error("", "request_id is required", stateStore.state().wireName());
            }
            String command = Json.stringValue(requestJson, "command", "");
            if ("status".equals(command)) {
                stateStore.markStaleIfNeeded(nowMs);
                return ok(requestId, stateStore.state().wireName(), null, null);
            }
            if ("stop".equals(command)) {
                tunnelController.stop();
                forceIdle(nowMs);
                return ok(requestId, AgentState.IDLE.wireName(), null, null);
            }
            if ("start".equals(command)) {
                return start(requestId, requestJson, nowMs);
            }
            return error(requestId, "unknown command: " + command, stateStore.state().wireName());
        } catch (RuntimeException exc) {
            return error(requestId, exc.getMessage(), stateStore.state().wireName());
        }
    }

    private String start(String requestId, String requestJson, long nowMs) {
        String targetPackage = Json.stringValue(requestJson, "target_package", "");
        String sessionId = Json.stringValue(requestJson, "session_id", "");
        String digest = Json.stringValue(requestJson, "profile_digest", "");
        if (targetPackage.isBlank()) {
            return error(requestId, "target_package is required", stateStore.state().wireName());
        }
        if (sessionId.isBlank()) {
            return error(requestId, "session_id is required", stateStore.state().wireName());
        }
        if (!packageVerifier.isInstalled(targetPackage)) {
            return error(requestId, "target package is not installed: " + targetPackage, stateStore.state().wireName());
        }
        if (!tunnelController.isAuthorized()) {
            moveToPermissionRequired(nowMs);
            return ok(requestId, AgentState.PERMISSION_REQUIRED.wireName(), sessionId, digest);
        }
        WeakNetworkProfile profile = WeakNetworkProfile.fromJson(requestJson);
        if (stateStore.state() == AgentState.ACTIVE || stateStore.state() == AgentState.STOPPING) {
            tunnelController.stop();
            forceIdle(nowMs);
        }
        stateStore.transitionTo(AgentState.PERMISSION_REQUIRED, nowMs);
        stateStore.transitionTo(AgentState.STARTING, nowMs);
        TunnelStartResult startResult = tunnelController.start(targetPackage, profile);
        if (!startResult.ok) {
            tunnelController.stop();
            forceIdle(nowMs);
            return error(requestId, startResult.error, AgentState.IDLE.wireName());
        }
        stateStore.activate(sessionId, targetPackage, profile, nowMs);
        return ok(requestId, AgentState.ACTIVE.wireName(), sessionId, digest);
    }

    private void moveToPermissionRequired(long nowMs) {
        if (stateStore.state() == AgentState.IDLE) {
            stateStore.transitionTo(AgentState.PERMISSION_REQUIRED, nowMs);
        }
    }

    private void forceIdle(long nowMs) {
        AgentState state = stateStore.state();
        if (state == AgentState.IDLE) {
            return;
        }
        if (state == AgentState.PERMISSION_REQUIRED) {
            stateStore.transitionTo(AgentState.STARTING, nowMs);
            stateStore.transitionTo(AgentState.ACTIVE, nowMs);
        }
        if (state == AgentState.STARTING) {
            stateStore.transitionTo(AgentState.ACTIVE, nowMs);
        }
        if (state == AgentState.ACTIVE) {
            stateStore.transitionTo(AgentState.STOPPING, nowMs);
        }
        if (stateStore.state() == AgentState.STOPPING) {
            stateStore.transitionTo(AgentState.IDLE, nowMs);
        }
    }

    private static String ok(String requestId, String state, String sessionId, String digest) {
        return response(requestId, true, state, sessionId, digest, null);
    }

    private static String error(String requestId, String error, String state) {
        return response(requestId, false, state, null, null, error == null ? "request failed" : error);
    }

    private static String response(String requestId, boolean ok, String state, String sessionId, String digest, String error) {
        StringBuilder builder = new StringBuilder();
        builder.append("{\"schema_version\":1,")
                .append("\"request_id\":\"").append(Json.escape(requestId)).append("\",")
                .append("\"ok\":").append(ok).append(",")
                .append("\"payload\":{")
                .append("\"state\":\"").append(Json.escape(state)).append("\",")
                .append("\"protocol_version\":1");
        if (sessionId != null && !sessionId.isBlank()) {
            builder.append(",\"session_id\":\"").append(Json.escape(sessionId)).append("\"");
        }
        if (digest != null && !digest.isBlank()) {
            builder.append(",\"profile_digest\":\"").append(Json.escape(digest)).append("\"");
        }
        builder.append("},\"error\":");
        if (error == null) {
            builder.append("null");
        } else {
            builder.append("\"").append(Json.escape(error)).append("\"");
        }
        builder.append("}");
        return builder.toString();
    }
}
