#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Android 录屏 E2E 验收入口（P2-T1）；实现见 ``accept_record_gate.py``。

用法::

    python scripts/accept_record_e2e.py
    python scripts/accept_record_e2e.py --duration 65 --quality 720p
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from accept_record_gate import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
