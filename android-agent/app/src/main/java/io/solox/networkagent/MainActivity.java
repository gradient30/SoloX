package io.solox.networkagent;

import android.app.Activity;
import android.content.Intent;
import android.net.VpnService;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import io.solox.networkagent.logging.AgentLogEntry;
import io.solox.networkagent.logging.AgentLogLevel;
import io.solox.networkagent.runtime.AgentRuntime;
import io.solox.networkagent.vpn.SoloXVpnService;

public final class MainActivity extends Activity {
    private static final int VPN_REQUEST_CODE = 4100;
    private static final int PAGE_PADDING = 28;
    private static final int SECTION_PADDING = 12;
    private TextView statusText;
    private TextView backgroundServiceText;
    private TextView logsText;
    private AgentLogLevel selectedLogLevel;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        renderDashboard();
        handleIntent(getIntent());
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshDashboard();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    private void renderDashboard() {
        ScrollView scrollView = new ScrollView(this);
        LinearLayout dashboard = new LinearLayout(this);
        dashboard.setOrientation(LinearLayout.VERTICAL);
        dashboard.setPadding(PAGE_PADDING, PAGE_PADDING, PAGE_PADDING, PAGE_PADDING);
        scrollView.addView(dashboard);

        TextView title = sectionText("QAS Network Agent");
        title.setTextSize(22);
        dashboard.addView(title);

        statusText = bodyText("");
        dashboard.addView(sectionText("Status"));
        dashboard.addView(statusText);

        dashboard.addView(sectionText("VPN authorization"));
        dashboard.addView(actionButton("Authorize VPN and start service", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                requestVpnAuthorization();
            }
        }));

        dashboard.addView(sectionText("Target package"));
        dashboard.addView(bodyText("Controlled by SoloX over the local control socket per start request."));

        dashboard.addView(sectionText("Weak network profile"));
        dashboard.addView(bodyText("Delay, jitter, loss, bandwidth, and reordering are applied by the native data plane."));

        dashboard.addView(sectionText("Background service"));
        backgroundServiceText = bodyText("");
        dashboard.addView(backgroundServiceText);
        LinearLayout serviceActions = buttonRow();
        serviceActions.addView(actionButton("Start foreground service", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                startAgentService();
                refreshDashboard();
            }
        }));
        serviceActions.addView(actionButton("Stop service", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                stopAgentService();
                refreshDashboard();
            }
        }));
        serviceActions.addView(actionButton("Refresh", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                refreshDashboard();
            }
        }));
        dashboard.addView(serviceActions);

        dashboard.addView(sectionText("Agent logs"));
        LinearLayout filters = buttonRow();
        filters.addView(filterButton("ERROR", AgentLogLevel.ERROR));
        filters.addView(filterButton("WARN", AgentLogLevel.WARN));
        filters.addView(filterButton("INFO", AgentLogLevel.INFO));
        filters.addView(filterButton("DEBUG", AgentLogLevel.DEBUG));
        filters.addView(filterButton("ALL", null));
        dashboard.addView(filters);
        logsText = bodyText("");
        logsText.setTextIsSelectable(true);
        dashboard.addView(logsText);

        setContentView(scrollView);
        refreshDashboard();
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

    private void stopAgentService() {
        stopService(new Intent(this, SoloXVpnService.class));
    }

    private void refreshDashboard() {
        if (statusText != null) {
            boolean authorized = VpnService.prepare(this) == null;
            statusText.setText(authorized
                    ? "VPN authorization: granted"
                    : "VPN authorization: required before per-app weak-network control can run");
        }
        if (backgroundServiceText != null) {
            backgroundServiceText.setText("Foreground service uses QAS notification, startForeground, and START_STICKY for background operation.");
        }
        if (logsText != null) {
            logsText.setText(renderLogs());
        }
    }

    public String renderLogs() {
        StringBuilder builder = new StringBuilder();
        for (AgentLogEntry entry : AgentRuntime.latestLogs()) {
            if (selectedLogLevel != null && entry.level() != selectedLogLevel) {
                continue;
            }
            builder.append(entry.sequence())
                    .append(' ')
                    .append(entry.level().name())
                    .append(' ')
                    .append(entry.source())
                    .append(": ")
                    .append(entry.message())
                    .append('\n');
        }
        if (builder.length() == 0) {
            return selectedLogLevel == null
                    ? "No Agent logs recorded yet."
                    : "No Agent logs recorded for " + selectedLogLevel.name() + ".";
        }
        return builder.toString();
    }

    private TextView sectionText(String value) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(16);
        view.setPadding(0, SECTION_PADDING, 0, 4);
        return view;
    }

    private TextView bodyText(String value) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(14);
        view.setPadding(0, 0, 0, SECTION_PADDING);
        return view;
    }

    private LinearLayout buttonRow() {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setPadding(0, 0, 0, SECTION_PADDING);
        return row;
    }

    private Button actionButton(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(label);
        button.setOnClickListener(listener);
        return button;
    }

    private Button filterButton(String label, final AgentLogLevel level) {
        return actionButton(label, new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                selectedLogLevel = level;
                refreshDashboard();
            }
        });
    }
}
