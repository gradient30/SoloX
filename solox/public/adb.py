#!/usr/bin/python
# encoding=utf-8

"""
@Author  :  Lijiawei
@Date    :  2022/6/19
@Desc    :  adb line.
@Update  :  2022/7/14 by Rafa chen
"""
import os
import platform
import stat
import subprocess
from solox.public.performance_telemetry import telemetry

STATICPATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_ADB_PATH = {
    "Windows": os.path.join(STATICPATH, "adb", "windows", "adb.exe"),
    "Darwin": os.path.join(STATICPATH, "adb", "mac", "adb"),
    "Linux": os.path.join(STATICPATH, "adb", "linux", "adb"),
    "Linux-x86_64": os.path.join(STATICPATH, "adb", "linux", "adb"),
    "Linux-armv7l": os.path.join(STATICPATH, "adb", "linux_arm", "adb"),
}


def _windows_hidden_process_kwargs():
    if platform.system() != "Windows":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "startupinfo": startupinfo,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }


def _popen_hidden(cmd, **kwargs):
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    kwargs.update(_windows_hidden_process_kwargs())
    return subprocess.Popen(cmd, **kwargs)


def _run_hidden(cmd):
    proc = _popen_hidden(
        cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.wait()


def _read_hidden(cmd, split_lines=False):
    proc = _popen_hidden(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, _ = proc.communicate()
    text = stdout.decode("utf-8", errors="ignore") if isinstance(stdout, bytes) else stdout
    return text.splitlines(True) if split_lines else text


def make_file_executable(file_path):
    """
    If the path does not have executable permissions, execute chmod +x
    :param file_path:
    :return:
    """
    if os.path.isfile(file_path):
        mode = os.lstat(file_path)[stat.ST_MODE]
        executable = True if mode & stat.S_IXUSR else False
        if not executable:
            os.chmod(file_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return True
    return False


def builtin_adb_path():
    """
    Return built-in adb executable path

    Returns:
        adb executable path

    """
    system = platform.system()
    machine = platform.machine()
    adb_path = DEFAULT_ADB_PATH.get('{}-{}'.format(system, machine))
    result = _read_hidden('adb devices')
    if result and "command not found" not in result:
        adb_path = "adb"
        return adb_path

    if not adb_path:
        adb_path = DEFAULT_ADB_PATH.get(system)
    if not adb_path:
        raise RuntimeError("No adb executable supports this platform({}-{}).".format(system, machine))

    # overwrite uiautomator adb
    if "ANDROID_HOME" in os.environ:
        del os.environ["ANDROID_HOME"]
    if system != "Windows":
        # chmod +x adb
        make_file_executable(adb_path)
    return adb_path


class ADB(object):

    def __init__(self):
        self.adb_path = builtin_adb_path()

    def shell(self, cmd, deviceId):
        started = telemetry.begin_adb()
        try:
            run_cmd = f'{self.adb_path} -s {deviceId} shell {cmd}'
            result = _popen_hidden(
                run_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).communicate()[0].decode("utf-8").strip()
            return result
        finally:
            telemetry.end_adb(started)
    
    def tcp_shell(self, deviceId, cmd):
        started = telemetry.begin_adb()
        try:
            run_cmd = f'{self.adb_path} -s {deviceId} {cmd}'
            result = _run_hidden(run_cmd)
            return result
        finally:
            telemetry.end_adb(started)

    def shell_noDevice(self, cmd):
        started = telemetry.begin_adb()
        try:
            run_cmd = f'{self.adb_path} {cmd}'
            result = _run_hidden(run_cmd)
            return result
        finally:
            telemetry.end_adb(started)

    def popen_readlines(self, cmd):
        started = telemetry.begin_adb()
        try:
            return _read_hidden(cmd, split_lines=True)
        finally:
            telemetry.end_adb(started)

    def popen_read(self, cmd):
        started = telemetry.begin_adb()
        try:
            return _read_hidden(cmd)
        finally:
            telemetry.end_adb(started)



adb = ADB()
