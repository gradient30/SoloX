# QAS Network Agent Productization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the existing Android weak-network Agent demo shell into a traceable, test-department-ready `QAS Network Agent` APK.

**Architecture:** Preserve the verified `io.solox.networkagent` package, control socket, `VpnService`, and native tun2proxy data plane. Add product identity, local bounded Agent logs, a native Java operational console UI, adaptive icon resources, packaging metadata updates, and explicit acceptance evidence.

**Tech Stack:** Android Java views, Android foreground `VpnService`, Gradle Android plugin, Python contract tests, Java harness tests, PowerShell packaging scripts.

---

### Task 1: Capture Baseline Evidence

**Files:**
- Create: `docs/acceptance/qas-network-agent-productization-2026-06-19.md`

**Step 1: Record repository state**

Run:

```powershell
git status --short --branch
git worktree list
git branch --all --verbose --no-abbrev
```

Expected: `main` is current, existing dirty files are visible, and `codex/android-vpn-weaknet` appears as a linked worktree.

**Step 2: Create evidence ledger**

Create `docs/acceptance/qas-network-agent-productization-2026-06-19.md` with sections:

````markdown
# QAS Network Agent Productization Acceptance Evidence

## Gate 0: Baseline Capture

Commands:

```powershell
git status --short --branch
git worktree list
git branch --all --verbose --no-abbrev
```

Evidence:

- Pending capture.

Acceptance:

- Existing dirty files are listed.
- No unrelated user changes are reverted.
- Branch/worktree relationship is known before integration.
````

**Step 3: Commit**

Run:

```powershell
git add docs/acceptance/qas-network-agent-productization-2026-06-19.md
git commit -m "docs: capture qas network agent acceptance gates"
```

### Task 2: Add Failing Product Identity Tests

**Files:**
- Modify: `tests/test_android_agent_project.py`

**Step 1: Write failing tests**

Update expectations so current code fails for the new product name and artifact name:

```python
def test_android_agent_uses_qas_product_identity():
    manifest = read('app/src/main/AndroidManifest.xml')
    notification = read('app/src/main/java/io/solox/networkagent/notification/AgentNotification.java')
    activity = read('app/src/main/java/io/solox/networkagent/MainActivity.java')

    assert 'android:label="QAS Network Agent"' in manifest
    assert 'android:icon="@mipmap/ic_launcher"' in manifest
    assert 'android:roundIcon="@mipmap/ic_launcher_round"' in manifest
    assert 'QAS Network Agent' in notification
    assert 'QAS Network Agent' in activity


def test_android_agent_package_metadata_uses_qas_artifact_name():
    package_script = ROOT / 'scripts' / 'android_agent' / 'package.ps1'
    metadata_path = ROOT / 'solox' / 'public' / 'android_agent' / 'checksums.json'
    script = package_script.read_text(encoding='utf-8')
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))

    assert 'qas-network-agent-' in script
    assert 'solox-network-agent-' not in script
    assert metadata['package_id'] == 'io.solox.networkagent'
    assert metadata['apk'].startswith('qas-network-agent-')
```

Adjust existing package metadata assertions from `solox-network-agent-` to `qas-network-agent-`.

**Step 2: Verify RED**

Run:

```powershell
pytest tests/test_android_agent_project.py -q
```

Expected: FAIL because manifest, notification, package script, and metadata still contain `SoloX Network Agent` or `solox-network-agent`.

### Task 3: Implement Product Identity

**Files:**
- Modify: `android-agent/app/src/main/AndroidManifest.xml`
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java`
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/notification/AgentNotification.java`
- Modify: `scripts/android_agent/package.ps1`
- Modify: `solox/public/android_agent/checksums.json`
- Modify: `tests/test_android_agent_project.py`

**Step 1: Change user-visible name**

Set:

```xml
android:label="QAS Network Agent"
```

Keep:

```kotlin
applicationId = "io.solox.networkagent"
namespace = "io.solox.networkagent"
```

**Step 2: Update UI and notification copy**

Use `QAS Network Agent` for Activity title text, notification title, channel name, and channel description.

**Step 3: Update APK artifact name**

In `scripts/android_agent/package.ps1`, change:

```powershell
$apkName = "qas-network-agent-$version.apk"
```

Update `solox/public/android_agent/checksums.json` so `apk` starts with `qas-network-agent-`.

**Step 4: Verify GREEN**

Run:

```powershell
pytest tests/test_android_agent_project.py -q
```

Expected: PASS.

**Step 5: Commit**

Run:

```powershell
git add android-agent/app/src/main/AndroidManifest.xml `
  android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java `
  android-agent/app/src/main/java/io/solox/networkagent/notification/AgentNotification.java `
  scripts/android_agent/package.ps1 `
  solox/public/android_agent/checksums.json `
  tests/test_android_agent_project.py
git commit -m "feat(android-agent): rename public app to qas network agent"
```

### Task 4: Add Failing Icon Contract Tests

**Files:**
- Modify: `tests/test_android_agent_project.py`

**Step 1: Write failing test**

Add:

```python
def test_android_agent_declares_custom_launcher_icon_resources():
    manifest = read('app/src/main/AndroidManifest.xml')
    assert 'android:icon="@mipmap/ic_launcher"' in manifest
    assert 'android:roundIcon="@mipmap/ic_launcher_round"' in manifest

    required = [
        AGENT / 'app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml',
        AGENT / 'app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml',
        AGENT / 'app/src/main/res/drawable/ic_launcher_foreground.xml',
        AGENT / 'app/src/main/res/drawable/ic_launcher_background.xml',
    ]
    for path in required:
        assert path.is_file(), path

    foreground = required[2].read_text(encoding='utf-8')
    assert 'network cable' in foreground.lower()
    assert 'person' in foreground.lower()
```

**Step 2: Verify RED**

Run:

```powershell
pytest tests/test_android_agent_project.py::test_android_agent_declares_custom_launcher_icon_resources -q
```

Expected: FAIL because `res` icon files do not exist.

### Task 5: Implement Launcher Icon Resources

**Files:**
- Modify: `android-agent/app/src/main/AndroidManifest.xml`
- Create: `android-agent/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`
- Create: `android-agent/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml`
- Create: `android-agent/app/src/main/res/drawable/ic_launcher_foreground.xml`
- Create: `android-agent/app/src/main/res/drawable/ic_launcher_background.xml`

**Step 1: Add manifest references**

Set:

```xml
android:icon="@mipmap/ic_launcher"
android:roundIcon="@mipmap/ic_launcher_round"
```

**Step 2: Add adaptive icon XML**

Create adaptive icon files referencing background and foreground drawables.

**Step 3: Add vector icon foreground**

Create a vector drawable that includes an XML comment containing:

```xml
<!-- person pulling network cable with both hands -->
```

The vector should use simple paths for a small person and left/right cable lines so it remains buildable without bitmap generation.

**Step 4: Verify GREEN**

Run:

```powershell
pytest tests/test_android_agent_project.py::test_android_agent_declares_custom_launcher_icon_resources -q
```

Expected: PASS.

**Step 5: Build check**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 --offline assembleRelease
```

Expected: Android build succeeds, or any missing local toolchain dependency is recorded in the evidence ledger.

**Step 6: Commit**

Run:

```powershell
git add android-agent/app/src/main/AndroidManifest.xml android-agent/app/src/main/res tests/test_android_agent_project.py
git commit -m "feat(android-agent): add qas launcher icon"
```

### Task 6: Add Failing Agent Log Store Tests

**Files:**
- Modify: `tests/test_android_agent_control_plane.py`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/logging/AgentLogLevel.java`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/logging/AgentLogEntry.java`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/logging/AgentLogStore.java`

**Step 1: Write Java harness test first**

Add a Python test that writes and compiles `AgentLogStoreHarness.java`:

```java
import io.solox.networkagent.logging.AgentLogEntry;
import io.solox.networkagent.logging.AgentLogLevel;
import io.solox.networkagent.logging.AgentLogStore;

public final class AgentLogStoreHarness {
    public static void main(String[] args) {
        AgentLogStore store = new AgentLogStore(3);
        store.record(AgentLogLevel.INFO, "ui", "created", 100L);
        store.record(AgentLogLevel.WARN, "vpn", "slow", 200L);
        store.record(AgentLogLevel.ERROR, "native", "failed", 300L);
        store.record(AgentLogLevel.DEBUG, "socket", "accepted", 400L);

        check(store.recent(null).size() == 3, "bounded to latest entries");
        check(store.recent(AgentLogLevel.ERROR).size() == 1, "filters errors");
        AgentLogEntry last = store.recent(null).get(2);
        check(last.sequence() == 4L, "sequence increments");
        check(last.message().equals("accepted"), "keeps latest message");
        check(store.toJson(AgentLogLevel.WARN).contains("\"level\":\"WARN\""), "json includes level");
    }

    private static void check(boolean condition, String label) {
        if (!condition) {
            throw new AssertionError(label);
        }
    }
}
```

Compile sources including the three logging classes.

**Step 2: Verify RED**

Run:

```powershell
pytest tests/test_android_agent_control_plane.py::test_agent_log_store_bounds_entries_and_filters_by_level -q
```

Expected: FAIL because logging classes do not exist.

### Task 7: Implement Agent Log Store

**Files:**
- Create: `android-agent/app/src/main/java/io/solox/networkagent/logging/AgentLogLevel.java`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/logging/AgentLogEntry.java`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/logging/AgentLogStore.java`
- Modify: `tests/test_android_agent_control_plane.py`

**Step 1: Implement enum**

```java
package io.solox.networkagent.logging;

public enum AgentLogLevel {
    ERROR, WARN, INFO, DEBUG
}
```

**Step 2: Implement immutable entry**

Fields: `sequence`, `timestampMs`, `level`, `source`, `message`; expose simple getters.

**Step 3: Implement bounded store**

Use synchronized methods and an `ArrayDeque<AgentLogEntry>`.

Methods:

- `record(AgentLogLevel level, String source, String message, long timestampMs)`
- `recent(AgentLogLevel minimumOrExactLevel)`
- `toJson(AgentLogLevel minimumOrExactLevel)`

For this phase, use exact-level filtering when a level is provided.

**Step 4: Verify GREEN**

Run:

```powershell
pytest tests/test_android_agent_control_plane.py::test_agent_log_store_bounds_entries_and_filters_by_level -q
```

Expected: PASS.

**Step 5: Commit**

Run:

```powershell
git add android-agent/app/src/main/java/io/solox/networkagent/logging tests/test_android_agent_control_plane.py
git commit -m "feat(android-agent): add bounded local log store"
```

### Task 8: Add Failing Service Logging Contract Tests

**Files:**
- Modify: `tests/test_android_agent_control_plane.py`

**Step 1: Add source-level contract test**

Assert that:

- `SoloXVpnService` creates an `AgentLogStore`.
- `CommandDispatcher` accepts or uses a log store.
- `ControlSocketServer` records accept/request failures.
- `MainActivity` reads logs for display.

Example assertions:

```python
assert 'AgentLogStore' in service
assert 'record(AgentLogLevel.INFO' in service
assert 'record(AgentLogLevel.ERROR' in service
assert 'AgentLogStore' in dispatcher
assert 'AgentLogStore' in socket
assert 'renderLogs' in activity
```

**Step 2: Verify RED**

Run:

```powershell
pytest tests/test_android_agent_control_plane.py::test_android_agent_records_traceable_lifecycle_logs -q
```

Expected: FAIL because services are not wired to the log store yet.

### Task 9: Wire Lifecycle Logs

**Files:**
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/vpn/SoloXVpnService.java`
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/control/CommandDispatcher.java`
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/control/ControlSocketServer.java`
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java`

**Step 1: Share log store**

Add a process-local holder or singleton accessor, for example `AgentRuntime`.

If a holder is needed:

- Create: `android-agent/app/src/main/java/io/solox/networkagent/runtime/AgentRuntime.java`
- It exposes `public static AgentLogStore logs()`.

**Step 2: Record key events**

Record at least:

- Service created.
- Control socket started.
- Control socket accept failure.
- Request dispatch start command.
- Permission required.
- Target package missing.
- VPN tunnel start success.
- Native tunnel start failure.
- Stop/cleanup.
- Service destroyed.

**Step 3: Verify GREEN**

Run:

```powershell
pytest tests/test_android_agent_control_plane.py::test_android_agent_records_traceable_lifecycle_logs -q
```

Expected: PASS.

**Step 4: Commit**

Run:

```powershell
git add android-agent/app/src/main/java/io/solox/networkagent tests/test_android_agent_control_plane.py
git commit -m "feat(android-agent): record traceable lifecycle logs"
```

### Task 10: Add Failing Professional UI Contract Tests

**Files:**
- Modify: `tests/test_android_agent_control_plane.py`

**Step 1: Add source-level UI test**

Assert `MainActivity.java` contains operational sections:

```python
assert 'renderDashboard' in activity
assert 'Status' in activity
assert 'VPN authorization' in activity
assert 'Target package' in activity
assert 'Weak network profile' in activity
assert 'Background service' in activity
assert 'Agent logs' in activity
assert 'ERROR' in activity
assert 'WARN' in activity
assert 'INFO' in activity
assert 'DEBUG' in activity
assert 'requestVpnAuthorization' in activity
assert 'stopService' in activity
```

**Step 2: Verify RED**

Run:

```powershell
pytest tests/test_android_agent_control_plane.py::test_main_activity_renders_professional_agent_console -q
```

Expected: FAIL because Activity is still a single `TextView`.

### Task 11: Implement Agent Console UI

**Files:**
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java`
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/state/AgentStateStore.java` if snapshot helpers are needed.
- Modify: `android-agent/app/src/main/java/io/solox/networkagent/runtime/AgentRuntime.java` if created.

**Step 1: Replace single TextView with native layout**

Build a `ScrollView` containing a vertical `LinearLayout`.

Sections:

- Header: `QAS Network Agent`.
- Status row.
- VPN authorization row.
- Background service row.
- Target package row.
- Weak network profile row.
- Action row: authorize/start service, stop service, refresh.
- Segmented level filter row using simple `Button`s.
- Logs list.

**Step 2: Keep controls simple**

Use native `Button`, `TextView`, and `LinearLayout`. Do not add AppCompat or Material dependencies.

**Step 3: Render logs**

Implement:

- `renderDashboard()`
- `renderLogs()`
- `setLogFilter(AgentLogLevel level)`

**Step 4: Verify GREEN**

Run:

```powershell
pytest tests/test_android_agent_control_plane.py::test_main_activity_renders_professional_agent_console -q
```

Expected: PASS.

**Step 5: Commit**

Run:

```powershell
git add android-agent/app/src/main/java/io/solox/networkagent/MainActivity.java
git commit -m "feat(android-agent): add operational console UI"
```

### Task 12: Verify Background Operation Contract

**Files:**
- Modify: `tests/test_android_agent_control_plane.py`

**Step 1: Extend existing background test**

Assert:

```python
assert 'startForeground' in service
assert 'START_STICKY' in service
assert 'startForegroundService' in activity
assert 'stopService' in activity
assert 'QAS Network Agent' in notification
assert 'Background service' in activity
```

**Step 2: Run targeted test**

Run:

```powershell
pytest tests/test_android_agent_control_plane.py::test_android_agent_has_authorization_service_and_control_socket_files -q
```

Expected: PASS after UI/service updates.

**Step 3: Commit if test-only adjustments were needed**

Run:

```powershell
git add tests/test_android_agent_control_plane.py
git commit -m "test(android-agent): verify background operation contract"
```

### Task 13: Update Documentation And Public References

**Files:**
- Modify: `docs/04-user-guides/weak-network-testing.md`
- Modify: `docs/06-engineering/weak-network-tooling.md`
- Modify: `solox/public/android_agent/README.md`
- Modify: any references found by `rg "SoloX Network Agent|solox-network-agent"`

**Step 1: Find references**

Run:

```powershell
rg "SoloX Network Agent|solox-network-agent" docs solox scripts tests android-agent -n
```

**Step 2: Update user-facing references**

Use `QAS Network Agent` and `qas-network-agent-<version>.apk` for public docs.

Keep protocol/package references unchanged:

- `io.solox.networkagent`
- `solox.networkagent.control`

**Step 3: Run docs-sensitive tests**

Run:

```powershell
pytest tests/test_android_agent_project.py tests/test_weaknet_agent.py -q
```

Expected: PASS.

**Step 4: Commit**

Run:

```powershell
git add docs solox/public/android_agent/README.md tests
git commit -m "docs(android-agent): document qas network agent packaging"
```

### Task 14: Run Full Relevant Verification

**Files:**
- Modify: `docs/acceptance/qas-network-agent-productization-2026-06-19.md`

**Step 1: Run Python tests**

Run:

```powershell
pytest tests/test_android_agent_project.py tests/test_android_agent_control_plane.py tests/test_android_agent_protocol.py tests/test_android_agent_native_integration.py tests/test_weaknet_agent.py -q
```

Expected: PASS.

**Step 2: Run Android build**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 --offline assembleRelease
```

Expected: PASS if local toolchain is complete. If it fails due missing local SDK/JDK cache, record the exact failure in the evidence ledger.

**Step 3: Optional real-device acceptance**

If a device is attached, run:

```powershell
adb devices
adb install -r solox/public/android_agent/qas-network-agent-0.1.0.apk
adb shell monkey -p io.solox.networkagent 1
adb shell pidof io.solox.networkagent
adb shell dumpsys activity services io.solox.networkagent
```

Capture screenshots if available.

**Step 4: Update evidence ledger**

Record command, date, result, and known gaps for every gate.

**Step 5: Commit**

Run:

```powershell
git add docs/acceptance/qas-network-agent-productization-2026-06-19.md
git commit -m "docs: record qas network agent acceptance evidence"
```

### Task 15: Integrate Development Branch Into Main

**Files:**
- No direct file edits unless merge conflicts require resolution.

**Step 1: Re-check state**

Run:

```powershell
git status --short --branch
git worktree list
git rev-list --left-right --count main...codex/android-vpn-weaknet
```

Expected: Current uncommitted changes are known. Do not delete or overwrite them.

**Step 2: Protect current work**

If productization changes are committed and unrelated dirty files remain, leave them in place unless they block merge. If they block merge, stop and list conflicting files.

**Step 3: Merge or cherry-pick**

Prefer merge if it is clean:

```powershell
git merge codex/android-vpn-weaknet
```

If merge is blocked by dirty files, do not force it. Use a temporary integration worktree or ask for direction.

**Step 4: Verify after integration**

Run:

```powershell
pytest tests/test_android_agent_project.py tests/test_android_agent_control_plane.py tests/test_android_agent_protocol.py tests/test_android_agent_native_integration.py tests/test_weaknet_agent.py -q
```

Expected: PASS.

**Step 5: Remove branch only after verification**

Run:

```powershell
git worktree remove D:\workDir\githubwork\SoloX\.worktrees\android-vpn-weaknet
git branch -d codex/android-vpn-weaknet
git branch --all
git worktree list
```

Expected: only `main` remains locally for this work, and no linked Android weaknet worktree remains.

### Task 16: Final Acceptance Report

**Files:**
- Modify: `docs/acceptance/qas-network-agent-productization-2026-06-19.md`

**Step 1: Add final checklist**

Checklist:

- Product name is `QAS Network Agent`.
- APK artifact is `qas-network-agent-<version>.apk`.
- Package ID remains `io.solox.networkagent`.
- Control socket remains `solox.networkagent.control`.
- UI has operational console sections.
- Logs support level filtering.
- Foreground/background service contract remains.
- Launcher icon resources exist.
- Relevant tests pass or blocked commands are recorded.
- Branch integration status is recorded.

**Step 2: Commit final evidence**

Run:

```powershell
git add docs/acceptance/qas-network-agent-productization-2026-06-19.md
git commit -m "docs: finalize qas network agent acceptance report"
```

## Traceability Summary

Every implementation task must leave one of these evidence types:

- A failing test before implementation.
- A passing test after implementation.
- A build command result.
- A device command result.
- A committed evidence note explaining why verification could not run locally.

No phase is accepted on source inspection alone unless the evidence ledger explicitly marks it as a source-contract gate.
