# Recording Health Status Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make long recording failures observable during collection and report recording failure reasons after collection.

**Architecture:** Keep the existing scrcpy single-file recorder. Add a status API backed by `Scrcpy` runtime metadata, update report generation to persist recorder errors, and add a small top-page UI poller for elapsed time and risk messaging.

**Tech Stack:** Flask routes in `solox/view/apis.py`, recorder state in `solox/public/common.py`, jQuery UI in `solox/templates/index.html`, pytest/unittest coverage.

---

### Task 1: Backend Recording State

**Files:**
- Modify: `solox/public/common.py`
- Test: `tests/test_record_player.py`

**Steps:**
1. Add failing tests for `Scrcpy.record_status()` returning running state, elapsed seconds, file size, risk level, and process-exited errors.
2. Run the focused test and confirm it fails.
3. Add metadata fields to `Scrcpy` and implement `record_status()`.
4. Run the focused test and confirm it passes.

### Task 2: Report Failure Reason

**Files:**
- Modify: `solox/public/common.py`
- Test: `tests/test_record_player.py`

**Steps:**
1. Add failing tests for zero-byte `record.mkv` producing a `record_error`.
2. Add `Scrcpy.record_result_error()` and patch `File.make_report()` to persist `record_error`.
3. Run focused tests.

### Task 3: Status API

**Files:**
- Modify: `solox/view/apis.py`
- Test: `tests/test_record_player.py`

**Steps:**
1. Add failing route test for `/apm/record/status`.
2. Implement the route.
3. Run focused tests.

### Task 4: Frontend Status

**Files:**
- Modify: `solox/templates/index.html`
- Test: `tests/test_frontend_performance.py`

**Steps:**
1. Add static tests for the recording status badge, timer, risk thresholds, and polling function.
2. Implement the top-page UI and polling lifecycle.
3. Run frontend tests.

### Task 5: Verification

**Commands:**
- `python -m pytest -q`
- `python -m compileall -q solox tests`
- `git diff --check`

Restart a single SoloX service instance after verification.
