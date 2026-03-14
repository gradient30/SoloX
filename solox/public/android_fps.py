# -*- coding: utf-8 -*-
import datetime
import queue
import re
import threading
import time
import traceback
from logzero import logger
from solox.public.adb import adb
from solox.public.common import Devices

d = Devices()

collect_fps = 0
collect_jank = 0

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
        'org.cocos2dx.cpp.AppActivity',
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
    """Detects rendering surfaces for game engine apps across Android 8.x-16.x."""

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
                self._sdk_version = 28
        return self._sdk_version

    def get_all_surfaces(self):
        """Get all SurfaceFlinger surfaces for this package."""
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
        """
        all_surfaces = self.get_all_surfaces()
        if not all_surfaces:
            return []

        game_surfaceviews = []
        normal_surfaceviews = []
        activity_surfaces = []

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

        candidates = game_surfaceviews + normal_surfaceviews + activity_surfaces
        return candidates

    def should_prefer_page_flip(self):
        """On Android 8.x (API 26-27), SurfaceFlinger latency is unreliable."""
        sdk = self.get_sdk_version()
        return sdk <= 27


class SurfaceStatsCollector(object):
    def __init__(self, device, frequency, package_name, fps_queue, jank_threshold, surfaceview, use_legacy=False):
        self.device = device
        self.frequency = frequency
        self.package_name = package_name
        self.jank_threshold = jank_threshold / 1000.0 
        self.use_legacy_method = use_legacy
        self.surface_before = 0
        self.last_timestamp = 0
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.focus_window = None
        self.surfaceview = surfaceview
        self.fps_queue = fps_queue
        self._surface_candidates = []
        self._game_detector = None
        self._use_page_flip = False

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

    def stop(self):
        if self.collector_thread:
            self.stop_event.set()
            self.collector_thread.join()
            self.collector_thread = None
            if self.fps_queue:
                self.fps_queue.task_done()

    def get_surfaceview(self):
        """Get the best SurfaceView surface name for FPS measurement.

        Enhanced to support:
        - Game engine surfaces (Unity, UE4/5, Cocos, Laya)
        - Android 12+ BLAST surface format: SurfaceView[pkg](BLAST)#N
        - Activity-level surface format: pkg/Activity#N
        """
        try:
            detector = GameSurfaceDetector(self.device, self.package_name)
            candidates = detector.get_candidate_surfaces()

            if candidates:
                engine = detector.detect_game_engine(candidates[0])
                if engine:
                    logger.info('Detected {} game engine surface: {}'.format(engine, candidates[0]))
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
                if line.startswith('SurfaceView[') and self.package_name in line:
                    return line

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
                if (line.startswith('SurfaceView') or line.startswith('SurfaceView[')) and self.package_name in line:
                    activity_line = line
                    break

            if activity_line:
                if ' - ' in activity_line:
                    parts = activity_line.split(' - ', 1)
                    if len(parts) > 1:
                        activity_name = parts[1].strip()
                        if '#' in activity_name:
                            activity_name = activity_name.split('#')[0]
                elif activity_line.startswith('SurfaceView['):
                    match = re.search(r'SurfaceView\[([^\]]+)\]', activity_line)
                    if match:
                        activity_name = match.group(1)
                elif activity_line.startswith('SurfaceView'):
                    activity_name = activity_line.replace('SurfaceView', '').replace('[', '').replace(']', '').replace('-', '').strip()

                if not activity_name:
                    activity_name = activity_line
            else:
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

    def get_focus_activity(self):
        activity_name = ''
        activity_line = ''
        # Try 'dumpsys window windows' first, then 'dumpsys window' as fallback
        for cmd in ['dumpsys window windows', 'dumpsys window']:
            dumpsys_result = adb.shell(cmd=cmd, deviceId=self.device)
            dumpsys_result_list = dumpsys_result.split('\n')
            for line in dumpsys_result_list:
                if 'mCurrentFocus' in line or 'mFocusedWindow' in line:
                    activity_line = line.strip()
                    break
            if activity_line:
                break
        if activity_line:
            activity_line_split = activity_line.split(' ')
        else:
            return activity_name
        if len(activity_line_split) > 1:
            if activity_line_split[1] == 'u0':
                activity_name = activity_line_split[2].rstrip('}')
            else:
                activity_name = activity_line_split[1]
        if not activity_name:
            activity_name = self.get_surfaceview_activity()
        return activity_name

    def get_foreground_process(self):
        focus_activity = self.get_focus_activity()
        if focus_activity:
            return focus_activity.split("/")[0]
        else:
            return ""

    def _calculate_results(self, refresh_period, timestamps):
        frame_count = len(timestamps)
        if frame_count == 0:
            fps = 0
            jank = 0
        elif frame_count == 1:
            fps = 1
            jank = 0
        else:
            seconds = timestamps[-1][1] - timestamps[0][1]
            if seconds > 0:
                fps = int(round((frame_count - 1) / seconds))
                jank = self._calculate_janky(timestamps)
            else:
                fps = 1
                jank = 0
        return fps, jank

    def _calculate_results_new(self, refresh_period, timestamps):
        frame_count = len(timestamps)
        if frame_count == 0:
            fps = 0
            jank = 0
        elif frame_count == 1:
            fps = 1
            jank = 0
        elif frame_count == 2 or frame_count == 3 or frame_count == 4:
            seconds = timestamps[-1][1] - timestamps[0][1]
            if seconds > 0:
                fps = int(round((frame_count - 1) / seconds))
                jank = self._calculate_janky(timestamps)
            else:
                fps = 1
                jank = 0
        else:
            seconds = timestamps[-1][1] - timestamps[0][1]
            if seconds > 0:
                fps = int(round((frame_count - 1) / seconds))
                jank = self._calculate_jankey_new(timestamps)
            else:
                fps = 1
                jank = 0
        return fps, jank

    def _calculate_jankey_new(self, timestamps):
        twofilmstamp = 83.3 / 1000.0
        tempstamp = 0
        jank = 0
        for index, timestamp in enumerate(timestamps):
            if (index == 0) or (index == 1) or (index == 2) or (index == 3):
                if tempstamp == 0:
                    tempstamp = timestamp[1]
                    continue
                costtime = timestamp[1] - tempstamp
                if costtime > self.jank_threshold:
                    jank = jank + 1
                tempstamp = timestamp[1]
            elif index > 3:
                currentstamp = timestamps[index][1]
                lastonestamp = timestamps[index - 1][1]
                lasttwostamp = timestamps[index - 2][1]
                lastthreestamp = timestamps[index - 3][1]
                lastfourstamp = timestamps[index - 4][1]
                tempframetime = ((lastthreestamp - lastfourstamp) + (lasttwostamp - lastthreestamp) + (
                        lastonestamp - lasttwostamp)) / 3 * 2
                currentframetime = currentstamp - lastonestamp
                if (currentframetime > tempframetime) and (currentframetime > twofilmstamp):
                    jank = jank + 1
        return jank

    def _calculate_janky(self, timestamps):
        tempstamp = 0
        jank = 0
        for timestamp in timestamps:
            if tempstamp == 0:
                tempstamp = timestamp[1]
                continue
            costtime = timestamp[1] - tempstamp
            if costtime > self.jank_threshold:
                jank = jank + 1
            tempstamp = timestamp[1]
        return jank

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

                    # Got valid data - reset failure counter
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

    def _clear_surfaceflinger_latency_data(self):
        """Clears the SurfaceFlinger latency data.

        Returns:
            True if SurfaceFlinger latency is supported by the device, otherwise
            False.
        """
        # The command returns nothing if it is supported, otherwise returns many
        # lines of result just like 'dumpsys SurfaceFlinger'.
        if self.focus_window is None:
            results = adb.shell(cmd='dumpsys SurfaceFlinger --latency-clear', deviceId=self.device)
        else:
            results = adb.shell(cmd='dumpsys SurfaceFlinger --latency-clear %s' % self.focus_window,
                                deviceId=self.device)
        return not len(results)

    def get_sdk_version(self):
        sdk_version = int(adb.shell(cmd='getprop ro.build.version.sdk', deviceId=self.device))
        return sdk_version

    def _get_surfaceflinger_frame_data(self):
        """Returns collected SurfaceFlinger frame timing data.

        Enhanced with multi-surface fallback for game engines.

        Returns:
            A tuple (refresh_period, timestamps) or (None, None).
        """
        nanoseconds_per_second = 1e9
        pending_fence_timestamp = (1 << 63) - 1

        if self.surfaceview is not True:
            return self._get_frame_data_from_gfxinfo(nanoseconds_per_second, pending_fence_timestamp)
        else:
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
            results = adb.shell(
                cmd='dumpsys SurfaceFlinger --latency \\"%s\\"' % surface_name,
                deviceId=self.device
            )
            results = results.replace("\r\n", "\n").splitlines()

            if not results or len(results) <= 1:
                return (None, None)

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
                if timestamp[1] == pending_fence_timestamp:
                    continue
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
        # Step 1: Try current surface
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
                continue
            result = self._try_surface_latency(
                surface, nanoseconds_per_second, pending_fence_timestamp
            )
            if result[0] is not None:
                logger.info('Found valid FPS surface: {}'.format(surface))
                self.focus_window = surface
                return result

        # Step 3: Try activity name version
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

    def _get_surface_stats_legacy(self):
        """Legacy method (before JellyBean), returns the current Surface index
             and timestamp.

        Calculate FPS by measuring the difference of Surface index returned by
        SurfaceFlinger in a period of time.

        Returns:
            Dict of {page_flip_count (or 0 if there was an error), timestamp}.
        """
        cur_surface = None
        timestamp = datetime.datetime.now()
        ret = adb.shell(cmd="service call SurfaceFlinger 1013", deviceId=self.device)
        if not ret:
            return None
        if 'Error' in ret or 'not permitted' in ret:
            return None
        match = re.search(r'^Result: Parcel\(([0-9a-fA-F]+)', ret)
        if match:
            cur_surface = int(match.group(1), 16)
            return {'page_flip_count': cur_surface, 'timestamp': timestamp}
        return None

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
            # Check for error response first
            if 'Error' in ret or 'not permitted' in ret:
                return -1
            match = re.search(r'Parcel\(([0-9a-fA-F]+)', ret)
            if match:
                return int(match.group(1), 16)
        except Exception:
            traceback.print_exc()
        return -1

    def _get_fps_by_page_flip(self):
        """Calculate FPS using page flip count difference over 1 second.

        Falls back to gfxinfo total frames if page flip count is not permitted.

        Returns:
            tuple: (fps, 0) - jank is always 0 for this method
        """
        count1 = self._get_page_flip_count()
        if count1 < 0:
            # Page flip not available, try gfxinfo total frames fallback
            return self._get_fps_by_gfxinfo_frames()
        time.sleep(1)
        count2 = self._get_page_flip_count()
        if count2 < 0:
            return self._get_fps_by_gfxinfo_frames()
        fps = count2 - count1
        if fps < 0:
            fps = 0
        if fps > 120:
            fps = 120
        return fps, 0

    def _get_fps_by_gfxinfo_frames(self):
        """Calculate FPS from 'dumpsys gfxinfo' Total frames rendered count.

        This is the final fallback when both SurfaceFlinger latency and
        page flip count are unavailable.

        Returns:
            tuple: (fps, 0)
        """
        try:
            result1 = adb.shell(
                cmd='dumpsys gfxinfo {} | {} "Total frames"'.format(
                    self.package_name, d.filterType()),
                deviceId=self.device
            )
            match1 = re.search(r'Total frames rendered:\s*(\d+)', result1)
            if not match1:
                return 0, 0
            frames1 = int(match1.group(1))
            time.sleep(1)
            result2 = adb.shell(
                cmd='dumpsys gfxinfo {} | {} "Total frames"'.format(
                    self.package_name, d.filterType()),
                deviceId=self.device
            )
            match2 = re.search(r'Total frames rendered:\s*(\d+)', result2)
            if not match2:
                return 0, 0
            frames2 = int(match2.group(1))
            fps = frames2 - frames1
            if fps < 0:
                fps = 0
            if fps > 120:
                fps = 120
            return fps, 0
        except Exception:
            traceback.print_exc()
            return 0, 0


class Monitor(object):
    def __init__(self, **kwargs):
        self.config = kwargs
        self.matched_data = {}

    def start(self):
        logger.warn("请在%s类中实现start方法" % type(self))

    def clear(self):
        self.matched_data = {}

    def stop(self):
        logger.warning("请在%s类中实现stop方法" % type(self))

    def save(self):
        logger.warning("请在%s类中实现save方法" % type(self))


class TimeUtils(object):
    UnderLineFormatter = "%Y_%m_%d_%H_%M_%S"
    NormalFormatter = "%Y-%m-%d %H-%M-%S"
    ColonFormatter = "%Y-%m-%d %H:%M:%S"

    @staticmethod
    def getCurrentTimeUnderline():
        return time.strftime(TimeUtils.UnderLineFormatter, time.localtime(time.time()))


class FPSMonitor(Monitor):
    def __init__(self, device_id, package_name=None, frequency=1.0, timeout=24 * 60 * 60, fps_queue=None,
                 jank_threshold=166, use_legacy=False, surfaceview=True, start_time=None, **kwargs):
        super().__init__(**kwargs)
        self.start_time = start_time
        self.use_legacy = use_legacy
        self.frequency = frequency  # 取样频率
        self.jank_threshold = jank_threshold
        self.device = device_id
        self.timeout = timeout
        self.surfaceview = surfaceview
        self.package = package_name
        self.fpscollector = SurfaceStatsCollector(self.device, self.frequency, package_name, fps_queue,
                                                  self.jank_threshold, self.surfaceview, self.use_legacy)

    def start(self):
        self.fpscollector.start(self.start_time)

    def stop(self):
        global collect_fps
        global collect_jank
        self.fpscollector.stop()
        return collect_fps, collect_jank

    def save(self):
        pass

    def parse(self, file_path):
        pass

    def get_fps_collector(self):
        return self.fpscollector
