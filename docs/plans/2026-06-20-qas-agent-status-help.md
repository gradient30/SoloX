# QAS Agent Status Help Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add truthful status feedback, stronger visual hierarchy, colored logs, and a help dialog to QAS Network Agent.

**Architecture:** Keep the no-dependency native Java Android app. Add a small SharedPreferences-backed UI state store shared by `MainActivity` and `SoloXVpnService`; the service writes lifecycle and tunnel state, while the activity reads it and presents status cards, operation feedback, and help content.

**Tech Stack:** Android Java, VpnService, SharedPreferences, AlertDialog, Gradle Android Plugin 8.13.0, pytest source-contract tests.

---

### Task 1: Add Failing UI Contract Tests

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/tests/test_android_agent_project.py`
- Modify: `D:/workDir/githubwork/SoloX/tests/test_android_agent_control_plane.py`

**Step 1: Write failing tests**

Add assertions that `MainActivity.java` contains:

```python
for text in ('授权状态', '服务状态', '隧道状态', '最近操作'):
    assert text in activity
for text in ('▶ 启动', '■ 停止', '⟳ 刷新', '⚙ VPN', '?'):
    assert text in activity
assert 'showHelpDialog' in activity
assert '目标 App → Android VPN → QAS Agent' in activity
assert 'VPN 图标只会在真实 VPN 隧道建立后出现' in activity
assert 'Settings.ACTION_VPN_SETTINGS' in activity
```

Add assertions that log colors exist:

```python
for symbol in ('logLevelColor', 'AgentLogLevel.ERROR', 'AgentLogLevel.WARN', 'AgentLogLevel.INFO', 'AgentLogLevel.DEBUG'):
    assert symbol in activity
```

Add assertions that service state persistence exists:

```python
state = read('app/src/main/java/io/solox/networkagent/state/AgentUiState.java')
service = read('app/src/main/java/io/solox/networkagent/vpn/SoloXVpnService.java')
assert 'SharedPreferences' in state
assert 'markServiceRunning' in service
assert 'markTunnelActive' in service
assert 'markTunnelIdle' in service
assert 'markServiceStopped' in service
```

**Step 2: Verify RED**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py tests/test_android_agent_control_plane.py -k "status_feedback or operational_console" -q
```

Expected: FAIL because status store, help dialog, and updated UI strings do not exist yet.

### Task 2: Add Shared UI State Store

**Files:**
- Create: `D:/workDir/githubwork/SoloX/android-agent/app/src/main/java/io/solox/networkagent/state/AgentUiState.java`
- Modify: `D:/workDir/githubwork/SoloX/android-agent/app/src/main/java/io/solox/networkagent/vpn/SoloXVpnService.java`

**Step 1: Implement state store**

Create `AgentUiState` with:

- `markServiceRunning(Context)`
- `markServiceStopped(Context)`
- `markTunnelActive(Context, String targetPackage)`
- `markTunnelIdle(Context)`
- `markError(Context, String message)`
- `recordOperation(Context, String message)`
- `Snapshot read(Context)`

Snapshot fields:

- `serviceRunning`
- `tunnelActive`
- `targetPackage`
- `lastOperation`
- `lastError`
- `updatedAtMs`

**Step 2: Wire service lifecycle**

In `SoloXVpnService`:

- `onCreate`: `AgentUiState.markServiceRunning(this)`
- `onDestroy`: `AgentUiState.markServiceStopped(this)`
- tunnel start success: `AgentUiState.markTunnelActive(this, targetPackage)`
- `stopTunnel`: `AgentUiState.markTunnelIdle(this)`
- native/control errors: `AgentUiState.markError(this, "...")`

**Step 3: Run focused tests**

Run:

```powershell
python -m pytest tests/test_android_agent_control_plane.py -q
```

Expected: PASS after UI implementation is complete; may still fail until Task 3.

### Task 3: Redesign Overview Feedback And Buttons

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java`

**Step 1: Implement status cards**

Update total overview to show:

- `授权状态`
- `服务状态`
- `隧道状态`
- `最近操作`
- VPN icon explanation

Use `AgentUiState.read(this)` and `VpnService.prepare(this)`.

**Step 2: Implement action feedback**

Button behavior:

- `▶ 启动`: record operation, request authorization/start service, redraw.
- `■ 停止`: record operation, stop service, mark stopped, redraw.
- `⟳ 刷新`: record operation, redraw.
- `⚙ VPN`: open `Settings.ACTION_VPN_SETTINGS`, fallback to `Settings.ACTION_SETTINGS`.

**Step 3: Keep buttons compact**

Use a horizontal row with equal-width buttons; allow vertical fallback if needed.

### Task 4: Improve Logs And Help Dialog

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java`

**Step 1: Add help button**

Top title bar includes `?`; clicking calls `showHelpDialog`.

**Step 2: Add help content**

Dialog includes non-technical explanation and chain:

```text
目标 App → Android VPN → QAS Agent → tun2proxy → SOCKS5 弱网整形 → 真实网络
```

**Step 3: Color log levels**

Render logs as cells with `logLevelColor(AgentLogLevel)` and smaller message text.

### Task 5: Verify And Package

**Files:**
- Public APK: `D:/workDir/githubwork/SoloX/solox/public/android_agent/qas-network-agent-0.1.0.apk`
- Metadata: `D:/workDir/githubwork/SoloX/solox/public/android_agent/checksums.json`

**Step 1: Run tests**

```powershell
python -m pytest tests/test_android_agent_project.py tests/test_android_agent_control_plane.py tests/test_android_agent_native_integration.py -q
```

**Step 2: Build and package**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1
powershell -ExecutionPolicy Bypass -File scripts/android_agent/package.ps1
```

**Step 3: Verify APK identity**

```powershell
runtime/android-toolchain/android-sdk/build-tools/36.0.0/aapt2.exe dump badging solox/public/android_agent/qas-network-agent-0.1.0.apk
```

Expected:

- package `io.solox.networkagent`
- label `QAS Network Agent`

**Step 4: Device smoke when available**

Install and launch:

```powershell
D:/softDir/adt-bundle-windows/sdk/platform-tools/adb.exe -s ecc3b00e install -r solox/public/android_agent/qas-network-agent-0.1.0.apk
D:/softDir/adt-bundle-windows/sdk/platform-tools/adb.exe -s ecc3b00e shell monkey -p io.solox.networkagent -c android.intent.category.LAUNCHER 1
```

Check UI dump for:

- `授权状态`
- `服务状态`
- `隧道状态`
- `最近操作`
- `?`
- `VPN 图标只会在真实 VPN 隧道建立后出现`

### Task 6: Commit

**Files:**
- Docs plan/design.
- Tests.
- Java sources.
- Public APK and checksum.

**Step 1: Inspect**

```powershell
git diff --stat
git status --short
```

**Step 2: Commit**

```powershell
git add docs/plans/2026-06-20-qas-agent-status-help-design.md docs/plans/2026-06-20-qas-agent-status-help.md tests/test_android_agent_project.py tests/test_android_agent_control_plane.py android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java android-agent/app/src/main/java/io/solox/networkagent/vpn/SoloXVpnService.java android-agent/app/src/main/java/io/solox/networkagent/state/AgentUiState.java solox/public/android_agent/qas-network-agent-0.1.0.apk solox/public/android_agent/checksums.json
git commit -m "feat(android-agent): improve status feedback help"
```
