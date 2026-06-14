# -*- coding: utf-8 -*-
"""CPU and Memory unit tests with mocked ADB — no device required."""

import unittest
from unittest.mock import patch, MagicMock

from solox.public.apm import CPU, Memory
from solox.public.common import Devices, Platform


DEVICE = 'test_device'
PKG = 'com.test.app'
PID = '12345'


def _proc_stat_line(utime=1000, stime=500, cutime=100, cstime=50):
    """Build /proc/{pid}/stat with utime-stime-cutime-cstime at indices 13-16."""
    parts = [PID, f'({PKG})', 'R'] + ['0'] * 10
    parts += [str(utime), str(stime), str(cutime), str(cstime)]
    return ' '.join(parts)


def _ps_ef_line(name=f'{PKG}:main'):
    """Android ps -ef row: index 1 = pid, index 7 = process name."""
    return f'u0_a1 {PID} 1 0 0 0 0 {name}'


def _legacy_ps_line(name=PKG):
    """Legacy ps row (API < 26): index 1 = pid, index 8 = process name."""
    return f'u0_a1 {PID} 1 2 3 4 5 6 {name}'


def _cpu_total_stat(user=10000, nice=0, system=5000, idle=80000,
                    core_user=2500, core_system=1250, core_idle=20000):
    return (
        f'cpu  {user} {nice} {system} {idle} 0 0 0 0 0 0\n'
        f'cpu0 {core_user} 0 {core_system} {core_idle} 0 0 0 0 0 0'
    )


_MEMINFO_ANDROID_11 = """
Applications Memory Usage (in Kilobytes):
Uptime: 123456 Realtime: 789012

** MEMINFO in pid 12345 [com.test.app] **
                   Pss  Private  Private  SwapPss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------
  Native Heap    10000    10000        0        0    20000    15000     5000
  Dalvik Heap     5000     5000        0        0     8000     6000     2000
         TOTAL   204800      0        0     1024
         TOTAL SWAP PSS:       1024
"""

_MEMINFO_ANDROID_14 = """
** MEMINFO in pid 12345 [com.test.app] **
  Java Heap:    51200
  Native Heap:  102400
  Code:          8192
  Stack:           512
  Graphics:     40960
  Private Other:  2048
  System:         1024
         TOTAL PSS:   204800
         TOTAL SWAP (KB):   1024
"""


class TestCpuCollectionMocked(unittest.TestCase):
    """CPU rate calculation from mocked /proc data."""

    @patch('solox.public.apm.time.sleep')
    @patch('solox.public.apm.adb.shell')
    @patch.object(Devices, 'getPid')
    def test_android_cpu_rate_computed_from_proc(self, mock_get_pid, mock_shell, _sleep):
        mock_get_pid.return_value = [f'{PID}:{PKG}']

        proc_reads = [
            _proc_stat_line(1000, 500, 100, 50),
            _cpu_total_stat(core_user=2500, core_system=1250, core_idle=20000),
            _cpu_total_stat(core_user=2500, core_system=1250, core_idle=20000),
            _proc_stat_line(2000, 600, 100, 50),
            _cpu_total_stat(core_user=5000, core_system=2500, core_idle=22500),
            _cpu_total_stat(core_user=5000, core_system=2500, core_idle=22500),
        ]
        mock_shell.side_effect = proc_reads

        cpu = CPU(pkgName=PKG, deviceId=DEVICE, platform=Platform.Android, pid=PID)
        app_rate, sys_rate = cpu.getAndroidCpuRate(noLog=True)

        self.assertGreater(app_rate, 0)
        self.assertGreater(sys_rate, 0)
        self.assertLessEqual(app_rate, 100)
        self.assertLessEqual(sys_rate, 100)

    @patch('solox.public.apm.time.sleep')
    @patch('solox.public.apm.adb.shell')
    @patch.object(Devices, 'getPid')
    def test_cpu_returns_zero_when_process_missing(self, mock_get_pid, mock_shell, _sleep):
        mock_get_pid.return_value = []
        mock_shell.side_effect = Exception('no such file')

        cpu = CPU(pkgName=PKG, deviceId=DEVICE, platform=Platform.Android, pid=PID)
        app_rate, sys_rate = cpu.getAndroidCpuRate(noLog=True)

        self.assertEqual(app_rate, 0)
        self.assertEqual(sys_rate, 0)

    @patch.object(Devices, 'getSdkVersion')
    def test_getpid_uses_ps_ef_on_api_30_plus(self, mock_sdk):
        mock_sdk.return_value = '30'
        devices = Devices()
        with patch('solox.public.common.adb.popen_readlines') as mock_popen:
            mock_popen.return_value = [
                _ps_ef_line() + '\n'
            ]
            result = devices.getPid(DEVICE, PKG)
        cmd = mock_popen.call_args[0][0]
        self.assertIn('ps -ef', cmd)
        self.assertEqual(result[0], f'{PID}:{PKG}:main')

    @patch.object(Devices, 'getSdkVersion')
    def test_getpid_uses_legacy_ps_below_api_26(self, mock_sdk):
        mock_sdk.return_value = '25'
        devices = Devices()
        with patch('solox.public.common.adb.popen_readlines') as mock_popen:
            mock_popen.return_value = [
                _legacy_ps_line() + '\n'
            ]
            result = devices.getPid(DEVICE, PKG)
        cmd = mock_popen.call_args[0][0]
        self.assertNotIn('ps -ef', cmd)
        self.assertIn('ps |', cmd)
        self.assertEqual(result[0], f'{PID}:{PKG}')


class TestMemoryCollectionMocked(unittest.TestCase):
    """Memory parsing from mocked dumpsys meminfo output."""

    @patch('solox.public.apm.adb.shell')
    @patch.object(Devices, 'getPid')
    def test_memory_android_11_format(self, mock_get_pid, mock_shell):
        mock_get_pid.return_value = [f'{PID}:{PKG}']
        mock_shell.return_value = _MEMINFO_ANDROID_11

        mem = Memory(pkgName=PKG, deviceId=DEVICE, platform=Platform.Android, pid=PID)
        total, swap = mem.getAndroidMemory()

        self.assertAlmostEqual(total, 200.0, places=0)
        self.assertAlmostEqual(swap, 1.0, places=0)

    @patch('solox.public.apm.adb.shell')
    @patch.object(Devices, 'getPid')
    def test_memory_android_14_format(self, mock_get_pid, mock_shell):
        mock_get_pid.return_value = [f'{PID}:{PKG}']
        mock_shell.return_value = _MEMINFO_ANDROID_14

        mem = Memory(pkgName=PKG, deviceId=DEVICE, platform=Platform.Android, pid=PID)
        total, swap = mem.getAndroidMemory()

        self.assertAlmostEqual(total, 200.0, places=0)
        self.assertAlmostEqual(swap, 1.0, places=0)

    @patch('solox.public.apm.adb.shell')
    @patch.object(Devices, 'getPid')
    def test_memory_detail_parses_heap_fields(self, mock_get_pid, mock_shell):
        mock_get_pid.return_value = [f'{PID}:{PKG}']
        mock_shell.return_value = _MEMINFO_ANDROID_14

        mem = Memory(pkgName=PKG, deviceId=DEVICE, platform=Platform.Android, pid=PID)
        detail = mem.getAndroidMemoryDetail(noLog=True)

        self.assertAlmostEqual(detail['java_heap'], 50.0, places=0)
        self.assertAlmostEqual(detail['native_heap'], 100.0, places=0)
        self.assertGreater(detail['graphics_pss'], 0)

    @patch('solox.public.apm.adb.shell')
    @patch.object(Devices, 'getPid')
    def test_memory_returns_zero_on_parse_failure(self, mock_get_pid, mock_shell):
        mock_get_pid.return_value = [f'{PID}:{PKG}']
        mock_shell.return_value = 'invalid meminfo output'

        mem = Memory(pkgName=PKG, deviceId=DEVICE, platform=Platform.Android, pid=PID)
        total, swap = mem.getAndroidMemory()

        self.assertEqual(total, 0)
        self.assertEqual(swap, 0)


if __name__ == '__main__':
    unittest.main()
