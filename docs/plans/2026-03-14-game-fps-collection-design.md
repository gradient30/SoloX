# Design: Enhanced Game FPS Collection for Android 8.x-16.x

## Status: IMPLEMENTED ✅

## Date: 2026-03-14

## Problem

SoloX's FPS collection fails on Android game apps built with Unity, Unreal Engine 4/5, Cocos2d-x/Creator, and Laya. Two specific failure modes:

1. **FPS always returns 0**: `dumpsys SurfaceFlinger --latency` returns all-zero timestamps for game surfaces
2. **Surface not found**: `get_surfaceview()` cannot locate the correct rendering surface for game processes

### Root Cause

Game engines render directly via OpenGL ES / Vulkan to a Surface, bypassing Android's standard View hierarchy. The current code:

- `get_surfaceview()` only looks for lines starting with `"SurfaceView"` prefix — misses game engine naming variants
- `dumpsys gfxinfo framestats` (non-surfaceview mode) returns zero data for game engines since they don't use the Android UI toolkit
- On Android 8.x (API 26-27), `dumpsys SurfaceFlinger --latency` is known to return all-zero data on some devices
- Surface name format changed significantly between Android 8-11 and Android 12+

## Solution: Approach 1 — Enhanced Surface Discovery + Multi-Surface Fallback

### Architecture

```
FPS Request
    |
    v
+-------------------------------+
|  GameSurfaceDetector (NEW)    |
|  - dumpsys SurfaceFlinger     |
|    --list                     |
|  - Pattern match for game     |
|    engines                    |
|  - Rank candidate surfaces    |
+---------------+---------------+
                |
                v
+----------------------------------+
|  FPS Strategy Chain              |
|                                  |
|  1. SurfaceFlinger --latency     |
|     (best candidate surface)     |
|          | returns zeros?        |
|          v                       |
|  2. Try ALL candidate surfaces   |
|          | all fail?             |
|          v                       |
|  3. Page flip count (1013)       |
|     (global, works everywhere)   |
+----------------------------------+
```

### Game Engine Surface Patterns

| Engine | Activity Patterns |
|--------|------------------|
| Unity | `com.unity3d.player.UnityPlayerActivity`, `UnityPlayerNativeActivity`, `UnityPlayerGameActivity` |
| UE4/5 | `com.epicgames.ue4.GameActivity`, `com.epicgames.unreal.GameActivity` |
| Cocos | `org.cocos2dx.lib.Cocos2dxActivity`, `com.cocos.game.AppActivity` |
| Laya | `com.layabox.game`, `com.layabox.conch` |

### Android Version Surface Name Formats

| Android Version | API Level | Surface Name Format |
|----------------|-----------|---------------------|
| 8.x-11 | 26-30 | `SurfaceView - pkg/Activity#N` |
| 12-13 | 31-33 | `SurfaceView[pkg](BLAST)#N` or `pkg/Activity#N` |
| 14+ | 34+ | May omit `SurfaceView` prefix, `pkg/Activity#N` |

### Key Components

#### 1. GameSurfaceDetector class

Responsibilities:
- Parse `dumpsys SurfaceFlinger --list` output
- Match surfaces against known game engine patterns
- Handle all Android version surface name formats
- Return a ranked list of candidate surfaces (game surfaces first)

#### 2. Enhanced get_surfaceview()

Changes:
- Support Android 12+ `SurfaceView[pkg](BLAST)#N` format
- Support activity-only format `pkg/Activity#N`
- Recognize game engine activity names
- Return multiple candidates instead of just one

#### 3. Multi-surface try loop

In `_get_surfaceflinger_frame_data()`:
- Get all candidate surfaces from GameSurfaceDetector
- Try `dumpsys SurfaceFlinger --latency` on each candidate
- Use the first one that returns non-zero timestamp data
- If all fail, fall back to page flip count

#### 4. Page flip count fallback

`service call SurfaceFlinger 1013` returns a global page flip counter:
- Sample twice with 1-second interval
- FPS = (count2 - count1) / time_delta
- Works on all Android versions 8.x-16.x
- No jank detection, but ensures FPS is never 0 when screen is updating

#### 5. Android SDK version awareness

- API 26-27 (Android 8.x): Deprioritize SurfaceFlinger latency, prefer page flip count for games
- API 28-30 (Android 9-11): Standard SurfaceFlinger latency
- API 31+ (Android 12+): Handle BLAST surface format
- API 34+ (Android 14+): Handle latest format changes

### Files to Modify

1. **`solox/public/android_fps.py`** — Main changes:
   - Add `GameSurfaceDetector` class
   - Modify `SurfaceStatsCollector.get_surfaceview()` for game-aware patterns
   - Modify `SurfaceStatsCollector._get_surfaceflinger_frame_data()` with multi-surface fallback
   - Add page flip count fallback method
   - Add SDK version detection caching

2. **`solox/public/apm.py`** — Minor: ensure parameters pass through correctly

### Trade-offs

- **Pro**: Most accurate approach, game-engine-aware, works across all Android versions
- **Pro**: Graceful degradation — always returns some FPS value
- **Con**: Multiple adb calls during surface discovery (mitigated by caching)
- **Con**: Page flip count fallback measures global screen fps (not per-app)

## Implementation Notes

All components have been implemented and tested on a real Cocos2d game (`com.lyjz.chqsy.vivo`) on Android 11 (vivo device).

### Key Implementation Decisions

1. **Game engine auto-detection in `start()`**: Rather than runtime fallback in `_get_surfaceflinger_frame_data()`, game engines are detected at startup and `surfaceview` is forced to `True`. This is because `gfxinfo framestats` returns stale data (not None) for game engines — 12 old frame lines from Activity setup — which means a runtime "is None?" check never triggers.

2. **Page flip count**: `service call SurfaceFlinger 1013` may return permission denied (-1) on some devices (e.g., vivo). In this case, SurfaceFlinger latency with SurfaceView remains the only working method.

3. **Cocos pattern**: Added `org.cocos2dx.cpp.AppActivity` to game engine patterns — real-world Cocos games use this Activity name in addition to the standard patterns.

### Verification Results

| Test Path | surfaceview | Result |
|-----------|------------|--------|
| Python API | True | FPS=59 ✅ |
| Python API | False (auto-detect→True) | FPS=59 ✅ |
| Web API surv=true | True | FPS=59 ✅ |
| Web API surv=false | False (auto-detect→True) | FPS=59 ✅ |

### Commits

- `7c864f9` feat: add GameSurfaceDetector for game engine surface discovery
- `1256c02` feat: add page flip count fallback for reliable FPS on all Android versions
- `cdd0320` feat: enhance surface discovery for game engines and Android 12+ formats
- `94eae55` feat: rewrite frame data collection with multi-surface fallback for game engines
- `7fefc03` feat: integrate page flip fallback into collector/calculator threads
- `235e71e` fix: add Cocos cpp activity pattern and enhance focus activity detection
- `87300df` fix: auto-detect game engines at startup and force SurfaceView mode
