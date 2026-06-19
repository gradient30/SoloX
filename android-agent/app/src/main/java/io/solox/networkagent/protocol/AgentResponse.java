package io.solox.networkagent.protocol;

import io.solox.networkagent.model.Json;

public final class AgentResponse {
    public static final int SCHEMA_VERSION = 1;

    private final int schemaVersion;
    private final String requestId;
    private final boolean ok;
    private final String state;
    private final String error;

    private AgentResponse(int schemaVersion, String requestId, boolean ok, String state, String error) {
        if (schemaVersion != SCHEMA_VERSION) {
            throw new IllegalArgumentException("unsupported schema version: " + schemaVersion);
        }
        if (requestId == null || requestId.isBlank()) {
            throw new IllegalArgumentException("request_id is required");
        }
        this.schemaVersion = schemaVersion;
        this.requestId = requestId;
        this.ok = ok;
        this.state = state;
        this.error = error;
    }

    public static AgentResponse ok(String requestId, String state) {
        return new AgentResponse(SCHEMA_VERSION, requestId, true, state, null);
    }

    public static AgentResponse error(String requestId, String error) {
        return new AgentResponse(SCHEMA_VERSION, requestId, false, null, error);
    }

    public static AgentResponse fromJson(String json) {
        int schemaVersion = Json.intValue(json, "schema_version", -1);
        if (schemaVersion != SCHEMA_VERSION) {
            throw new IllegalArgumentException("unsupported schema version: " + schemaVersion);
        }
        return new AgentResponse(
                schemaVersion,
                Json.stringValue(json, "request_id", ""),
                Json.booleanValue(json, "ok", false),
                Json.stringValue(json, "state", null),
                Json.stringValue(json, "error", null));
    }

    public String toJson() {
        StringBuilder builder = new StringBuilder();
        builder.append("{")
                .append("\"schema_version\":").append(schemaVersion).append(",")
                .append("\"request_id\":\"").append(Json.escape(requestId)).append("\",")
                .append("\"ok\":").append(ok);
        if (state != null) {
            builder.append(",\"state\":\"").append(Json.escape(state)).append("\"");
        }
        if (error != null) {
            builder.append(",\"error\":\"").append(Json.escape(error)).append("\"");
        } else {
            builder.append(",\"error\":null");
        }
        builder.append("}");
        return builder.toString();
    }

    public int schemaVersion() { return schemaVersion; }
    public String requestId() { return requestId; }
    public boolean ok() { return ok; }
    public String state() { return state; }
    public String error() { return error; }
}
