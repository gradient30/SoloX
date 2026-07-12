# -*- coding: utf-8 -*-
"""accept_record_gate 纯函数单测（不跑真 scrcpy / adb）。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from accept_record_gate import (  # noqa: E402
    list_android_device_ids,
    should_run_record_accept,
    validate_record_file,
)


def _fake_mp4_payload(extra: bytes = b"") -> bytes:
    body = b"\x00" * 4 + b"ftyp" + b"isom" + extra
    body += b"\x00" * 2000 + b"moov" + b"\x00" * 64
    return body


class TestAcceptRecordGate(unittest.TestCase):

    def test_should_run_record_accept_default_off(self) -> None:
        self.assertFalse(should_run_record_accept({}))

    def test_should_run_record_accept_enabled(self) -> None:
        self.assertTrue(should_run_record_accept({"SOLOX_RECORD_ACCEPT": "1"}))

    def test_validate_record_file_rejects_missing(self) -> None:
        result = validate_record_file("/nonexistent/record.mp4")
        self.assertFalse(result["passed"])
        self.assertEqual(result["reason"], "file_not_found")

    def test_validate_record_file_rejects_empty(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as fh:
            fh.write(b"")
            path = fh.name
        try:
            result = validate_record_file(path)
            self.assertFalse(result["passed"])
            self.assertFalse(result["valid"])
        finally:
            os.unlink(path)

    def test_validate_record_file_accepts_fake_moov(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as fh:
            fh.write(_fake_mp4_payload())
            path = fh.name
        try:
            result = validate_record_file(path, min_duration_sec=0)
            self.assertTrue(result["valid"])
            self.assertTrue(result["passed"])
        finally:
            os.unlink(path)

    def test_validate_record_file_short_duration_fails(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as fh:
            fh.write(_fake_mp4_payload())
            path = fh.name
        try:
            with patch(
                "accept_record_gate.ffprobe_duration", return_value=10.0,
            ):
                result = validate_record_file(path, min_duration_sec=55.0)
            self.assertTrue(result["valid"])
            self.assertFalse(result["passed"])
            self.assertEqual(result["reason"], "duration_too_short")
        finally:
            os.unlink(path)

    def test_list_android_device_ids_parses_output(self) -> None:
        stdout = "List of devices attached\nabc123\tdevice\noffline\toffline\n"
        with patch("accept_record_gate.subprocess.run") as mock_run:
            mock_run.return_value.stdout = stdout
            mock_run.return_value.returncode = 0
            ids = list_android_device_ids(["adb", "devices"])
        self.assertEqual(ids, ["abc123"])


if __name__ == "__main__":
    unittest.main()
