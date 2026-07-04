# Android Rust Shared Toolchain Design

## Background

`SoloX` currently stores Android and Rust build tooling under
`runtime/android-toolchain/` inside the repository. The build and packaging
scripts, Cargo vendor configuration, tests, and engineering docs all assume
that project-local location.

That layout has two problems on a personal development machine:

- Every repository must download and unpack the same JDK, Android SDK/NDK,
  Gradle, Rust sysroot, and Cargo vendor data again.
- Toolchain state is tied to a single project checkout instead of being reused
  across projects.

The current project must remain safe during the transition. If the shared
toolchain is missing or incomplete, `SoloX` must keep working with the existing
project-local toolchain.

## Goals

- Support a shared Android/Rust toolchain on one developer machine.
- Preserve current `SoloX` behavior when no shared toolchain is explicitly
  enabled.
- Allow future repositories to reuse the same directory layout directly.
- Avoid machine-wide `JAVA_HOME` or `ANDROID_HOME` changes.

## Non-goals

- No tool version upgrades in this change.
- No changes to APK contents, Rust crate versions, or Android build logic.
- No requirement to migrate every existing checkout immediately.

## Selected Approach

Use a dual-mode layout with explicit shared opt-in and safe fallback:

1. Support environment variable `SOLOX_SHARED_TOOLROOT`.
2. Support a canonical default shared path for manual use on Windows:
   `%LOCALAPPDATA%\SoloX\toolchains\android-rust`.
3. Keep `runtime/android-toolchain/` as the compatibility fallback for the
   current repository.
4. During the transition, build scripts prefer the project-local toolchain by
   default unless `SOLOX_SHARED_TOOLROOT` is set and passes validation.

## Toolchain Resolution Rules

All Android Agent scripts should resolve the toolchain root through one shared
PowerShell helper instead of hardcoding `runtime/android-toolchain`.

Resolution order:

1. If `SOLOX_SHARED_TOOLROOT` is set:
   - Validate the directory layout.
   - If valid, use it.
   - If invalid, print a warning and fall back to the project-local toolchain.
2. Otherwise, use `runtime/android-toolchain/`.

The helper should also expose the default shared path so bootstrap flows and
docs can point users to one stable machine-local location.

## Validation Contract

A shared toolchain is considered usable only if the expected key files exist,
including:

- `jdk-stage/.../bin/java.exe`
- `android-sdk/platforms/android-36/android.jar`
- `android-sdk/build-tools/36.0.0/aapt2.exe`
- `android-sdk/ndk/29.0.14206865/.../clang.cmd`
- `gradle-8.13/bin/gradle.bat`
- `downloads/rust/...`
- `downloads/cargo-vendor/`

This must be a real validation gate, not just a directory existence check.

## Cargo Compatibility Strategy

`.cargo/config.toml` currently points at the project-local vendor directory.
That is safe for existing `SoloX` users and should remain the default
compatibility contract.

When the resolved toolchain root is shared, the build script should inject the
shared `cargo-vendor` directory into `cargo build` explicitly so Cargo uses the
resolved toolchain without requiring a machine-global Cargo setup.

## Script Changes

### `scripts/android_agent/bootstrap.ps1`

- Add a shared toolchain helper import.
- Support installing into:
  - the project-local fallback root
  - an explicit shared root via `SOLOX_SHARED_TOOLROOT`
  - the canonical default shared path when requested
- Continue writing `android-agent/local.properties` for the selected SDK root.

### `scripts/android_agent/build.ps1`

- Resolve the effective toolchain root through the shared helper.
- Reuse the selected JDK, Android SDK/NDK, Gradle, Rust sysroot, and Cargo
  vendor directory from that root.
- Keep current cleanup and Gradle invocation behavior intact.

### `scripts/android_agent/package.ps1`

- No new toolchain logic beyond delegating to `build.ps1`.

## Test Changes

Tests must stop assuming the only valid toolchain path is
`runtime/android-toolchain`.

Add path-resolution helpers in tests so they:

- prefer `SOLOX_SHARED_TOOLROOT` when present and complete
- otherwise keep using the project-local toolchain

Contract tests should also assert that build scripts mention the shared
toolchain environment variable and keep the project-local fallback path.

## Documentation Changes

Update engineering docs and script docs to describe:

- shared toolchain as the recommended personal-machine setup
- `runtime/android-toolchain/` as compatibility fallback
- `SOLOX_SHARED_TOOLROOT` as the opt-in switch
- the canonical default shared path for Windows users

## Risks And Mitigations

### Risk: shared path exists but is incomplete

Mitigation:

- validate required files before use
- warn and fall back to project-local toolchain

### Risk: Cargo still reads the old vendored source path

Mitigation:

- keep the committed project-local config for backward compatibility
- inject the resolved vendor directory from the build script when using a
  shared toolchain

### Risk: tests become host-dependent

Mitigation:

- centralize test-side toolchain resolution
- continue supporting project-local layout so current CI and local clones do
  not regress

## Approval Summary

Approved constraints from the user:

- shared toolchain is for one personal development machine
- the current `SoloX` project must not be broken during the migration
- transition policy is project-local first, shared toolchain opt-in second
