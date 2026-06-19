# QAS Network Agent Productization Design

## Goal

Productize the existing Android weak-network Agent into a test-department-ready APK named `QAS Network Agent`, while preserving the verified VPN data plane and making every delivery phase traceable and acceptable.

## Current Baseline

- The Android Agent already uses `VpnService` to capture the target application by package UID.
- The native data plane already uses `tun2proxy` plus the local SOCKS5 shaper.
- Real-device verification has confirmed `com.lyjz.chqsy.vivo` UID `10241` routes through VPN.
- Cleanup verification has confirmed no `tun0` or VPN residue remains after teardown.
- The current app UI is a single authorization prompt in `MainActivity`.
- The foreground service and `START_STICKY` service mode already provide the base for background operation.

## Naming Decision

The public product name becomes `QAS Network Agent`.

For this phase, keep the Android package ID as `io.solox.networkagent` and keep the control socket as `solox.networkagent.control`. These identifiers are already referenced by the SoloX controller, tests, ADB forwarding, and documentation. Changing them would expand the blast radius without improving the tester workflow.

Change only these externally visible surfaces:

- Android launcher label.
- Main screen title.
- Foreground notification title and channel name.
- Bundled APK file name and metadata.
- User-facing documentation references.

## Approach

Use a narrow Java-only Android implementation with no new runtime dependencies. The Agent UI will be built with native Android views so the existing Gradle dependency contract remains lightweight.

The design keeps the verified VPN/tun2proxy path untouched. Productization is layered around it through state presentation, local audit logs, packaging metadata, and icon assets.

## Agent UI

The main screen will become an operational console for testers:

- Header with product name, version, and protocol version.
- Status section showing `idle`, `permission_required`, `starting`, `active`, `stopping`, or `error`.
- VPN authorization and foreground-service/background status.
- Current session ID, target package, and weak-network profile summary when available.
- Action buttons for requesting VPN authorization, starting the foreground Agent service, stopping the Agent service, and refreshing status.
- Recent log preview with entry level, timestamp, source, and message.
- Dedicated log filter controls for `ERROR`, `WARN`, `INFO`, and `DEBUG`.

The UI should be dense and operational rather than marketing-like. It should help a test engineer answer: "Is the Agent alive, what app is affected, what profile is applied, and what went wrong?"

## Local Agent Logs

Add an in-process `AgentLogStore` with a bounded ring buffer.

Each log entry contains:

- Monotonic sequence number.
- Wall-clock timestamp.
- Level: `ERROR`, `WARN`, `INFO`, or `DEBUG`.
- Source: UI, service, control socket, dispatcher, VPN, native bridge.
- Message.

The log store is the traceability spine for the Agent. It records authorization requests, control socket lifecycle, start/stop commands, target package validation, VPN establishment, native tunnel failures, stale heartbeat transitions, cleanup, and service destruction.

For this phase, logs are kept local and bounded in memory. Export-to-report integration can follow after the UI proves useful on devices.

## Background Operation

Do not redesign the background model. The current service already calls `startForeground(...)` and returns `START_STICKY`.

Improve acceptance by exposing the state:

- UI shows whether the foreground service has been started.
- Notification title and content use `QAS Network Agent`.
- Logs record service start, stop, and cleanup.
- Tests assert the foreground-service contract remains present.

## Launcher Icon

Add Android adaptive launcher icons representing a small person pulling a network cable with both hands.

Acceptance criteria:

- `android:icon` and `android:roundIcon` are declared in the manifest.
- Foreground vector remains recognizable at launcher size.
- Background color is not a generic SoloX/demo placeholder.
- The asset is stored under normal Android `res/mipmap-*` or adaptive icon resource paths.

## Packaging

Change bundled APK naming from `solox-network-agent-<version>.apk` to `qas-network-agent-<version>.apk`.

Update package metadata so SoloX downloads and installs the new APK name while keeping the package ID `io.solox.networkagent`.

The old temporary install path `/data/local/tmp/solox-network-agent.apk` may remain as an implementation detail if tests rely on it. Public artifact names should use `qas-network-agent`.

## Branch Integration

The repository currently has:

- `main` as the working branch.
- A linked worktree for `codex/android-vpn-weaknet`.
- Dirty working tree changes on both worktrees.

Integration must be traceable:

1. Record the pre-integration status with `git status --short --branch` and `git worktree list`.
2. Commit productization work as focused commits on `main`.
3. Verify tests on `main`.
4. Merge or cherry-pick remaining `codex/android-vpn-weaknet` commits only after protecting current uncommitted work.
5. Verify tests again after integration.
6. Remove the linked worktree and delete `codex/android-vpn-weaknet` only after verification.

No branch deletion is acceptable until the merged `main` build and tests pass.

## Traceability And Acceptance Gates

### Gate 0: Baseline Capture

Evidence:

- `git status --short --branch`
- `git worktree list`
- Current Android Agent file inventory.

Acceptance:

- Existing dirty files are listed.
- Existing branch and worktree relationship is documented.
- No unrelated files are reverted.

### Gate 1: Contract Tests

Evidence:

- Failing tests first for product name, manifest icon declarations, APK artifact naming, log store behavior, and UI/service contract strings.

Acceptance:

- Each new behavior has a test that fails before implementation for the expected reason.

### Gate 2: Product Identity

Evidence:

- Manifest label.
- Notification title/channel text.
- Packaging script and metadata tests.

Acceptance:

- User-visible app name is `QAS Network Agent`.
- APK artifact starts with `qas-network-agent-`.
- Package ID remains `io.solox.networkagent`.

### Gate 3: Agent Logs

Evidence:

- Unit-level Java harness or Python contract test for bounded log buffer and level filtering.
- Source call sites in service, dispatcher, control socket, and UI.

Acceptance:

- Logs can be filtered by level.
- Recent entries survive within bounded memory.
- Key lifecycle events are recorded.

### Gate 4: Professional UI

Evidence:

- Source contract test for UI sections and labels.
- Android build output.
- Optional device screenshot after install.

Acceptance:

- UI no longer presents as a demo-only text prompt.
- Status, authorization, target package/session/profile summary, service controls, and log filter are visible.

### Gate 5: Background Operation

Evidence:

- Source contract test for `startForeground`, `START_STICKY`, service control, and notification copy.
- Device command evidence when available: `pidof`, `dumpsys activity services`, and VPN cleanup checks.

Acceptance:

- Existing foreground service behavior remains intact.
- UI and logs make background state inspectable.

### Gate 6: Icon

Evidence:

- Manifest icon references.
- Resource files under Android `res`.
- Build succeeds.

Acceptance:

- APK has a non-default launcher icon matching the requested small-person-and-network-cable concept.

### Gate 7: Main-Only Integration

Evidence:

- Test command output after integration.
- `git branch --all` and `git worktree list` output.

Acceptance:

- `main` contains the accepted work.
- The temporary development branch/worktree is removed only after verification.
- No unreviewed user changes are discarded.

## High-Value Follow-Up Requirements

After this phase, the most valuable test-department features are:

- Weak-network presets for 2G, 3G, 4G edge, subway, elevator, overseas high latency, jitter, packet loss, and intermittent reconnect.
- Session report integration that includes target app, profile, timestamps, traffic counters, error state, and Agent logs.
- One-click self-check for VPN permission, target package availability, native runtime, ADB forward, control socket, and cleanup residue.
- Historical session replay that reapplies the same package and weak-network profile.
- Evidence bundle export for defects, combining SoloX report data, Agent logs, profile config, and device metadata.

## Risks

- Changing package ID now would require broad updates across controller code, tests, docs, and installed-device cleanup flows.
- Android UI without AppCompat/Material means less built-in styling, but it preserves the current no-dependency Android shell.
- In-memory logs are simple and safe, but process death clears them. Report export can persist logs in a later phase.
- Deleting the development branch before verifying merged `main` could lose work because both worktrees are currently dirty.

## Non-Goals

- No redesign of the VPN/tun2proxy/native shaper path.
- No package ID migration.
- No cloud reporting backend.
- No persistent log database.
- No new Android UI framework dependency.
