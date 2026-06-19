package io.solox.networkagent.protocol;

import io.solox.networkagent.model.Json;
import io.solox.networkagent.model.WeakNetworkProfile;

public final class AgentCommand {
    public static final int SCHEMA_VERSION = 1;

    private final int schemaVersion;
    private final String requestId;
    private final String command;
    private final String targetPackage;
    private final String sessionId;
    private final WeakNetworkProfile profile;

    private AgentCommand(
            int schemaVersion,
            String requestId,
            String command,
            String targetPackage,
            String sessionId,
            WeakNetworkProfile profile) {
        if (schemaVersion != SCHEMA_VERSION) {
            throw new IllegalArgumentException("unsupported schema version: " + schemaVersion);
        }
        if (requestId == null || requestId.isBlank()) {
            throw new IllegalArgumentException("request_id is required");
        }
        if (command == null || command.isBlank()) {
            throw new IllegalArgumentException("command is required");
        }
        this.schemaVersion = schemaVersion;
        this.requestId = requestId;
        this.command = command;
        this.targetPackage = targetPackage;
        this.sessionId = sessionId;
        this.profile = profile;
    }

    public static AgentCommand start(String requestId, String targetPackage, String sessionId, WeakNetworkProfile profile) {
        if (targetPackage == null || targetPackage.isBlank()) {
            throw new IllegalArgumentException("target package is required");
        }
        if (sessionId == null || sessionId.isBlank()) {
            throw new IllegalArgumentException("session id is required");
        }
        if (profile == null) {
            throw new IllegalArgumentException("profile is required");
        }
        return new AgentCommand(SCHEMA_VERSION, requestId, "start", targetPackage, sessionId, profile);
    }

    public static AgentCommand status(String requestId) {
        return new AgentCommand(SCHEMA_VERSION, requestId, "status", null, null, null);
    }

    public static AgentCommand fromJson(String json) {
        int schemaVersion = Json.intValue(json, "schema_version", -1);
        if (schemaVersion != SCHEMA_VERSION) {
            throw new IllegalArgumentException("unsupported schema version: " + schemaVersion);
        }
        String command = Json.stringValue(json, "command", "");
        WeakNetworkProfile profile = json.contains("\"profile\"") ? WeakNetworkProfile.fromJson(json) : null;
        return new AgentCommand(
                schemaVersion,
                Json.stringValue(json, "request_id", ""),
                command,
                Json.stringValue(json, "target_package", null),
                Json.stringValue(json, "session_id", null),
                profile);
    }

    public String toJson() {
        StringBuilder builder = new StringBuilder();
        builder.append("{")
                .append("\"schema_version\":").append(schemaVersion).append(",")
                .append("\"request_id\":\"").append(Json.escape(requestId)).append("\",")
                .append("\"command\":\"").append(Json.escape(command)).append("\"");
        if (targetPackage != null) {
            builder.append(",\"target_package\":\"").append(Json.escape(targetPackage)).append("\"");
        }
        if (sessionId != null) {
            builder.append(",\"session_id\":\"").append(Json.escape(sessionId)).append("\"");
        }
        if (profile != null) {
            builder.append(",\"profile\":").append(profile.toJson());
        }
        builder.append("}");
        return builder.toString();
    }

    public int schemaVersion() { return schemaVersion; }
    public String requestId() { return requestId; }
    public String command() { return command; }
    public String targetPackage() { return targetPackage; }
    public String sessionId() { return sessionId; }
    public WeakNetworkProfile profile() { return profile; }
}
