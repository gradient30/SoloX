# Recording MKV Remux Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Record Android game video reliably by writing MKV first and remuxing to browser-playable MP4.

**Architecture:** `Scrcpy.start_record()` validates ffmpeg availability, removes stale artifacts, and starts scrcpy with `--record=record.mkv --record-format=mkv`. `Scrcpy.stop_record()` gracefully stops scrcpy, waits for MKV, runs ffmpeg copy remux to `record.mp4`, validates MP4 `moov`, and leaves MKV only as system-player fallback when MP4 cannot be produced. Report video resolution prefers valid MP4 and marks MKV as not browser-playable.

**Tech Stack:** Python, Flask, scrcpy, ffmpeg, pytest.

---

### Task 1: Record Resolution Contracts

**Files:**
- Modify: `tests/test_record_player.py`
- Modify: `tests/test_joint_acceptance.py`
- Modify: `solox/public/common.py`

**Step 1: Write the failing test**

Add assertions that MKV resolves with `browser_playable=False` and MP4 remains preferred.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_record_player.py::TestResolveRecordVideo::test_mkv_browser_playable -q`

Expected: FAIL because current code marks MKV browser-playable.

**Step 3: Write minimal implementation**

Set the MKV `browser_playable` flag to `False`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_record_player.py tests/test_joint_acceptance.py::TestRecordPlayerAcceptance -q`

### Task 2: ffmpeg Detection and Start Guard

**Files:**
- Modify: `tests/test_record_player.py`
- Modify: `solox/public/common.py`
- Modify: `solox/view/apis.py`

**Step 1: Write the failing test**

Add tests for `_find_ffmpeg_binary()` search order and `start_record()` returning failure with a useful error when ffmpeg is missing.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_record_player.py -q`

Expected: FAIL because helpers do not exist and start does not guard ffmpeg.

**Step 3: Write minimal implementation**

Implement ffmpeg path lookup and expose `Scrcpy.last_record_error()` to the API.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_record_player.py -q`

### Task 3: MKV Recording and MP4 Remux

**Files:**
- Modify: `tests/test_record_player.py`
- Modify: `solox/public/common.py`

**Step 1: Write the failing test**

Add tests that `start_record()` uses `record.mkv` plus `--record-format=mkv`, and `stop_record()` invokes ffmpeg to create `record.mp4`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_record_player.py -q`

Expected: FAIL because current code records MP4 directly and never remuxes.

**Step 3: Write minimal implementation**

Change scrcpy record target to MKV and add `_remux_recording_to_mp4()`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_record_player.py -q`

### Task 4: Verification

**Files:**
- Modify: `docs/acceptance/joint-review-2026-compatibility.md`

**Step 1: Run focused tests**

Run: `python -m pytest tests/test_record_player.py tests/test_joint_acceptance.py::TestRecordPlayerAcceptance -q`

**Step 2: Run full suite**

Run: `python -m pytest -q`

**Step 3: Run syntax and whitespace checks**

Run: `python -m compileall -q solox`
Run: `git diff --check`

**Step 4: Hand off manual testing**

Provide the user with the expected manual test path and ffmpeg installation note.
