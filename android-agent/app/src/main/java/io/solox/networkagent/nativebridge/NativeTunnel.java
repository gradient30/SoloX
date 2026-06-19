package io.solox.networkagent.nativebridge;

import io.solox.networkagent.model.WeakNetworkProfile;

public final class NativeTunnel {
    private static final String ARG_TUN_FD = "--tun-fd";
    private static final String ARG_PROXY_LOCAL_SOCKS = "--proxy=socks5://127.0.0.1:1080";
    private static final String ARG_DNS_OVER_TCP = "--dns=over-tcp";
    private static final String ARG_IPV6 = "--ipv6-enabled";
    private static final String ARG_MAX_SESSIONS = "--max-sessions=256";
    private static final String ARG_CLOSE_FD_ON_DROP = "--close-fd-on-drop=true";

    static {
        System.loadLibrary("solox_network_agent_native");
    }

    private NativeTunnel() {
    }

    public static String[] directArguments(int tunFd, boolean ipv6Enabled) {
        String tunFdValue = Integer.toString(tunFd);
        if (ipv6Enabled) {
            return new String[] {
                    ARG_TUN_FD,
                    tunFdValue,
                    ARG_PROXY_LOCAL_SOCKS,
                    ARG_DNS_OVER_TCP,
                    ARG_MAX_SESSIONS,
                    ARG_CLOSE_FD_ON_DROP,
                    ARG_IPV6
            };
        }
        return new String[] {
                ARG_TUN_FD,
                tunFdValue,
                ARG_PROXY_LOCAL_SOCKS,
                ARG_DNS_OVER_TCP,
                ARG_MAX_SESSIONS,
                ARG_CLOSE_FD_ON_DROP
        };
    }

    public static long start(int tunFd, boolean ipv6Enabled, WeakNetworkProfile profile) {
        if (profile == null) {
            throw new IllegalArgumentException("profile is required");
        }
        return nativeStart(
                tunFd,
                ipv6Enabled,
                profile.uplinkDelayMs(),
                profile.uplinkJitterMs(),
                profile.uplinkLossPct(),
                profile.uplinkBandwidthKbps(),
                profile.downlinkDelayMs(),
                profile.downlinkJitterMs(),
                profile.downlinkLossPct(),
                profile.downlinkBandwidthKbps());
    }

    public static void stop(long handle) {
        nativeStop(handle);
    }

    private static native long nativeStart(
            int tunFd,
            boolean ipv6Enabled,
            int uplinkDelayMs,
            int uplinkJitterMs,
            double uplinkLossPct,
            int uplinkBandwidthKbps,
            int downlinkDelayMs,
            int downlinkJitterMs,
            double downlinkLossPct,
            int downlinkBandwidthKbps);

    private static native void nativeStop(long handle);
}
