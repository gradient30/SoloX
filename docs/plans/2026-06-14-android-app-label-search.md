# Android App Label Search Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add reliable Android application-name display and search without blocking package selection or breaking package-name fallback.

**Architecture:** `/device/package` remains the fast package-list endpoint and returns package metadata from cached labels only. A new Android-only label endpoint resolves requested package labels asynchronously, preferring cached values and using local `aapt dump badging` against pulled APKs when available, with `dumpsys` as a best-effort fallback. The frontend renders package names immediately, then patches visible options with resolved labels and uses a two-line Select2 template to prevent overflow.

**Tech Stack:** Flask, ADB, optional Android SDK `aapt`, jQuery, Select2, pytest.

---

### Task 1: Backend Fast Package Metadata

**Files:**
- Modify: `solox/public/common.py`
- Modify: `solox/view/apis.py`
- Test: `tests/test_android_app_selection.py`

**Steps:**
1. Add failing tests showing `getAndroidPackages()` does not invoke slow full `dumpsys package` and marks unresolved labels as pending.
2. Add a failing API test for `/device/package/labels`.
3. Implement cached-only package item rendering for `/device/package`.
4. Implement `resolveAndroidPackageLabels(deviceId, package_names)` with cache, package path lookup, optional `aapt`, and fallback to package name.
5. Run `python -m pytest tests/test_android_app_selection.py -q`.

### Task 2: Frontend Async Label Hydration

**Files:**
- Modify: `solox/templates/index.html`
- Test: `tests/test_frontend_performance.py`

**Steps:**
1. Add failing static/runtime tests for Select2 custom templates, two-line truncation classes, label hydration endpoint use, and app-name search data.
2. Render package options immediately with `data-label-pending`.
3. Add `resolveAndroidPackageLabels()` to request labels for visible packages after list render.
4. Patch option text, `data-label`, `data-display`, and `data-search` when labels arrive; preserve current selection.
5. Run `python -m pytest tests/test_frontend_performance.py -q`.

### Task 3: Verification

**Files:**
- Modify: `docs/acceptance/joint-review-2026-compatibility.md`

**Steps:**
1. Update acceptance matrix counts and risk notes.
2. Run targeted tests: `python -m pytest tests/test_android_app_selection.py tests/test_frontend_performance.py -q`.
3. Run full suite: `python -m pytest -q`.
4. Run compatibility validation: `python scripts/validate_compatibility_matrix.py`.
5. Restart service and verify Android page in the browser.
