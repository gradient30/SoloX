package io.solox.networkagent;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.VpnService;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import io.solox.networkagent.logging.AgentLogEntry;
import io.solox.networkagent.logging.AgentLogLevel;
import io.solox.networkagent.runtime.AgentRuntime;
import io.solox.networkagent.state.AgentUiState;
import io.solox.networkagent.vpn.SoloXVpnService;

public final class MainActivity extends Activity {
    private static final int VPN_REQUEST_CODE = 4100;
    private static final int COLOR_BACKGROUND = Color.rgb(246, 248, 251);
    private static final int COLOR_SURFACE = Color.WHITE;
    private static final int COLOR_PRIMARY = Color.rgb(25, 103, 210);
    private static final int COLOR_SUCCESS = Color.rgb(24, 128, 56);
    private static final int COLOR_WARNING = Color.rgb(180, 95, 0);
    private static final int COLOR_DANGER = Color.rgb(185, 28, 28);
    private static final int COLOR_DEBUG = Color.rgb(93, 95, 239);
    private static final int COLOR_TEXT = Color.rgb(32, 33, 36);
    private static final int COLOR_SUB_TEXT = Color.rgb(95, 99, 104);
    private static final int COLOR_BORDER = Color.rgb(220, 224, 229);
    private static final int COLOR_MUTED_FILL = Color.rgb(241, 243, 244);
    private static final int COLOR_SUCCESS_FILL = Color.rgb(232, 245, 233);
    private static final int COLOR_WARNING_FILL = Color.rgb(255, 247, 237);
    private static final int COLOR_DANGER_FILL = Color.rgb(254, 242, 242);
    private static final int COLOR_INFO_FILL = Color.rgb(232, 240, 254);
    private static final String[] TAB_TITLES = {"总览", "弱网", "日志", "设置"};
    private LinearLayout contentLayout;
    private final Button[] tabButtons = new Button[TAB_TITLES.length];
    private TextView authorizationText;
    private TextView serviceStateText;
    private TextView tunnelStateText;
    private TextView lastOperationText;
    private TextView vpnIconHintText;
    private TextView logsText;
    private LinearLayout logsContainer;
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

        LinearLayout titleBar = new LinearLayout(this);
        titleBar.setOrientation(LinearLayout.HORIZONTAL);
        titleBar.setGravity(Gravity.CENTER_VERTICAL);
        titleBar.setPadding(dp(20), dp(8), dp(12), dp(8));

        TextView title = new TextView(this);
        title.setText("QAS 弱网代理");
        title.setTextColor(COLOR_TEXT);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextSize(20);
        title.setGravity(Gravity.CENTER_VERTICAL);
        titleBar.addView(title, new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.MATCH_PARENT,
                1));

        Button helpButton = new Button(this);
        helpButton.setAllCaps(false);
        helpButton.setText("?");
        helpButton.setTextSize(18);
        helpButton.setTypeface(Typeface.DEFAULT_BOLD);
        helpButton.setTextColor(COLOR_PRIMARY);
        helpButton.setMinHeight(0);
        helpButton.setMinimumHeight(0);
        helpButton.setPadding(0, 0, 0, 0);
        helpButton.setBackground(rounded(COLOR_INFO_FILL, COLOR_PRIMARY, 18));
        helpButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                showHelpDialog();
            }
        });
        titleBar.addView(helpButton, new LinearLayout.LayoutParams(dp(40), dp(40)));
        root.addView(titleBar, new LinearLayout.LayoutParams(
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
        authorizationText = null;
        serviceStateText = null;
        tunnelStateText = null;
        lastOperationText = null;
        vpnIconHintText = null;
        logsText = null;
        logsContainer = null;
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
        addPageTitle("总览", "准备接收 SoloX 弱网控制；当前状态来自系统授权、后台服务和真实 VPN 隧道记录");

        LinearLayout statusCard = card();
        statusCard.addView(cardTitle("当前检测结果"));
        authorizationText = statusCell(statusCard, "授权状态");
        serviceStateText = statusCell(statusCard, "服务状态");
        tunnelStateText = statusCell(statusCard, "隧道状态");
        lastOperationText = statusCell(statusCard, "最近操作");
        vpnIconHintText = bodyText("VPN 图标只会在真实 VPN 隧道建立后出现");
        vpnIconHintText.setTextColor(COLOR_PRIMARY);
        vpnIconHintText.setTypeface(Typeface.DEFAULT_BOLD);
        statusCard.addView(vpnIconHintText);
        contentLayout.addView(statusCard);

        LinearLayout actions = card();
        actions.addView(cardTitle("快捷操作"));
        actions.addView(bodyText("常用动作：授权并启动、停止服务、刷新状态、查看系统 VPN。"));
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.addView(compactActionButton("▶ 启动", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                AgentUiState.recordOperation(MainActivity.this, "已点击启动，正在处理 VPN 授权与后台服务");
                requestVpnAuthorization();
                refreshDashboard();
            }
        }));
        row.addView(compactActionButton("■ 停止", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                AgentUiState.recordOperation(MainActivity.this, "已点击停止，正在清理后台服务和 VPN 隧道");
                stopAgentService();
                AgentUiState.markServiceStopped(MainActivity.this);
                refreshDashboard();
            }
        }));
        row.addView(compactActionButton("⟳ 刷新", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                AgentUiState.recordOperation(MainActivity.this, "状态已刷新");
                refreshDashboard();
            }
        }));
        row.addView(compactActionButton("⚙ VPN", new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                AgentUiState.recordOperation(MainActivity.this, "已打开系统 VPN 设置");
                openVpnSettings();
                refreshDashboard();
            }
        }));
        actions.addView(row);
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
        profileCard.addView(bodyText("诊断链路：目标 App → Android VPN → QAS Agent → tun2proxy → SOCKS5 shaper → 真实网络。"));
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
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.addView(filterButton("全部", null));
        row.addView(filterButton("错误 ERROR", AgentLogLevel.ERROR));
        row.addView(filterButton("警告 WARN", AgentLogLevel.WARN));
        row.addView(filterButton("信息 INFO", AgentLogLevel.INFO));
        row.addView(filterButton("调试 DEBUG", AgentLogLevel.DEBUG));
        filters.addView(row);
        contentLayout.addView(filters);

        LinearLayout logsCard = card();
        logsCard.addView(cardTitle("日志流"));
        logsContainer = new LinearLayout(this);
        logsContainer.setOrientation(LinearLayout.VERTICAL);
        logsCard.addView(logsContainer);
        logsText = bodyText("");
        logsText.setTextIsSelectable(true);
        logsText.setVisibility(View.GONE);
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
        titleView.setTextSize(22);
        titleView.setPadding(0, dp(8), 0, dp(2));
        contentLayout.addView(titleView);

        TextView subtitleView = bodyText(subtitle);
        subtitleView.setPadding(0, 0, 0, dp(12));
        contentLayout.addView(subtitleView);
    }

    private void handleIntent(Intent intent) {
        if (intent != null && intent.getBooleanExtra("request_vpn", false)) {
            AgentUiState.recordOperation(this, "收到 SoloX 控制端授权请求");
            requestVpnAuthorization();
        }
    }

    private void requestVpnAuthorization() {
        Intent prepareIntent = VpnService.prepare(this);
        if (prepareIntent != null) {
            AgentUiState.recordOperation(this, "等待系统 VPN 授权弹窗确认");
            startActivityForResult(prepareIntent, VPN_REQUEST_CODE);
            return;
        }
        AgentUiState.recordOperation(this, "VPN 已授权，正在启动后台服务");
        startAgentService();
        refreshDashboard();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == VPN_REQUEST_CODE && resultCode == RESULT_OK) {
            AgentUiState.recordOperation(this, "VPN 授权已通过，正在启动后台服务");
            startAgentService();
            refreshDashboard();
        } else if (requestCode == VPN_REQUEST_CODE) {
            AgentUiState.markError(this, "VPN 授权未通过");
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

    private void openVpnSettings() {
        try {
            startActivity(new Intent(Settings.ACTION_VPN_SETTINGS));
        } catch (RuntimeException exc) {
            startActivity(new Intent(Settings.ACTION_SETTINGS));
        }
    }

    private void refreshDashboard() {
        AgentUiState.Snapshot snapshot = AgentUiState.read(this);
        boolean authorized = VpnService.prepare(this) == null;
        if (authorizationText != null) {
            setStatusText(
                    authorizationText,
                    authorized ? "已授权，可接收按 App 弱网控制" : "待授权，授权后才能执行按 App 弱网控制",
                    authorized ? COLOR_SUCCESS : COLOR_WARNING);
        }
        if (serviceStateText != null) {
            setStatusText(
                    serviceStateText,
                    snapshot.serviceRunning() ? "后台服务运行中" : "后台服务未运行",
                    snapshot.serviceRunning() ? COLOR_SUCCESS : COLOR_SUB_TEXT);
        }
        if (tunnelStateText != null) {
            if (snapshot.tunnelActive()) {
                setStatusText(tunnelStateText, "VPN 隧道已建立：" + snapshot.targetPackage(), COLOR_SUCCESS);
            } else if (!snapshot.lastError().isEmpty()) {
                setStatusText(tunnelStateText, "VPN 隧道未建立；" + snapshot.lastError(), COLOR_DANGER);
            } else {
                setStatusText(tunnelStateText, "VPN 隧道未建立，等待 SoloX 下发目标 App", COLOR_SUB_TEXT);
            }
        }
        if (lastOperationText != null) {
            String operation = snapshot.lastOperation().isEmpty() ? "暂无操作记录" : snapshot.lastOperation();
            setStatusText(lastOperationText, operation, COLOR_PRIMARY);
        }
        if (vpnIconHintText != null) {
            vpnIconHintText.setText(snapshot.tunnelActive()
                    ? "系统状态栏应显示 VPN 图标；如未显示，请打开系统 VPN 设置确认。"
                    : "VPN 图标只会在真实 VPN 隧道建立后出现；仅授权或启动后台服务不会显示。");
        }
        if (logsText != null) {
            logsText.setText(renderLogs());
        }
        if (logsContainer != null) {
            renderLogCells();
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
                    .append(logLevelLabel(entry.level()))
                    .append("  ")
                    .append(entry.source())
                    .append('\n')
                    .append(entry.message())
                    .append("\n\n");
        }
        if (builder.length() == 0) {
            return selectedLogLevel == null
                    ? "暂无 Agent 日志。"
                    : "暂无 " + logLevelLabel(selectedLogLevel) + " 级别日志。";
        }
        return builder.toString();
    }

    private void renderLogCells() {
        logsContainer.removeAllViews();
        boolean hasLog = false;
        for (AgentLogEntry entry : AgentRuntime.latestLogs()) {
            if (selectedLogLevel != null && entry.level() != selectedLogLevel) {
                continue;
            }
            logsContainer.addView(renderLogEntry(entry));
            hasLog = true;
        }
        if (!hasLog) {
            logsContainer.addView(bodyText(selectedLogLevel == null
                    ? "暂无 Agent 日志。"
                    : "暂无 " + logLevelLabel(selectedLogLevel) + " 级别日志。"));
        }
    }

    private View renderLogEntry(AgentLogEntry entry) {
        LinearLayout item = new LinearLayout(this);
        item.setOrientation(LinearLayout.VERTICAL);
        item.setPadding(dp(10), dp(8), dp(10), dp(8));
        item.setBackground(rounded(logLevelFillColor(entry.level()), logLevelColor(entry.level()), 6));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, 0, 0, dp(8));
        item.setLayoutParams(params);

        TextView header = new TextView(this);
        header.setText("#" + entry.sequence() + "  " + logLevelLabel(entry.level()) + "  " + entry.source());
        header.setTextColor(logLevelColor(entry.level()));
        header.setTypeface(Typeface.DEFAULT_BOLD);
        header.setTextSize(12);
        item.addView(header);

        TextView message = bodyText(entry.message());
        message.setTextColor(COLOR_TEXT);
        message.setTextSize(12);
        message.setPadding(0, dp(4), 0, 0);
        item.addView(message);
        return item;
    }

    private int logLevelColor(AgentLogLevel level) {
        if (level == AgentLogLevel.ERROR) {
            return COLOR_DANGER;
        }
        if (level == AgentLogLevel.WARN) {
            return COLOR_WARNING;
        }
        if (level == AgentLogLevel.DEBUG) {
            return COLOR_DEBUG;
        }
        return COLOR_SUCCESS;
    }

    private int logLevelFillColor(AgentLogLevel level) {
        if (level == AgentLogLevel.ERROR) {
            return COLOR_DANGER_FILL;
        }
        if (level == AgentLogLevel.WARN) {
            return COLOR_WARNING_FILL;
        }
        if (level == AgentLogLevel.DEBUG) {
            return COLOR_INFO_FILL;
        }
        return COLOR_SUCCESS_FILL;
    }

    private String logLevelLabel(AgentLogLevel level) {
        if (level == AgentLogLevel.ERROR) {
            return "错误 ERROR";
        }
        if (level == AgentLogLevel.WARN) {
            return "警告 WARN";
        }
        if (level == AgentLogLevel.DEBUG) {
            return "调试 DEBUG";
        }
        return "信息 INFO";
    }

    private void showHelpDialog() {
        new AlertDialog.Builder(this)
                .setTitle("弱网原理说明")
                .setMessage(
                        "QAS 弱网代理像一条测试专用通道，只接管被 SoloX 指定的目标 App 流量。\n\n"
                                + "链路图：目标 App → Android VPN → QAS Agent → tun2proxy → SOCKS5 弱网整形 → 真实网络\n\n"
                                + "Android VPN 负责把目标 App 的网络包交给 Agent；tun2proxy 把这些网络包转换成本地代理流量；SOCKS5 弱网整形负责添加延迟、抖动、丢包和限速。\n\n"
                                + "VPN 图标只会在真实 VPN 隧道建立后出现。仅完成授权或启动后台服务时，系统通常不会显示顶部 VPN 图标。")
                .setPositiveButton("知道了", null)
                .show();
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

    private TextView statusCell(LinearLayout parent, String title) {
        LinearLayout cell = new LinearLayout(this);
        cell.setOrientation(LinearLayout.VERTICAL);
        cell.setPadding(dp(10), dp(8), dp(10), dp(8));
        cell.setBackground(rounded(COLOR_MUTED_FILL, COLOR_BORDER, 6));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, 0, 0, dp(8));
        cell.setLayoutParams(params);

        TextView titleView = new TextView(this);
        titleView.setText(title);
        titleView.setTextColor(COLOR_SUB_TEXT);
        titleView.setTextSize(12);
        titleView.setPadding(0, 0, 0, dp(3));
        cell.addView(titleView);

        TextView valueView = new TextView(this);
        valueView.setTextColor(COLOR_TEXT);
        valueView.setTypeface(Typeface.DEFAULT_BOLD);
        valueView.setTextSize(13);
        valueView.setLineSpacing(0, 1.12f);
        cell.addView(valueView);
        parent.addView(cell);
        return valueView;
    }

    private void setStatusText(TextView textView, String value, int color) {
        textView.setText(value);
        textView.setTextColor(color);
    }

    private TextView cardTitle(String value) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextColor(COLOR_TEXT);
        view.setTypeface(Typeface.DEFAULT_BOLD);
        view.setTextSize(15);
        view.setPadding(0, 0, 0, dp(6));
        return view;
    }

    private TextView bodyText(String value) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextColor(COLOR_SUB_TEXT);
        view.setTextSize(13);
        view.setLineSpacing(0, 1.12f);
        view.setPadding(0, 0, 0, dp(8));
        return view;
    }

    private Button compactActionButton(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(12);
        button.setTextColor(COLOR_TEXT);
        button.setMinHeight(0);
        button.setMinimumHeight(0);
        button.setPadding(0, 0, 0, 0);
        button.setOnClickListener(listener);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                0,
                dp(44),
                1);
        params.setMargins(dp(2), dp(4), dp(2), 0);
        button.setLayoutParams(params);
        return button;
    }

    private Button actionButton(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(14);
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
        button.setTextSize(11);
        button.setPadding(0, 0, 0, 0);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(42), 1);
        params.setMargins(dp(2), dp(4), dp(2), 0);
        button.setLayoutParams(params);
        if (selectedLogLevel == level) {
            button.setTextColor(level == null ? COLOR_PRIMARY : logLevelColor(level));
            button.setTypeface(Typeface.DEFAULT_BOLD);
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
