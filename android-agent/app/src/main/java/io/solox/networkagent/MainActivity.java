package io.solox.networkagent;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.VpnService;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
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
    private static final int COLOR_BACKGROUND = Color.rgb(246, 248, 251);
    private static final int COLOR_SURFACE = Color.WHITE;
    private static final int COLOR_PRIMARY = Color.rgb(25, 103, 210);
    private static final int COLOR_TEXT = Color.rgb(32, 33, 36);
    private static final int COLOR_SUB_TEXT = Color.rgb(95, 99, 104);
    private static final int COLOR_BORDER = Color.rgb(220, 224, 229);
    private static final String[] TAB_TITLES = {"总览", "弱网", "日志", "设置"};
    private LinearLayout contentLayout;
    private final Button[] tabButtons = new Button[TAB_TITLES.length];
    private TextView statusText;
    private TextView backgroundServiceText;
    private TextView logsText;
    private AgentLogLevel selectedLogLevel;
    private int selectedTabIndex;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        renderShell();
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

    private void renderShell() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(COLOR_BACKGROUND);

        TextView title = new TextView(this);
        title.setText("QAS 弱网代理");
        title.setTextColor(COLOR_TEXT);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextSize(20);
        title.setGravity(Gravity.CENTER_VERTICAL);
        title.setPadding(dp(20), dp(12), dp(20), dp(12));
        root.addView(title, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(56)));

        ScrollView scrollView = new ScrollView(this);
        contentLayout = new LinearLayout(this);
        contentLayout.setOrientation(LinearLayout.VERTICAL);
        contentLayout.setPadding(dp(16), dp(8), dp(16), dp(16));
        scrollView.addView(contentLayout);
        root.addView(scrollView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1));

        LinearLayout tabBar = new LinearLayout(this);
        tabBar.setOrientation(LinearLayout.HORIZONTAL);
        tabBar.setPadding(dp(8), dp(6), dp(8), dp(6));
        tabBar.setBackgroundColor(COLOR_SURFACE);
        for (int i = 0; i < TAB_TITLES.length; i++) {
            final int tabIndex = i;
            Button button = new Button(this);
            button.setAllCaps(false);
            button.setText(TAB_TITLES[i]);
            button.setTextSize(13);
            button.setMinHeight(0);
            button.setMinimumHeight(0);
            button.setPadding(0, 0, 0, 0);
            button.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    selectedTabIndex = tabIndex;
                    renderCurrentPage();
                }
            });
            tabButtons[i] = button;
            tabBar.addView(button, new LinearLayout.LayoutParams(
                    0,
                    dp(48),
                    1));
        }
        root.addView(tabBar, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(60)));

        setContentView(root);
        renderCurrentPage();
    }

    private void renderCurrentPage() {
        statusText = null;
        backgroundServiceText = null;
        logsText = null;
        contentLayout.removeAllViews();
        updateTabButtons();
        if (selectedTabIndex == 0) {
            renderOverviewPage();
        } else if (selectedTabIndex == 1) {
            renderWeakNetworkPage();
        } else if (selectedTabIndex == 2) {
            renderLogsPage();
        } else {
            renderSettingsPage();
        }
        refreshDashboard();
    }

    private void renderOverviewPage() {
        addPageTitle("总览", "准备接收 SoloX 弱网控制");

        LinearLayout statusCard = card();
        statusCard.addView(cardTitle("运行状态"));
        statusText = bodyText("");
        statusCard.addView(statusText);
        backgroundServiceText = bodyText("");
        statusCard.addView(backgroundServiceText);
        contentLayout.addView(statusCard);

        LinearLayout actions = card();
        actions.addView(cardTitle("快捷操作"));
        actions.addView(actionButton("授权并启动", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                requestVpnAuthorization();
            }
        }));
        actions.addView(actionButton("停止服务", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                stopAgentService();
                refreshDashboard();
            }
        }));
        actions.addView(actionButton("刷新状态", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                refreshDashboard();
            }
        }));
        contentLayout.addView(actions);

        contentLayout.addView(infoCell(
                "控制方式",
                "弱网参数由 SoloX 控制端下发，Agent 端负责 VPN 授权、后台服务和数据面执行。"));
    }

    private void renderWeakNetworkPage() {
        addPageTitle("弱网", "按目标 App 捕获流量并应用弱网模型");

        LinearLayout targetCard = card();
        targetCard.addView(cardTitle("目标应用"));
        targetCard.addView(bodyText("目标包名由 SoloX 控制端在启动请求中指定。"));
        targetCard.addView(bodyText("VpnService 使用 addAllowedApplication 仅捕获目标 App UID。"));
        contentLayout.addView(targetCard);

        LinearLayout profileCard = card();
        profileCard.addView(cardTitle("弱网数据面"));
        profileCard.addView(bodyText("延迟、抖动、丢包、带宽和乱序由 native 数据面执行。"));
        profileCard.addView(bodyText("诊断链路：TUN -> tun2proxy -> SOCKS5 shaper。"));
        contentLayout.addView(profileCard);

        contentLayout.addView(infoCell(
                "安全边界",
                "Agent 不在端上主动选择模板，避免测试现场误操作影响非目标 App。"));
    }

    private void renderLogsPage() {
        addPageTitle("日志", "Agent 端独立跟踪日志");

        LinearLayout filters = card();
        filters.addView(cardTitle("级别筛选"));
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.addView(filterButton("全部", null));
        row.addView(filterButton("错误 ERROR", AgentLogLevel.ERROR));
        row.addView(filterButton("警告 WARN", AgentLogLevel.WARN));
        row.addView(filterButton("信息 INFO", AgentLogLevel.INFO));
        row.addView(filterButton("调试 DEBUG", AgentLogLevel.DEBUG));
        filters.addView(row);
        contentLayout.addView(filters);

        LinearLayout logsCard = card();
        logsCard.addView(cardTitle("日志流"));
        logsText = bodyText("");
        logsText.setTextIsSelectable(true);
        logsCard.addView(logsText);
        contentLayout.addView(logsCard);
    }

    private void renderSettingsPage() {
        addPageTitle("设置", "终端代理诊断信息");

        LinearLayout identityCard = card();
        identityCard.addView(cardTitle("应用信息"));
        identityCard.addView(bodyText("产品名称：QAS Network Agent"));
        identityCard.addView(bodyText("显示名称：QAS 弱网代理"));
        identityCard.addView(bodyText("版本：" + appVersionName()));
        contentLayout.addView(identityCard);

        LinearLayout protocolCard = card();
        protocolCard.addView(cardTitle("控制协议"));
        protocolCard.addView(bodyText("包名：io.solox.networkagent"));
        protocolCard.addView(bodyText("控制 socket：solox.networkagent.control"));
        protocolCard.addView(bodyText("状态字段与命令字保持英文，确保 SoloX 控制链路兼容。"));
        contentLayout.addView(protocolCard);

        LinearLayout backgroundCard = card();
        backgroundCard.addView(cardTitle("后台运行"));
        backgroundCard.addView(bodyText("前台服务使用常驻通知运行，onStartCommand 返回 START_STICKY。"));
        backgroundCard.addView(bodyText("通知栏可用于确认弱网代理正在后台运行。"));
        contentLayout.addView(backgroundCard);
    }

    private void addPageTitle(String title, String subtitle) {
        TextView titleView = new TextView(this);
        titleView.setText(title);
        titleView.setTextColor(COLOR_TEXT);
        titleView.setTypeface(Typeface.DEFAULT_BOLD);
        titleView.setTextSize(24);
        titleView.setPadding(0, dp(8), 0, dp(2));
        contentLayout.addView(titleView);

        TextView subtitleView = bodyText(subtitle);
        subtitleView.setPadding(0, 0, 0, dp(12));
        contentLayout.addView(subtitleView);
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
        refreshDashboard();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == VPN_REQUEST_CODE && resultCode == RESULT_OK) {
            startAgentService();
            refreshDashboard();
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
                    ? "VPN 授权：已授权，可接收按 App 弱网控制"
                    : "VPN 授权：待授权，授权后才能执行按 App 弱网控制");
        }
        if (backgroundServiceText != null) {
            backgroundServiceText.setText("后台运行：前台服务 + 常驻通知 + START_STICKY。");
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
            builder.append('#')
                    .append(entry.sequence())
                    .append("  ")
                    .append(entry.level().name())
                    .append("  ")
                    .append(entry.source())
                    .append('\n')
                    .append(entry.message())
                    .append("\n\n");
        }
        if (builder.length() == 0) {
            return selectedLogLevel == null
                    ? "暂无 Agent 日志。"
                    : "暂无 " + selectedLogLevel.name() + " 级别日志。";
        }
        return builder.toString();
    }

    private LinearLayout card() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(14), dp(12), dp(14), dp(12));
        card.setBackground(rounded(COLOR_SURFACE, COLOR_BORDER, 8));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, 0, 0, dp(12));
        card.setLayoutParams(params);
        return card;
    }

    private View infoCell(String title, String body) {
        LinearLayout cell = card();
        cell.addView(cardTitle(title));
        cell.addView(bodyText(body));
        return cell;
    }

    private TextView cardTitle(String value) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextColor(COLOR_TEXT);
        view.setTypeface(Typeface.DEFAULT_BOLD);
        view.setTextSize(16);
        view.setPadding(0, 0, 0, dp(6));
        return view;
    }

    private TextView bodyText(String value) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextColor(COLOR_SUB_TEXT);
        view.setTextSize(14);
        view.setLineSpacing(0, 1.12f);
        view.setPadding(0, 0, 0, dp(8));
        return view;
    }

    private Button actionButton(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(15);
        button.setTextColor(COLOR_TEXT);
        button.setOnClickListener(listener);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(48));
        params.setMargins(0, dp(6), 0, 0);
        button.setLayoutParams(params);
        return button;
    }

    private Button filterButton(String label, final AgentLogLevel level) {
        Button button = actionButton(label, new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                selectedLogLevel = level;
                renderCurrentPage();
            }
        });
        if (selectedLogLevel == level) {
            button.setTextColor(COLOR_PRIMARY);
        }
        return button;
    }

    private void updateTabButtons() {
        for (int i = 0; i < tabButtons.length; i++) {
            Button button = tabButtons[i];
            boolean selected = i == selectedTabIndex;
            button.setTextColor(selected ? Color.WHITE : COLOR_SUB_TEXT);
            button.setTypeface(selected ? Typeface.DEFAULT_BOLD : Typeface.DEFAULT);
            button.setBackground(rounded(
                    selected ? COLOR_PRIMARY : COLOR_SURFACE,
                    selected ? COLOR_PRIMARY : COLOR_BORDER,
                    8));
        }
    }

    private GradientDrawable rounded(int fillColor, int strokeColor, int radiusDp) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fillColor);
        drawable.setCornerRadius(dp(radiusDp));
        drawable.setStroke(dp(1), strokeColor);
        return drawable;
    }

    private String appVersionName() {
        try {
            PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), 0);
            return info.versionName == null ? "unknown" : info.versionName;
        } catch (PackageManager.NameNotFoundException exc) {
            return "unknown";
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
