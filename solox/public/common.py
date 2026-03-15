import json
import os
import platform
import re
import shutil
import subprocess
import threading
import time
import requests
from logzero import logger
from tqdm import tqdm
import socket
from urllib.request import urlopen
import ssl
import xlwt
import psutil
import signal
from functools import wraps
from jinja2 import Environment, FileSystemLoader
from tidevice._device import Device
from tidevice import Usbmux
from solox.public.adb import adb


class Platform:
    Android = 'Android'
    iOS = 'iOS'
    Mac = 'MacOS'
    Windows = 'Windows'

class Devices:

    def __init__(self, platform=Platform.Android):
        self.platform = platform
        self.adb = adb.adb_path

    def execCmd(self, cmd):
        """Execute the command to get the terminal print result"""
        r = os.popen(cmd)
        try:
            text = r.buffer.read().decode(encoding='gbk').replace('\x1b[0m','').strip()
        except UnicodeDecodeError:
            text = r.buffer.read().decode(encoding='utf-8').replace('\x1b[0m','').strip()
        finally:
            r.close()
        return text

    def filterType(self):
        """Select the pipe filtering method according to the system"""
        filtertype = ('grep', 'findstr')[platform.system() == Platform.Windows]
        return filtertype

    def getDeviceIds(self):
        """Get all connected device ids"""
        Ids = list(os.popen(f"{self.adb} devices").readlines())
        deviceIds = []
        for i in range(1, len(Ids) - 1):
            id, state = Ids[i].strip().split()
            if state == 'device':
                deviceIds.append(id)
        return deviceIds

    def getDevicesName(self, deviceId):
        """Get the device name of the Android corresponding device ID"""
        try:
            devices_name = os.popen(f'{self.adb} -s {deviceId} shell getprop ro.product.model').readlines()[0].strip()
        except Exception:
            devices_name = os.popen(f'{self.adb} -s {deviceId} shell getprop ro.product.model').buffer.readlines()[0].decode("utf-8").strip()
        return devices_name

    def getDevices(self):
        """Get all Android devices"""
        DeviceIds = self.getDeviceIds()
        Devices = [f'{id}({self.getDevicesName(id)})' for id in DeviceIds]
        logger.info('Connected devices: {}'.format(Devices))
        return Devices

    def getIdbyDevice(self, deviceinfo, platform):
        """Obtain the corresponding device id according to the Android device information"""
        if platform == Platform.Android:
            deviceId = re.sub(u"\\(.*?\\)|\\{.*?}|\\[.*?]", "", deviceinfo)
            if deviceId not in self.getDeviceIds():
                raise Exception('no device found')
        else:
            deviceId = deviceinfo
        return deviceId
    
    def getSdkVersion(self, deviceId):
        version = adb.shell(cmd='getprop ro.build.version.sdk', deviceId=deviceId)
        return version
    
    def getCpuCores(self, deviceId):
        """get Android cpu cores"""
        cmd = 'cat /sys/devices/system/cpu/online'
        result = adb.shell(cmd=cmd, deviceId=deviceId)
        try:
            nums = int(result.split('-')[1]) + 1
        except:
            nums = 1
        return nums

    def getPid(self, deviceId, pkgName):
        """Get the pid corresponding to the Android package name"""
        try:
            sdkversion = self.getSdkVersion(deviceId)
            if sdkversion and int(sdkversion) < 26:
                result = os.popen(f"{self.adb} -s {deviceId} shell ps | {self.filterType()} {pkgName}").readlines()
                processList = ['{}:{}'.format(process.split()[1],process.split()[8]) for process in result]
            else:
                result = os.popen(f"{self.adb} -s {deviceId} shell ps -ef | {self.filterType()} {pkgName}").readlines()
                processList = ['{}:{}'.format(process.split()[1],process.split()[7]) for process in result]
            for i in range(len(processList)):
                if processList[i].count(':') == 1:
                    index = processList.index(processList[i])
                    processList.insert(0, processList.pop(index))
                    break
            if len(processList) == 0:
               logger.warning('{}: no pid found'.format(pkgName))     
        except Exception as e:
            processList = []
            logger.exception(e)
        return processList

    def checkPkgname(self, pkgname):
        flag = True
        replace_list = ['com.google']
        for i in replace_list:
            if i in pkgname:
                flag = False
        return flag

    def getPkgname(self, deviceId):
        """Get all package names of Android devices"""
        pkginfo = os.popen(f"{self.adb} -s {deviceId} shell pm list packages --user 0")
        pkglist = [p.lstrip('package').lstrip(":").strip() for p in pkginfo]
        if pkglist.__len__() > 0:
            return pkglist
        else:
            pkginfo = os.popen(f"{self.adb} -s {deviceId} shell pm list packages")
            pkglist = [p.lstrip('package').lstrip(":").strip() for p in pkginfo]
            return pkglist

    def getDeviceInfoByiOS(self):
        """Get a list of all successfully connected iOS devices"""
        deviceInfo = [udid for udid in Usbmux().device_udid_list()]
        logger.info('Connected devices: {}'.format(deviceInfo))    
        return deviceInfo

    def getPkgnameByiOS(self, udid):
        """Get all package names of the corresponding iOS device"""
        d = Device(udid)
        pkgNames = [i.get("CFBundleIdentifier") for i in d.installation.iter_installed(app_type="User")]
        return pkgNames
    
    def get_pc_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            logger.error('get local ip failed')
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    
    def get_device_ip(self, deviceId):
        content = os.popen(f"{self.adb} -s {deviceId} shell ip addr show wlan0").read()
        logger.info(content)
        math_obj = re.search(r'inet\s(\d+\.\d+\.\d+\.\d+).*?wlan0', content)
        if math_obj and math_obj.group(1):
            return math_obj.group(1)
        return None
    
    def devicesCheck(self, platform, deviceid=None, pkgname=None):
        """Check the device environment"""
        match(platform):
            case Platform.Android:
                if len(self.getDeviceIds()) == 0:
                    raise Exception('no devices found')
                if len(self.getPid(deviceId=deviceid, pkgName=pkgname)) == 0:
                    raise Exception('no process found')
            case Platform.iOS:
                if len(self.getDeviceInfoByiOS()) == 0:
                    raise Exception('no devices found')
            case _:
                raise Exception('platform must be Android or iOS')        
            
    def getDdeviceDetail(self, deviceId, platform):
        result = dict()
        match(platform):
            case Platform.Android:
                result['brand'] = adb.shell(cmd='getprop ro.product.brand', deviceId=deviceId)
                result['name'] = adb.shell(cmd='getprop ro.product.model', deviceId=deviceId)
                result['version'] = adb.shell(cmd='getprop ro.build.version.release', deviceId=deviceId)
                result['serialno'] = adb.shell(cmd='getprop ro.serialno', deviceId=deviceId)
                if not result['serialno']:
                    result['serialno'] = adb.shell(cmd='getprop persist.sys.usb.config', deviceId=deviceId) or ''
                cmd = f'ip addr show wlan0 | {self.filterType()} link/ether'
                wifiadr_content = adb.shell(cmd=cmd, deviceId=deviceId)
                result['wifiadr'] = Method._index(wifiadr_content.split(), 1, '')
                result['cpu_cores'] = self.getCpuCores(deviceId)
                result['physical_size'] = adb.shell(cmd='wm size', deviceId=deviceId).replace('Physical size:','').strip()
                # Extended device info
                result['os'] = 'Android ' + result['version']
                sdk = adb.shell(cmd='getprop ro.build.version.sdk', deviceId=deviceId)
                if sdk:
                    result['os'] += ' (API {})'.format(sdk)
                result['cpu_type'] = self._getDeviceProp(deviceId,
                    'ro.hardware', 'ro.board.platform', 'ro.product.board')
                result['cpu_info'] = self._getCpuInfo(deviceId)
                result['cpu_arch'] = adb.shell(cmd='getprop ro.product.cpu.abi', deviceId=deviceId)
                result['cpu_freq'] = self._getCpuFreq(deviceId)
                result['gpu_type'] = self._getGpuType(deviceId)
                result['opengl'] = self._getOpenGLVersion(deviceId)
                result['gpu_freq'] = self._getGpuFreq(deviceId)
                result['screen_size'] = self._getScreenDensity(deviceId)
                result['ram_size'] = self._getRamSize(deviceId)
                result['lmk_threshold'] = self._getLmkThreshold(deviceId)
                result['swap'] = self._getSwapInfo(deviceId)
                result['root'] = self._getRootStatus(deviceId)
            case Platform.iOS:
                ios_device = Device(udid=deviceId)
                result['brand'] = ios_device.get_value("DeviceClass", no_session=True)
                result['name'] = ios_device.get_value("DeviceName", no_session=True)
                result['version'] = ios_device.get_value("ProductVersion", no_session=True)
                result['serialno'] = deviceId
                result['wifiadr'] = ios_device.get_value("WiFiAddress", no_session=True)
                result['cpu_cores'] = 0
                result['physical_size'] = self.getPhysicalSzieOfiOS(deviceId)
                result['os'] = 'iOS ' + (result['version'] or '')
                result['cpu_type'] = ios_device.get_value("HardwareModel", no_session=True) or ''
                result['cpu_info'] = ios_device.get_value("CPUArchitecture", no_session=True) or ''
                result['cpu_arch'] = result['cpu_info']
                result['cpu_freq'] = ''
                result['gpu_type'] = ''
                result['opengl'] = ''
                result['gpu_freq'] = ''
                result['screen_size'] = result['physical_size']
                try:
                    ram_bytes = ios_device.get_value("TotalDiskCapacity", no_session=True)
                    result['ram_size'] = ''
                except Exception:
                    result['ram_size'] = ''
                result['lmk_threshold'] = ''
                result['swap'] = ''
                result['root'] = ''
            case _:
                raise Exception('{} is undefined'.format(platform))
        return result

    def _getDeviceProp(self, deviceId, *props):
        """Try multiple property names, return first non-empty value."""
        for prop in props:
            val = adb.shell(cmd='getprop {}'.format(prop), deviceId=deviceId)
            if val:
                return val
        return ''

    def _getCpuInfo(self, deviceId):
        """Get CPU model name from /proc/cpuinfo."""
        try:
            result = adb.shell(cmd='cat /proc/cpuinfo | grep -i "Hardware\\|model name" | head -1',
                               deviceId=deviceId)
            if result and ':' in result:
                return result.split(':', 1)[1].strip()
            # Fallback: try ro.hardware.chipname (Qualcomm/Samsung)
            for prop in ('ro.hardware.chipname', 'ro.soc.model', 'ro.hardware'):
                val = adb.shell(cmd='getprop {}'.format(prop), deviceId=deviceId)
                if val:
                    return val
        except Exception:
            pass
        return ''

    def _getCpuFreq(self, deviceId):
        """Get CPU max frequency."""
        try:
            # Try cpuinfo_max_freq (in kHz)
            result = adb.shell(
                cmd='cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq',
                deviceId=deviceId)
            if result and result.isdigit():
                freq_mhz = int(result) / 1000
                if freq_mhz >= 1000:
                    return '{:.2f} GHz'.format(freq_mhz / 1000)
                return '{:.0f} MHz'.format(freq_mhz)
            # Fallback: scaling_max_freq
            result = adb.shell(
                cmd='cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq',
                deviceId=deviceId)
            if result and result.isdigit():
                freq_mhz = int(result) / 1000
                if freq_mhz >= 1000:
                    return '{:.2f} GHz'.format(freq_mhz / 1000)
                return '{:.0f} MHz'.format(freq_mhz)
        except Exception:
            pass
        return ''

    def _getGpuType(self, deviceId):
        """Get GPU type/model."""
        try:
            # Method 1: dumpsys SurfaceFlinger (GLES info)
            result = adb.shell(
                cmd='dumpsys SurfaceFlinger | grep "GLES:" | head -1',
                deviceId=deviceId)
            if result and 'GLES:' in result:
                parts = result.split('GLES:', 1)[1].strip()
                # Format: "Vendor, Model, OpenGL ES version"
                fields = [f.strip() for f in parts.split(',')]
                if len(fields) >= 2:
                    return fields[1]  # GPU model
                return parts
            # Method 2: getprop
            for prop in ('ro.hardware.egl', 'ro.hardware.vulkan'):
                val = adb.shell(cmd='getprop {}'.format(prop), deviceId=deviceId)
                if val:
                    return val
        except Exception:
            pass
        return ''

    def _getOpenGLVersion(self, deviceId):
        """Get OpenGL ES version."""
        try:
            result = adb.shell(
                cmd='dumpsys SurfaceFlinger | grep "GLES:" | head -1',
                deviceId=deviceId)
            if result and 'GLES:' in result:
                parts = result.split('GLES:', 1)[1].strip()
                fields = [f.strip() for f in parts.split(',')]
                if len(fields) >= 3:
                    return fields[2]  # OpenGL ES version string
            # Fallback: getprop
            val = adb.shell(cmd='getprop ro.opengles.version', deviceId=deviceId)
            if val and val.isdigit():
                v = int(val)
                major = (v >> 16) & 0xFF
                minor = v & 0xFF
                return 'OpenGL ES {}.{}'.format(major, minor)
        except Exception:
            pass
        return ''

    def _getGpuFreq(self, deviceId):
        """Get GPU max frequency."""
        try:
            # Qualcomm Adreno
            result = adb.shell(
                cmd='cat /sys/class/kgsl/kgsl-3d0/max_clock_mhz 2>/dev/null || '
                    'cat /sys/class/kgsl/kgsl-3d0/devfreq/max_freq 2>/dev/null',
                deviceId=deviceId)
            if result and result.strip():
                val = result.strip().split('\n')[0].strip()
                if val.isdigit():
                    freq = int(val)
                    if freq > 100000:  # in Hz, convert
                        return '{} MHz'.format(freq // 1000000)
                    elif freq > 1000:  # in kHz
                        return '{} MHz'.format(freq // 1000)
                    else:  # already MHz
                        return '{} MHz'.format(freq)
            # Mali GPU
            result = adb.shell(
                cmd='cat /sys/devices/platform/*/mali*/max_clock 2>/dev/null || '
                    'cat /sys/class/devfreq/*mali*/max_freq 2>/dev/null || '
                    'cat /sys/class/devfreq/*gpu*/max_freq 2>/dev/null',
                deviceId=deviceId)
            if result and result.strip():
                val = result.strip().split('\n')[0].strip()
                if val.isdigit():
                    freq = int(val)
                    if freq > 100000000:
                        return '{} MHz'.format(freq // 1000000)
                    elif freq > 100000:
                        return '{} MHz'.format(freq // 1000)
        except Exception:
            pass
        return ''

    def _getScreenDensity(self, deviceId):
        """Get screen density (DPI) and compute approximate screen size."""
        try:
            density = adb.shell(cmd='wm density', deviceId=deviceId)
            density = density.replace('Physical density:', '').strip() if density else ''
            size = adb.shell(cmd='wm size', deviceId=deviceId)
            size = size.replace('Physical size:', '').strip() if size else ''
            if density and size and 'x' in size:
                w, h = size.split('x')
                w, h = int(w.strip()), int(h.strip())
                dpi = int(density.split('\n')[0].strip())
                diag_px = (w**2 + h**2) ** 0.5
                diag_inch = diag_px / dpi
                return '{} dpi ({:.1f}")'.format(dpi, diag_inch)
            return density
        except Exception:
            pass
        return ''

    def _getRamSize(self, deviceId):
        """Get total RAM size."""
        try:
            result = adb.shell(cmd='cat /proc/meminfo | grep MemTotal', deviceId=deviceId)
            if result and 'MemTotal' in result:
                val = result.split(':')[1].strip()  # e.g. "5939412 kB"
                parts = val.split()
                if parts and parts[0].isdigit():
                    kb = int(parts[0])
                    gb = kb / 1024 / 1024
                    if gb >= 1:
                        return '{:.1f} GB'.format(gb)
                    return '{:.0f} MB'.format(kb / 1024)
        except Exception:
            pass
        return ''

    def _getLmkThreshold(self, deviceId):
        """Get LMK (Low Memory Killer) thresholds."""
        try:
            # Method 1: minfree thresholds
            result = adb.shell(
                cmd='cat /sys/module/lowmemorykiller/parameters/minfree 2>/dev/null',
                deviceId=deviceId)
            if result and result.strip() and 'No such file' not in result:
                # Convert pages to MB (4KB per page)
                pages = [p.strip() for p in result.strip().split(',') if p.strip().isdigit()]
                if pages:
                    mb_vals = [str(int(p) * 4 // 1024) + 'MB' for p in pages]
                    return ','.join(mb_vals)
            # Method 2: lmkd (Android 10+)
            result = adb.shell(cmd='getprop sys.lmk.minfree_levels', deviceId=deviceId)
            if result and result.strip():
                return result.strip()
            # Method 3: device_config
            result = adb.shell(
                cmd='device_config get lmkd_native kill_heaviest_task 2>/dev/null',
                deviceId=deviceId)
            if result and result.strip() and 'null' not in result:
                return 'lmkd: ' + result.strip()
        except Exception:
            pass
        return ''

    def _getSwapInfo(self, deviceId):
        """Get swap/zRAM info."""
        try:
            result = adb.shell(cmd='cat /proc/meminfo | grep SwapTotal', deviceId=deviceId)
            if result and 'SwapTotal' in result:
                val = result.split(':')[1].strip()
                parts = val.split()
                if parts and parts[0].isdigit():
                    kb = int(parts[0])
                    if kb == 0:
                        return 'No Swap'
                    gb = kb / 1024 / 1024
                    if gb >= 1:
                        return '{:.1f} GB'.format(gb)
                    return '{:.0f} MB'.format(kb / 1024)
        except Exception:
            pass
        return ''

    def _getRootStatus(self, deviceId):
        """Check if device is rooted."""
        try:
            # Method 1: check su binary
            result = adb.shell(cmd='which su 2>/dev/null', deviceId=deviceId)
            if result and '/su' in result:
                return 'Yes'
            # Method 2: check ro.debuggable + ro.secure
            debuggable = adb.shell(cmd='getprop ro.debuggable', deviceId=deviceId)
            secure = adb.shell(cmd='getprop ro.secure', deviceId=deviceId)
            if debuggable == '1' and secure == '0':
                return 'Likely'
            return 'No'
        except Exception:
            pass
        return ''
    
    def getPhysicalSzieOfiOS(self, deviceId):
        ios_device = Device(udid=deviceId)
        try:
            screen_info = ios_device.screen_info()
            PhysicalSzie = '{}x{}'.format(screen_info.get('width'), screen_info.get('height'))
        except Exception as e:
            PhysicalSzie = ''  
            logger.exception(e)  
        return PhysicalSzie
    
    def getCurrentActivity(self, deviceId):
        result = adb.shell(cmd='dumpsys window | {} mCurrentFocus'.format(self.filterType()), deviceId=deviceId)
        if result.__contains__('mCurrentFocus'):
            activity = str(result).split(' ')[-1].replace('}','') 
            return activity
        else:
            raise Exception('No activity found')

    def getLauncherActivity(self, pkg_name, deviceId):
        """Find the exported launcher activity for a package."""
        # Method 1: Parse dumpsys package (reliable, always available on device)
        try:
            result = self._adb_shell_timeout(
                'dumpsys package {} | grep -B 5 "android.intent.category.LAUNCHER"'.format(pkg_name),
                deviceId, timeout=10
            )
            if result:
                for line in result.strip().split('\n'):
                    line = line.strip()
                    m = re.search(r'({}/\S+)'.format(re.escape(pkg_name)), line)
                    if m:
                        comp = m.group(1).split()[0].rstrip('}')
                        return comp
        except Exception:
            pass

        # Method 2: cmd package resolve-activity (short timeout, may not work on all devices)
        try:
            result = self._adb_shell_timeout(
                'cmd package resolve-activity --brief -a android.intent.action.MAIN '
                '-c android.intent.category.LAUNCHER {}'.format(pkg_name),
                deviceId, timeout=5
            )
            if result:
                for line in result.strip().split('\n'):
                    line = line.strip()
                    if '/' in line and not line.startswith('priority'):
                        return line
        except Exception:
            pass

        return None

    def _adb_shell_timeout(self, cmd, deviceId, timeout=10):
        """Run adb shell command with timeout, return stdout string."""
        run_cmd = '{} -s {} shell {}'.format(adb.adb_path, deviceId, cmd)
        try:
            proc = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=timeout)
            return stdout.decode('utf-8', errors='replace').strip()
        except subprocess.TimeoutExpired:
            proc.kill()
            return ''
        except Exception:
            return ''

    def sendHomeKey(self, deviceId):
        """Send HOME key (keyevent 3) to background the current app."""
        adb.shell(cmd='input keyevent 3', deviceId=deviceId)

    def _run_am_start(self, cmd, deviceId, timeout=30):
        """Run am start command capturing both stdout and stderr, return combined output."""
        run_cmd = '{} -s {} shell {}'.format(adb.adb_path, deviceId, cmd)
        try:
            proc = subprocess.Popen(
                run_cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate(timeout=timeout)
            output = stdout.decode('utf-8', errors='replace').strip()
            err_output = stderr.decode('utf-8', errors='replace').strip()
            return output + '\n' + err_output if err_output else output
        except subprocess.TimeoutExpired:
            proc.kill()
            return 'Error: Command timed out after {} seconds'.format(timeout)
        except Exception as e:
            return 'Error: {}'.format(str(e))

    def _parse_am_output(self, combined, launch_type):
        """Parse am start -W output into structured result."""
        parsed = {
            'raw': combined,
            'launch_type': launch_type,
            'TotalTime': -1,
            'WaitTime': -1,
            'LaunchState': '',
            'Status': '',
            'error': ''
        }
        if not combined:
            return parsed

        for line in combined.strip().split('\n'):
            line = line.strip()
            if line.startswith('Status:'):
                parsed['Status'] = line.split(':', 1)[1].strip()
            elif line.startswith('TotalTime:'):
                try:
                    parsed['TotalTime'] = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith('WaitTime:'):
                try:
                    parsed['WaitTime'] = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith('LaunchState:'):
                parsed['LaunchState'] = line.split(':', 1)[1].strip()
            elif 'SecurityException' in line or 'Permission Denial' in line:
                parsed['error'] = 'security'
            elif 'Error' in line and 'not exported' in line:
                parsed['error'] = 'not_exported'
            elif 'Exception' in line and not parsed['error']:
                parsed['error'] = line

        return parsed

    def getStartupTimeByAndroid(self, activity, deviceId, launch_type='cold'):
        """Measure Android app startup time following industry standards.

        Automatically resolves launcher activity when the specified activity
        is not exported (SecurityException). Uses am start -W -S for cold start.
        For hot start, auto-sends HOME key to background the app first.
        """
        pkg_name = activity.split('/')[0] if '/' in activity else activity

        # For hot start, first send app to background and wait
        if launch_type == 'hot':
            try:
                self.sendHomeKey(deviceId)
                time.sleep(1.5)
            except Exception:
                pass

        # Build the am start command based on launch type
        if launch_type == 'cold':
            cmd = 'am start -W -S {}'.format(activity)
        else:
            cmd = 'am start -W {}'.format(activity)

        combined = self._run_am_start(cmd, deviceId)
        parsed = self._parse_am_output(combined, launch_type)

        # If SecurityException (activity not exported), auto-retry with launcher activity
        if parsed['error'] in ('security', 'not_exported') or (
            'SecurityException' in combined or 'not exported' in combined
        ):
            logger.warning('Activity not exported, resolving launcher activity for {}'.format(pkg_name))

            # Strategy 1: resolve launcher activity via package manager
            launcher = self.getLauncherActivity(pkg_name, deviceId)
            if launcher:
                logger.info('Found launcher activity: {}'.format(launcher))
                if launch_type == 'cold':
                    cmd2 = 'am start -W -S {}'.format(launcher)
                else:
                    cmd2 = 'am start -W {}'.format(launcher)

                combined2 = self._run_am_start(cmd2, deviceId)
                parsed2 = self._parse_am_output(combined2, launch_type)

                if parsed2['TotalTime'] >= 0 or parsed2['Status']:
                    parsed2['raw'] = '[Auto-resolved launcher: {}]\n{}'.format(launcher, combined2)
                    parsed2['resolved_activity'] = launcher
                    return parsed2

            # Strategy 2: launch via intent action (no specific component)
            logger.info('Trying intent-based launch for {}'.format(pkg_name))
            if launch_type == 'cold':
                adb.shell(cmd='am force-stop {}'.format(pkg_name), deviceId=deviceId)
                time.sleep(1)
            cmd3 = 'am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {}'.format(pkg_name)
            combined3 = self._run_am_start(cmd3, deviceId)
            parsed3 = self._parse_am_output(combined3, launch_type)

            if parsed3['TotalTime'] >= 0 or parsed3['Status']:
                parsed3['raw'] = '[Launched via package intent: {}]\n{}'.format(pkg_name, combined3)
                return parsed3

            # All strategies failed — return original error with guidance
            parsed['raw'] = combined + '\n\n--- Retry via launcher ---\n' + (combined2 if launcher else 'No launcher found') + '\n--- Retry via intent ---\n' + combined3
            parsed['error'] = 'not_exported'

        return parsed

    def getStartupTimeByiOS(self, pkgname):
        try:
            import ios_device
        except ImportError:
            logger.error('py-ios-devices not found, please run [pip install py-ios-devices]') 
        result = self.execCmd('pyidevice instruments app_lifecycle -b {}'.format(pkgname))       
        return result          

class File:

    def __init__(self, fileroot='.'):
        self.fileroot = fileroot
        self.report_dir = self.get_repordir()

    def clear_file(self):
        logger.info('Clean up useless files ...')
        if os.path.exists(self.report_dir):
            for f in os.listdir(self.report_dir):
                filename = os.path.join(self.report_dir, f)
                if f.split(".")[-1] in ['log', 'json', 'mkv', 'mp4']:
                    os.remove(filename)
        Scrcpy.stop_record()            
        logger.info('Clean up useless files success')            

    def export_excel(self, platform, scene):
        logger.info('Exporting excel ...')
        android_log_file_list = ['cpu_app','cpu_sys','mem_total','mem_swap',
                                 'battery_level', 'battery_tem','upflow','downflow','fps','gpu']
        ios_log_file_list = ['cpu_app','cpu_sys', 'mem_total', 'battery_tem', 'battery_current', 
                             'battery_voltage', 'battery_power','upflow','downflow','fps','gpu']
        log_file_list = android_log_file_list if platform == 'Android' else ios_log_file_list
        wb = xlwt.Workbook(encoding = 'utf-8')
        k = 1
        for name in log_file_list:
            ws1 = wb.add_sheet(name)
            ws1.write(0,0,'Time') 
            ws1.write(0,1,'Value')
            row = 1 #start row
            col = 0 #start col
            if os.path.exists(f'{self.report_dir}/{scene}/{name}.log'):
                f = open(f'{self.report_dir}/{scene}/{name}.log','r',encoding='utf-8')
                for lines in f: 
                    target = lines.split('=')
                    k += 1
                    for i in range(len(target)):
                        ws1.write(row, col ,target[i])
                        col += 1
                    row += 1
                    col = 0
        xls_path = os.path.join(self.report_dir, scene, f'{scene}.xls')            
        wb.save(xls_path)
        logger.info('Exporting excel success : {}'.format(xls_path))
        return xls_path   
    
    def make_android_html(self, scene, summary : dict, report_path=None):
        logger.info('Generating HTML ...')
        STATICPATH = os.path.dirname(os.path.realpath(__file__))
        file_loader = FileSystemLoader(os.path.join(STATICPATH, 'report_template'))
        env = Environment(loader=file_loader)
        template = env.get_template('android.html')
        if report_path:
            html_path = report_path
        else:
            html_path = os.path.join(self.report_dir, scene, 'report.html')   
        with open(html_path,'w+') as fout:
            html_content = template.render(devices=summary['devices'],app=summary['app'],
                                           platform=summary['platform'],ctime=summary['ctime'],
                                           cpu_app=summary['cpu_app'],cpu_sys=summary['cpu_sys'],
                                           mem_total=summary['mem_total'],mem_swap=summary['mem_swap'],
                                           fps=summary['fps'],jank=summary['jank'],level=summary['level'],
                                           tem=summary['tem'],net_send=summary['net_send'],
                                           net_recv=summary['net_recv'],cpu_charts=summary['cpu_charts'],
                                           mem_charts=summary['mem_charts'],net_charts=summary['net_charts'],
                                           battery_charts=summary['battery_charts'],fps_charts=summary['fps_charts'],
                                           jank_charts=summary['jank_charts'],mem_detail_charts=summary['mem_detail_charts'],
                                           gpu=summary['gpu'], gpu_charts=summary['gpu_charts'])
            
            fout.write(html_content)
        logger.info('Generating HTML success : {}'.format(html_path))  
        return html_path
    
    def make_ios_html(self, scene, summary : dict, report_path=None):
        logger.info('Generating HTML ...')
        STATICPATH = os.path.dirname(os.path.realpath(__file__))
        file_loader = FileSystemLoader(os.path.join(STATICPATH, 'report_template'))
        env = Environment(loader=file_loader)
        template = env.get_template('ios.html')
        if report_path:
            html_path = report_path
        else:
            html_path = os.path.join(self.report_dir, scene, 'report.html')
        with open(html_path,'w+') as fout:
            html_content = template.render(devices=summary['devices'],app=summary['app'],
                                           platform=summary['platform'],ctime=summary['ctime'],
                                           cpu_app=summary['cpu_app'],cpu_sys=summary['cpu_sys'],gpu=summary['gpu'],
                                           mem_total=summary['mem_total'],fps=summary['fps'],
                                           tem=summary['tem'],current=summary['current'],
                                           voltage=summary['voltage'],power=summary['power'],
                                           net_send=summary['net_send'],net_recv=summary['net_recv'],
                                           cpu_charts=summary['cpu_charts'],mem_charts=summary['mem_charts'],
                                           net_charts=summary['net_charts'],battery_charts=summary['battery_charts'],
                                           fps_charts=summary['fps_charts'],gpu_charts=summary['gpu_charts'])            
            fout.write(html_content)
        logger.info('Generating HTML success : {}'.format(html_path))  
        return html_path
  
    def filter_secen(self, scene):
        dirs = os.listdir(self.report_dir)
        dir_list = list(reversed(sorted(dirs, key=lambda x: os.path.getmtime(os.path.join(self.report_dir, x)))))
        dir_list.remove(scene)
        return dir_list

    def get_repordir(self):
        report_dir = os.path.join(os.getcwd(), 'report')
        if not os.path.exists(report_dir):
            os.mkdir(report_dir)
        return report_dir

    def getDuration(self, scene):
        """Calculate test duration from first/last log timestamps."""
        from datetime import datetime
        scene_dir = os.path.join(self.report_dir, scene)
        if not os.path.isdir(scene_dir):
            return ''
        first_ts, last_ts = None, None
        for fname in os.listdir(scene_dir):
            if not fname.endswith('.log'):
                continue
            fpath = os.path.join(scene_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as fh:
                    first_line = fh.readline().strip()
                if not first_line or '=' not in first_line:
                    continue
                with open(fpath, 'rb') as fh:
                    fh.seek(0, 2)
                    pos = fh.tell()
                    if pos < 2:
                        continue
                    fh.seek(-2, 2)
                    while fh.tell() > 0 and fh.read(1) != b'\n':
                        fh.seek(-2, 1)
                    last_line = fh.readline().decode('utf-8').strip()
                if not last_line or '=' not in last_line:
                    continue
                t1 = first_line.split('=')[0]
                t2 = last_line.split('=')[0]
                if first_ts is None or t1 < first_ts:
                    first_ts = t1
                if last_ts is None or t2 > last_ts:
                    last_ts = t2
            except Exception:
                continue
        if first_ts and last_ts:
            try:
                fmt = '%H:%M:%S.%f'
                delta = datetime.strptime(last_ts, fmt) - datetime.strptime(first_ts, fmt)
                total_sec = int(delta.total_seconds())
                if total_sec < 0:
                    return ''
                h, m, s = total_sec // 3600, (total_sec % 3600) // 60, total_sec % 60
                if h > 0:
                    return f'{h:02d}:{m:02d}:{s:02d}'
                return f'{m:02d}:{s:02d}'
            except Exception:
                return ''
        return ''

    def create_file(self, filename, content=''):
        if not os.path.exists(self.report_dir):
            os.mkdir(self.report_dir)
        with open(os.path.join(self.report_dir, filename), 'a+', encoding="utf-8") as file:
            file.write(content)

    def add_log(self, path, log_time, value):
        if value >= 0:
            with open(path, 'a+', encoding="utf-8") as file:
                file.write(f'{log_time}={str(value)}' + '\n')
    
    def record_net(self, type, send , recv):
        net_dict = dict()
        match(type):
            case 'pre':
                net_dict['send'] = send
                net_dict['recv'] = recv
                content = json.dumps(net_dict)
                self.create_file(filename='pre_net.json', content=content)
            case 'end':
                net_dict['send'] = send
                net_dict['recv'] = recv
                content = json.dumps(net_dict)
                self.create_file(filename='end_net.json', content=content)
            case _:
                logger.error('record network data failed')
    
    def make_report(self, app, devices, video, platform=Platform.Android, model='normal', cores=0):
        logger.info('Generating test results ...')
        current_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        result_dict = {
            "app": app,
            "icon": "",
            "platform": platform,
            "model": model,
            "devices": devices,
            "ctime": current_time,
            "video": video,
            "cores":cores
        }
        content = json.dumps(result_dict)
        self.create_file(filename='result.json', content=content)
        report_new_dir = os.path.join(self.report_dir, f'apm_{current_time}')
        if not os.path.exists(report_new_dir):
            os.mkdir(report_new_dir)

        for f in os.listdir(self.report_dir):
            filename = os.path.join(self.report_dir, f)
            if f.split(".")[-1] in ['log', 'json', 'mkv', 'mp4']:
                shutil.move(filename, report_new_dir)        
        logger.info('Generating test results success: {}'.format(report_new_dir))
        return f'apm_{current_time}'        

    def instance_type(self, data):
        if isinstance(data, float):
            return 'float'
        elif isinstance(data, int):
            return 'int'
        else:
            return 'int'
    
    def open_file(self, path, mode):
        with open(path, mode) as f:
            for line in f:
                yield line
    
    def readJson(self, scene):
        path = os.path.join(self.report_dir,scene,'result.json')
        result_json = open(file=path, mode='r').read()
        result_dict = json.loads(result_json)
        return result_dict

    def readLog(self, scene, filename):
        """Read apmlog file data"""
        log_data_list = list()
        target_data_list = list()
        if os.path.exists(os.path.join(self.report_dir,scene,filename)):
            lines = self.open_file(os.path.join(self.report_dir,scene,filename), "r")
            for line in lines:
                if isinstance(line.split('=')[1].strip(), int):
                    log_data_list.append({
                        "x": line.split('=')[0].strip(),
                        "y": int(line.split('=')[1].strip())
                    })
                    target_data_list.append(int(line.split('=')[1].strip()))
                else:
                    log_data_list.append({
                        "x": line.split('=')[0].strip(),
                        "y": float(line.split('=')[1].strip())
                    })
                    target_data_list.append(float(line.split('=')[1].strip()))
        return log_data_list, target_data_list
        
    def getCpuLog(self, platform, scene):
        targetDic = dict()
        targetDic['cpuAppData'] = self.readLog(scene=scene, filename='cpu_app.log')[0]
        targetDic['cpuSysData'] = self.readLog(scene=scene, filename='cpu_sys.log')[0]
        result = {'status': 1, 'cpuAppData': targetDic['cpuAppData'], 'cpuSysData': targetDic['cpuSysData']}
        return result
    
    def getCpuLogCompare(self, platform, scene1, scene2):
        targetDic = dict()
        targetDic['scene1'] = self.readLog(scene=scene1, filename='cpu_app.log')[0]
        targetDic['scene2'] = self.readLog(scene=scene2, filename='cpu_app.log')[0]
        result = {'status': 1, 'scene1': targetDic['scene1'], 'scene2': targetDic['scene2']}
        return result
    
    def getGpuLog(self, platform, scene):
        targetDic = dict()
        targetDic['gpu'] = self.readLog(scene=scene, filename='gpu.log')[0]
        result = {'status': 1, 'gpu': targetDic['gpu']}
        return result
    
    def getGpuLogCompare(self, platform, scene1, scene2):
        targetDic = dict()
        targetDic['scene1'] = self.readLog(scene=scene1, filename='gpu.log')[0]
        targetDic['scene2'] = self.readLog(scene=scene2, filename='gpu.log')[0]
        result = {'status': 1, 'scene1': targetDic['scene1'], 'scene2': targetDic['scene2']}
        return result
    
    def getMemLog(self, platform, scene):
        targetDic = dict()
        targetDic['memTotalData'] = self.readLog(scene=scene, filename='mem_total.log')[0]
        if platform == Platform.Android:
            targetDic['memSwapData']  = self.readLog(scene=scene, filename='mem_swap.log')[0]
            result = {'status': 1, 
                      'memTotalData': targetDic['memTotalData'], 
                      'memSwapData': targetDic['memSwapData']}
        else:
            result = {'status': 1, 'memTotalData': targetDic['memTotalData']}
        return result
    
    def getMemDetailLog(self, platform, scene):
        targetDic = dict()
        targetDic['java_heap'] = self.readLog(scene=scene, filename='mem_java_heap.log')[0]
        targetDic['native_heap'] = self.readLog(scene=scene, filename='mem_native_heap.log')[0]
        targetDic['code_pss'] = self.readLog(scene=scene, filename='mem_code_pss.log')[0]
        targetDic['stack_pss'] = self.readLog(scene=scene, filename='mem_stack_pss.log')[0]
        targetDic['graphics_pss'] = self.readLog(scene=scene, filename='mem_graphics_pss.log')[0]
        targetDic['private_pss'] = self.readLog(scene=scene, filename='mem_private_pss.log')[0]
        targetDic['system_pss'] = self.readLog(scene=scene, filename='mem_system_pss.log')[0]
        result = {'status': 1, 'memory_detail': targetDic}
        return result
    
    def getCpuCoreLog(self, platform, scene):
        targetDic = dict()
        cores =self.readJson(scene=scene).get('cores', 0)
        if int(cores) > 0:
            for i in range(int(cores)):
                targetDic['cpu{}'.format(i)] = self.readLog(scene=scene, filename='cpu{}.log'.format(i))[0]
        result = {'status': 1, 'cores':cores, 'cpu_core': targetDic}
        return result
    
    def getMemLogCompare(self, platform, scene1, scene2):
        targetDic = dict()
        targetDic['scene1'] = self.readLog(scene=scene1, filename='mem_total.log')[0]
        targetDic['scene2'] = self.readLog(scene=scene2, filename='mem_total.log')[0]
        result = {'status': 1, 'scene1': targetDic['scene1'], 'scene2': targetDic['scene2']}
        return result
    
    def getBatteryLog(self, platform, scene):
        targetDic = dict()
        if platform == Platform.Android:
            targetDic['batteryLevel'] = self.readLog(scene=scene, filename='battery_level.log')[0]
            targetDic['batteryTem'] = self.readLog(scene=scene, filename='battery_tem.log')[0]
            result = {'status': 1, 
                      'batteryLevel': targetDic['batteryLevel'], 
                      'batteryTem': targetDic['batteryTem']}
        else:
            targetDic['batteryTem'] = self.readLog(scene=scene, filename='battery_tem.log')[0]
            targetDic['batteryCurrent'] = self.readLog(scene=scene, filename='battery_current.log')[0]
            targetDic['batteryVoltage'] = self.readLog(scene=scene, filename='battery_voltage.log')[0]
            targetDic['batteryPower'] = self.readLog(scene=scene, filename='battery_power.log')[0]
            result = {'status': 1, 
                      'batteryTem': targetDic['batteryTem'], 
                      'batteryCurrent': targetDic['batteryCurrent'],
                      'batteryVoltage': targetDic['batteryVoltage'], 
                      'batteryPower': targetDic['batteryPower']}    
        return result
    
    def getBatteryLogCompare(self, platform, scene1, scene2):
        targetDic = dict()
        if platform == Platform.Android:
            targetDic['scene1'] = self.readLog(scene=scene1, filename='battery_level.log')[0]
            targetDic['scene2'] = self.readLog(scene=scene2, filename='battery_level.log')[0]
            result = {'status': 1, 'scene1': targetDic['scene1'], 'scene2': targetDic['scene2']}
        else:
            targetDic['scene1'] = self.readLog(scene=scene1, filename='batteryPower.log')[0]
            targetDic['scene2'] = self.readLog(scene=scene2, filename='batteryPower.log')[0]
            result = {'status': 1, 'scene1': targetDic['scene1'], 'scene2': targetDic['scene2']}    
        return result
    
    def getFlowLog(self, platform, scene):
        targetDic = dict()
        targetDic['upFlow'] = self.readLog(scene=scene, filename='upflow.log')[0]
        targetDic['downFlow'] = self.readLog(scene=scene, filename='downflow.log')[0]
        result = {'status': 1, 'upFlow': targetDic['upFlow'], 'downFlow': targetDic['downFlow']}
        return result
    
    def getFlowSendLogCompare(self, platform, scene1, scene2):
        targetDic = dict()
        targetDic['scene1'] = self.readLog(scene=scene1, filename='upflow.log')[0]
        targetDic['scene2'] = self.readLog(scene=scene2, filename='upflow.log')[0]
        result = {'status': 1, 'scene1': targetDic['scene1'], 'scene2': targetDic['scene2']}
        return result
    
    def getFlowRecvLogCompare(self, platform, scene1, scene2):
        targetDic = dict()
        targetDic['scene1'] = self.readLog(scene=scene1, filename='downflow.log')[0]
        targetDic['scene2'] = self.readLog(scene=scene2, filename='downflow.log')[0]
        result = {'status': 1, 'scene1': targetDic['scene1'], 'scene2': targetDic['scene2']}
        return result
    
    def getFpsLog(self, platform, scene):
        targetDic = dict()
        targetDic['fps'] = self.readLog(scene=scene, filename='fps.log')[0]
        if platform == Platform.Android:
            targetDic['jank'] = self.readLog(scene=scene, filename='jank.log')[0]
            result = {'status': 1, 'fps': targetDic['fps'], 'jank': targetDic['jank']}
        else:
            result = {'status': 1, 'fps': targetDic['fps']}     
        return result
    
    def getDiskLog(self, platform, scene):
        targetDic = dict()
        targetDic['used'] = self.readLog(scene=scene, filename='disk_used.log')[0]
        targetDic['free'] = self.readLog(scene=scene, filename='disk_free.log')[0]
        result = {'status': 1, 'used': targetDic['used'], 'free':targetDic['free']}
        return result

    def analysisDisk(self, scene):
        initail_disk_list = list()
        current_disk_list = list()
        sum_init_disk = dict()
        sum_current_disk = dict()
        if os.path.exists(os.path.join(self.report_dir,scene,'initail_disk.log')):
            size_list = list()
            used_list = list()
            free_list = list()
            lines = self.open_file(os.path.join(self.report_dir,scene,'initail_disk.log'), "r")
            for line in lines:
                if 'Filesystem' not in line and line.strip() != '':
                    disk_value_list = line.split()
                    disk_dict = dict(
                        filesystem = disk_value_list[0],
                        blocks = disk_value_list[1],
                        used = disk_value_list[2],
                        available = disk_value_list[3],
                        use_percent = disk_value_list[4],
                        mounted = disk_value_list[5]
                    )
                    initail_disk_list.append(disk_dict)
                    size_list.append(int(disk_value_list[1]))
                    used_list.append(int(disk_value_list[2]))
                    free_list.append(int(disk_value_list[3]))
            sum_init_disk['sum_size'] = int(sum(size_list) / 1024 / 1024)
            sum_init_disk['sum_used'] = int(sum(used_list) / 1024)
            sum_init_disk['sum_free'] = int(sum(free_list) / 1024)
               
        if os.path.exists(os.path.join(self.report_dir,scene,'current_disk.log')):
            size_list = list()
            used_list = list()
            free_list = list()
            lines = self.open_file(os.path.join(self.report_dir,scene,'current_disk.log'), "r")
            for line in lines:
                if 'Filesystem' not in line and line.strip() != '':
                    disk_value_list = line.split()
                    disk_dict = dict(
                        filesystem = disk_value_list[0],
                        blocks = disk_value_list[1],
                        used = disk_value_list[2],
                        available = disk_value_list[3],
                        use_percent = disk_value_list[4],
                        mounted = disk_value_list[5]
                    )
                    current_disk_list.append(disk_dict)
                    size_list.append(int(disk_value_list[1]))
                    used_list.append(int(disk_value_list[2]))
                    free_list.append(int(disk_value_list[3]))
            sum_current_disk['sum_size'] = int(sum(size_list) / 1024 / 1024)
            sum_current_disk['sum_used'] = int(sum(used_list) / 1024)
            sum_current_disk['sum_free'] = int(sum(free_list) / 1024)       
                 
        return initail_disk_list, current_disk_list, sum_init_disk, sum_current_disk

    def getFpsLogCompare(self, platform, scene1, scene2):
        targetDic = dict()
        targetDic['scene1'] = self.readLog(scene=scene1, filename='fps.log')[0]
        targetDic['scene2'] = self.readLog(scene=scene2, filename='fps.log')[0]
        result = {'status': 1, 'scene1': targetDic['scene1'], 'scene2': targetDic['scene2']}
        return result
        
    def approximateSize(self, size, a_kilobyte_is_1024_bytes=True):
        '''
        convert a file size to human-readable form.
        Keyword arguments:
        size -- file size in bytes
        a_kilobyte_is_1024_bytes -- if True (default),use multiples of 1024
                                    if False, use multiples of 1000
        Returns: string
        '''

        suffixes = {1000: ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
                    1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']}

        if size < 0:
            raise ValueError('number must be non-negative')

        multiple = 1024 if a_kilobyte_is_1024_bytes else 1000

        for suffix in suffixes[multiple]:
            size /= multiple
            if size < multiple:
                return '{0:.2f} {1}'.format(size, suffix)
    
    def _setAndroidPerfs(self, scene):
        """Aggregate APM data for Android"""
        
        app = self.readJson(scene=scene).get('app')
        devices = self.readJson(scene=scene).get('devices')
        platform = self.readJson(scene=scene).get('platform')
        ctime = self.readJson(scene=scene).get('ctime')

        cpuAppData = self.readLog(scene=scene, filename=f'cpu_app.log')[1]
        cpuSystemData = self.readLog(scene=scene, filename=f'cpu_sys.log')[1]
        if cpuAppData.__len__() > 0 and cpuSystemData.__len__() > 0:
            cpuAppRate = f'{round(sum(cpuAppData) / len(cpuAppData), 2)}%'
            cpuSystemRate = f'{round(sum(cpuSystemData) / len(cpuSystemData), 2)}%'
        else:
            cpuAppRate, cpuSystemRate = 0, 0    

        batteryLevelData = self.readLog(scene=scene, filename=f'battery_level.log')[1]
        batteryTemlData = self.readLog(scene=scene, filename=f'battery_tem.log')[1]
        if batteryLevelData.__len__() > 0 and batteryTemlData.__len__() > 0:
            batteryLevel = f'{batteryLevelData[-1]}%'
            batteryTeml = f'{batteryTemlData[-1]}°C'
        else:
            batteryLevel, batteryTeml = 0, 0   
    

        totalPassData = self.readLog(scene=scene, filename=f'mem_total.log')[1]
        
        if totalPassData.__len__() > 0:
            swapPassData = self.readLog(scene=scene, filename=f'mem_swap.log')[1]
            totalPassAvg = f'{round(sum(totalPassData) / len(totalPassData), 2)}MB'
            swapPassAvg = f'{round(sum(swapPassData) / len(swapPassData), 2)}MB'
        else:
            totalPassAvg, swapPassAvg = 0, 0    

        fpsData = self.readLog(scene=scene, filename=f'fps.log')[1]
        jankData = self.readLog(scene=scene, filename=f'jank.log')[1]
        if fpsData.__len__() > 0:
            fpsAvg = f'{int(sum(fpsData) / len(fpsData))}HZ/s'
            jankAvg = f'{int(sum(jankData))}'
        else:
            fpsAvg, jankAvg = 0, 0    

        if os.path.exists(os.path.join(self.report_dir,scene,'end_net.json')):
            f_pre = open(os.path.join(self.report_dir,scene,'pre_net.json'))
            f_end = open(os.path.join(self.report_dir,scene,'end_net.json'))
            json_pre = json.loads(f_pre.read())
            json_end = json.loads(f_end.read())
            send = json_end['send'] - json_pre['send']
            recv = json_end['recv'] - json_pre['recv']
        else:
            send, recv = 0, 0    
        flowSend = f'{round(float(send / 1024), 2)}MB'
        flowRecv = f'{round(float(recv / 1024), 2)}MB'

        gpuData = self.readLog(scene=scene, filename='gpu.log')[1]
        if gpuData.__len__() > 0:
            gpu = round(sum(gpuData) / len(gpuData), 2)
        else:
            gpu = 0

        mem_detail_flag = os.path.exists(os.path.join(self.report_dir,scene,'mem_java_heap.log'))
        disk_flag = os.path.exists(os.path.join(self.report_dir,scene,'disk_free.log'))
        thermal_flag = os.path.exists(os.path.join(self.report_dir,scene,'init_thermal_temp.json'))
        cpu_core_flag = os.path.exists(os.path.join(self.report_dir,scene,'cpu0.log'))
        apm_dict = dict()
        apm_dict['app'] = app
        apm_dict['devices'] = devices
        apm_dict['platform'] = platform
        apm_dict['ctime'] = ctime
        apm_dict['cpuAppRate'] = cpuAppRate
        apm_dict['cpuSystemRate'] = cpuSystemRate
        apm_dict['totalPassAvg'] = totalPassAvg
        apm_dict['swapPassAvg'] = swapPassAvg
        apm_dict['fps'] = fpsAvg
        apm_dict['jank'] = jankAvg
        apm_dict['flow_send'] = flowSend
        apm_dict['flow_recv'] = flowRecv
        apm_dict['batteryLevel'] = batteryLevel
        apm_dict['batteryTeml'] = batteryTeml
        apm_dict['mem_detail_flag'] = mem_detail_flag
        apm_dict['disk_flag'] = disk_flag
        apm_dict['gpu'] = gpu
        apm_dict['thermal_flag'] = thermal_flag
        apm_dict['cpu_core_flag'] = cpu_core_flag
        
        if thermal_flag:
            init_thermal_temp = json.loads(open(os.path.join(self.report_dir,scene,'init_thermal_temp.json')).read())
            current_thermal_temp = json.loads(open(os.path.join(self.report_dir,scene,'current_thermal_temp.json')).read())
            apm_dict['init_thermal_temp'] = init_thermal_temp
            apm_dict['current_thermal_temp'] = current_thermal_temp

        return apm_dict

    def _setiOSPerfs(self, scene):
        """Aggregate APM data for iOS"""
        
        app = self.readJson(scene=scene).get('app')
        devices = self.readJson(scene=scene).get('devices')
        platform = self.readJson(scene=scene).get('platform')
        ctime = self.readJson(scene=scene).get('ctime')

        cpuAppData = self.readLog(scene=scene, filename=f'cpu_app.log')[1]
        cpuSystemData = self.readLog(scene=scene, filename=f'cpu_sys.log')[1]
        if cpuAppData.__len__() > 0 and cpuSystemData.__len__() > 0:
            cpuAppRate = f'{round(sum(cpuAppData) / len(cpuAppData), 2)}%'
            cpuSystemRate = f'{round(sum(cpuSystemData) / len(cpuSystemData), 2)}%'
        else:
            cpuAppRate, cpuSystemRate = 0, 0

        totalPassData = self.readLog(scene=scene, filename='mem_total.log')[1]
        if totalPassData.__len__() > 0:
            totalPassAvg = f'{round(sum(totalPassData) / len(totalPassData), 2)}MB'
        else:
            totalPassAvg = 0

        fpsData = self.readLog(scene=scene, filename='fps.log')[1]
        if fpsData.__len__() > 0:
            fpsAvg = f'{int(sum(fpsData) / len(fpsData))}HZ/s'
        else:
            fpsAvg = 0

        flowSendData = self.readLog(scene=scene, filename='upflow.log')[1]
        flowRecvData = self.readLog(scene=scene, filename='downflow.log')[1]
        if flowSendData.__len__() > 0:
            flowSend = f'{round(float(sum(flowSendData) / 1024), 2)}MB'
            flowRecv = f'{round(float(sum(flowRecvData) / 1024), 2)}MB'
        else:
            flowSend, flowRecv = 0, 0    

        batteryTemlData = self.readLog(scene=scene, filename='battery_tem.log')[1]
        batteryCurrentData = self.readLog(scene=scene, filename='battery_current.log')[1]
        batteryVoltageData = self.readLog(scene=scene, filename='battery_voltage.log')[1]
        batteryPowerData = self.readLog(scene=scene, filename='battery_power.log')[1]
        if batteryTemlData.__len__() > 0:
            batteryTeml = int(batteryTemlData[-1])
            batteryCurrent = int(sum(batteryCurrentData) / len(batteryCurrentData))
            batteryVoltage = int(sum(batteryVoltageData) / len(batteryVoltageData))
            batteryPower = int(sum(batteryPowerData) / len(batteryPowerData))
        else:
            batteryTeml,  batteryCurrent , batteryVoltage, batteryPower = 0, 0, 0, 0 

        gpuData = self.readLog(scene=scene, filename='gpu.log')[1]
        if gpuData.__len__() > 0:
            gpu = round(sum(gpuData) / len(gpuData), 2)
        else:
            gpu = 0    
        disk_flag = os.path.exists(os.path.join(self.report_dir,scene,'disk_free.log'))
        apm_dict = dict()
        apm_dict['app'] = app
        apm_dict['devices'] = devices
        apm_dict['platform'] = platform
        apm_dict['ctime'] = ctime
        apm_dict['cpuAppRate'] = cpuAppRate
        apm_dict['cpuSystemRate'] = cpuSystemRate
        apm_dict['totalPassAvg'] = totalPassAvg
        apm_dict['nativePassAvg'] = 0
        apm_dict['dalvikPassAvg'] = 0
        apm_dict['fps'] = fpsAvg
        apm_dict['jank'] = 0
        apm_dict['flow_send'] = flowSend
        apm_dict['flow_recv'] = flowRecv
        apm_dict['batteryTeml'] = batteryTeml
        apm_dict['batteryCurrent'] = batteryCurrent
        apm_dict['batteryVoltage'] = batteryVoltage
        apm_dict['batteryPower'] = batteryPower
        apm_dict['gpu'] = gpu
        apm_dict['disk_flag'] = disk_flag
        return apm_dict

    def _setpkPerfs(self, scene):
        """Aggregate APM data for pk model"""
        cpuAppData1 = self.readLog(scene=scene, filename='cpu_app1.log')[1]
        cpuAppRate1 = f'{round(sum(cpuAppData1) / len(cpuAppData1), 2)}%'
        cpuAppData2 = self.readLog(scene=scene, filename='cpu_app2.log')[1]
        cpuAppRate2 = f'{round(sum(cpuAppData2) / len(cpuAppData2), 2)}%'

        totalPassData1 = self.readLog(scene=scene, filename='mem1.log')[1]
        totalPassAvg1 = f'{round(sum(totalPassData1) / len(totalPassData1), 2)}MB'
        totalPassData2 = self.readLog(scene=scene, filename='mem2.log')[1]
        totalPassAvg2 = f'{round(sum(totalPassData2) / len(totalPassData2), 2)}MB'

        fpsData1 = self.readLog(scene=scene, filename='fps1.log')[1]
        fpsAvg1 = f'{int(sum(fpsData1) / len(fpsData1))}HZ/s'
        fpsData2 = self.readLog(scene=scene, filename='fps2.log')[1]
        fpsAvg2 = f'{int(sum(fpsData2) / len(fpsData2))}HZ/s'

        networkData1 = self.readLog(scene=scene, filename='network1.log')[1]
        network1 = f'{round(float(sum(networkData1) / 1024), 2)}MB'
        networkData2 = self.readLog(scene=scene, filename='network2.log')[1]
        network2 = f'{round(float(sum(networkData2) / 1024), 2)}MB'
        
        apm_dict = dict()
        apm_dict['cpuAppRate1'] = cpuAppRate1
        apm_dict['cpuAppRate2'] = cpuAppRate2
        apm_dict['totalPassAvg1'] = totalPassAvg1
        apm_dict['totalPassAvg2'] = totalPassAvg2
        apm_dict['network1'] = network1
        apm_dict['network2'] = network2
        apm_dict['fpsAvg1'] = fpsAvg1
        apm_dict['fpsAvg2'] = fpsAvg2
        return apm_dict

class Method:
    
    @classmethod
    def _request(cls, request, object):
        match(request.method):
            case 'POST':
                return request.form[object]
            case 'GET':
                return request.args[object]
            case _:
                raise Exception('request method error')
    
    @classmethod   
    def _setValue(cls, value, default = 0):
        try:
            result = value
        except ZeroDivisionError :
            result = default
        except IndexError:
            result = default        
        except Exception:
            result = default            
        return result
    
    @classmethod
    def _settings(cls, request):
        content = {}
        content['cpuWarning'] = (0, request.cookies.get('cpuWarning'))[request.cookies.get('cpuWarning') not in [None, 'NaN']]
        content['memWarning'] = (0, request.cookies.get('memWarning'))[request.cookies.get('memWarning') not in [None, 'NaN']]
        content['fpsWarning'] = (0, request.cookies.get('fpsWarning'))[request.cookies.get('fpsWarning') not in [None, 'NaN']]
        content['netdataRecvWarning'] = (0, request.cookies.get('netdataRecvWarning'))[request.cookies.get('netdataRecvWarning') not in [None, 'NaN']]
        content['netdataSendWarning'] = (0, request.cookies.get('netdataSendWarning'))[request.cookies.get('netdataSendWarning') not in [None, 'NaN']]
        content['betteryWarning'] = (0, request.cookies.get('betteryWarning'))[request.cookies.get('betteryWarning') not in [None, 'NaN']]
        content['gpuWarning'] = (0, request.cookies.get('gpuWarning'))[request.cookies.get('gpuWarning') not in [None, 'NaN']]
        content['duration'] = (0, request.cookies.get('duration'))[request.cookies.get('duration') not in [None, 'NaN']]
        content['solox_host'] = ('', request.cookies.get('solox_host'))[request.cookies.get('solox_host') not in [None, 'NaN']]
        content['host_switch'] = request.cookies.get('host_switch')
        return content
    
    @classmethod
    def _index(cls, target: list, index: int, default: any):
        try:
            return target[index]
        except IndexError:
            return default

class Install:

    def uploadFile(self, file_path, file_obj):
        """save upload file"""
        try:
            file_obj.save(file_path)
            return True
        except Exception as e:
            logger.exception(e)
            return False            

    def downloadLink(self,filelink=None, path=None, name=None):
        try:
            logger.info('Install link : {}'.format(filelink))
            ssl._create_default_https_context = ssl._create_unverified_context
            file_size = int(urlopen(filelink).info().get('Content-Length', -1))
            header = {"Range": "bytes=%s-%s" % (0, file_size)}
            pbar = tqdm(
                total=file_size, initial=0,
                unit='B', unit_scale=True, desc=filelink.split('/')[-1])
            req = requests.get(filelink, headers=header, stream=True)
            with(open(os.path.join(path, name), 'ab')) as f:
                for chunk in req.iter_content(chunk_size=1024):
                    if chunk:
                         f.write(chunk)
                         pbar.update(1024)
            pbar.close()
            return True
        except Exception as e:
            logger.exception(e)
            return False

    def installAPK(self, path):
        result = adb.shell_noDevice(cmd='install -r {}'.format(path))
        if result == 0:
            os.remove(path)
            return True, result
        else:
            return False, result

    def installIPA(self, path):
        result = os.system('tidevice install {}'.format(path))
        if result == 0:
            os.remove(path)
            return True, result
        else:
            return False, result

class Scrcpy:

    STATICPATH = os.path.dirname(os.path.realpath(__file__))
    DEFAULT_SCRCPY_PATH = {
        "64": os.path.join(STATICPATH, "scrcpy", "scrcpy-win64-v2.4", "scrcpy.exe"),
        "32": os.path.join(STATICPATH, "scrcpy", "scrcpy-win32-v2.4", "scrcpy.exe"),
        "default":"scrcpy"
    }

    # Track active scrcpy processes
    _cast_process = None
    _cast_thread = None
    _cast_device = None
    _cast_running = False
    _cast_quality = 'medium'
    _record_process = None

    @classmethod
    def scrcpy_path(cls):
        bit = platform.architecture()[0]
        path = cls.DEFAULT_SCRCPY_PATH["default"]
        if platform.system().lower().__contains__('windows'):
            if bit.__contains__('64'):
                path =  cls.DEFAULT_SCRCPY_PATH["64"]
            elif bit.__contains__('32'):
                path =  cls.DEFAULT_SCRCPY_PATH["32"]
        return path

    @classmethod
    def _is_recording(cls):
        """Check if screen recording is currently active."""
        if cls._record_process and cls._record_process.poll() is None:
            return True
        return False

    # Use software encoder by default to avoid hardware encoder crashes
    # (OMX.qcom.video.encoder.avc crashes with 0x80001009 on many Qualcomm devices)
    _use_sw_encoder = True

    @classmethod
    def _get_cast_params(cls, device, for_recording=False, quality='medium'):
        """Get optimized scrcpy parameters based on current state and quality setting.

        quality: 'high', 'medium', 'low'
        When data collection + recording run simultaneously,
        use lower quality settings to reduce USB bandwidth pressure.
        Uses software encoder (c2.android.avc.encoder) by default to avoid
        hardware encoder crashes on Qualcomm/MediaTek devices.
        """
        params = [cls.scrcpy_path(), '-s', device, '--no-audio', '--video-codec=h264']

        # Software encoder fallback: avoids OMX hardware encoder crashes
        if cls._use_sw_encoder:
            params.append('--video-encoder=c2.android.avc.encoder')

        if for_recording:
            # Recording mode: no display, lower quality to avoid USB contention
            params.extend(['--no-playback', '--max-size=720', '--video-bit-rate=2M'])
        else:
            # Cast mode quality presets (bitrates lowered to reduce encoder stress)
            quality_presets = {
                'high':   {'max_size': 1920, 'max_fps': 60, 'bitrate': '6M'},
                'medium': {'max_size': 1024, 'max_fps': 60, 'bitrate': '3M'},
                'low':    {'max_size': 720,  'max_fps': 30, 'bitrate': '1M'},
            }
            preset = quality_presets.get(quality, quality_presets['medium'])

            if cls._is_recording():
                # Both casting and recording: force low quality regardless
                params.extend(['--stay-awake', '--max-size=720', '--max-fps=30',
                              '--video-bit-rate=1M'])
                logger.info('cast screen: reduced quality due to concurrent recording')
            else:
                params.extend(['--stay-awake',
                              '--max-size={}'.format(preset['max_size']),
                              '--max-fps={}'.format(preset['max_fps']),
                              '--video-bit-rate={}'.format(preset['bitrate'])])
        return params

    @classmethod
    def start_record(cls, device):
        f = File()
        logger.info('start record screen')
        video_path = os.path.join(f.report_dir, 'record.mp4')
        params = cls._get_cast_params(device, for_recording=True)
        params.extend(['--record={}'.format(video_path)])

        try:
            if platform.system().lower().__contains__('windows'):
                cls._record_process = subprocess.Popen(
                    params, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                cls._record_process = subprocess.Popen(
                    params, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
            # Wait briefly to check if process started OK
            import time as _time
            _time.sleep(1)
            if cls._record_process.poll() is not None:
                stderr = cls._record_process.stderr.read().decode('utf-8', errors='replace')
                logger.error('scrcpy record failed: {}'.format(stderr))
                cls._record_process = None
                return 1
            logger.info("record screen success : {}".format(video_path))
            return 0
        except Exception as e:
            logger.error("scrcpy record launch failed: {}".format(e))
            logger.info("Please install scrcpy: brew install scrcpy (macOS) or download from github.com/Genymobile/scrcpy")
            return 1

    @classmethod
    def _graceful_stop_process(cls, proc, name='scrcpy'):
        """Gracefully stop a scrcpy process using SIGINT to allow file finalization."""
        if proc is None or proc.poll() is not None:
            return
        try:
            if platform.system().lower().__contains__('windows'):
                # Windows: send CTRL_BREAK_EVENT (works with CREATE_NEW_PROCESS_GROUP)
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.GenerateConsoleCtrlEvent(1, proc.pid)  # CTRL_BREAK_EVENT=1
            else:
                # Unix: send SIGINT for graceful shutdown
                import signal as _signal
                proc.send_signal(_signal.SIGINT)

            # Wait up to 10 seconds for scrcpy to finalize the video container
            proc.wait(timeout=10)
            logger.info('{} process stopped gracefully (video finalized)'.format(name))
        except subprocess.TimeoutExpired:
            logger.warning('{} did not stop gracefully, forcing termination'.format(name))
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        except Exception as e:
            logger.warning('{} graceful stop failed: {}, using terminate'.format(name, e))
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    @classmethod
    def stop_record(cls):
        logger.info('stop scrcpy record process')
        # Gracefully stop record process (SIGINT lets scrcpy finalize the video file)
        if cls._record_process and cls._record_process.poll() is None:
            cls._graceful_stop_process(cls._record_process, 'record')
            cls._record_process = None

        # Also stop any cast process
        cls._stop_cast_process()

        # Fallback: kill any remaining scrcpy processes (backward compat)
        pids = psutil.pids()
        try:
            for pid in pids:
                try:
                    p = psutil.Process(pid)
                    if p.name().__contains__('scrcpy'):
                        if platform.system().lower().__contains__('windows'):
                            p.terminate()
                        else:
                            import signal as _signal
                            os.kill(pid, _signal.SIGINT)
                        logger.info('stopped remaining scrcpy pid: {}'.format(pid))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.exception(e)

    @classmethod
    def _stop_cast_process(cls):
        """Stop the cast screen process."""
        cls._cast_running = False
        if cls._cast_process and cls._cast_process.poll() is None:
            try:
                cls._cast_process.terminate()
                cls._cast_process.wait(timeout=3)
            except Exception:
                try:
                    cls._cast_process.kill()
                except Exception:
                    pass
        cls._cast_process = None

    @classmethod
    def _cast_monitor_thread(cls, device):
        """Monitor thread that runs the cast process.
        If software encoder fails, retries once with hardware encoder."""
        params = cls._get_cast_params(device, for_recording=False, quality=cls._cast_quality)
        try:
            if platform.system().lower().__contains__('windows'):
                cls._cast_process = subprocess.Popen(
                    params, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
            else:
                cls._cast_process = subprocess.Popen(
                    params, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
            logger.info("cast screen started (quality={}, sw_encoder={})".format(
                cls._cast_quality, cls._use_sw_encoder))

            # Wait for process to exit
            cls._cast_process.wait()
            exit_code = cls._cast_process.returncode

            if not cls._cast_running:
                # Intentional stop
                logger.info('cast screen stopped by user')
                return

            if exit_code != 0:
                stderr = ''
                try:
                    stderr = cls._cast_process.stderr.read().decode('utf-8', errors='replace')[:500]
                except Exception:
                    pass

                # If software encoder failed, retry with hardware encoder
                if cls._use_sw_encoder and cls._cast_running:
                    logger.warning('software encoder failed (code={}), retrying with hardware encoder: {}'.format(
                        exit_code, stderr))
                    cls._use_sw_encoder = False
                    params2 = cls._get_cast_params(device, for_recording=False, quality=cls._cast_quality)
                    cls._cast_process = subprocess.Popen(
                        params2, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                    )
                    logger.info("cast screen retrying with hardware encoder")
                    cls._cast_process.wait()
                    if not cls._cast_running:
                        return
                    if cls._cast_process.returncode != 0:
                        logger.warning('hardware encoder also failed (code={})'.format(
                            cls._cast_process.returncode))
                    else:
                        logger.info('cast screen closed normally (hardware encoder)')
                else:
                    logger.warning('cast screen exited unexpectedly (code={}): {}'.format(exit_code, stderr))
            else:
                logger.info('cast screen closed normally (user closed scrcpy window)')
        except Exception as e:
            logger.error('cast monitor error: {}'.format(e))
        finally:
            cls._cast_running = False
            cls._cast_process = None

    @classmethod
    def cast_screen(cls, device, quality='medium'):
        logger.info('start cast screen (quality={})'.format(quality))
        # Stop any existing cast
        cls._stop_cast_process()

        cls._cast_device = device
        cls._cast_quality = quality
        cls._cast_running = True
        cls._cast_thread = threading.Thread(
            target=cls._cast_monitor_thread, args=(device,), daemon=True
        )
        cls._cast_thread.start()

        # Wait briefly to see if it started OK
        import time as _time
        _time.sleep(1.5)
        if cls._cast_process and cls._cast_process.poll() is None:
            logger.info("cast screen success")
            return 0
        elif not cls._cast_running:
            logger.error("solox's scrcpy is incompatible with your PC")
            logger.info("Please install scrcpy yourself or upgrade to latest version: https://github.com/Genymobile/scrcpy/releases")
            return 1
        return 0

    @classmethod
    def play_video(cls, video):
        logger.info('start play video : {}'.format(video))
        if not os.path.exists(video):
            logger.error('Video file not found: {}'.format(video))
            return
        try:
            if platform.system().lower().__contains__('windows'):
                os.startfile(video)
            elif platform.system().lower().__contains__('darwin'):
                subprocess.Popen(['open', video])
            else:
                subprocess.Popen(['xdg-open', video])
        except Exception as e:
            logger.error('Failed to open video with system player: {}'.format(e))


class LogcatManager:
    """Manages adb logcat process for error log streaming via AJAX polling.
    Supports severity filtering, tag extraction, and structured log parsing."""

    _instance = None
    _lock = threading.Lock()

    # Severity levels for logcat
    SEVERITIES = ['V', 'D', 'I', 'W', 'E', 'F']

    def __init__(self):
        self._process = None
        self._lines = []  # list of dicts: {raw, severity, tag, msg, time}
        self._reader_thread = None
        self._running = False
        self._device_id = None
        self._severity = 'E'  # minimum severity to capture

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def _parse_logcat_line(line):
        """Parse a logcat line into structured fields.
        Format: '03-15 20:56:01.780 12345 12346 E Tag    : message'
        Returns dict with severity, tag, msg, time, or None if unparseable."""
        import re
        m = re.match(
            r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+\d+\s+\d+\s+([VDIWEF])\s+(\S+)\s*:\s*(.*)',
            line
        )
        if m:
            return {
                'time': m.group(1),
                'severity': m.group(2),
                'tag': m.group(3),
                'msg': m.group(4),
                'raw': line
            }
        return {'time': '', 'severity': '?', 'tag': '', 'msg': line, 'raw': line}

    def start(self, device_id, severity='E'):
        """Start logcat capture for a device.
        severity: minimum severity level (V/D/I/W/E/F). Default 'E' for errors only."""
        if self._running:
            self.stop()
        self._device_id = device_id
        self._lines = []
        self._running = True
        self._severity = severity if severity in self.SEVERITIES else 'E'
        try:
            # Capture from the requested severity level and above
            cmd = '{} -s {} logcat *:{}'.format(adb.adb_path, device_id, self._severity)
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=True, bufsize=1
            )
            self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self._reader_thread.start()
            logger.info('logcat started for device: {} (severity>={})'.format(device_id, self._severity))
            return True
        except Exception as e:
            logger.exception(e)
            self._running = False
            return False

    def _read_output(self):
        """Background thread that reads logcat output."""
        try:
            for line in iter(self._process.stdout.readline, b''):
                if not self._running:
                    break
                try:
                    decoded = line.decode('utf-8', errors='replace').rstrip('\n\r')
                except Exception:
                    decoded = str(line)
                if decoded:
                    parsed = self._parse_logcat_line(decoded)
                    self._lines.append(parsed)
                    # Keep buffer bounded to 5000 entries
                    if len(self._lines) > 5000:
                        self._lines = self._lines[-3000:]
        except Exception as e:
            logger.error('logcat reader error: {}'.format(e))
        finally:
            self._running = False

    def stop(self):
        """Stop logcat capture."""
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        self._reader_thread = None
        logger.info('logcat stopped')

    def get_lines(self, offset=0, severity=None, tag=None, keyword=None):
        """Get log lines starting from offset with optional filtering.
        Returns (lines, new_offset, total_count)."""
        total = len(self._lines)
        if offset >= total:
            return [], total, total

        batch = self._lines[offset:min(offset + 200, total)]
        new_offset = min(offset + 200, total)

        # Apply client-side filters
        if severity or tag or keyword:
            filtered = []
            sev_set = set(severity.split(',')) if severity else None
            tag_lower = tag.lower() if tag else None
            kw_lower = keyword.lower() if keyword else None
            for item in batch:
                if sev_set and item['severity'] not in sev_set:
                    continue
                if tag_lower and tag_lower not in item['tag'].lower():
                    continue
                if kw_lower and kw_lower not in item['raw'].lower():
                    continue
                filtered.append(item)
            batch = filtered

        # Return raw strings for backward compat plus structured data
        result = []
        for item in batch:
            result.append({
                'raw': item['raw'],
                'severity': item['severity'],
                'tag': item['tag'],
                'time': item['time'],
                'msg': item['msg']
            })
        return result, new_offset, total

    def get_all_lines(self, severity=None, tag=None, keyword=None):
        """Get all buffered lines with optional filtering. For export."""
        sev_set = set(severity.split(',')) if severity else None
        tag_lower = tag.lower() if tag else None
        kw_lower = keyword.lower() if keyword else None
        result = []
        for item in self._lines:
            if sev_set and item['severity'] not in sev_set:
                continue
            if tag_lower and tag_lower not in item['tag'].lower():
                continue
            if kw_lower and kw_lower not in item['raw'].lower():
                continue
            result.append(item['raw'])
        return result

    def clear(self):
        """Clear buffered log lines."""
        self._lines = []

    @property
    def is_running(self):
        return self._running
