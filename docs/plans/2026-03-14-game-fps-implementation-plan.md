# Game FPS Collection Implementation Plan

> **Status: COMPLETED ✅** — All 7 tasks implemented, tested, and committed.

**Goal:** Fix FPS collection for Android game apps (Unity, UE4/5, Cocos, Laya) across Android 8.x-16.x by enhancing surface discovery and adding multi-surface fallback with page flip count as a last resort.

**Architecture:** Add a `GameSurfaceDetector` class that intelligently discovers game engine rendering surfaces from `dumpsys SurfaceFlinger --list`. Modify the existing `SurfaceStatsCollector` to try multiple candidate surfaces and fall back to page flip count when SurfaceFlinger latency returns zeros.

**Tech Stack:** Python 3, adb shell commands, `dumpsys SurfaceFlinger`, `dumpsys gfxinfo`

---

### Task 1: Add GameSurfaceDetector class with game engine pattern matching

**Files:**
- Modify: `solox/public/android_fps.py` (add new class after line 15, before `SurfaceStatsCollector`)

**Step 1: Add GameSurfaceDetector class with engine patterns and surface parsing**

Insert this code after line 15 (`collect_jank = 0`) in `solox/public/android_fps.py`:

```python

# Known game engine activity patterns for surface name matching
GAME_ENGINE_PATTERNS = {
    'unity': [
        'com.unity3d.player.UnityPlayerActivity',
        'com.unity3d.player.UnityPlayerNativeActivity',
        'com.unity3d.player.UnityPlayerGameActivity',
        'com.unity3d.player.UnityPlayerNativeActivityPico',
    ],
    'unreal': [
        'com.epicgames.ue4.GameActivity',
        'com.epicgames.unreal.GameActivity',
        'com.epicgames.ue4.SplashActivity',
    ],
    'cocos': [
        'org.cocos2dx.lib.Cocos2dxActivity',
        'com.cocos.game.AppActivity',
        'org.cocos2dx.lib.Cocos2dxGLSurfaceView',
        'org.cocos2dx.javascript.AppActivity',
    ],
    'laya': [
        'com.layabox.game',
        'com.layabox.conch',
        'com.layabox.conch5.LayaMainActivity',
    ],
}

# Flatten all game engine activity keywords for quick lookup
_ALL_GAME_KEYWORDS = []
for patterns in GAME_ENGINE_PATTERNS.values():
    _ALL_GAME_KEYWORDS.extend(patterns)


class GameSurfaceDetector(object):
    """Detects rendering surfaces for game engine apps across Android 8.x-16.x.

    Game engines (Unity, UE4/5, Cocos, Laya) render via OpenGL/Vulkan directly
    to a Surface, bypassing Android's View system. Their surfaces have different
    naming patterns than standard apps, and the format varies by Android version:

    - Android 8-11:  SurfaceView - pkg/Activity#N
    - Android 12+:   SurfaceView[pkg](BLAST)#N  or  pkg/Activity#N
    - Android 14+:   May omit SurfaceView prefix entirely
    """

    def __init__(self, device, package_name):
        self.device = device
        self.package_name = package_name
        self._sdk_version = None

    def get_sdk_version(self):
        if self._sdk_version is None:
            try:
                result = adb.shell(cmd='getprop ro.build.version.sdk', deviceId=self.device)
                self._sdk_version = int(result.strip())
            except Exception:
                self._sdk_version = 28  # default to safe value
        return self._sdk_version

    def get_all_surfaces(self):
        """Get all SurfaceFlinger surfaces for this package.

        Returns a list of surface name strings matching this package.
        """
        try:
            result = adb.shell(
                cmd='dumpsys SurfaceFlinger --list',
                deviceId=self.device
            )
            if not result:
                return []
            lines = result.strip().split('\n')
            surfaces = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if self.package_name in line:
                    surfaces.append(line)
            return surfaces
        except Exception:
            traceback.print_exc()
            return []

    def is_game_surface(self, surface_name):
        """Check if a surface name matches a known game engine pattern."""
        for keyword in _ALL_GAME_KEYWORDS:
            if keyword in surface_name:
                return True
        return False

    def detect_game_engine(self, surface_name):
        """Detect which game engine a surface belongs to. Returns engine name or None."""
        for engine, patterns in GAME_ENGINE_PATTERNS.items():
            for pattern in patterns:
                if pattern in surface_name:
                    return engine
        return None

    def get_candidate_surfaces(self):
        """Get ranked list of candidate surfaces for FPS measurement.

        Priority order:
        1. SurfaceView surfaces matching game engine patterns
        2. SurfaceView surfaces matching the package
        3. Any surface matching the package (activity-level)

        Returns list of surface name strings, best candidates first.
        """
        all_surfaces = self.get_all_surfaces()
        if not all_surfaces:
            return []

        game_surfaceviews = []     # Priority 1: game engine SurfaceView
        normal_surfaceviews = []   # Priority 2: generic SurfaceView
        activity_surfaces = []     # Priority 3: activity-level surfaces

        for surface in all_surfaces:
            is_surfaceview = (
                surface.startswith('SurfaceView') or
                surface.startswith('SurfaceView[')
            )
            is_game = self.is_game_surface(surface)

            if is_surfaceview and is_game:
                game_surfaceviews.append(surface)
            elif is_surfaceview:
                normal_surfaceviews.append(surface)
            elif self.package_name in surface:
                activity_surfaces.append(surface)

        # Return ranked: game surfaces first, then normal SurfaceViews, then activity
        candidates = game_surfaceviews + normal_surfaceviews + activity_surfaces
        return candidates

    def should_prefer_page_flip(self):
        """On Android 8.x (API 26-27), SurfaceFlinger latency is unreliable.
        Prefer page flip count method for game apps on these versions."""
        sdk = self.get_sdk_version()
        return sdk <= 27
```

**Step 2: Verify no syntax errors**

Run: `python -c "import ast; ast.parse(open('solox/public/android_fps.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add solox/public/android_fps.py
git commit -m "feat: add GameSurfaceDetector for game engine surface discovery"
```

---

### Task 2: Add page flip count fallback method to SurfaceStatsCollector

**Files:**
- Modify: `solox/public/android_fps.py` — add `_get_fps_by_page_flip()` method to `SurfaceStatsCollector` class

**Step 1: Add page flip count method**

Add this method to the `SurfaceStatsCollector` class, right after `_get_surface_stats_legacy()` (after line 465):

```python
    def _get_page_flip_count(self):
        """Get current page flip count from SurfaceFlinger.

        Uses 'service call SurfaceFlinger 1013' which returns a global
        page flip counter. Works on all Android versions 8.x-16.x.

        Returns:
            int: current page flip count, or -1 on failure
        """
        try:
            ret = adb.shell(cmd="service call SurfaceFlinger 1013", deviceId=self.device)
            if not ret:
                return -1
            match = re.search(r'Parcel\((\w+)', ret)
            if match:
                return int(match.group(1), 16)
        except Exception:
            traceback.print_exc()
        return -1

    def _get_fps_by_page_flip(self):
        """Calculate FPS using page flip count difference over 1 second.

        This is the most reliable fallback — works on all Android versions
        and all app types including game engines. Measures global screen
        frame rate (not per-app), but ensures FPS is never 0 when the
        screen is actively updating.

        Returns:
            tuple: (fps, 0) — jank is always 0 for this method
        """
        count1 = self._get_page_flip_count()
        if count1 < 0:
            return 0, 0
        time.sleep(1)
        count2 = self._get_page_flip_count()
        if count2 < 0:
            return 0, 0
        fps = count2 - count1
        if fps < 0:
            fps = 0
        if fps > 120:
            fps = 120
        return fps, 0
```

**Step 2: Verify no syntax errors**

Run: `python -c "import ast; ast.parse(open('solox/public/android_fps.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add solox/public/android_fps.py
git commit -m "feat: add page flip count fallback for reliable FPS on all Android versions"
```

---

### Task 3: Enhance get_surfaceview() to support game engines and Android 12+ formats

**Files:**
- Modify: `solox/public/android_fps.py` — rewrite `get_surfaceview()` method (lines 60-79)

**Step 1: Replace get_surfaceview() with game-aware version**

Replace the existing `get_surfaceview()` method (lines 60-79) with:

```python
    def get_surfaceview(self):
        """Get the best SurfaceView surface name for FPS measurement.

        Enhanced to support:
        - Game engine surfaces (Unity, UE4/5, Cocos, Laya)
        - Android 12+ BLAST surface format: SurfaceView[pkg](BLAST)#N
        - Activity-level surface format: pkg/Activity#N
        - Falls back through multiple candidates
        """
        try:
            detector = GameSurfaceDetector(self.device, self.package_name)
            candidates = detector.get_candidate_surfaces()

            if candidates:
                engine = detector.detect_game_engine(candidates[0])
                if engine:
                    logger.info('Detected {} game engine surface: {}'.format(engine, candidates[0]))
                # Store all candidates for fallback in _get_surfaceflinger_frame_data
                self._surface_candidates = candidates
                return candidates[0]

            # Original fallback: use dumpsys SurfaceFlinger --list with grep
            dumpsys_result = adb.shell(
                cmd='dumpsys SurfaceFlinger --list | {} {}'.format(d.filterType(), self.package_name),
                deviceId=self.device
            )
            dumpsys_result_list = dumpsys_result.split('\n')
            for line in dumpsys_result_list:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('SurfaceView') and self.package_name in line:
                    return line
                # Android 12+ format: SurfaceView[pkg](BLAST)#N
                if line.startswith('SurfaceView[') and self.package_name in line:
                    return line

            # Last resort: return last non-empty line
            for line in reversed(dumpsys_result_list):
                line = line.strip()
                if line and self.package_name in line:
                    return line

            logger.error('get surface name failed for {}'.format(self.package_name))
            logger.info('dumpsys SurfaceFlinger --list info: {}'.format(dumpsys_result))
        except Exception:
            traceback.print_exc()
            logger.error('get surface name failed for {}'.format(self.package_name))
        return ''
```

**Step 2: Also replace get_surfaceview_activity() (lines 81-105) with an enhanced version**

Replace `get_surfaceview_activity()` with:

```python
    def get_surfaceview_activity(self):
        """Extract the activity name from the SurfaceView surface.

        Handles multiple formats:
        - 'SurfaceView - pkg/Activity#N' -> 'pkg/Activity'
        - 'SurfaceView[pkg](BLAST)#N' -> 'pkg'
        - 'pkg/Activity#N' -> 'pkg/Activity'
        """
        activity_name = ''
        try:
            dumpsys_result = adb.shell(
                cmd='dumpsys SurfaceFlinger --list | {} {}'.format(d.filterType(), self.package_name),
                deviceId=self.device
            )
            dumpsys_result_list = dumpsys_result.split('\n')
            activity_line = ''

            for line in dumpsys_result_list:
                line = line.strip()
                if not line:
                    continue
                # Match SurfaceView lines containing our package
                if (line.startswith('SurfaceView') or line.startswith('SurfaceView[')) and self.package_name in line:
                    activity_line = line
                    break

            if activity_line:
                # Format: "SurfaceView - pkg/Activity#N"
                if ' - ' in activity_line:
                    parts = activity_line.split(' - ', 1)
                    if len(parts) > 1:
                        activity_name = parts[1].strip()
                        # Remove trailing #N
                        if '#' in activity_name:
                            activity_name = activity_name.split('#')[0]
                # Format: "SurfaceView[pkg](BLAST)#N"
                elif activity_line.startswith('SurfaceView['):
                    match = re.search(r'SurfaceView\[([^\]]+)\]', activity_line)
                    if match:
                        activity_name = match.group(1)
                # Format: "SurfaceView pkg/Activity"
                elif activity_line.startswith('SurfaceView'):
                    activity_name = activity_line.replace('SurfaceView', '').replace('[', '').replace(']', '').replace('-', '').strip()

                if not activity_name:
                    activity_name = activity_line
            else:
                # No SurfaceView found, try last line matching package
                for line in reversed(dumpsys_result_list):
                    line = line.strip()
                    if line and self.package_name in line:
                        activity_name = line
                        if '#' in activity_name:
                            activity_name = activity_name.split('#')[0]
                        break

                if activity_name and self.package_name not in activity_name:
                    logger.error('get activity name failed for {}'.format(self.package_name))
                    logger.info('dumpsys SurfaceFlinger --list info: {}'.format(dumpsys_result))
        except Exception:
            traceback.print_exc()
            logger.error('get activity name failed for {}'.format(self.package_name))
        return activity_name
```

**Step 3: Verify no syntax errors**

Run: `python -c "import ast; ast.parse(open('solox/public/android_fps.py').read()); print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add solox/public/android_fps.py
git commit -m "feat: enhance surface discovery for game engines and Android 12+ formats"
```

---

### Task 4: Rewrite _get_surfaceflinger_frame_data() with multi-surface fallback

**Files:**
- Modify: `solox/public/android_fps.py` — rewrite `_get_surfaceflinger_frame_data()` method (lines 321-444)

**Step 1: Replace _get_surfaceflinger_frame_data() with multi-surface fallback version**

Replace the entire `_get_surfaceflinger_frame_data()` method with:

```python
    def _get_surfaceflinger_frame_data(self):
        """Returns collected SurfaceFlinger frame timing data.

        Enhanced with multi-surface fallback for game engines:
        1. Try the current focus_window / surfaceview surface
        2. If zeros, try all candidate surfaces from GameSurfaceDetector
        3. If all fail, return None to trigger page flip fallback

        Returns:
            A tuple containing:
            - The display's nominal refresh period in seconds.
            - A list of timestamps signifying frame presentation times in seconds.
            The return value may be (None, None) if there was no data collected.
        """
        nanoseconds_per_second = 1e9
        pending_fence_timestamp = (1 << 63) - 1

        if self.surfaceview is not True:
            # Non-SurfaceView mode: use gfxinfo framestats (for standard Android apps)
            return self._get_frame_data_from_gfxinfo(nanoseconds_per_second, pending_fence_timestamp)
        else:
            # SurfaceView mode: use SurfaceFlinger --latency with multi-surface fallback
            return self._get_frame_data_from_surfaceflinger(nanoseconds_per_second, pending_fence_timestamp)

    def _get_frame_data_from_gfxinfo(self, nanoseconds_per_second, pending_fence_timestamp):
        """Get frame data from dumpsys gfxinfo framestats (for standard Android apps)."""
        refresh_period = None
        timestamps = []
        try:
            results = adb.shell(
                cmd='dumpsys SurfaceFlinger --latency %s' % self.focus_window, deviceId=self.device)
            results = results.replace("\r\n", "\n").splitlines()
            if not results or not results[0].strip().isdigit():
                return (None, None)
            refresh_period = int(results[0]) / nanoseconds_per_second

            results = adb.shell(cmd='dumpsys gfxinfo %s framestats' % self.package_name, deviceId=self.device)
            results = results.replace("\r\n", "\n").splitlines()
            if not len(results):
                return (None, None)
            isHaveFoundWindow = False
            PROFILEDATA_line = 0
            activity = self.focus_window
            if self.focus_window and '#' in self.focus_window:
                activity = activity.split('#')[0]
            for line in results:
                if not isHaveFoundWindow:
                    if "Window" in line and activity in line:
                        isHaveFoundWindow = True
                if not isHaveFoundWindow:
                    continue
                if "PROFILEDATA" in line:
                    PROFILEDATA_line += 1
                fields = line.split(",")
                if fields and '0' == fields[0]:
                    timestamp = [int(fields[1]), int(fields[2]), int(fields[13])]
                    if timestamp[1] == pending_fence_timestamp:
                        continue
                    timestamp = [_timestamp / nanoseconds_per_second for _timestamp in timestamp]
                    timestamps.append(timestamp)
                if 2 == PROFILEDATA_line:
                    break
        except Exception:
            traceback.print_exc()
            return (None, None)
        return (refresh_period, timestamps)

    def _try_surface_latency(self, surface_name, nanoseconds_per_second, pending_fence_timestamp):
        """Try to get frame timing data from a specific surface.

        Returns:
            tuple: (refresh_period, timestamps) or (None, None) if no valid data
        """
        try:
            # Quote the surface name for the shell command
            results = adb.shell(
                cmd='dumpsys SurfaceFlinger --latency \\"%s\\"' % surface_name,
                deviceId=self.device
            )
            results = results.replace("\r\n", "\n").splitlines()

            if not results or len(results) <= 1:
                return (None, None)

            # First line should be the refresh period (nanoseconds)
            first_line = results[0].strip()
            if not first_line.isdigit():
                return (None, None)

            refresh_period = int(first_line) / nanoseconds_per_second
            if refresh_period <= 0:
                return (None, None)

            timestamps = []
            for line in results[1:]:
                fields = line.split()
                if len(fields) != 3:
                    continue
                try:
                    timestamp = [int(fields[0]), int(fields[1]), int(fields[2])]
                except ValueError:
                    continue
                # Skip pending fence timestamps
                if timestamp[1] == pending_fence_timestamp:
                    continue
                # Skip all-zero lines
                if timestamp[0] == 0 and timestamp[1] == 0 and timestamp[2] == 0:
                    continue
                timestamp = [_timestamp / nanoseconds_per_second for _timestamp in timestamp]
                timestamps.append(timestamp)

            if len(timestamps) > 0:
                return (refresh_period, timestamps)
            return (None, None)
        except Exception:
            return (None, None)

    def _get_frame_data_from_surfaceflinger(self, nanoseconds_per_second, pending_fence_timestamp):
        """Get frame data from SurfaceFlinger with multi-surface fallback.

        Strategy:
        1. Try the current surfaceview surface
        2. If that returns no data, try all candidate surfaces from GameSurfaceDetector
        3. Return the first surface that yields valid timestamps
        """
        # Step 1: Try current surface (from get_surfaceview)
        if self.focus_window:
            result = self._try_surface_latency(
                self.focus_window, nanoseconds_per_second, pending_fence_timestamp
            )
            if result[0] is not None:
                return result

        # Step 2: Try all candidate surfaces from GameSurfaceDetector
        candidates = getattr(self, '_surface_candidates', None)
        if not candidates:
            detector = GameSurfaceDetector(self.device, self.package_name)
            candidates = detector.get_candidate_surfaces()
            self._surface_candidates = candidates

        for surface in candidates:
            if surface == self.focus_window:
                continue  # Already tried
            result = self._try_surface_latency(
                surface, nanoseconds_per_second, pending_fence_timestamp
            )
            if result[0] is not None:
                # Found valid data — update focus_window for future calls
                logger.info('Found valid FPS surface: {}'.format(surface))
                self.focus_window = surface
                return result

        # Step 3: Also try the activity name version
        activity = self.get_surfaceview_activity()
        if activity and activity != self.focus_window:
            result = self._try_surface_latency(
                activity, nanoseconds_per_second, pending_fence_timestamp
            )
            if result[0] is not None:
                self.focus_window = activity
                return result

        logger.warning('All SurfaceFlinger surfaces returned no data for {}'.format(self.package_name))
        return (None, None)
```

**Step 2: Verify no syntax errors**

Run: `python -c "import ast; ast.parse(open('solox/public/android_fps.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add solox/public/android_fps.py
git commit -m "feat: rewrite frame data collection with multi-surface fallback for game engines"
```

---

### Task 5: Integrate page flip fallback into the collector/calculator threads

**Files:**
- Modify: `solox/public/android_fps.py` — modify `_collector_thread()` and `_calculator_thread()` and `start()`

**Step 1: Modify __init__ to add GameSurfaceDetector and _surface_candidates**

Add `self._surface_candidates = []` and `self._game_detector = None` to `SurfaceStatsCollector.__init__()` (after line 31 `self.fps_queue = fps_queue`):

```python
        self._surface_candidates = []
        self._game_detector = None
        self._use_page_flip = False
```

**Step 2: Modify start() to detect games and choose strategy**

Replace the existing `start()` method (lines 33-50) with:

```python
    def start(self, start_time):
        self._game_detector = GameSurfaceDetector(self.device, self.package_name)

        if not self.use_legacy_method:
            try:
                # Check if we should prefer page flip (Android 8.x + game app)
                if self._game_detector.should_prefer_page_flip():
                    candidates = self._game_detector.get_candidate_surfaces()
                    has_game_surface = any(self._game_detector.is_game_surface(s) for s in candidates)
                    if has_game_surface:
                        logger.info('Android 8.x detected with game engine app, using page flip count method')
                        self._use_page_flip = True

                if not self._use_page_flip:
                    if self.surfaceview:
                        self.focus_window = self.get_surfaceview()
                    else:
                        self.focus_window = self.get_focus_activity()

                    if self.focus_window and '$' in self.focus_window:
                        self.focus_window = self.focus_window.replace('$', '\\$')

                    if not self.focus_window:
                        logger.warning('Could not find focus window, will try multi-surface detection')
            except Exception:
                logger.warning('Unable to get activity/surface, trying page flip fallback')
                traceback.print_exc()
                self._use_page_flip = True
        else:
            self.use_legacy_method = True
            self.surface_before = self._get_surface_stats_legacy()

        self.collector_thread = threading.Thread(target=self._collector_thread)
        self.collector_thread.start()
        self.calculator_thread = threading.Thread(target=self._calculator_thread, args=(start_time,))
        self.calculator_thread.start()
```

**Step 3: Modify _collector_thread() to use page flip fallback**

Replace the existing `_collector_thread()` method (lines 258-299) with:

```python
    def _collector_thread(self):
        is_first = True
        consecutive_failures = 0
        max_failures_before_fallback = 3

        while not self.stop_event.is_set():
            try:
                before = time.time()

                if self.use_legacy_method:
                    surface_state = self._get_surface_stats_legacy()
                    if surface_state:
                        self.data_queue.put(surface_state)
                elif self._use_page_flip:
                    # Page flip count fallback
                    fps, jank = self._get_fps_by_page_flip()
                    self.data_queue.put(('page_flip', fps, jank, time.time()))
                else:
                    timestamps = []
                    refresh_period, new_timestamps = self._get_surfaceflinger_frame_data()

                    if refresh_period is None or new_timestamps is None:
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures_before_fallback:
                            logger.warning(
                                'SurfaceFlinger returned no data {} times, switching to page flip fallback'
                                .format(consecutive_failures)
                            )
                            self._use_page_flip = True
                            continue
                        # Try refreshing focus window
                        if self.surfaceview:
                            self.focus_window = self.get_surfaceview()
                        else:
                            self.focus_window = self.get_focus_activity()
                        logger.warning("refresh_period is None or timestamps is None, retry #{}"
                                      .format(consecutive_failures))
                        continue

                    # Got valid data — reset failure counter
                    consecutive_failures = 0

                    timestamps += [timestamp for timestamp in new_timestamps
                                   if timestamp[1] > self.last_timestamp]
                    if len(timestamps):
                        first_timestamp = [[0, self.last_timestamp, 0]]
                        if not is_first:
                            timestamps = first_timestamp + timestamps
                        self.last_timestamp = timestamps[-1][1]
                        is_first = False
                    else:
                        is_first = True
                        if not self.surfaceview:
                            cur_focus_window = self.get_focus_activity()
                            if self.focus_window != cur_focus_window:
                                self.focus_window = cur_focus_window
                                continue

                    self.data_queue.put((refresh_period, timestamps, time.time()))

                time_consume = time.time() - before
                delta_inter = self.frequency - time_consume
                if delta_inter > 0:
                    time.sleep(delta_inter)
            except Exception:
                logger.error("an exception happened in fps _collector_thread")
                s = traceback.format_exc()
                logger.debug(s)
                if self.fps_queue:
                    self.fps_queue.task_done()
        self.data_queue.put('Stop')
```

**Step 4: Modify _calculator_thread() to handle page flip data**

Replace the existing `_calculator_thread()` method (lines 218-256) with:

```python
    def _calculator_thread(self, start_time):
        global collect_fps
        global collect_jank
        while True:
            try:
                data = self.data_queue.get()
                if isinstance(data, str) and data == 'Stop':
                    break
                before = time.time()
                if self.use_legacy_method:
                    td = data['timestamp'] - self.surface_before['timestamp']
                    seconds = td.seconds + td.microseconds / 1e6
                    frame_count = (data['page_flip_count'] -
                                   self.surface_before['page_flip_count'])
                    fps = int(round(frame_count / seconds))
                    if fps > 60:
                        fps = 60
                    self.surface_before = data
                    collect_fps = fps
                elif isinstance(data, tuple) and len(data) == 4 and data[0] == 'page_flip':
                    # Page flip fallback data
                    fps = data[1]
                    jank = data[2]
                    collect_fps = fps
                    collect_jank = jank
                else:
                    refresh_period = data[0]
                    timestamps = data[1]
                    collect_time = data[2]
                    fps, jank = self._calculate_results_new(refresh_period, timestamps)
                    collect_fps = fps
                    collect_jank = jank
                time_consume = time.time() - before
                delta_inter = self.frequency - time_consume
                if delta_inter > 0:
                    time.sleep(delta_inter)
            except Exception:
                logger.error("an exception happened in fps _calculator_thread")
                s = traceback.format_exc()
                logger.debug(s)
                if self.fps_queue:
                    self.fps_queue.task_done()
```

**Step 5: Verify no syntax errors**

Run: `python -c "import ast; ast.parse(open('solox/public/android_fps.py').read()); print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add solox/public/android_fps.py
git commit -m "feat: integrate page flip fallback into collector/calculator threads"
```

---

### Task 6: Start SoloX and verify FPS collection on connected device

**Files:**
- No file changes — testing only

**Step 1: Install dependencies**

Run: `pip install -e .`
Expected: Successful installation

**Step 2: Start SoloX server**

Run: `python -m solox --host=0.0.0.0 --port=50003`
Expected: Server starts, prints SOLOX banner, opens browser

**Step 3: Verify connected Android device**

Run: `adb devices`
Expected: Shows connected device ID

**Step 4: Test FPS collection via API**

In another terminal, test the FPS API with a game app:

Run: `curl "http://localhost:50003/apm/fps?platform=Android&device=<DEVICE>&pkgname=<GAME_PACKAGE>&surv=true"`
Expected: JSON response with `fps` > 0 (not always 0)

**Step 5: Test with surfaceview=false as well**

Run: `curl "http://localhost:50003/apm/fps?platform=Android&device=<DEVICE>&pkgname=<GAME_PACKAGE>&surv=false"`
Expected: JSON response with `fps` value

**Step 6: Commit any fixes needed**

If issues found during testing, fix and commit.

---

### Task 7: Final cleanup and documentation commit

**Files:**
- Modify: `solox/public/android_fps.py` — any final cleanup

**Step 1: Review the complete android_fps.py for consistency**

Read through the full file and verify:
- No duplicate methods
- All imports are present
- No leftover debug code

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat: complete game engine FPS support for Android 8.x-16.x

Adds GameSurfaceDetector for Unity/UE4/UE5/Cocos/Laya surface discovery.
Enhanced surface name matching for Android 12+ BLAST format.
Multi-surface fallback tries all candidate surfaces.
Page flip count (SurfaceFlinger 1013) as final fallback.
Android 8.x auto-detects unreliable SurfaceFlinger and uses page flip."
```
