package io.solox.networkagent.notification;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.os.Build;

import io.solox.networkagent.R;

public final class AgentNotification {
    public static final String CHANNEL_ID = "solox_network_agent";
    private static final int SMALL_ICON = R.drawable.ic_agent_notification;

    private AgentNotification() {}

    public static Notification create(Context context) {
        ensureChannel(context);
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(context, CHANNEL_ID)
                : new Notification.Builder(context);
        return builder
                .setContentTitle("QAS Network Agent")
                .setContentText("弱网代理正在后台运行")
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
        channel.setDescription("QAS 弱网代理前台服务");
        manager.createNotificationChannel(channel);
    }
}
