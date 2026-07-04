# Android Rust Shared Toolchain Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an opt-in shared Android/Rust toolchain path for a personal
development machine while keeping the current project-local toolchain behavior
as the safe default fallback.

**Architecture:** Introduce one PowerShell toolchain resolver used by Android
Agent bootstrap/build/package scripts, keep the committed project-local Cargo
config as a compatibility fallback, and inject the resolved vendor directory
into cargo invocations when a shared toolchain is selected.

**Tech Stack:** PowerShell, Cargo, Gradle, pytest source-contract tests, repo
documentation.

---

### Task 1: Add failing contract tests for shared toolchain resolution

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/tests/test_android_agent_project.py`
- Modify: `D:/workDir/githubwork/SoloX/tests/test_android_agent_control_plane.py`
- Modify: `D:/workDir/githubwork/SoloX/tests/test_android_agent_protocol.py`

**Step 1: Write the failing test**

Add tests that require:

- script text to reference `SOLOX_SHARED_TOOLROOT`
- script text to keep `runtime/android-toolchain` as fallback
- Python-side toolchain helpers to prefer a valid shared root and otherwise use
  the project-local root
- Java harness tests to resolve `javac` and `java` through that helper instead
  of a hardcoded project-local path

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py tests/test_android_agent_control_plane.py tests/test_android_agent_protocol.py -q
```

Expected: FAIL because shared toolchain resolution does not exist yet.

### Task 2: Add a shared toolchain resolver for Android scripts

**Files:**
- Create: `D:/workDir/githubwork/SoloX/scripts/android_agent/toolchain.ps1`
- Modify: `D:/workDir/githubwork/SoloX/scripts/android_agent/bootstrap.ps1`
- Modify: `D:/workDir/githubwork/SoloX/scripts/android_agent/build.ps1`
- Modify: `D:/workDir/githubwork/SoloX/scripts/android_agent/package.ps1`

**Step 1: Write minimal implementation**

Create a shared PowerShell helper that:

- exposes the project-local tool root
- exposes the canonical shared tool root under `%LOCALAPPDATA%`
- resolves the active tool root from `SOLOX_SHARED_TOOLROOT` with validation
- falls back to `runtime/android-toolchain` when the shared root is invalid

Update bootstrap/build/package scripts to import and use that helper.

**Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py -q
```

Expected: PASS for script-path contract tests, with Java harness tests possibly
still failing until Task 3 finishes.

### Task 3: Support shared Cargo vendor resolution without breaking fallback mode

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/scripts/android_agent/build.ps1`
- Modify: `D:/workDir/githubwork/SoloX/.cargo/config.toml`

**Step 1: Implement vendor directory injection**

Keep `.cargo/config.toml` compatible with the project-local toolchain, and make
`build.ps1` pass the resolved vendor directory into `cargo build` when the
shared toolchain root is selected.

**Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py tests/test_android_agent_protocol.py tests/test_android_agent_control_plane.py -q
```

Expected: PASS.

### Task 4: Update developer documentation for shared toolchains

**Files:**
- Modify: `D:/workDir/githubwork/SoloX/scripts/README.md`
- Modify: `D:/workDir/githubwork/SoloX/docs/06-engineering/weak-network-tooling.md`
- Modify: `D:/workDir/githubwork/SoloX/docs/06-engineering/android-agent-third-party.md`
- Modify: `D:/workDir/githubwork/SoloX/runtime/README.md`

**Step 1: Update docs**

Document:

- `SOLOX_SHARED_TOOLROOT`
- `%LOCALAPPDATA%\\SoloX\\toolchains\\android-rust`
- project-local fallback behavior
- expectation that the current repo remains usable without shared setup

**Step 2: Run doc-adjacent tests if any**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py -q
```

Expected: PASS.

### Task 5: Verify end-to-end regression safety

**Files:**
- Verify only

**Step 1: Run targeted verification**

Run:

```powershell
python -m pytest tests/test_android_agent_project.py tests/test_android_agent_native_integration.py tests/test_android_agent_control_plane.py tests/test_android_agent_protocol.py -q
```

Expected: PASS.

**Step 2: Run build verification if environment is available**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 native assembleDebug
```

Expected: build succeeds using the project-local fallback unless
`SOLOX_SHARED_TOOLROOT` is configured and valid.
