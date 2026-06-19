# Android VPN Weak Network Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a verifiable Android non-root weak-network engine based on `VpnService`, retain the current root `tc/netem` engine, and provide a gateway calibration contract.

**Architecture:** SoloX selects a weak-network engine through a common Python interface. The Android agent captures only the selected application with `VpnService`; a Rust `ShapedDevice` applies packet-level uplink/downlink impairment before the packets enter the pinned `tun2proxy` direct TCP/UDP stack. SoloX controls the agent through an ADB-forwarded local abstract socket and never silently changes engines.

**Tech Stack:** Python 3.10+, Flask, pytest, Kotlin, Android SDK 36, AGP 8.13.0, Gradle 8.13, JDK 17, Rust 1.85+, Android NDK 29.0.14206865, tun2proxy v0.8.2 (`eed123fbbec06295bf83f9be36d5a0f64ed9a8cb`, MIT).

---

## Delivery Boundaries

The implementation is divided into two release gates.

**Gate A: Preview**

- Existing root behavior remains compatible.
- Agent install, VPN authorization, start, status, stop and recovery work.
- IPv4/IPv6 TCP and UDP forwarding works in direct mode.
- Fixed delay, jitter, random loss and bandwidth limits work independently in both directions.
- Only one target package is captured.
- The UI labels Agent mode as Preview.

**Gate B: Stable**

- Android 8/11/13/15/16 matrix passes.
- TCP, UDP, QUIC, DNS, IPv4 and IPv6 pass gateway comparison.
- 16 KB page-size device/emulator passes.
- Agent overhead and accuracy meet the design thresholds.

Gate A must not be advertised as Stable before Gate B evidence exists.

### Task 1: Python Profile Model and Engine Contract

**Files:**

- Create: `solox/public/weaknet/__init__.py`
- Create: `solox/public/weaknet/models.py`
- Create: `solox/public/weaknet/engine.py`
- Create: `solox/public/weaknet/root_tc.py`
- Modify: `solox/public/weak_network.py`
- Modify: `tests/test_weak_network.py`

**Step 1: Write failing profile tests**

Add tests proving:

```python
def test_legacy_profile_maps_to_both_directions():
    profile = WeakNetworkProfile.from_legacy(
        delay_ms=200,
        jitter_ms=50,
        loss_pct=2,
        rate="5mbit",
    )
    assert profile.uplink.delay_ms == 200
    assert profile.downlink.delay_ms == 200
    assert profile.uplink.bandwidth_kbps == 5000


def test_profile_rejects_invalid_loss():
    with pytest.raises(ValueError, match="loss"):
        DirectionProfile(loss_pct=101)
```

Cover rate parsing for `kbit`, `mbit`, integers and `None`.

**Step 2: Verify the tests fail**

Run:

```powershell
python -m pytest tests/test_weak_network.py -q
```

Expected: import failure because `solox.public.weaknet.models` does not exist.

**Step 3: Implement immutable models**

Implement:

```python
@dataclass(frozen=True)
class DirectionProfile:
    delay_ms: int = 0
    jitter_ms: int = 0
    loss_pct: float = 0.0
    bandwidth_kbps: int | None = None
    burst_loss_pct: float = 0.0


@dataclass(frozen=True)
class WeakNetworkProfile:
    uplink: DirectionProfile
    downlink: DirectionProfile
    protocol: Literal["all", "tcp", "udp"] = "all"
    ip_filter: tuple[str, ...] = ()
```

Validate values in `__post_init__`. Keep `WEAKNET_PRESETS` output compatible.

Define `WeakNetworkEngine` as a `Protocol` with `capabilities`, `apply`, `status` and `clear`.

Move existing root commands into `RootTcWeakNetworkEngine` without changing command strings or current public responses.

Keep `solox/public/weak_network.py` as the compatibility facade.

**Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/test_weak_network.py -q
```

Expected: all weak-network tests pass.

**Step 5: Run the complete Python suite**

Run:

```powershell
python -m pytest -q
```

Expected: 100% pass with only the existing warnings.

**Step 6: Commit**

```powershell
git add solox/public/weaknet solox/public/weak_network.py tests/test_weak_network.py
git commit -m "refactor: introduce weak network engine contract"
```

### Task 2: Android Agent Host Controller

**Files:**

- Create: `solox/public/weaknet/agent.py`
- Create: `solox/public/weaknet/agent_protocol.py`
- Create: `solox/public/android_agent/README.md`
- Create: `solox/public/android_agent/.gitkeep`
- Create: `tests/test_weaknet_agent.py`
- Modify: `MANIFEST.in`
- Modify: `pyproject.toml`

**Step 1: Write failing controller tests**

Use a small fake ADB adapter, not global command mocks, to prove:

- Missing APK returns `available=False` without installing anything.
- Installed version is read from `dumpsys package`.
- `install()` invokes `adb install -r` only after an explicit call.
- `prepare()` starts `io.solox.networkagent/.MainActivity`.
- ADB forwarding uses `localabstract:solox.networkagent.control`.
- JSON line responses reject unknown schema versions.
- `apply()` does not report active unless the returned session and profile digest match.
- Socket timeout triggers a stop attempt and a clear error.

Desired API:

```python
controller = AndroidAgentController(adb_client, apk_path)
controller.capabilities(device_id)
controller.install(device_id)
controller.prepare(device_id)
controller.apply(device_id, target_package, profile)
controller.status(device_id)
controller.clear(device_id)
```

**Step 2: Verify the tests fail**

Run:

```powershell
python -m pytest tests/test_weaknet_agent.py -q
```

Expected: module import failure.

**Step 3: Implement the controller**

Implement a versioned JSON-line protocol:

```json
{"schema_version":1,"request_id":"uuid","command":"status","payload":{}}
```

Responses:

```json
{"schema_version":1,"request_id":"uuid","ok":true,"payload":{},"error":null}
```

Use a random free local TCP port and:

```text
adb -s SERIAL forward tcp:PORT localabstract:solox.networkagent.control
```

Always remove the forwarding rule in `finally`.

Do not automatically install, start an Activity or request VPN permission from `capabilities()`.

**Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_weaknet_agent.py tests/test_weak_network.py -q
```

Expected: all pass.

**Step 5: Commit**

```powershell
git add solox/public/weaknet solox/public/android_agent tests/test_weaknet_agent.py MANIFEST.in pyproject.toml
git commit -m "feat: add Android weak network agent controller"
```

### Task 3: Engine Selection and API Compatibility

**Files:**

- Modify: `solox/public/weak_network.py`
- Modify: `solox/view/apis.py`
- Modify: `tests/test_weak_network.py`
- Modify: `tests/test_joint_acceptance.py`

**Step 1: Write failing selection tests**

Cover:

- `engine=agent` requires the installed and authorized Agent.
- `engine=root_tc` retains current behavior.
- `engine=auto` selects an already authorized healthy Agent first.
- `engine=auto` falls back to root only before a test starts.
- An Agent start failure never silently continues using root.
- Legacy preset calls still work.
- `target_package` is required for Agent mode.
- Separate uplink/downlink API fields are parsed.

Expected normalized response:

```json
{
  "status": 1,
  "engine": "agent",
  "active": true,
  "target_package": "com.example.app",
  "session_id": "uuid",
  "profile": {}
}
```

**Step 2: Verify failure**

Run:

```powershell
python -m pytest tests/test_weak_network.py tests/test_joint_acceptance.py -q
```

Expected: failures for unsupported arguments and missing endpoints.

**Step 3: Implement selection and APIs**

Extend:

- `/apm/weaknet/capabilities`
- `/apm/weaknet/status`
- `/apm/weaknet/apply`
- `/apm/weaknet/clear`

Add:

- `/apm/weaknet/agent/status`
- `/apm/weaknet/agent/install`
- `/apm/weaknet/agent/prepare`

Use `request.values` consistently so GET and POST remain compatible.

**Step 4: Verify**

Run:

```powershell
python -m pytest tests/test_weak_network.py tests/test_weaknet_agent.py tests/test_joint_acceptance.py -q
python -m pytest -q
```

Expected: all pass.

**Step 5: Commit**

```powershell
git add solox/public/weak_network.py solox/view/apis.py tests
git commit -m "feat: integrate Android agent weak network APIs"
```

### Task 4: Reproducible Android Toolchain and Project Skeleton

**Files:**

- Create: `android-agent/settings.gradle.kts`
- Create: `android-agent/build.gradle.kts`
- Create: `android-agent/gradle.properties`
- Create: `android-agent/gradle/wrapper/gradle-wrapper.properties`
- Create: `android-agent/gradlew`
- Create: `android-agent/gradlew.bat`
- Create: `android-agent/app/build.gradle.kts`
- Create: `android-agent/app/proguard-rules.pro`
- Create: `android-agent/app/src/main/AndroidManifest.xml`
- Create: `scripts/android_agent/bootstrap.ps1`
- Create: `scripts/android_agent/build.ps1`
- Create: `tests/test_android_agent_project.py`

**Step 1: Write failing project contract tests**

Use Python tests to assert:

- `compileSdk` and `targetSdk` are 36.
- `minSdk` is 21.
- AGP is pinned to 8.13.0.
- Gradle wrapper is pinned to 8.13 with a distribution checksum.
- NDK is pinned to `29.0.14206865`.
- Package ID is `io.solox.networkagent`.
- Release ABI filters contain `arm64-v8a`; debug also contains `x86_64`.
- The manifest declares `BIND_VPN_SERVICE`, required foreground-service permissions and no dangerous unrelated permissions.

**Step 2: Verify failure**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py -q
```

Expected: missing project files.

**Step 3: Create pinned project files**

Use:

- AGP `8.13.0`
- Gradle `8.13`
- Kotlin Android plugin `2.1.20`
- JDK 17
- Android SDK 36
- NDK `29.0.14206865`

The bootstrap script downloads tools into `runtime/android-toolchain/`, which is ignored, and verifies published SHA-256 values before extraction.

Do not alter machine-level `JAVA_HOME` or `ANDROID_HOME`.

**Step 4: Verify project contracts**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py -q
```

Expected: pass.

**Step 5: Bootstrap and build the empty Agent**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/bootstrap.ps1
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 testDebugUnitTest assembleDebug
```

Expected: Gradle exits 0 and produces a debug APK.

**Step 6: Commit**

```powershell
git add android-agent scripts/android_agent tests/test_android_agent_project.py
git commit -m "build: add reproducible Android agent project"
```

### Task 5: Kotlin Protocol and VPN State Machine

**Files:**

- Create: `android-agent/app/src/main/java/io/solox/networkagent/protocol/AgentCommand.kt`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/protocol/AgentResponse.kt`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/model/WeakNetworkProfile.kt`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/state/AgentState.kt`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/state/AgentStateStore.kt`
- Create: `android-agent/app/src/test/java/io/solox/networkagent/ProtocolTest.kt`
- Create: `android-agent/app/src/test/java/io/solox/networkagent/AgentStateStoreTest.kt`

**Step 1: Write failing Kotlin tests**

Cover:

- Schema version 1 round-trip.
- Unknown schema version rejection.
- Invalid profile values.
- Only legal state transitions:
  `idle -> permission_required -> starting -> active -> stopping -> idle`.
- A stale heartbeat transitions to stopping.
- State persistence never stores packet payloads.

**Step 2: Verify tests fail**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 testDebugUnitTest
```

Expected: compilation failure for missing classes.

**Step 3: Implement the minimal model and state machine**

Use `kotlinx.serialization` with explicit `schema_version` names. Keep serialization independent of Android framework classes so unit tests run on the JVM.

**Step 4: Verify tests**

Run the same Gradle command.

Expected: all unit tests pass.

**Step 5: Commit**

```powershell
git add android-agent
git commit -m "feat: add agent protocol and lifecycle state machine"
```

### Task 6: Rust Packet Shaper

**Files:**

- Create: `android-agent/native/Cargo.toml`
- Create: `android-agent/native/Cargo.lock`
- Create: `android-agent/native/src/lib.rs`
- Create: `android-agent/native/src/config.rs`
- Create: `android-agent/native/src/shaper.rs`
- Create: `android-agent/native/src/device.rs`
- Create: `android-agent/native/src/counters.rs`
- Create: `android-agent/native/tests/shaper_test.rs`

**Step 1: Write failing deterministic Rust tests**

Use a fake clock and seeded RNG to prove:

- Zero profile is pass-through.
- Uplink and downlink profiles are independent.
- A packet selected for loss is consumed but not forwarded.
- Fixed delay never releases early.
- Jitter is bounded.
- Token-bucket bandwidth converges within 10%.
- Queue memory has a fixed maximum and reports overflow drops.
- IPv4 and IPv6 packet metadata is classified without reading payload content.

**Step 2: Verify failure**

Run:

```powershell
cargo test --manifest-path android-agent/native/Cargo.toml
```

Expected: missing modules or tests fail.

**Step 3: Implement the shaper**

`ShapedDevice<D>` implements:

```rust
impl<D> AsyncRead for ShapedDevice<D>
where
    D: AsyncRead + AsyncWrite + Unpin
```

Reads from the Android TUN are uplink. Writes to the Android TUN are downlink.

The wrapper must preserve packet boundaries, apply loss before the `tun2proxy` IP stack sees uplink packets, and report accepted downlink writes while scheduling or dropping complete packets. Counters are atomic and contain only lengths, protocol and direction.

**Step 4: Verify Rust tests**

Run:

```powershell
cargo fmt --manifest-path android-agent/native/Cargo.toml --check
cargo clippy --manifest-path android-agent/native/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path android-agent/native/Cargo.toml
```

Expected: all pass.

**Step 5: Commit**

```powershell
git add android-agent/native
git commit -m "feat: add deterministic bidirectional packet shaper"
```

### Task 7: Pin tun2proxy Direct Stack and JNI

**Files:**

- Modify: `android-agent/native/Cargo.toml`
- Modify: `android-agent/native/src/lib.rs`
- Create: `android-agent/native/src/runtime.rs`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/nativebridge/NativeTunnel.kt`
- Create: `android-agent/app/src/test/java/io/solox/networkagent/NativeArgumentsTest.kt`
- Modify: `scripts/android_agent/build.ps1`
- Create: `docs/06-engineering/android-agent-third-party.md`

**Step 1: Write failing argument and supply-chain tests**

Assert:

- Direct mode always uses `proxy=none`.
- IPv6 is enabled when the VPN has an IPv6 route.
- DNS strategy is direct.
- Maximum sessions and timeouts are bounded.
- `Cargo.lock` pins tun2proxy to commit `eed123fbbec06295bf83f9be36d5a0f64ed9a8cb`.
- MIT license text and source URL are documented.

**Step 2: Verify failure**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py -q
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 testDebugUnitTest
```

Expected: missing native bridge/metadata failures.

**Step 3: Integrate tun2proxy**

Pin:

```toml
tun2proxy = {
  git = "https://github.com/tun2proxy/tun2proxy.git",
  rev = "eed123fbbec06295bf83f9be36d5a0f64ed9a8cb",
  default-features = false
}
```

The native runtime:

1. Reconstructs the VPN TUN file descriptor with `close_fd_on_drop=false`.
2. Wraps it in `ShapedDevice`.
3. Calls public `tun2proxy::run()` with `ArgProxy::try_from("none")`.
4. Stores a cancellation token for stop.
5. Exposes counters and the last native error over JNI.

Do not use tun2proxy's upstream hard-coded Shadowsocks JNI class.

**Step 4: Cross-compile**

The build script installs Rust Android targets and builds:

- `aarch64-linux-android`
- `x86_64-linux-android`

Copy libraries into generated `jniLibs` directories. Do not commit `target/`.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 native testDebugUnitTest assembleDebug
```

Expected: APK contains both native ABIs and all ELF LOAD segments meet 16 KB alignment requirements.

**Step 5: Commit**

```powershell
git add android-agent scripts/android_agent docs/06-engineering/android-agent-third-party.md
git commit -m "feat: integrate pinned tun2proxy direct stack"
```

### Task 8: VpnService and ADB Control Socket

**Files:**

- Create: `android-agent/app/src/main/java/io/solox/networkagent/MainActivity.kt`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/vpn/SoloXVpnService.kt`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/control/ControlSocketServer.kt`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/control/CommandDispatcher.kt`
- Create: `android-agent/app/src/main/java/io/solox/networkagent/notification/AgentNotification.kt`
- Create: `android-agent/app/src/androidTest/java/io/solox/networkagent/VpnConfigurationTest.kt`
- Create: `android-agent/app/src/test/java/io/solox/networkagent/CommandDispatcherTest.kt`
- Modify: `android-agent/app/src/main/AndroidManifest.xml`

**Step 1: Write failing command tests**

Cover:

- `status` never starts the VPN.
- `start` rejects missing or non-installed target package.
- `start` returns `permission_required` when `VpnService.prepare()` is non-null.
- A second session first clears the old one.
- `stop` is idempotent.
- Session/profile digest must match.
- Heartbeat timeout stops the tunnel.
- Unknown commands do not change state.

**Step 2: Verify tests fail**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 testDebugUnitTest
```

Expected: missing dispatcher/service classes.

**Step 3: Implement the control plane**

Bind a local abstract Unix socket named:

```text
solox.networkagent.control
```

The socket accepts only one request per connection, caps request length, enforces a timeout, and never accepts file paths or shell commands.

**Step 4: Implement VpnService**

Configure:

- IPv4 TUN address and default route.
- IPv6 TUN address and default route.
- DNS from the active physical network with safe fallback.
- MTU 1500.
- `addAllowedApplication(targetPackage)`.
- Foreground notification before native startup.

The Agent package itself must not be added to the allowed list, so native direct sockets stay outside the VPN.

Only report `active` after the TUN descriptor and native runtime are running.

**Step 5: Run unit and instrumentation tests**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 testDebugUnitTest assembleDebug
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 connectedDebugAndroidTest
```

Expected: JVM tests pass; instrumentation tests pass when a device is attached.

**Step 6: Commit**

```powershell
git add android-agent
git commit -m "feat: implement Android VPN agent control plane"
```

### Task 9: Web UI Preview Flow

**Files:**

- Modify: `solox/templates/index.html`
- Modify: `tests/test_joint_acceptance.py`

**Step 1: Write failing acceptance tests**

Assert rendered HTML contains:

- Engine selector: Auto, Agent Preview, Root tc.
- Agent installation status.
- Explicit Install and Authorize buttons.
- Selected package passed as `target_package`.
- Separate uplink/downlink fields.
- Emergency network restore.

Assert page initialization does not call Agent install or prepare endpoints.

**Step 2: Verify failure**

Run:

```powershell
python -m pytest tests/test_joint_acceptance.py -q
```

Expected: missing controls and request parameters.

**Step 3: Implement UI**

Reuse the current selected Android package.

Rules:

- Disable Agent Apply until a package is selected and authorization is ready.
- Never prompt during page initialization.
- Display the exact active engine.
- Display Agent as Preview.
- Keep existing controls and root workflow usable.
- Emergency restore calls clear and then refreshes status.

**Step 4: Verify**

Run:

```powershell
python -m pytest tests/test_joint_acceptance.py tests/test_weak_network.py tests/test_weaknet_agent.py -q
python -m pytest -q
```

Expected: all pass.

**Step 5: Commit**

```powershell
git add solox/templates/index.html tests/test_joint_acceptance.py
git commit -m "feat: add Android agent weak network preview UI"
```

### Task 10: APK Packaging and Integrity

**Files:**

- Modify: `scripts/android_agent/build.ps1`
- Create: `scripts/android_agent/package.ps1`
- Create: `solox/public/android_agent/checksums.json`
- Modify: `tests/test_android_agent_project.py`
- Modify: `MANIFEST.in`
- Modify: `pyproject.toml`

**Step 1: Write failing packaging tests**

Assert:

- Bundled APK filename is versioned.
- `checksums.json` includes version, SHA-256, package ID and minimum protocol version.
- Python controller rejects an APK whose digest differs.
- Wheel package data includes APK and checksum metadata.

**Step 2: Verify failure**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py tests/test_weaknet_agent.py -q
```

Expected: missing checksum/package failures.

**Step 3: Implement package task**

Build a release APK, copy it to:

```text
solox/public/android_agent/solox-network-agent-<version>.apk
```

Generate metadata deterministically. Do not commit debug APKs.

**Step 4: Verify packaging**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/android_agent/package.ps1
python -m build
python -m pytest tests/test_android_agent_project.py tests/test_weaknet_agent.py -q
```

Inspect the wheel archive and verify the APK digest.

**Step 5: Commit**

```powershell
git add scripts/android_agent solox/public/android_agent MANIFEST.in pyproject.toml tests
git commit -m "build: bundle verified Android network agent"
```

### Task 11: Gateway Calibration Contract

**Files:**

- Create: `scripts/weaknet_gateway/apply.sh`
- Create: `scripts/weaknet_gateway/clear.sh`
- Create: `scripts/weaknet_gateway/status.sh`
- Create: `scripts/weaknet_gateway/README.md`
- Create: `tests/test_weaknet_gateway_scripts.py`

**Step 1: Write failing script tests**

Validate generated commands include:

- Egress root qdisc.
- Ingress redirect to IFB.
- Separate ingress/egress netem rules.
- IPv4 and IPv6 forwarding prerequisites.
- Idempotent clear.
- Refusal to operate on an empty or loopback interface.

**Step 2: Verify failure**

Run:

```powershell
python -m pytest tests/test_weaknet_gateway_scripts.py -q
```

Expected: missing scripts.

**Step 3: Implement scripts**

Use explicit arguments and no `eval`. Include a dry-run mode used by tests.

**Step 4: Verify**

Run:

```powershell
python -m pytest tests/test_weaknet_gateway_scripts.py -q
```

Expected: pass.

**Step 5: Commit**

```powershell
git add scripts/weaknet_gateway tests/test_weaknet_gateway_scripts.py
git commit -m "feat: add Linux gateway weak network calibration scripts"
```

### Task 12: Real-Device Acceptance Harness

**Files:**

- Create: `scripts/android_agent/acceptance.py`
- Create: `tests/integration/test_android_agent_device.py`
- Modify: `docs/acceptance/joint-review-2026-compatibility.md`
- Modify: `docs/04-user-guides/api-documentation.md`
- Modify: `docs/01-architecture/technical-architecture.md`
- Modify: `docs/06-engineering/project-layout.md`

**Step 1: Write harness unit tests**

Test parsing and threshold decisions from stored sample measurements:

- Baseline RTT overhead.
- Bandwidth accuracy.
- UDP loss confidence interval.
- TCP retransmission evidence.
- IPv6 leak detection.
- Recovery after USB disconnect.

**Step 2: Verify failure**

Run:

```powershell
python -m pytest tests/integration/test_android_agent_device.py -q
```

Expected: missing harness.

**Step 3: Implement harness**

The harness must:

- Refuse to run without an explicitly selected device and package.
- Record device, OS, APK version, engine and configuration.
- Run baseline first.
- Exercise TCP and UDP test endpoints.
- Save raw evidence under `report/weaknet-acceptance-*`.
- Always clear the Agent in `finally`.

**Step 4: Run complete automated gates**

Run:

```powershell
python -m pytest -q
python scripts/validate_compatibility_matrix.py
cargo fmt --manifest-path android-agent/native/Cargo.toml --check
cargo clippy --manifest-path android-agent/native/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path android-agent/native/Cargo.toml
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 testDebugUnitTest assembleDebug
```

Expected: every command exits 0.

**Step 5: Run first connected-device smoke**

Run:

```powershell
python scripts/android_agent/acceptance.py `
  --device ecc3b00e `
  --package <selected-test-package> `
  --profile lte_weak `
  --smoke
```

The user manually accepts Android's VPN consent dialog. The harness then verifies start, traffic, counters, stop and network recovery.

**Step 6: Run gateway comparison before Stable**

Run the full harness against the same profile using Agent and gateway modes. Record deviations and do not promote the Agent to Stable if any mandatory threshold fails.

**Step 7: Commit**

```powershell
git add scripts/android_agent tests/integration docs
git commit -m "test: add Android weak network real-device acceptance"
```

## Final Verification

Run fresh:

```powershell
git status --short
python -m pytest -q
python scripts/validate_compatibility_matrix.py
cargo test --manifest-path android-agent/native/Cargo.toml
powershell -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 testDebugUnitTest assembleDebug
```

Then inspect:

```powershell
git diff main...HEAD --check
git log --oneline main..HEAD
```

Do not claim Gate A complete until the connected Android device has:

- Installed the bundled APK.
- Granted VPN consent.
- Forwarded real TCP and UDP traffic.
- Demonstrated non-zero shaped packet counters.
- Cleared the VPN and restored normal networking.

