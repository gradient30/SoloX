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
- `pages.py` — Flask Blueprint for HTML pages (index, report, analysis, PK comparison)
- `apis.py` — Flask Blueprint for REST API endpoints (`/apm/cpu`, `/apm/fps`, `/apm/memory`, etc.)
- API endpoints create metric collector objects from `solox/public/apm.py`, call their `get*()` methods, return JSON

### Performance Collection (`solox/public/`)
- `apm.py` — Metric classes: `CPU`, `Memory`, `FPS`, `GPU`, `Battery`, `Network`, `Energy`, `Disk`, `ThermalSensor`. Each wraps platform-specific collection. `FPS.getObject()` is a singleton factory for Android FPS.
- `apm_pk.py` — PK (comparison) mode: `CPU_PK`, `MEM_PK`, `Flow_PK`, `FPS_PK` for dual-device/dual-app benchmarking
- `android_fps.py` — Android FPS collection engine. Key classes:
  - `GameSurfaceDetector` — Detects game engine surfaces (Unity/UE4/5/Cocos/Laya) across Android 8-16
  - `SurfaceStatsCollector` — Main collector with threaded collection/calculation. Uses SurfaceFlinger `--latency` for SurfaceView apps, `gfxinfo framestats` for standard apps, with page flip count and gfxinfo total frames as fallbacks
  - `FPSMonitor` — Wrapper that starts/stops `SurfaceStatsCollector`
- `common.py` — `Devices` (device discovery, ADB ID lookup, PID), `File` (report I/O, log management), `Method` (request helpers), `Platform` enum
- `adb.py` — ADB wrapper with bundled platform-specific adb binaries (`solox/public/adb/{windows,mac,linux}/`). Key method: `adb.shell(cmd, deviceId)` for all device commands

### iOS Support
- `_iosPerf.py` — iOS performance collection bridge
- `iosperf/` — iOS device communication library (USB muxd, instruments, device pairing)

### Frontend
- `solox/templates/` — Jinja2 HTML templates
- `solox/static/` — JS, CSS, images for the web UI

## Key Patterns

### Android FPS Collection Flow
API request → `FPS.getObject()` (singleton) → `FPSMonitor.start()` → `SurfaceStatsCollector`:
1. `GameSurfaceDetector` checks if app is a game engine → auto-forces SurfaceView mode for games
2. `surfaceview=True`: SurfaceFlinger `--latency` with surface name from `dumpsys SurfaceFlinger --list`
3. `surfaceview=False`: `gfxinfo framestats` (only works for View-based apps, not game engines)
4. Fallback chain: multi-surface retry → page flip count (`service call SurfaceFlinger 1013`) → gfxinfo total frames

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
