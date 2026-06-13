# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SoloX is a real-time mobile performance data collection tool for Android and iOS. It runs as a Flask web server that communicates with devices via ADB (Android) and tidevice (iOS) to collect CPU, Memory, FPS, Network, Battery, GPU, Disk, and Thermal metrics.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install in dev mode with test/lint tools
pip install -e ".[dev,test]"

# Run the server (default: http://<local-ip>:50003)
python -m solox
python -m solox --host=0.0.0.0 --port=50005  # custom host/port

# Debug mode (runs from solox/ dir with Flask debug=True)
cd solox && python debug.py

# Run tests
python -m pytest tests/ -v --cov=solox

# Release gate (matrix + full pytest)
bash scripts/release_gate.sh

# Dev server (background)
bash scripts/dev.sh start   # logs → runtime/logs/

# Health probe
curl http://127.0.0.1:50003/health

# Lint
flake8 solox/ --count --select=E9,F63,F7,F82 --show-source --statistics

# Format
black solox/
isort solox/

# Build package
python -m build
```

## Architecture

### Entry Points
- `solox/__main__.py` → calls `solox.web.main()` via `fire.Fire`
- `solox/web.py` → Creates Flask app, spawns two processes: `start()` (Flask server) and `open_url()` (browser launcher)
- `solox/debug.py` → Debug entry point, runs Flask with `debug=True` (uses relative imports from `view/`)

### Web Layer (`solox/view/`)
- `pages.py` — Flask Blueprint for HTML pages (index, report, analysis, PK comparison). Report page uses AJAX pagination (`/apm/report/list`).
- `apis.py` — Flask Blueprint for REST API endpoints (`/apm/cpu`, `/apm/fps`, `/apm/memory`, `/apm/report/list`, `/apm/logcat/*`, `/apm/record/cast`, etc.)
- API endpoints create metric collector objects from `solox/public/apm.py`, call their `get*()` methods, return JSON

### Performance Collection (`solox/public/`)
- `apm.py` — Metric classes: `CPU`, `Memory`, `FPS`, `GPU`, `Battery`, `Network`, `Energy`, `Disk`, `ThermalSensor`. Each wraps platform-specific collection. `FPS.getObject()` is a singleton factory for Android FPS.
- `apm_pk.py` — PK (comparison) mode: `CPU_PK`, `MEM_PK`, `Flow_PK`, `FPS_PK` for dual-device/dual-app benchmarking
- `android_fps.py` — Android FPS collection engine. Key classes:
  - `GameSurfaceDetector` — Detects game engine surfaces (Unity/UE4/5/Cocos/Laya) across Android 8-16
  - `SurfaceStatsCollector` — Main collector with threaded collection/calculation. Uses SurfaceFlinger `--latency` for SurfaceView apps, `gfxinfo framestats` for standard apps, with page flip count and gfxinfo total frames as fallbacks. Includes credibility metadata for data quality tracking.
  - `FPSMonitor` — Wrapper that starts/stops `SurfaceStatsCollector`
- `common.py` — Core utilities:
  - `Devices` — Device discovery, ADB ID lookup, PID resolution
  - `File` — Report I/O, log management, `getDuration()` for test duration calculation
  - `Method` — HTTP request helpers
  - `Platform` — Platform enum
  - `Scrcpy` — Screen casting/recording via scrcpy. Uses software encoder (`c2.android.avc.encoder`) by default to avoid hardware encoder crashes. Supports High/Medium/Low quality presets.
  - `LogcatManager` — Singleton for adb logcat streaming via AJAX polling. Supports severity-level capture (`*:V` through `*:F`), structured log parsing (time/severity/tag/msg), client-side filtering, and export.
- `adb.py` — ADB wrapper with bundled platform-specific adb binaries (`solox/public/adb/{windows,mac,linux}/`). Key method: `adb.shell(cmd, deviceId)` for all device commands

### iOS Support
- `_iosPerf.py` — iOS performance collection bridge
- `iosperf/` — iOS device communication library (USB muxd, instruments, device pairing)

### Frontend
- `solox/templates/` — Jinja2 HTML templates. Key templates:
  - `index.html` — Main dashboard with device selection, metric charts, screen cast (quality dropdown), error log panel (severity/tag/keyword filters, pause, export), WiFi ADB modal
  - `report.html` — Report management with AJAX pagination and duration column
  - `base.html` — Layout shell with settings offcanvas (Timer, Remote Connection, with feature descriptions)
- `solox/static/` — JS, CSS, images for the web UI

### Tests
- `tests/test_fps_calculation.py` — 21 unit tests covering FPS calculation, jank detection, game engine surface detection, and fallback chains

## Key Patterns

### Android FPS Collection Flow
API request → `FPS.getObject()` (singleton) → `FPSMonitor.start()` → `SurfaceStatsCollector`:
1. `GameSurfaceDetector` checks if app is a game engine → auto-forces SurfaceView mode for games
2. `surfaceview=True`: SurfaceFlinger `--latency` with surface name from `dumpsys SurfaceFlinger --list`
3. `surfaceview=False`: `gfxinfo framestats` (only works for View-based apps, not game engines)
4. Fallback chain: multi-surface retry → page flip count (`service call SurfaceFlinger 1013`) → gfxinfo total frames

### Screen Casting
`Scrcpy.cast_screen(device, quality)` → `_cast_monitor_thread()`:
- Default: software encoder (`c2.android.avc.encoder`) to avoid Qualcomm OMX hardware encoder crashes
- Auto-retry: if software encoder fails, falls back to hardware encoder
- Quality presets: high (1920/60fps/6M), medium (1024/60fps/3M), low (720/30fps/1M)

### Weak Network Testing
`WeakNetworkManager` in `solox/public/weak_network.py`:
- Presets: WiFi/LTE/3G/2G/high latency/high loss (PerfDog-style)
- Simulation: root + `tc qdisc replace dev IFACE root netem` on device
- Probe: `ping` on device for RTT/loss/jitter (no root)
- APIs: `/apm/weaknet/presets|capabilities|apply|clear|probe`
- Cleared automatically on collection stop (`stopTask` → `clearWeakNet`)

### Project Layout
- `scripts/` — dev, release gate, packaging (see `scripts/README.md`)
- `runtime/` — dev log/PID (`runtime/logs`, `runtime/pids`); gitignored
- `report/` — APM session logs and recordings; gitignored
- `docs/06-engineering/` — directory, dev vs release, pre-publish checklist

### Device Communication
All Android commands go through `adb.shell()`. The `Devices` class provides:
- `getDeviceIds()` — List connected Android devices
- `getIdbyDevice(deviceinfo, platform)` — Strip bracket decorations from device display name to get raw device ID
- `getPid(pkgName, deviceId)` — Get process ID for a package
- `filterType()` — Returns `grep` or `findstr` depending on host OS

### Dependency Pinning
Flask/SocketIO versions are **strictly pinned** for compatibility. Do not upgrade independently:
- Flask==2.0.3, Werkzeug==2.0.3, Jinja2==3.0.1
- Flask-SocketIO==4.3.1, python-socketio==4.6.0, python-engineio==3.13.2

### Python Compatibility
- Requires Python >= 3.10 (uses `match/case` syntax)
- eventlet must be >= 0.35 for Python 3.12+ (`ssl.wrap_socket` removed in 3.12)
