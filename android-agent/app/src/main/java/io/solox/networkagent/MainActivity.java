package io.solox.networkagent;

import android.app.Activity;
import android.content.Intent;
import android.net.VpnService;
import android.os.Build;
import android.os.Bundle;
import android.widget.TextView;

import io.solox.networkagent.vpn.SoloXVpnService;

public final class MainActivity extends Activity {
    private static final int VPN_REQUEST_CODE = 4100;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        TextView message = new TextView(this);
        message.setText("QAS Network Agent\nVPN authorization is required before weak-network preview can run.");
        message.setPadding(32, 32, 32, 32);
        setContentView(message);
        handleIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    private void handleIntent(Intent intent) {
        if (intent != null && intent.getBooleanExtra("request_vpn", false)) {
            requestVpnAuthorization();
        }
    }

    private void requestVpnAuthorization() {
        Intent prepareIntent = VpnService.prepare(this);
        if (prepareIntent != null) {
            startActivityForResult(prepareIntent, VPN_REQUEST_CODE);
            return;
        }
        startAgentService();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == VPN_REQUEST_CODE && resultCode == RESULT_OK) {
            startAgentService();
        }
    }

    private void startAgentService() {
        Intent serviceIntent = new Intent(this, SoloXVpnService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }
}
