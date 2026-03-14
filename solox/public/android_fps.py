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

    def start(self, start_time):
        if not self.use_legacy_method:
            try:
                self.focus_window = self.get_focus_activity()
                if self.focus_window.find('$') != -1:
                    self.focus_window = self.focus_window.replace('$', '\$')
            except Exception:
                logger.warning(u'Unable to dynamically obtain the current activity name, using page_ Flip statistics full screen frame rate')
                self.use_legacy_method = True
                self.surface_before = self._get_surface_stats_legacy()
        else:
            logger.debug("dumpsys SurfaceFlinger --latency-clear is none")
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
        dumpsys_result = adb.shell(cmd='dumpsys window windows', deviceId=self.device)
        dumpsys_result_list = dumpsys_result.split('\n')
        for line in dumpsys_result_list:
            if line.find('mCurrentFocus') != -1:
                activity_line = line.strip()
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
                    # logger.debug('FPS:%2s'%fps)
                    collect_fps = fps
                else:
                    refresh_period = data[0]
                    timestamps = data[1]
                    collect_time = data[2]
                    # fps,jank = self._calculate_results(refresh_period, timestamps)
                    fps, jank = self._calculate_results_new(refresh_period, timestamps)
                    # logger.debug('FPS:%2s Jank:%s'%(fps,jank))
                    collect_fps = fps
                    collect_jank = jank
                time_consume = time.time() - before
                delta_inter = self.frequency - time_consume
                if delta_inter > 0:
                    time.sleep(delta_inter)
            except:
                logger.error("an exception hanpend in fps _calculator_thread ,reason unkown!")
                s = traceback.format_exc()
                logger.debug(s)
                if self.fps_queue:
                    self.fps_queue.task_done()

    def _collector_thread(self):
        is_first = True
        while not self.stop_event.is_set():
            try:
                before = time.time()
                if self.use_legacy_method:
                    surface_state = self._get_surface_stats_legacy()
                    if surface_state:
                        self.data_queue.put(surface_state)
                else:
                    timestamps = []
                    refresh_period, new_timestamps = self._get_surfaceflinger_frame_data()
                    if refresh_period is None or new_timestamps is None:
                        self.focus_window = self.get_focus_activity()
                        logger.warning("refresh_period is None or timestamps is None")
                        continue
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
                        cur_focus_window = self.get_focus_activity()
                        if self.focus_window != cur_focus_window:
                            self.focus_window = cur_focus_window
                            continue
                    self.data_queue.put((refresh_period, timestamps, time.time()))
                    time_consume = time.time() - before
                    delta_inter = self.frequency - time_consume
                    if delta_inter > 0:
                        time.sleep(delta_inter)
            except:
                logger.error("an exception hanpend in fps _collector_thread , reason unkown!")
                s = traceback.format_exc()
                logger.debug(s)
                if self.fps_queue:
                    self.fps_queue.task_done()
        self.data_queue.put(u'Stop')

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
        return:(16.6,[[t1,t2,t3],[t4,t5,t6]])
        Returns:
            A tuple containing:
            - The display's nominal refresh period in seconds.
            - A list of timestamps signifying frame presentation times in seconds.
            The return value may be (None, None) if there was no data collected (for
            example, if the app was closed before the collector thread has finished).
        """
        # shell dumpsys SurfaceFlinger --latency <window name>
        # prints some information about the last 128 frames displayed in
        # that window.
        # The data returned looks like this:
        # 16954612
        # 7657467895508     7657482691352     7657493499756
        # 7657484466553     7657499645964     7657511077881
        # 7657500793457     7657516600576     7657527404785
        # (...)
        #
        # The first line is the refresh period (here 16.95 ms), it is followed
        # by 128 lines w/ 3 timestamps in nanosecond each:
        # A) when the app started to draw
        # B) the vsync immediately preceding SF submitting the frame to the h/w
        # C) timestamp immediately after SF submitted that frame to the h/w
        #
        # The difference between the 1st and 3rd timestamp is the frame-latency.
        # An interesting data is when the frame latency crosses a refresh period
        # boundary, this can be calculated this way:
        #
        # ceil((C - A) / refresh-period)
        #
        # (each time the number above changes, we have a "jank").
        # If this happens a lot during an animation, the animation appears
        # janky, even if it runs at 60 fps in average.
        #

        # Google Pixel 2 android8.0 dumpsys SurfaceFlinger --latency结果
        # 16666666
        # 0       0       0
        # 0       0       0
        # 0       0       0
        # 0       0       0
        # 但华为 荣耀9 android8.0 dumpsys SurfaceFlinger --latency结果是正常的 但数据更新很慢  也不能用来计算fps
        # 16666666
        # 9223372036854775807     3618832932780   9223372036854775807
        # 9223372036854775807     3618849592155   9223372036854775807
        # 9223372036854775807     3618866251530   9223372036854775807

        refresh_period = None
        timestamps = []
        nanoseconds_per_second = 1e9
        pending_fence_timestamp = (1 << 63) - 1
        if self.surfaceview is not True:
            results = adb.shell(
                cmd='dumpsys SurfaceFlinger --latency %s' % self.focus_window, deviceId=self.device)
            results = results.replace("\r\n", "\n").splitlines()
            refresh_period = int(results[0]) / nanoseconds_per_second
            results = adb.shell(cmd='dumpsys gfxinfo %s framestats' % self.package_name, deviceId=self.device)
            results = results.replace("\r\n", "\n").splitlines()
            if not len(results):
                return (None, None)
            isHaveFoundWindow = False
            PROFILEDATA_line = 0
            activity = self.focus_window
            if self.focus_window.__contains__('#'):
                activity = activity.split('#')[0]
            for line in results:
                if not isHaveFoundWindow:
                    if "Window" in line and activity in line:
                        isHaveFoundWindow = True
                if not isHaveFoundWindow:
                    continue
                if "PROFILEDATA" in line:
                    PROFILEDATA_line += 1
                fields = []
                fields = line.split(",")
                if fields and '0' == fields[0]:
                    # https://www.cnblogs.com/zhengna/p/10032078.html
                    # 1 INTENDED_VSYNC
                    # 2 VSYNC
                    # 13 FRAME_COMPLETED
                    timestamp = [int(fields[1]), int(fields[2]), int(fields[13])]
                    if timestamp[1] == pending_fence_timestamp:
                        continue
                    timestamp = [_timestamp / nanoseconds_per_second for _timestamp in timestamp]
                    timestamps.append(timestamp)
                if 2 == PROFILEDATA_line:
                    break
        else:
            # self.focus_window = self.get_surfaceview_activity()
            self.focus_window = self.get_surfaceview()
            results = adb.shell(
                cmd='dumpsys SurfaceFlinger --latency \\"%s\\"' % self.focus_window, deviceId=self.device)
            results = results.replace("\r\n", "\n").splitlines()
            if len(results) <= 1 or int(results[-2].split()[0]) ==0:
                self.focus_window = self.get_surfaceview_activity()
                results = adb.shell(
                cmd='dumpsys SurfaceFlinger --latency \\"%s\\"' % self.focus_window, deviceId=self.device)
                results = results.replace("\r\n", "\n").splitlines()
            if not len(results):
                return (None, None)
            if not results[0].isdigit():
                return (None, None)
            try:
                refresh_period = int(results[0]) / nanoseconds_per_second
            except Exception as e:
                logger.exception(e)
                return (None, None)
            # If a fence associated with a frame is still pending when we query the
            # latency data, SurfaceFlinger gives the frame a timestamp of INT64_MAX.
            # Since we only care about completed frames, we will ignore any timestamps
            # with this value.
            
            for line in results[2:]:
                fields = line.split()
                if len(fields) != 3:
                    continue
                timestamp = [int(fields[0]), int(fields[1]), int(fields[2])]
                if timestamp[1] == pending_fence_timestamp:
                    continue
                timestamp = [_timestamp / nanoseconds_per_second for _timestamp in timestamp]
                timestamps.append(timestamp)
        return (refresh_period, timestamps)

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
        match = re.search('^Result: Parcel\((\w+)', ret)
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
            match = re.search(r'Parcel\((\w+)', ret)
            if match:
                return int(match.group(1), 16)
        except Exception:
            traceback.print_exc()
        return -1

    def _get_fps_by_page_flip(self):
        """Calculate FPS using page flip count difference over 1 second.

        This is the most reliable fallback - works on all Android versions
        and all app types including game engines. Measures global screen
        frame rate (not per-app), but ensures FPS is never 0 when the
        screen is actively updating.

        Returns:
            tuple: (fps, 0) - jank is always 0 for this method
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
