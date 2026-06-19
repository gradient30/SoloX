package io.solox.networkagent.model;

public final class WeakNetworkProfile {
    private final int uplinkDelayMs;
    private final int uplinkJitterMs;
    private final double uplinkLossPct;
    private final int uplinkBandwidthKbps;
    private final int downlinkDelayMs;
    private final int downlinkJitterMs;
    private final double downlinkLossPct;
    private final int downlinkBandwidthKbps;
    private final String protocol;

    private WeakNetworkProfile(
            int uplinkDelayMs,
            int uplinkJitterMs,
            double uplinkLossPct,
            int uplinkBandwidthKbps,
            int downlinkDelayMs,
            int downlinkJitterMs,
            double downlinkLossPct,
            int downlinkBandwidthKbps,
            String protocol) {
        validateNonNegative("uplink delay", uplinkDelayMs);
        validateNonNegative("uplink jitter", uplinkJitterMs);
        validateLoss("uplink loss", uplinkLossPct);
        validateNonNegative("uplink bandwidth", uplinkBandwidthKbps);
        validateNonNegative("downlink delay", downlinkDelayMs);
        validateNonNegative("downlink jitter", downlinkJitterMs);
        validateLoss("downlink loss", downlinkLossPct);
        validateNonNegative("downlink bandwidth", downlinkBandwidthKbps);
        if (!("all".equals(protocol) || "tcp".equals(protocol) || "udp".equals(protocol))) {
            throw new IllegalArgumentException("protocol must be all, tcp or udp");
        }
        this.uplinkDelayMs = uplinkDelayMs;
        this.uplinkJitterMs = uplinkJitterMs;
        this.uplinkLossPct = uplinkLossPct;
        this.uplinkBandwidthKbps = uplinkBandwidthKbps;
        this.downlinkDelayMs = downlinkDelayMs;
        this.downlinkJitterMs = downlinkJitterMs;
        this.downlinkLossPct = downlinkLossPct;
        this.downlinkBandwidthKbps = downlinkBandwidthKbps;
        this.protocol = protocol;
    }

    public static WeakNetworkProfile of(
            int uplinkDelayMs,
            int uplinkJitterMs,
            double uplinkLossPct,
            int uplinkBandwidthKbps,
            int downlinkDelayMs,
            int downlinkJitterMs,
            double downlinkLossPct,
            int downlinkBandwidthKbps,
            String protocol) {
        return new WeakNetworkProfile(
                uplinkDelayMs,
                uplinkJitterMs,
                uplinkLossPct,
                uplinkBandwidthKbps,
                downlinkDelayMs,
                downlinkJitterMs,
                downlinkLossPct,
                downlinkBandwidthKbps,
                protocol == null ? "all" : protocol);
    }

    public int uplinkDelayMs() { return uplinkDelayMs; }
    public int uplinkJitterMs() { return uplinkJitterMs; }
    public double uplinkLossPct() { return uplinkLossPct; }
    public int uplinkBandwidthKbps() { return uplinkBandwidthKbps; }
    public int downlinkDelayMs() { return downlinkDelayMs; }
    public int downlinkJitterMs() { return downlinkJitterMs; }
    public double downlinkLossPct() { return downlinkLossPct; }
    public int downlinkBandwidthKbps() { return downlinkBandwidthKbps; }
    public String protocol() { return protocol; }

    public String toJson() {
        return "{"
                + "\"uplink_delay_ms\":" + uplinkDelayMs + ","
                + "\"uplink_jitter_ms\":" + uplinkJitterMs + ","
                + "\"uplink_loss_pct\":" + uplinkLossPct + ","
                + "\"uplink_bandwidth_kbps\":" + uplinkBandwidthKbps + ","
                + "\"downlink_delay_ms\":" + downlinkDelayMs + ","
                + "\"downlink_jitter_ms\":" + downlinkJitterMs + ","
                + "\"downlink_loss_pct\":" + downlinkLossPct + ","
                + "\"downlink_bandwidth_kbps\":" + downlinkBandwidthKbps + ","
                + "\"protocol\":\"" + Json.escape(protocol) + "\""
                + "}";
    }

    public static WeakNetworkProfile fromJson(String json) {
        return of(
                Json.intValue(json, "uplink_delay_ms", 0),
                Json.intValue(json, "uplink_jitter_ms", 0),
                Json.doubleValue(json, "uplink_loss_pct", 0.0),
                Json.intValue(json, "uplink_bandwidth_kbps", 0),
                Json.intValue(json, "downlink_delay_ms", 0),
                Json.intValue(json, "downlink_jitter_ms", 0),
                Json.doubleValue(json, "downlink_loss_pct", 0.0),
                Json.intValue(json, "downlink_bandwidth_kbps", 0),
                Json.stringValue(json, "protocol", "all"));
    }

    private static void validateNonNegative(String name, int value) {
        if (value < 0) {
            throw new IllegalArgumentException(name + " must be non-negative");
        }
    }

    private static void validateLoss(String name, double value) {
        if (value < 0.0 || value > 100.0) {
            throw new IllegalArgumentException(name + " must be between 0 and 100");
        }
    }
}
