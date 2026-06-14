# Android App and Process Selection Design

**Date:** 2026-06-13

**Scope:** Android homepage app and process selection only. iOS package selection remains unchanged.

## Goals

1. Let users filter Android apps by third-party, system, or all packages.
2. Make app search friendlier by matching launcher label when available, while always falling back to package name.
3. Detect the current foreground Android app and reduce manual selection:
   - If exactly one foreground third-party app process is found, select app and process automatically.
   - If multiple matching foreground processes exist, select the app and show all processes for manual choice.
   - If no foreground third-party app is found, keep the existing manual flow.

## Design

### Android App Metadata

The backend will add an Android-only structured package list built from `pm list packages`:

- `package`: package name.
- `label`: launcher label when available, otherwise package name.
- `type`: `user` or `system`.
- `display`: `label (package)` when label differs from package, otherwise package.

`/device/package` and `/device/info` will keep returning the existing `pkgnames` array for compatibility, and will add `packages` for the new UI.

Package type will use Android package manager flags:

- `pm list packages -3 --user 0` for third-party packages.
- `pm list packages -s --user 0` for system packages.
- fallback to `pm list packages --user 0` when filtered commands fail.

Launcher labels are best-effort. The first implementation will avoid icon extraction and heavy APK parsing. If label lookup fails or is slow on a device, the UI still works with package-name search.

### Foreground Selection

The backend will expose an Android-only endpoint that resolves:

- current focused activity from `dumpsys window`;
- foreground package name from that activity;
- app metadata for that package;
- running processes from existing `getPid`.

The endpoint returns `status=1` only when the foreground package is a third-party app. System launcher, Settings, System UI, and unresolved foreground state return `status=0` with a message, so the frontend falls back to manual selection.

### Frontend Flow

The homepage will keep the current device and process selects and enhance only Android:

1. Default app filter: third-party.
2. Filter buttons or compact select: third-party / system / all.
3. App dropdown options store `data-label`, `data-package`, and `data-type`.
4. Select2 matcher searches both label and package.
5. After device initialization, call foreground selection once:
   - one process: select app and process;
   - multiple processes: select app, populate process list, leave process for manual choice;
   - no match: no forced selection.
6. When app selection changes, reuse existing `/package/pids` flow.

## Risk Controls

- Preserve existing API fields and existing package-name value submitted to collection APIs.
- Do not block initialization on label lookup or foreground lookup failure.
- Do not apply this flow to iOS.
- Do not extract or render app icons in this phase.
- Keep ADB command count modest; labels are best-effort and may be cached per request only.

## Acceptance

- Android package API supports `type=user|system|all` and returns structured `packages`.
- Existing clients reading only `pkgnames` still work.
- Frontend defaults to third-party apps and can switch to system/all.
- Searching by package name still works; searching by label works when label exists.
- Foreground third-party app auto-selects app and process when only one process exists.
- Foreground app with multiple processes selects the app and shows all process choices.
- System foreground app does not auto-select.
- Focused tests, full tests, and browser smoke pass.
