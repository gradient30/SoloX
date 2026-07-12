import datetime
import re
import time
import os
import json
import sys
from logzero import logger
from typing import Optional
import tidevice
from tidevice._types import ConnectionType
from tidevice._usbmux import Usbmux
from tidevice._device import Device
import multiprocessing
import solox.public._iosPerf as iosP
from solox.public.iosperf._perf import DataType, Performance
from solox.public.adb import adb
from solox.public.common import Devices, File, Method, Platform, Scrcpy
from solox.public.android_fps import FPSMonitor, SurfaceStatsCollector, TimeUtils

d = Devices()
f = File()
m = Method()
um: Usbmux = None  # Usbmux

class Target:
    CPU = 'cpu'
    Memory = 'memory'
    MemoryDetail = 'memory_detail'
    Battery = 'battery'
    Network = 'network'
    FPS = 'fps'
    GPU = 'gpu'
    DISK = 'disk'

class CPU(object):

    def __init__(self, pkgName, deviceId, platform=Platform.Android, pid=None):
        self.pkgName = pkgName
        self.deviceId = deviceId
        self.platform = platform
        self.pid = pid
        if self.pid is None and self.platform == Platform.Android:
            self.pid = d.getPid(pkgName=self.pkgName, deviceId=self.deviceId)[0].split(':')[0]

    def getprocessCpuStat(self):
        """get the cpu usage of a process at a certain time"""
        cmd = 'cat /proc/{}/stat'.format(self.pid)
        result = adb.shell(cmd=cmd, deviceId=self.deviceId)
        r = re.compile("\\s+")
        toks = r.split(result)
        processCpu = float(toks[13]) + float(toks[14]) + float(toks[15]) + float(toks[16])
        return processCpu

    def getTotalCpuStat(self):
        """get the total cpu usage at a certain time"""
        cmd = 'cat /proc/stat |{} ^cpu'.format(d.filterType())
        result = adb.shell(cmd=cmd, deviceId=self.deviceId)
        totalCpu = 0
        lines = result.split('\n')
        lines.pop(0)
        for line in lines:
            toks = line.split()
            if toks[1] in ['', ' ']:
                toks.pop(1)
            for i in range(1, 8):
                totalCpu += float(toks[i])
        return float(totalCpu)
    
    def getCpuCoreStat(self):
        """get the core cpu usage at a certain time"""
        cmd = 'cat /proc/stat |{} ^cpu'.format(d.filterType())
        result = adb.shell(cmd=cmd, deviceId=self.deviceId)
        coreCpu = 0
        coreCpuList = []
        lines = result.split('\n')
        lines.pop(0)
        for line in lines:
            toks = line.split()
            if toks[1] in ['', ' ']:
                toks.pop(1)
            for i in range(1, 8):
                coreCpu += float(toks[i])
            coreCpuList.append(coreCpu)
            coreCpu = 0
        return coreCpuList
    
    def getCoreIdleCpuStat(self):
        """get the core idel cpu usage at a certain time"""
        cmd = 'cat /proc/stat |{} ^cpu'.format(d.filterType())
        result = adb.shell(cmd=cmd, deviceId=self.deviceId)
        idleCpuList = []
        idleCpu = 0
        lines = result.split('\n')
        lines.pop(0)
        for line in lines:
            toks = line.split()
            if toks[1] in ['', ' ']:
                toks.pop(1)
            idleCpu += float(toks[4])
            idleCpuList.append(idleCpu)
            idleCpu = 0
        return idleCpuList
    
    def getIdleCpuStat(self):
        """get the total cpu usage at a certain time"""
        cmd = 'cat /proc/stat |{} ^cpu'.format(d.filterType())
        result = adb.shell(cmd=cmd, deviceId=self.deviceId)
        idleCpu = 0
        lines = result.split('\n')
        lines.pop(0)
        for line in lines:
            toks = line.split()
            if toks[1] in ['', ' ']:
                toks.pop(1)
            idleCpu += float(toks[4])
        return idleCpu
    
    def getCoreCpuRate(self, cores=0,noLog=False):
        try:
            processCpuTime_1 = self.getprocessCpuStat()
            coreCpuTotalTime_List1 = self.getCpuCoreStat()
            time.sleep(1)
            processCpuTime_2 = self.getprocessCpuStat()
            coreCpuTotalTime_List2 = self.getCpuCoreStat()
            coreCpuRateList = list()
            for i in range(len(coreCpuTotalTime_List1)):
                coreCpuRate = round(float((processCpuTime_2 - processCpuTime_1) / (coreCpuTotalTime_List2[i] - coreCpuTotalTime_List1[i]) * 100), 2)
                coreCpuRate /= cores
                coreCpuRate = round(float(coreCpuRate), 2)
                coreCpuRateList.append(coreCpuRate)
                if noLog is False:
                    apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
                    f.add_log(os.path.join(f.report_dir,'cpu{}.log'.format(i)), apm_time, coreCpuRate)
        except Exception as e:
            if len(d.getPid(self.deviceId, self.pkgName)) == 0:
                logger.error('[CPU Core] {} : No process found'.format(self.pkgName))
            else:
                logger.exception(e)
        return coreCpuRateList    

    def getAndroidCpuRate(self, noLog=False):
        """获取 Android 进程 CPU 占用率(%)。

        口径说明（重要）：本方法把进程 CPU 时间增量除以**全部核心** CPU 时间
        增量之和，即 **100% = 全机所有核心满载**（如 8 核机上单核跑满≈12.5%）。
        这与 ``top`` / PerfDog 的"100%=单核"口径不同——与后者对比时需 ×核数。
        经真机核对：本方法 app% × 核数 ≈ ``dumpsys cpuinfo`` 的每核百分比。
        """
        try:
            processCpuTime_1 = self.getprocessCpuStat()
            totalCpuTime_1 = self.getTotalCpuStat()
            idleCputime_1 = self.getIdleCpuStat()
            time.sleep(1)
            processCpuTime_2 = self.getprocessCpuStat()
            totalCpuTime_2 = self.getTotalCpuStat()
            idleCputime_2 = self.getIdleCpuStat()
            appCpuRate = round(float((processCpuTime_2 - processCpuTime_1) / (totalCpuTime_2 - totalCpuTime_1) * 100), 2)
            sysCpuRate = round(float(((totalCpuTime_2 - idleCputime_2) - (totalCpuTime_1 - idleCputime_1)) / (totalCpuTime_2 - totalCpuTime_1) * 100), 2)
            if noLog is False:
                apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
                f.add_log(os.path.join(f.report_dir,'cpu_app.log'), apm_time, appCpuRate)
                f.add_log(os.path.join(f.report_dir,'cpu_sys.log'), apm_time, sysCpuRate)
        except Exception as e:
            appCpuRate, sysCpuRate = 0, 0
            if len(d.getPid(self.deviceId, self.pkgName)) == 0:
                logger.error('[CPU] {} : No process found'.format(self.pkgName))
            else:
                logger.exception(e)
        return appCpuRate, sysCpuRate

    def getiOSCpuRate(self, noLog=False):
        """get the iOS cpu rate of a process, unit:%"""
        apm = iosPerformance(self.pkgName, self.deviceId)
        appCpuRate = round(float(apm.getPerformance(apm.cpu)[0]), 2)
        sysCpuRate = round(float(apm.getPerformance(apm.cpu)[1]), 2)
        if noLog is False:
            apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
            f.add_log(os.path.join(f.report_dir,'cpu_app.log'), apm_time, appCpuRate)
            f.add_log(os.path.join(f.report_dir,'cpu_sys.log'), apm_time, sysCpuRate)
        return appCpuRate, sysCpuRate

    def getCpuRate(self, noLog=False):
        """Get the cpu rate of a process, unit:%"""
        appCpuRate, systemCpuRate = self.getAndroidCpuRate(noLog) if self.platform == Platform.Android else self.getiOSCpuRate(noLog)
        return appCpuRate, systemCpuRate    

class Memory(object):
    def __init__(self, pkgName, deviceId, platform=Platform.Android, pid=None):
        self.pkgName = pkgName
        self.deviceId = deviceId
        self.platform = platform
        self.pid = pid
        if self.pid is None and self.platform == Platform.Android:
            self.pid = d.getPid(pkgName=self.pkgName, deviceId=self.deviceId)[0].split(':')[0]

    def getAndroidMemory(self):
        """Get the Android memory ,unit:MB"""
        try:
            cmd = 'dumpsys meminfo {}'.format(self.pid)
            output = adb.shell(cmd=cmd, deviceId=self.deviceId)
            m_total = re.search(r'TOTAL\s*(\d+)', output)
            if not m_total:
                m_total = re.search(r'TOTAL PSS:\s*(\d+)', output)
            m_swap = re.search(r'TOTAL SWAP PSS:\s*(\d+)', output)
            if not m_swap:
                m_swap = re.search(r'TOTAL SWAP \(KB\):\s*(\d+)', output)
            totalPass = round(float(float(m_total.group(1))) / 1024, 2)
            swapPass = round(float(float(m_swap.group(1))) / 1024, 2)
        except Exception as e:
            totalPass, swapPass= 0, 0
            if len(d.getPid(self.deviceId, self.pkgName)) == 0:
                logger.error('[Memory] {} : No process found'.format(self.pkgName))
            else:
                logger.exception(e)
        return totalPass, swapPass
    
    def getAndroidMemoryDetail(self, noLog=False):
        """Get the Android detail memory ,unit:MB"""
        try:
            cmd = 'dumpsys meminfo {}'.format(self.pid)
            output = adb.shell(cmd=cmd, deviceId=self.deviceId)
            m_java = re.search(r'Java Heap:\s*(\d+)', output)
            m_native = re.search(r'Native Heap:\s*(\d+)', output)
            m_code = re.search(r'Code:\s*(\d+)', output)
            m_stack = re.search(r'Stack:\s*(\d+)', output)
            m_graphics = re.search(r'Graphics:\s*(\d+)', output)
            m_private = re.search(r'Private Other:\s*(\d+)', output)
            m_system = re.search(r'System:\s*(\d+)', output)
            java_heap = round(float(float(m_java.group(1))) / 1024, 2)
            native_heap = round(float(float(m_native.group(1))) / 1024, 2)
            code_pss = round(float(float(m_code.group(1))) / 1024, 2)
            stack_pss = round(float(float(m_stack.group(1))) / 1024, 2)
            graphics_pss = round(float(float(m_graphics.group(1))) / 1024, 2)
            private_pss = round(float(float(m_private.group(1))) / 1024, 2)
            system_pss = round(float(float(m_system.group(1))) / 1024, 2)
            memory_dict = dict(
                java_heap=java_heap,
                native_heap=native_heap,
                code_pss=code_pss,
                stack_pss=stack_pss,
                graphics_pss=graphics_pss,
                private_pss=private_pss,
                system_pss=system_pss
            )
            if noLog is False:
                apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
                f.add_log(os.path.join(f.report_dir,'mem_java_heap.log'), apm_time, memory_dict.get('java_heap'))
                f.add_log(os.path.join(f.report_dir,'mem_native_heap.log'), apm_time, memory_dict.get('native_heap'))
                f.add_log(os.path.join(f.report_dir,'mem_code_pss.log'), apm_time, memory_dict.get('code_pss'))
                f.add_log(os.path.join(f.report_dir,'mem_stack_pss.log'), apm_time, memory_dict.get('stack_pss'))
                f.add_log(os.path.join(f.report_dir,'mem_graphics_pss.log'), apm_time, memory_dict.get('graphics_pss'))
                f.add_log(os.path.join(f.report_dir,'mem_private_pss.log'), apm_time, memory_dict.get('private_pss'))
                f.add_log(os.path.join(f.report_dir,'mem_system_pss.log'), apm_time, memory_dict.get('system_pss'))
        except Exception as e:
            memory_dict = dict(
                java_heap=0,
                native_heap=0,
                code_pss=0,
                stack_pss=0,
                graphics_pss=0,
                private_pss=0,
                system_pss=0
            )
            if len(d.getPid(self.deviceId, self.pkgName)) == 0:
                logger.error('[Memory Detail] {} : No process found'.format(self.pkgName))
            else:
                logger.exception(e)
        return memory_dict

    def getiOSMemory(self):
        """获取 iOS 内存占用（单位 MB）。

        说明：iOS 采用 Instruments 上报的 ``physFootprint`` 作为物理内存，
        系统层面不向调试通道暴露 App 级 Swap 指标。为避免返回伪造的 0 值让
        用户误以为"Swap=0"，这里将 swap 明确置为 ``None``（表示"该平台不适用"），
        由上层 API 转换为 ``null`` + ``swap_supported=false``。

        :return: ``(totalPass, None)``，其中 None 表示 iOS 无 Swap 概念。
        """
        apm = iosPerformance(self.pkgName, self.deviceId)
        totalPass = round(float(apm.getPerformance(apm.memory)), 2)
        swapPass = None  # iOS 无 App 级 Swap 指标，None 表示"不适用"而非 0
        return totalPass, swapPass

    def getProcessMemory(self, noLog=False):
        """Get the app memory"""
        totalPass, swapPass = self.getAndroidMemory() if self.platform == Platform.Android else self.getiOSMemory()
        if noLog is False:
            apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
            f.add_log(os.path.join(f.report_dir,'mem_total.log'), apm_time, totalPass)
            if self.platform == Platform.Android:
                f.add_log(os.path.join(f.report_dir,'mem_swap.log'), apm_time, swapPass)
        return totalPass, swapPass

class Battery(object):
    def __init__(self, deviceId, platform=Platform.Android):
        self.deviceId = deviceId
        self.platform = platform

    def getBattery(self, noLog=False):
        if self.platform == Platform.Android:
            level, temperature = self.getAndroidBattery(noLog)
            return level, temperature
        else:
            temperature, current, voltage, power = self.getiOSBattery(noLog)
            return temperature, current, voltage, power

    def getAndroidBattery(self, noLog=False):
        """Get android battery info, unit:%"""
        try:
            # Switch mobile phone battery to non-charging state
            self.recoverBattery()
            cmd = 'dumpsys battery set status 1'
            adb.shell(cmd=cmd, deviceId=self.deviceId)
            # Get phone battery info
            cmd = 'dumpsys battery'
            output = adb.shell(cmd=cmd, deviceId=self.deviceId)
            level = int(re.findall(r'level:\s?(\d+)', output)[0])
            temperature = int(re.findall(r'temperature:\s?(\d+)', output)[0]) / 10
            if noLog is False:
                 apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
                 f.add_log(os.path.join(f.report_dir,'battery_level.log'), apm_time, level)
                 f.add_log(os.path.join(f.report_dir,'battery_tem.log'), apm_time, temperature)
        except Exception as e:
            level, temperature = 0, 0
            logger.exception(e)
        return level, temperature

    def getiOSBattery(self, noLog=False):
        """Get ios battery info, unit:%"""
        d  = tidevice.Device(udid=self.deviceId)
        ioDict =  d.get_io_power()
        tem = m._setValue(ioDict['Diagnostics']['IORegistry']['Temperature'] / 100)
        current = m._setValue(abs(ioDict['Diagnostics']['IORegistry']['InstantAmperage']))
        voltage = m._setValue(ioDict['Diagnostics']['IORegistry']['Voltage'])
        power = current * voltage / 1000
        if noLog is False:
            apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
            f.add_log(os.path.join(f.report_dir,'battery_tem.log'), apm_time, tem) # unknown
            f.add_log(os.path.join(f.report_dir,'battery_current.log'), apm_time, current) #mA
            f.add_log(os.path.join(f.report_dir,'battery_voltage.log'), apm_time, voltage) #mV
            f.add_log(os.path.join(f.report_dir,'battery_power.log'), apm_time, power)
        return tem, current, voltage, power

    def recoverBattery(self):
        """Reset phone charging status"""
        cmd = 'dumpsys battery reset'
        adb.shell(cmd=cmd, deviceId=self.deviceId)

class Network(object):

    def __init__(self, pkgName, deviceId, platform=Platform.Android, pid=None):
        self.pkgName = pkgName
        self.deviceId = deviceId
        self.platform = platform
        self.pid = pid
        if self.pid is None and self.platform == Platform.Android:
            self.pid = d.getPid(pkgName=self.pkgName, deviceId=self.deviceId)[0].split(':')[0]

    def getAndroidNet(self, wifi=True):
        """获取 Android 上/下行流量增量(KB)。

        数据源为 ``/proc/<pid>/net/dev`` 的 ``wlan0``(WiFi)/``rmnet_ipa0``(蜂窝)
        计数。**范围说明（重要）**：该文件是**网络命名空间级**统计，而 Android
        普通 App 共享默认命名空间，因此读到的是**采集窗口内本机该网卡的总流量**，
        并非严格的"仅该 App"流量；当被测 App 为前台主要流量来源时可近似其流量。
        严格 App 级流量需 UID 级统计（Android 10+ 的 eBPF，通常需 root），本项目
        未采用。返回 ``(sendNum, recNum)``，单位 KB。
        """
        try:
            if wifi is True:
                net = 'wlan0'
                adb.shell(cmd='svc wifi enable', deviceId=self.deviceId)
            else:
                net = 'rmnet_ipa0'
                adb.shell(cmd='svc wifi disable', deviceId=self.deviceId)
                adb.shell(cmd='svc data enable', deviceId=self.deviceId)
            cmd = 'cat /proc/{}/net/dev |{} {}'.format(self.pid, d.filterType(), net)
            output_pre = adb.shell(cmd=cmd, deviceId=self.deviceId)
            m_pre = re.search(r'{}:\s*(\d+)\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*(\d+)'.format(net), output_pre)
            sendNum_pre = round(float(float(m_pre.group(2)) / 1024), 2)
            recNum_pre = round(float(float(m_pre.group(1)) / 1024), 2)
            time.sleep(0.5)
            output_final = adb.shell(cmd=cmd, deviceId=self.deviceId)
            m_final = re.search(r'{}:\s*(\d+)\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*(\d+)'.format(net), output_final)
            sendNum_final = round(float(float(m_final.group(2)) / 1024), 2)
            recNum_final = round(float(float(m_final.group(1)) / 1024), 2)
            sendNum = round(float(sendNum_final - sendNum_pre), 2)
            recNum = round(float(recNum_final - recNum_pre), 2)
        except Exception as e:
            sendNum, recNum = 0, 0
            if len(d.getPid(self.deviceId, self.pkgName)) == 0:
                logger.error('[Network] {} : No process found'.format(self.pkgName))
            else:
                logger.exception(e)
        return sendNum, recNum

    def setAndroidNet(self, wifi=True):
        try:
            if wifi is True:
                net = 'wlan0'
                adb.shell(cmd='svc wifi enable', deviceId=self.deviceId)
            else:
                net = 'rmnet_ipa0'
                adb.shell(cmd='svc wifi disable', deviceId=self.deviceId)
                adb.shell(cmd='svc data enable', deviceId=self.deviceId)
            cmd = f'cat /proc/{self.pid}/net/dev |{d.filterType()} {net}'
            output_pre = adb.shell(cmd=cmd, deviceId=self.deviceId)
            m = re.search(r'{}:\s*(\d+)\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*\d+\s*(\d+)'.format(net), output_pre)    
            sendNum = round(float(float(m.group(2)) / 1024), 2)
            recNum = round(float(float(m.group(1)) / 1024), 2)
        except Exception as e:
            sendNum, recNum = 0, 0
            if len(d.getPid(self.deviceId, self.pkgName)) == 0:
                logger.error('[Network] {} : No process found'.format(self.pkgName))
            else:
                logger.exception(e)
        return sendNum, recNum


    def getiOSNet(self):
        """Get iOS upflow and downflow data"""
        apm = iosPerformance(self.pkgName, self.deviceId)
        apm_data = apm.getPerformance(apm.network)
        sendNum = round(float(apm_data[1]), 2)
        recNum = round(float(apm_data[0]), 2)
        return sendNum, recNum

    def getNetWorkData(self, wifi=True, noLog=False):
        """Get the upflow and downflow data, unit:KB"""
        sendNum, recNum = self.getAndroidNet(wifi) if self.platform == Platform.Android else self.getiOSNet()
        if noLog is False:
            apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
            f.add_log(os.path.join(f.report_dir,'upflow.log'), apm_time, sendNum)
            f.add_log(os.path.join(f.report_dir,'downflow.log'), apm_time, recNum)
        return sendNum, recNum

class FPS(object):
    AndroidFPS = None

    @classmethod
    def getObject(cls, *args, **kwargs):
        if kwargs['platform'] == Platform.Android:
            if cls.AndroidFPS is None:
                cls.AndroidFPS = FPS(*args, **kwargs)
            return cls.AndroidFPS
        return FPS(*args, **kwargs)

    @classmethod
    def clear(cls):
        cls.AndroidFPS = None

    def __init__(self, pkgName, deviceId, platform=Platform.Android, surfaceview=True):
        self.pkgName = pkgName
        self.deviceId = deviceId
        self.platform = platform
        self.surfaceview = surfaceview
        self.apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
        self.monitors = None
        self.fps_meta = None  # credibility metadata from last FPS collection
        self.big_jank = 0

    def getAndroidFps(self, noLog=False):
        """get Android Fps, unit:HZ

        Uses synchronous one-shot collection: reads SurfaceFlinger buffer,
        waits 1 second, reads again, and calculates FPS from fresh frames.
        This eliminates thread race conditions that caused ~50fps underreporting.

        Populates self.fps_meta with credibility metadata.
        """
        try:
            collector = SurfaceStatsCollector(
                device=self.deviceId,
                frequency=1,
                package_name=self.pkgName,
                fps_queue=None,
                jank_threshold=166,
                surfaceview=self.surfaceview,
            )
            fps, jank = collector.collect_oneshot()
            self.fps_meta = collector.last_collection_meta
            big_jank = int((self.fps_meta or {}).get('big_jank', 0) or 0)
            self.big_jank = big_jank
            if noLog is False:
                apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
                f.add_log(os.path.join(f.report_dir,'fps.log'), apm_time, fps)
                f.add_log(os.path.join(f.report_dir,'jank.log'), apm_time, jank)
                f.add_log(os.path.join(f.report_dir,'big_jank.log'), apm_time, big_jank)
        except Exception as e:
            fps, jank = 0, 0
            self.big_jank = 0
            self.fps_meta = {'source': 'error', 'fps': 0, 'confidence': 'low',
                             'fresh_frame_count': 0, 'verified': False}
            if len(d.getPid(self.deviceId, self.pkgName)) == 0:
                logger.error('[FPS] {} : No process found'.format(self.pkgName))
            else:
                logger.exception(e)
        return fps, jank
    
    def getiOSFps(self, noLog=False):
        """获取 iOS 帧率。

        说明：iOS 侧数据源（Instruments graphics.opengl 通道）只提供每采样
        区间的聚合 FPS 标量 ``CoreAnimationFramesPerSecond``，**没有逐帧的
        display 时间戳**，因此无法按 PerfDog 口径计算 Jank/BigJank。为避免
        返回一个看似"已测量、零卡顿"的伪造 0 值误导用户，这里将 jank 明确
        置为 ``None``（表示"该平台暂不支持"），由上层 API 转换为 ``null`` +
        ``jank_supported=false``。

        :param noLog: 为 True 时不落地日志。
        :return: ``(fps, None)``，其中 None 表示 iOS 不支持 Jank 测量。
        """
        apm = iosPerformance(self.pkgName, self.deviceId)
        fps = int(apm.getPerformance(apm.fps))
        self.big_jank = None  # iOS 无法测量，None 表示"不支持"而非 0
        if noLog is False:
            apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
            f.add_log(os.path.join(f.report_dir,'fps.log'), apm_time, fps)
        return fps, None

    def getFPS(self, noLog=False):
        """get fps、jank (big_jank available via self.big_jank)

        Android 返回真实测得的 jank（int）；iOS 的 jank 为 None，表示该平台
        暂不支持 Jank 测量（原因见 :meth:`getiOSFps`）。
        """
        fps, jank = self.getAndroidFps(noLog) if self.platform == Platform.Android else self.getiOSFps(noLog)
        return fps, jank

class GPU(object):
    def __init__(self, pkgName, deviceId, platform=Platform.Android):
        self.pkgName = pkgName
        self.deviceId = deviceId
        self.platform = platform
        # iOS GPU 细分利用率（Android 无此口径，保持 None 表示不适用）
        self.renderer = None
        self.tiler = None
        # GPU 利用率是否可测：Android 依赖高通 kgsl sysfs，非 root 设备通常
        # 被 SELinux 拒绝读取。默认 True，读取失败时置 False，供上层如实标注
        # gpu_supported=false（而非伪造 0，误导用户以为"GPU 空闲"）。
        self.gpu_supported = True
        self.gpu_unsupported_reason = None

    def getAndroidGpuRate(self):
        """读取 Adreno(kgsl) GPU 利用率(%)。

        数据源 ``/sys/class/kgsl/kgsl-3d0/gpubusy`` 仅在 **已 root 或该 sysfs
        节点对 shell 可读** 时可用；多数非 root 设备（含本机骁龙 855）会返回
        ``Permission denied``。此时**返回 None 表示"不可用"**，绝不伪造 0。

        注意：``dumpsys gfxinfo`` 提供的是 HWUI 帧的 GPU 绘制耗时(ms) 与 HWUI
        显存，**不是 GPU 利用率**，且对 SurfaceView 游戏不反映真实渲染，故不能
        作为本指标的替代来源。

        :return: 利用率百分比(float)；不可用时返回 ``None``。
        """
        try:
            cmd = 'cat /sys/class/kgsl/kgsl-3d0/gpubusy'
            result = adb.shell(cmd=cmd, deviceId=self.deviceId)
            parts = (result or '').split()
            # 权限拒绝/节点不存在/输出非数值 → 判定为不可用
            if (len(parts) < 2
                    or not parts[0].lstrip('-').isdigit()
                    or not parts[1].lstrip('-').isdigit()):
                self.gpu_supported = False
                self.gpu_unsupported_reason = (
                    'GPU 利用率不可用：设备未 root 或无 kgsl sysfs 读取权限'
                )
                logger.warning(
                    '[GPU] %s 读取 kgsl gpubusy 失败（非 root/无权限）：%s',
                    self.deviceId, (result or '').strip()[:120]
                )
                return None
            busy, total = int(parts[0]), int(parts[1])
            if total == 0:
                self.gpu_supported = False
                self.gpu_unsupported_reason = 'GPU 利用率不可用：分母为 0'
                return None
            self.gpu_supported = True
            return round(busy / total * 100, 2)
        except Exception as e:
            self.gpu_supported = False
            self.gpu_unsupported_reason = 'GPU 利用率读取异常：{}'.format(e)
            logger.warning('[GPU] %s 读取异常：%s', self.deviceId, e)
            return None

    def getiOSGpuRate(self):
        """获取 iOS GPU 利用率。

        iOS Instruments 的 graphics.opengl 通道同时提供三个利用率：

        - Device：整体 GPU 利用率（作为主 gpu 值，与 Android 口径大致对应）
        - Renderer：像素/片段着色阶段利用率（对齐 PerfDog 的 Render）
        - Tiler：顶点/几何着色阶段利用率（对齐 PerfDog 的 Tiler）

        为保持 ``gpu.log`` 与既有报告不变，本方法仍返回 Device 标量作为主值，
        Renderer/Tiler 通过 ``self.renderer`` / ``self.tiler`` 暴露给上层 API。

        :return: Device 利用率标量（float）。
        """
        apm = iosPerformance(self.pkgName, self.deviceId)
        gpu = apm.getPerformance(apm.gpu)
        if isinstance(gpu, (tuple, list)):
            device = gpu[0]
            self.renderer = gpu[1] if len(gpu) > 1 else None
            self.tiler = gpu[2] if len(gpu) > 2 else None
            return device
        # 兼容底层可能返回单标量的旧行为
        return gpu

    def getGPU(self, noLog=False):
        """获取 GPU 利用率(%)。

        Android 不可用时返回 ``None``（见 :meth:`getAndroidGpuRate`）；仅在取到
        数值时才落地日志，避免把"不可用"写成 0 污染报告。
        """
        gpu = self.getAndroidGpuRate() if self.platform == Platform.Android else self.getiOSGpuRate()
        if noLog is False and gpu is not None:
            apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
            f.add_log(os.path.join(f.report_dir,'gpu.log'), apm_time, gpu)
        return gpu

class Disk(object):
    def __init__(self, deviceId, platform=Platform.Android):
        self.deviceId = deviceId
        self.platform = platform

    def setInitialDisk(self):
        disk_info = adb.shell(cmd='df', deviceId=self.deviceId)
        with open(os.path.join(f.report_dir,'initail_disk.log'), 'a+', encoding="utf-8") as file:
                file.write(disk_info)

    def setCurrentDisk(self):
        disk_info = adb.shell(cmd='df', deviceId=self.deviceId)
        with open(os.path.join(f.report_dir,'current_disk.log'), 'a+', encoding="utf-8") as file:
                file.write(disk_info)
    
    def getAndroidDisk(self):
        disk_info = adb.shell(cmd='df', deviceId=self.deviceId)
        disk_lines = disk_info.splitlines()
        disk_lines.pop(0)
        size_list = list()
        used_list = list()
        free_list = list()
        for line in disk_lines:
            disk_value_list = line.split()
            size_list.append(int(disk_value_list[1]))
            used_list.append(int(disk_value_list[2]))
            free_list.append(int(disk_value_list[3]))
        sum_size = sum(size_list)    
        sum_used = sum(used_list)
        sum_free = sum(free_list)
        disk_dict = {'disk_size':sum_size, 'used':sum_used, 'free': sum_free}
        return disk_dict

    def getiOSDisk(self):
        ios_device = tidevice.Device(udid=self.deviceId)
        disk_dict  = ios_device.storage_info()
        return disk_dict
    
    def getDisk(self, noLog=False):
        disk = self.getAndroidDisk() if self.platform == Platform.Android else self.getiOSDisk()
        if noLog is False:
            apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
            f.add_log(os.path.join(f.report_dir,'disk_used.log'), apm_time, disk.get('used'))
            f.add_log(os.path.join(f.report_dir,'disk_free.log'), apm_time, disk.get('free'))
        return disk    

class ThermalSensor(object):
    def __init__(self, deviceId, platform=Platform.Android):
        self.deviceId = deviceId
        self.platform = platform

    def setInitalThermalTemp(self):
        temp_list = list()
        typeLength = len(self.getThermalType())
        if typeLength > 3:
            for i in range(len(self.getThermalType())):
                cmd = 'cat /sys/class/thermal/thermal_zone{}/temp'.format(i)
                temp = adb.shell(cmd=cmd, deviceId=self.deviceId)
                temp_dict = {
                    'type':self.getThermalType()[i],
                    'temp':temp
                }
                temp_list.append(temp_dict)
            content = json.dumps(temp_list)
            f.create_file(filename='init_thermal_temp.json', content=content)
    
    def setCurrentThermalTemp(self):
        temp_list = list()
        typeLength = len(self.getThermalType())
        if typeLength > 3:
            for i in range(len(self.getThermalType())):
                cmd = 'cat /sys/class/thermal/thermal_zone{}/temp'.format(i)
                temp = adb.shell(cmd=cmd, deviceId=self.deviceId)
                temp_dict = {
                    'type':self.getThermalType()[i],
                    'temp':temp
                }
                temp_list.append(temp_dict)
            content = json.dumps(temp_list)
            f.create_file(filename='current_thermal_temp.json', content=content)

    def getThermalType(self):
        cmd = 'cat /sys/class/thermal/thermal_zone*/type'
        result = adb.shell(cmd=cmd, deviceId=self.deviceId)
        typeList = result.splitlines()
        return typeList

    def getThermalTemp(self):
        temp_list = list()
        typeLength = len(self.getThermalType())
        if typeLength > 3:
            for i in range(len(self.getThermalType())):
                cmd = 'cat /sys/class/thermal/thermal_zone{}/temp'.format(i)
                temp = adb.shell(cmd=cmd, deviceId=self.deviceId)
                temp_dict = {
                    'type':self.getThermalType()[i],
                    'temp':temp
                }
                temp_list.append(temp_dict)
            return temp_list 
        else:
            logger.exception('No permission')     

class Energy(object):
    def __init__(self, deviceId, packageName):
        self.deviceId = deviceId
        self.packageName = packageName
    
    def _complete_udid(self, udid: Optional[str] = None) -> str:
        infos = um.device_list()
        # Find udid exactly match
        for info in infos:
            if info.udid == udid:
                return udid
        if udid:
            sys.exit("Device for %s not detected" % udid)

        if len(infos) == 1:
            return infos[0].udid

        # filter only usb connected devices
        infos = [info for info in infos if info.conn_type == ConnectionType.USB]
        if not udid:
            if len(infos) >= 2:
                sys.exit("More than 2 usb devices detected")
            if len(infos) == 0:
                sys.exit("No local device detected")
            return infos[0].udid
        raise RuntimeError("No matched device", udid)

    def _udid2device(self, udid: Optional[str] = None) -> Device:
        _udid = self._complete_udid(udid)
        if _udid != udid:
            logger.debug("AutoComplete udid %s", _udid)
        del (udid)
        return Device(_udid, um)

    def getEnergy(self):
        d = self._udid2device(self.deviceId)
        ts = d.connect_instruments()
        pid = ts.app_launch(self.packageName)
        ts.start_energy_sampling(pid)
        time.sleep(1.0)
        ret = ts.get_process_energy_stats(pid)
        return ret
          
class iosPerformance(object):

    def __init__(self, pkgName, deviceId):
        self.pkgName = pkgName
        self.deviceId = deviceId
        self.apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
        self.cpu = DataType.CPU
        self.memory = DataType.MEMORY
        self.network = DataType.NETWORK
        self.fps = DataType.FPS
        self.gpu = DataType.GPU
        self.perfs = 0
        self.app_cpu = 0
        self.sys_cpu = 0
        self.downflow = 0
        self.upflow = 0

    def callback(self, _type: DataType, value: dict):
        if _type == 'network':
            self.downflow = value['downFlow']
            self.upflow = value['upFlow']
        else:
            self.perfs = value['value']

    def getPerformance(self, perfType: DataType):
        if perfType == DataType.NETWORK:
            perf = Performance(tidevice.Device(udid=self.deviceId), [perfType])
            perf.start(self.pkgName, callback=self.callback)
            time.sleep(3)
            perf.stop()
            perf_value = self.downflow, self.upflow
        else:
            perf = iosP.Performance(tidevice.Device(udid=self.deviceId), [perfType])
            perf_value = perf.start(self.pkgName, callback=self.callback)
        return perf_value

class initPerformanceService(object):
    CONFIG_DIR = os.path.dirname(os.path.realpath(__file__))
    CONIFG_PATH = os.path.join(CONFIG_DIR, 'config.json')

    @classmethod
    def get_status(cls):
        config_json = open(file=cls.CONIFG_PATH, mode='r').read()
        run_switch = json.loads(config_json).get('run_switch')
        return run_switch
    
    @classmethod
    def start(cls):
        config_json = dict()
        config_json['run_switch'] = 'on'
        with open(cls.CONIFG_PATH, "w") as file:
            json.dump(config_json, file)

    @classmethod
    def stop(cls):
        config_json = dict()
        config_json['run_switch'] = 'off'
        with open(cls.CONIFG_PATH, "w") as file:
            json.dump(config_json, file) 
        logger.info('stop solox success')    
        return True           

class AppPerformanceMonitor(initPerformanceService):
    """for python api"""

    def __init__(self, pkgName=None, platform=Platform.Android, deviceId=None,
                 surfaceview=True, noLog=True, pid=None, record=False, collect_all=False,
                 duration=0):
        self.pkgName = pkgName
        self.deviceId = deviceId
        self.platform = platform
        self.surfaceview = surfaceview
        self.noLog = noLog
        self.pid = pid
        self.record = record
        self.collect_all = collect_all
        self.duration = duration
        self.end_time = time.time() + self.duration
        d.devicesCheck(platform=self.platform, deviceid=self.deviceId, pkgname=self.pkgName)
        self.start()
    
    def collectCpu(self):
        _cpu = CPU(self.pkgName, self.deviceId, self.platform, pid=self.pid)
        result = {}
        while self.get_status() == 'on':
            appCpuRate, systemCpuRate = _cpu.getCpuRate(noLog=self.noLog)
            result = {'appCpuRate': appCpuRate, 'systemCpuRate': systemCpuRate}
            logger.info(f'cpu: {result}')
            if self.collect_all is False:
                break
            if self.duration > 0 and time.time() > self.end_time:
                break
        return result

    def collectCoreCpu(self):
        _cpucore = CPU(self.pkgName, self.deviceId, self.platform, pid=self.pid)
        cores = d.getCpuCores(self.deviceId)
        value = _cpucore.getCoreCpuRate(cores=cores, noLog=self.noLog)
        result = {'cpu{}'.format(value.index(element)):element for element in  value}
        logger.info(f'cpu core: {result}')
        return result    
    
    def collectMemory(self):
        _memory = Memory(self.pkgName, self.deviceId, self.platform, pid=self.pid)
        result = {}
        while self.get_status() == 'on':
            total, swap = _memory.getProcessMemory(noLog=self.noLog)
            result = {'total': total, 'swap': swap}
            logger.info(f'memory: {result}')
            if self.collect_all is False:
                break
            if self.duration > 0 and time.time() > self.end_time:
                break
        return result
    
    def collectMemoryDetail(self):
        _memory = Memory(self.pkgName, self.deviceId, self.platform, pid=self.pid)
        result = {}
        while self.get_status() == 'on':
            if self.platform == Platform.iOS:
                break
            result = _memory.getAndroidMemoryDetail(noLog=self.noLog)
            logger.info(f'memory detail: {result}')
            if self.collect_all is False:
                break
            if self.duration > 0 and time.time() > self.end_time:
                break
        return result
    
    def collectBattery(self):
        _battery = Battery(self.deviceId, self.platform)
        result = {}
        while self.get_status() == 'on':
            final = _battery.getBattery(noLog=self.noLog)
            if self.platform == Platform.Android:
                result = {'level': final[0], 'temperature': final[1]}
            else:
                result = {'temperature': final[0], 'current': final[1], 'voltage': final[2], 'power': final[3]}
            logger.info(f'battery: {result}')
            if self.collect_all is False:
                break
            if self.duration > 0 and time.time() > self.end_time:
                break
        return result

    def collectNetwork(self, wifi=True):
        _network = Network(self.pkgName, self.deviceId, self.platform, pid=self.pid)
        if self.noLog is False and self.platform == Platform.Android:
            data = _network.setAndroidNet(wifi=wifi)
            f.record_net('pre', data[0], data[1])
        result = {}
        while self.get_status() == 'on':
            upFlow, downFlow = _network.getNetWorkData(wifi=wifi,noLog=self.noLog)
            result = {'send': upFlow, 'recv': downFlow}
            logger.info(f'network: {result}')
            if self.collect_all is False:
                break
            if self.duration > 0 and time.time() > self.end_time:
                break
        return result

    def collectFps(self):
        _fps = FPS(self.pkgName, self.deviceId, self.platform, self.surfaceview)
        result = {}
        while self.get_status() == 'on':
            fps, jank = _fps.getFPS(noLog=self.noLog)
            result = {'fps': fps, 'jank': jank}
            logger.info(f'fps: {result}')
            if self.collect_all is False:
                break
            if self.duration > 0 and time.time() > self.end_time:
                break
        return result

    def collectGpu(self):
        _gpu = GPU(self.pkgName, self.deviceId, self.platform)
        result = {}
        while self.get_status() == 'on':
            gpu = _gpu.getGPU(noLog=self.noLog)
            result = {'gpu': gpu}
            logger.info(f'gpu: {result}')
            if self.collect_all is False:
                break
            if self.duration > 0 and time.time() > self.end_time:
                break
        return result
    
    def collectThermal(self):
         _thermal = ThermalSensor(self.deviceId, self.platform)
         result = _thermal.getThermalTemp()
         logger.info(f'thermal: {result}')
         return result
    
    def collectDisk(self):
        _disk = Disk(self.deviceId, self.platform)
        result = _disk.getDisk()
        logger.info(f'disk: {result}')
        return result
    
    def setPerfs(self, report_path=None):
        match(self.platform):
            case Platform.Android:
                adb.shell(cmd='dumpsys battery reset', deviceId=self.deviceId)
                _flow = Network(self.pkgName, self.deviceId, self.platform, pid=self.pid)
                data = _flow.setAndroidNet()
                f.record_net('end', data[0], data[1])
                scene = f.make_report(app=self.pkgName, devices=self.deviceId,
                                      video=0, platform=self.platform, model='normal')
                summary = f._setAndroidPerfs(scene)
                summary_dict = {}
                summary_dict['app'] = summary['app']
                summary_dict['platform'] = summary['platform']
                summary_dict['devices'] = summary['devices']
                summary_dict['ctime'] = summary['ctime']
                summary_dict['cpu_app'] = summary['cpuAppRate']
                summary_dict['cpu_sys'] = summary['cpuSystemRate']
                summary_dict['mem_total'] = summary['totalPassAvg']
                summary_dict['mem_swap'] = summary['swapPassAvg']
                summary_dict['fps'] = summary['fps']
                summary_dict['jank'] = summary['jank']
                summary_dict['level'] = summary['batteryLevel']
                summary_dict['tem'] = summary['batteryTeml']
                summary_dict['net_send'] = summary['flow_send']
                summary_dict['net_recv'] = summary['flow_recv']
                summary_dict['gpu'] = summary['gpu']
                summary_dict['cpu_charts'] = f.getCpuLog(Platform.Android, scene)
                summary_dict['mem_charts'] = f.getMemLog(Platform.Android, scene)
                summary_dict['mem_detail_charts'] = f.getMemDetailLog(Platform.Android, scene)
                summary_dict['net_charts'] = f.getFlowLog(Platform.Android, scene)
                summary_dict['battery_charts'] = f.getBatteryLog(Platform.Android, scene)
                summary_dict['fps_charts'] = f.getFpsLog(Platform.Android, scene)['fps']
                summary_dict['jank_charts'] = f.getFpsLog(Platform.Android, scene)['jank']
                summary_dict['gpu_charts'] = f.getGpuLog(Platform.Android, scene)
                f.make_android_html(scene=scene, summary=summary_dict, report_path=report_path)
            case Platform.iOS:
                scene = f.make_report(app=self.pkgName, devices=self.deviceId,
                                      video=0, platform=self.platform, model='normal')
                summary = f._setiOSPerfs(scene)
                summary_dict = {}
                summary_dict['app'] = summary['app']
                summary_dict['platform'] = summary['platform']
                summary_dict['devices'] = summary['devices']
                summary_dict['ctime'] = summary['ctime']
                summary_dict['cpu_app'] = summary['cpuAppRate']
                summary_dict['cpu_sys'] = summary['cpuSystemRate']
                summary_dict['mem_total'] = summary['totalPassAvg']
                summary_dict['fps'] = summary['fps']
                summary_dict['current'] = summary['batteryCurrent']
                summary_dict['voltage'] = summary['batteryVoltage']
                summary_dict['power'] = summary['batteryPower']
                summary_dict['tem'] = summary['batteryTeml']
                summary_dict['gpu'] = summary['gpu']
                summary_dict['net_send'] = summary['flow_send']
                summary_dict['net_recv'] = summary['flow_recv']
                summary_dict['cpu_charts'] = f.getCpuLog(Platform.iOS, scene)
                summary_dict['mem_charts'] = f.getMemLog(Platform.iOS, scene)
                summary_dict['net_charts'] = f.getFlowLog(Platform.iOS, scene)
                summary_dict['battery_charts'] = f.getBatteryLog(Platform.iOS, scene)
                summary_dict['fps_charts'] = f.getFpsLog(Platform.iOS, scene)
                summary_dict['gpu_charts'] = f.getGpuLog(Platform.iOS, scene)
                f.make_ios_html(scene=scene, summary=summary_dict, report_path=report_path)
            case _:
                raise Exception('platfrom is invalid')

    def collectAll(self, report_path=None):
        try:
            f.clear_file()
            process_num = 8 if self.record else 7
            pool = multiprocessing.Pool(processes=process_num)
            pool.apply_async(self.collectCpu)
            pool.apply_async(self.collectMemory)
            pool.apply_async(self.collectMemoryDetail)
            pool.apply_async(self.collectBattery)
            pool.apply_async(self.collectFps)
            pool.apply_async(self.collectNetwork)
            pool.apply_async(self.collectGpu)
            if self.record:
                pool.apply_async(Scrcpy.start_record, (self.deviceId))
            pool.close()
            pool.join()
            self.setPerfs(report_path=report_path)
        except KeyboardInterrupt:
            Scrcpy.stop_record()
            self.setPerfs(report_path=report_path)
        except Exception as e:
            Scrcpy.stop_record()
            logger.exception(e)
        finally:
            logger.info('End of testing')         