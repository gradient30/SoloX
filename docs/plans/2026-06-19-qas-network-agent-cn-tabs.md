# QAS Network Agent Chinese 4 Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert the Android Agent APK from a demo-like English dashboard into a Chinese, mobile-native 4 Tab terminal-agent console.

**Architecture:** Keep the existing no-dependency native Java Android app. Rebuild `MainActivity` around a vertical root layout with a top title bar, a scrollable content area, and a bottom Tab Bar that swaps four first-level pages: overview, weak-network, logs, and settings. Keep protocol identifiers and runtime control logic unchanged.

**Tech Stack:** Android Java, VpnService, foreground service notification, Gradle Android Plugin 8.13.0, pytest source-contract tests, bundled Android SDK build tools.

---

### Task 1: Add Source Contract Tests

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/tests/test_android_agent_project.py`
- Test: `D:/workDir/githubwork/SoloX/tests/test_android_agent_project.py`

**Step 1: Write the failing test**

Add tests that read `MainActivity.java`, `AndroidManifest.xml`, and `AgentNotification.java` and assert:

```python
def test_android_agent_main_ui_is_chinese_four_tab_console():
    activity = read('app/src/main/java/io/solox/networkagent/MainActivity.java')
    for text in ('总览', '弱网', '日志', '设置'):
        assert text in activity
    assert 'Demo' not in activity
    assert 'demo' not in activity
    assert 'renderOverviewPage' in activity
    assert 'renderWeakNetworkPage' in activity
    assert 'renderLogsPage' in activity
    assert 'renderSettingsPage' in activity
    assert 'requestVpnAuthorization' in activity
    assert 'selectedLogLevel' in activity
```

Add a second test for localization boundaries:

```python
def test_android_agent_user_visible_copy_is_chinese_with_allowed_protocol_terms():
    manifest = read('app/src/main/AndroidManifest.xml')
    notification = read('app/src/main/java/io/solox/networkagent/notification/AgentNotification.java')
    activity = read('app/src/main/java/io/solox/networkagent/MainActivity.java')
    assert 'QAS Network Agent' in manifest
    assert 'QAS Network Agent' in notification
    for text in ('弱网代理正在后台运行', '准备接收 SoloX 弱网控制', '授权并启动', '停止服务'):
        assert text in activity + notification
    for forbidden in ('Authorize VPN and start service', 'Target package', 'Weak network profile',
                      'Background service', 'Agent logs', 'No Agent logs recorded yet'):
        assert forbidden not in activity
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py -k "chinese_four_tab or user_visible_copy" -q
```

Expected: FAIL because the current `MainActivity` still uses the old English demo dashboard.

**Step 3: Commit**

Do not commit yet. Continue to Task 2 and commit tests with implementation after green.

### Task 2: Implement Chinese 4 Tab MainActivity

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java`
- Test: `D:/workDir/githubwork/SoloX/tests/test_android_agent_project.py`

**Step 1: Build minimal implementation**

Replace the single scroll dashboard with:

- Top title bar: `QAS 弱网代理`
- Content area: `ScrollView`
- Bottom Tab Bar: `总览`、`弱网`、`日志`、`设置`
- Page render methods:
  - `renderOverviewPage`
  - `renderWeakNetworkPage`
  - `renderLogsPage`
  - `renderSettingsPage`

Keep existing logic:

- `requestVpnAuthorization`
- `startAgentService`
- `stopAgentService`
- `refreshDashboard`
- `renderLogs`
- `selectedLogLevel`

**Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py -k "chinese_four_tab or user_visible_copy" -q
```

Expected: PASS.

### Task 3: Localize Notification Copy

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/android-agent/app/src/main/java/io/solox/networkagent/notification/AgentNotification.java`
- Test: `D:/workDir/githubwork/SoloX/tests/test_android_agent_project.py`

**Step 1: Implement notification copy**

Change user-visible notification copy:

```java
.setContentTitle("QAS Network Agent")
.setContentText("弱网代理正在后台运行")
```

Change channel description to Chinese while preserving channel id:

```java
"QAS 弱网代理前台服务"
```

**Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py -k "agent_uses_qas_product_identity or user_visible_copy" -q
```

Expected: PASS.

### Task 4: Build And Package APK

**Files:**
- Build output: `D:/workDir/githubwork/SoloX/android-agent/app/build/outputs/apk/release/app-release.apk`
- Public output: `D:/workDir/githubwork/SoloX/solox/public/android_agent/qas-network-agent-0.1.0.apk`

**Step 1: Run Android release build**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1
```

Expected: Gradle `assembleRelease` succeeds.

**Step 2: Package public APK**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/package.ps1
```

Expected: public APK and `checksums.json` update.

### Task 5: Verify End To End

**Files:**
- Test: `D:/workDir/githubwork/SoloX/tests/test_android_agent_project.py`
- Test: `D:/workDir/githubwork/SoloX/tests/test_android_agent_protocol.py`
- Test: `D:/workDir/githubwork/SoloX/tests/test_android_agent_control_plane.py`
- Test: `D:/workDir/githubwork/SoloX/tests/test_android_agent_native_integration.py`

**Step 1: Run Android Agent tests**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py tests/test_android_agent_protocol.py tests/test_android_agent_control_plane.py tests/test_android_agent_native_integration.py -q
```

Expected: PASS.

**Step 2: Verify APK identity**

Run:

```powershell
runtime/android-toolchain/android-sdk/build-tools/36.0.0/aapt2.exe dump badging solox/public/android_agent/qas-network-agent-0.1.0.apk
```

Expected:

- package name remains `io.solox.networkagent`
- application label remains `QAS Network Agent`
- icon is present

**Step 3: Install and launch on connected device when available**

Run:

```powershell
D:/softDir/adt-bundle-windows/sdk/platform-tools/adb.exe devices
D:/softDir/adt-bundle-windows/sdk/platform-tools/adb.exe -s ecc3b00e install -r solox/public/android_agent/qas-network-agent-0.1.0.apk
D:/softDir/adt-bundle-windows/sdk/platform-tools/adb.exe -s ecc3b00e shell monkey -p io.solox.networkagent 1
```

Expected: install success and app launches.

### Task 6: Commit Traceable Result

**Files:**
- Modified source/test/docs/public APK files from previous tasks.

**Step 1: Inspect diff**

Run:

```powershell
git diff --stat
git status --short
```

Expected: only Android Agent UI/localization tests, docs, and packaged APK metadata changed.

**Step 2: Commit**

Run:

```powershell
git add docs/plans/2026-06-19-qas-network-agent-cn-tabs-design.md docs/plans/2026-06-19-qas-network-agent-cn-tabs.md tests/test_android_agent_project.py android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java android-agent/app/src/main/java/io/solox/networkagent/notification/AgentNotification.java solox/public/android_agent/qas-network-agent-0.1.0.apk solox/public/android_agent/checksums.json
git commit -m "feat(android-agent): localize qas agent tabs"
```

Expected: commit succeeds on `main`.
