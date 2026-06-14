# Android App Label Usability and Performance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep Android app choices on one line, preserve readable highlighted text, and avoid repeated slow APK label extraction across service restarts.

**Architecture:** Select2 options render the application name and package in one flex row with ellipsis, while the selected value remains application-name-only. Label lookup keeps the package-list endpoint non-blocking, prioritizes the selected or foreground package, and stores successful labels in a small persistent cache keyed by device and package.

**Tech Stack:** Flask, ADB, optional Android SDK `aapt`, jQuery, Select2, JSON cache, pytest.

---

### Task 1: UI Regression Coverage

**Files:**
- Modify: `tests/test_frontend_performance.py`
- Modify: `solox/templates/index.html`

**Steps:**
1. Add assertions for a single-line flex option layout.
2. Add assertions that highlighted label and package text use the highlighted option color.
3. Run the focused test and confirm it fails before changing the template.
4. Implement the minimal CSS and Select2 template change.
5. Re-run the focused test and confirm it passes.

### Task 2: Persistent Label Cache Coverage

**Files:**
- Modify: `tests/test_android_app_selection.py`
- Modify: `solox/public/common.py`
- Modify: `.gitignore`

**Steps:**
1. Add tests showing a successful label is written to persistent cache.
2. Add a test showing a new `Devices` instance can reuse the stored label without ADB or `aapt`.
3. Run the focused tests and confirm they fail before implementation.
4. Implement atomic JSON cache reads/writes under `runtime/cache`.
5. Ignore generated cache files and re-run the focused tests.

### Task 3: Resolution Priority

**Files:**
- Modify: `tests/test_frontend_performance.py`
- Modify: `solox/templates/index.html`

**Steps:**
1. Add a regression assertion that selected/foreground packages are moved to the front without discarding the remaining queue.
2. Run the focused test and confirm it fails.
3. Implement queue promotion and preserve the existing single-request ADB concurrency limit.
4. Re-run frontend tests.

### Task 4: Verification

**Files:**
- Modify: `docs/acceptance/joint-review-2026-compatibility.md`

**Steps:**
1. Run Android selection and frontend performance tests.
2. Run the full pytest suite and compatibility validator.
3. Restart the service.
4. Verify single-line layout, highlighted contrast, selected value, and cached reload behavior in the browser with a connected Android device.
