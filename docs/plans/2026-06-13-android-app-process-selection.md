# Android App and Process Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve Android homepage app/process selection with app type filters, label-aware search, and foreground app auto-selection.

**Architecture:** Add Android package metadata helpers in `Devices`, expose compatible API fields from `solox/view/apis.py`, then enhance `index.html` to render structured options and call a foreground selection endpoint. Existing package-name values and collection APIs stay unchanged.

**Tech Stack:** Flask, jQuery, Select2, ADB package manager commands, pytest, Node-based static/runtime frontend tests.

---

### Task 1: Backend Package Metadata Tests

**Files:**
- Modify: `tests/test_apm_collect_api.py`
- Modify: `solox/public/common.py`
- Modify: `solox/view/apis.py`

**Steps:**
1. Add failing tests for `/device/package?platform=Android&type=user` returning both `pkgnames` and structured `packages`.
2. Add failing tests for type fallback and legacy `pkgnames` compatibility.
3. Implement `Devices.getAndroidPackages(deviceId, package_type='all')`.
4. Update `/device/package` and `/device/info` to include `packages` for Android.
5. Run focused tests.

### Task 2: Foreground Selection Tests

**Files:**
- Modify: `tests/test_apm_collect_api.py`
- Modify: `solox/public/common.py`
- Modify: `solox/view/apis.py`

**Steps:**
1. Add failing tests for foreground third-party app with one process.
2. Add failing tests for foreground third-party app with multiple processes.
3. Add failing tests for foreground system app returning non-auto-select result.
4. Implement Android foreground package helper and `/package/foreground`.
5. Run focused tests.

### Task 3: Frontend Selection Contract Tests

**Files:**
- Modify: `tests/test_frontend_performance.py`
- Modify: `solox/templates/index.html`

**Steps:**
1. Add failing static tests for app type filter UI, structured option rendering, Select2 matcher, and foreground auto-select calls.
2. Add helper functions in `index.html`: render app options, filter package list, select foreground result.
3. Keep existing manual selection behavior.
4. Run frontend tests.

### Task 4: Full Verification

**Files:**
- No production edits expected.

**Steps:**
1. Run `python -m pytest tests/test_apm_collect_api.py tests/test_frontend_performance.py -q`.
2. Run `python -m pytest -q`.
3. Run `python scripts/validate_compatibility_matrix.py`.
4. Run `python -m compileall -q solox`.
5. Start local service and browser-smoke homepage.
