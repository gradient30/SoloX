package io.solox.networkagent.vpn;

import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.VpnService;
import android.os.IBinder;
import android.os.ParcelFileDescriptor;
import android.util.Log;

import java.io.IOException;

import io.solox.networkagent.control.CommandDispatcher;
import io.solox.networkagent.control.ControlSocketServer;
import io.solox.networkagent.model.WeakNetworkProfile;
import io.solox.networkagent.nativebridge.NativeTunnel;
import io.solox.networkagent.notification.AgentNotification;
import io.solox.networkagent.state.AgentStateStore;

public final class SoloXVpnService extends VpnService {
    private static final int NOTIFICATION_ID = 6201;
    private static final String TAG = "SoloXAgent";
    private static final int VPN_MTU = 1500;
    private static final String IPV4_ADDRESS = "10.111.0.2";
    private static final String IPV6_ADDRESS = "fd00:736f:6c6f::2";
    private ControlSocketServer controlSocketServer;
    private ParcelFileDescriptor tunDescriptor;
    private long nativeHandle;

    @Override
    public void onCreate() {
        super.onCreate();
        startForeground(NOTIFICATION_ID, AgentNotification.create(this));
        AgentStateStore stateStore = new AgentStateStore(10_000L);
        CommandDispatcher dispatcher = new CommandDispatcher(
                stateStore,
                new ServiceTunnelController(),
                this::isPackageInstalled);
        controlSocketServer = new ControlSocketServer(dispatcher);
        try {
            controlSocketServer.start();
        } catch (IOException exc) {
            Log.e(TAG, "cannot start control socket", exc);
            stopSelf();
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return super.onBind(intent);
    }

    @Override
    public void onDestroy() {
        stopTunnel();
        if (controlSocketServer != null) {
            try {
                controlSocketServer.close();
            } catch (IOException exc) {
                Log.w(TAG, "control socket close failed", exc);
            }
            controlSocketServer = null;
        }
        super.onDestroy();
    }

    private boolean isPackageInstalled(String packageName) {
        try {
            getPackageManager().getPackageInfo(packageName, 0);
            return true;
        } catch (PackageManager.NameNotFoundException exc) {
            return false;
        }
    }

    private synchronized CommandDispatcher.TunnelStartResult startTunnel(String targetPackage, WeakNetworkProfile profile) {
        stopTunnel();
        if (getPackageName().equals(targetPackage)) {
            return CommandDispatcher.TunnelStartResult.error("target package must not be the Agent package");
        }
        ParcelFileDescriptor descriptor = null;
        int detachedFd = -1;
        try {
            Builder builder = new Builder()
                    .setSession("SoloX weak network: " + targetPackage)
                    .setMtu(VPN_MTU)
                    .addAddress(IPV4_ADDRESS, 32)
                    .addRoute("0.0.0.0", 0)
                    .addDnsServer("8.8.8.8")
                    .addAllowedApplication(targetPackage);
            try {
                builder.addAddress(IPV6_ADDRESS, 128)
                        .addRoute("::", 0)
                        .addDnsServer("2001:4860:4860::8888");
            } catch (IllegalArgumentException exc) {
                Log.w(TAG, "IPv6 VPN route unavailable on this device", exc);
            }
            descriptor = builder.establish();
            if (descriptor == null) {
                return CommandDispatcher.TunnelStartResult.error("VPN establish returned null");
            }
            detachedFd = descriptor.detachFd();
            descriptor = null;
            long handle = NativeTunnel.start(detachedFd, true, profile);
            if (handle <= 0) {
                closeDetachedFd(detachedFd);
                return CommandDispatcher.TunnelStartResult.error("native data plane unavailable: code " + handle);
            }
            detachedFd = -1;
            nativeHandle = handle;
            return CommandDispatcher.TunnelStartResult.ok();
        } catch (PackageManager.NameNotFoundException exc) {
            closeQuietly(descriptor);
            if (detachedFd >= 0) {
                closeDetachedFd(detachedFd);
            }
            return CommandDispatcher.TunnelStartResult.error("target package is not installed: " + targetPackage);
        } catch (RuntimeException | Error exc) {
            closeQuietly(descriptor);
            if (detachedFd >= 0) {
                closeDetachedFd(detachedFd);
            }
            Log.e(TAG, "cannot start tunnel", exc);
            return CommandDispatcher.TunnelStartResult.error("native data plane unavailable");
        }
    }

    private synchronized void stopTunnel() {
        if (nativeHandle > 0) {
            try {
                NativeTunnel.stop(nativeHandle);
            } catch (RuntimeException | Error exc) {
                Log.w(TAG, "native tunnel stop failed", exc);
            }
            nativeHandle = 0;
        }
        closeQuietly(tunDescriptor);
        tunDescriptor = null;
    }

    private static void closeDetachedFd(int fd) {
        closeQuietly(ParcelFileDescriptor.adoptFd(fd));
    }

    private static void closeQuietly(ParcelFileDescriptor descriptor) {
        if (descriptor == null) {
            return;
        }
        try {
            descriptor.close();
        } catch (IOException exc) {
            Log.w(TAG, "TUN descriptor close failed", exc);
        }
    }

    private final class ServiceTunnelController implements CommandDispatcher.TunnelController {
        @Override
        public boolean isAuthorized() {
            return VpnService.prepare(SoloXVpnService.this) == null;
        }

        @Override
        public CommandDispatcher.TunnelStartResult start(String targetPackage, WeakNetworkProfile profile) {
            return startTunnel(targetPackage, profile);
        }

        @Override
        public void stop() {
            stopTunnel();
        }
    }
}
