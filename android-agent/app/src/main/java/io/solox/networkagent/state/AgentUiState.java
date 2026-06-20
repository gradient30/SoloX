package io.solox.networkagent.state;

import android.content.Context;
import android.content.SharedPreferences;

public final class AgentUiState {
    private static final String PREFS_NAME = "qas_network_agent_ui_state";
    private static final String KEY_SERVICE_RUNNING = "service_running";
    private static final String KEY_TUNNEL_ACTIVE = "tunnel_active";
    private static final String KEY_TARGET_PACKAGE = "target_package";
    private static final String KEY_LAST_OPERATION = "last_operation";
    private static final String KEY_LAST_ERROR = "last_error";
    private static final String KEY_UPDATED_AT_MS = "updated_at_ms";

    private AgentUiState() {
    }

    public static void markServiceRunning(Context context) {
        edit(context)
                .putBoolean(KEY_SERVICE_RUNNING, true)
                .putString(KEY_LAST_OPERATION, "后台服务已启动，正在等待 SoloX 控制端下发目标 App")
                .putLong(KEY_UPDATED_AT_MS, System.currentTimeMillis())
                .apply();
    }

    public static void markServiceStopped(Context context) {
        edit(context)
                .putBoolean(KEY_SERVICE_RUNNING, false)
                .putBoolean(KEY_TUNNEL_ACTIVE, false)
                .remove(KEY_TARGET_PACKAGE)
                .putString(KEY_LAST_OPERATION, "后台服务已停止，VPN 隧道已清理")
                .putLong(KEY_UPDATED_AT_MS, System.currentTimeMillis())
                .apply();
    }

    public static void markTunnelActive(Context context, String targetPackage) {
        edit(context)
                .putBoolean(KEY_SERVICE_RUNNING, true)
                .putBoolean(KEY_TUNNEL_ACTIVE, true)
                .putString(KEY_TARGET_PACKAGE, emptyToNull(targetPackage))
                .remove(KEY_LAST_ERROR)
                .putString(KEY_LAST_OPERATION, "VPN 隧道已建立，目标 App：" + emptyToNull(targetPackage))
                .putLong(KEY_UPDATED_AT_MS, System.currentTimeMillis())
                .apply();
    }

    public static void markTunnelIdle(Context context) {
        edit(context)
                .putBoolean(KEY_TUNNEL_ACTIVE, false)
                .remove(KEY_TARGET_PACKAGE)
                .putString(KEY_LAST_OPERATION, "VPN 隧道已停止，等待新的弱网任务")
                .putLong(KEY_UPDATED_AT_MS, System.currentTimeMillis())
                .apply();
    }

    public static void markError(Context context, String message) {
        String safeMessage = emptyToNull(message);
        edit(context)
                .putString(KEY_LAST_ERROR, safeMessage)
                .putString(KEY_LAST_OPERATION, "最近错误：" + safeMessage)
                .putLong(KEY_UPDATED_AT_MS, System.currentTimeMillis())
                .apply();
    }

    public static void recordOperation(Context context, String message) {
        edit(context)
                .putString(KEY_LAST_OPERATION, emptyToNull(message))
                .putLong(KEY_UPDATED_AT_MS, System.currentTimeMillis())
                .apply();
    }

    public static Snapshot read(Context context) {
        SharedPreferences prefs = prefs(context);
        return new Snapshot(
                prefs.getBoolean(KEY_SERVICE_RUNNING, false),
                prefs.getBoolean(KEY_TUNNEL_ACTIVE, false),
                prefs.getString(KEY_TARGET_PACKAGE, ""),
                prefs.getString(KEY_LAST_OPERATION, ""),
                prefs.getString(KEY_LAST_ERROR, ""),
                prefs.getLong(KEY_UPDATED_AT_MS, 0L));
    }

    private static SharedPreferences.Editor edit(Context context) {
        return prefs(context).edit();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext()
                .getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    private static String emptyToNull(String value) {
        if (value == null || value.trim().isEmpty()) {
            return "未指定";
        }
        return value.trim();
    }

    public static final class Snapshot {
        private final boolean serviceRunning;
        private final boolean tunnelActive;
        private final String targetPackage;
        private final String lastOperation;
        private final String lastError;
        private final long updatedAtMs;

        private Snapshot(
                boolean serviceRunning,
                boolean tunnelActive,
                String targetPackage,
                String lastOperation,
                String lastError,
                long updatedAtMs) {
            this.serviceRunning = serviceRunning;
            this.tunnelActive = tunnelActive;
            this.targetPackage = targetPackage == null ? "" : targetPackage;
            this.lastOperation = lastOperation == null ? "" : lastOperation;
            this.lastError = lastError == null ? "" : lastError;
            this.updatedAtMs = updatedAtMs;
        }

        public boolean serviceRunning() {
            return serviceRunning;
        }

        public boolean tunnelActive() {
            return tunnelActive;
        }

        public String targetPackage() {
            return targetPackage;
        }

        public String lastOperation() {
            return lastOperation;
        }

        public String lastError() {
            return lastError;
        }

        public long updatedAtMs() {
            return updatedAtMs;
        }
    }
}
