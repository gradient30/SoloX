package io.solox.networkagent.state;

public enum AgentState {
    IDLE("idle"),
    PERMISSION_REQUIRED("permission_required"),
    STARTING("starting"),
    ACTIVE("active"),
    STOPPING("stopping"),
    ERROR("error");

    private final String wireName;

    AgentState(String wireName) {
        this.wireName = wireName;
    }

    public String wireName() {
        return wireName;
    }
}
