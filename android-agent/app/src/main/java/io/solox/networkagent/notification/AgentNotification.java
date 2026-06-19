package io.solox.networkagent.notification;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.os.Build;

public final class AgentNotification {
    public static final String CHANNEL_ID = "solox_network_agent";
    private static final int SMALL_ICON = android.R.drawable.stat_sys_upload_done;

    private AgentNotification() {}

    public static Notification create(Context context) {
        ensureChannel(context);
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(context, CHANNEL_ID)
                : new Notification.Builder(context);
        return builder
                .setContentTitle("QAS Network Agent")
                .setContentText("Ready for weak-network preview control")
                .setSmallIcon(SMALL_ICON)
                .setOngoing(true)
                .build();
    }

    private static void ensureChannel(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null || manager.getNotificationChannel(CHANNEL_ID) != null) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "QAS Network Agent",
                NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("QAS Network Agent weak-network preview foreground service");
        manager.createNotificationChannel(channel);
    }
}
