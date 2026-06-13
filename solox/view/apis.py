import os
import shutil
import time
import requests
import json
from flask import g, request, make_response, send_file
from logzero import logger
from flask import Blueprint
from solox import __version__
from solox.public.apm import (CPU, Memory, Network, FPS, Battery, GPU, Energy, Disk,ThermalSensor, Target)
from solox.public.apm_pk import (CPU_PK, MEM_PK, Flow_PK, FPS_PK)
from solox.public.common import (Devices, File, Method, Install, Platform, Scrcpy, LogcatManager,
                                 CHART_DEFAULT_MAX_POINTS)
from solox.public.weak_network import WeakNetworkManager
from solox.public.performance_telemetry import telemetry

d = Devices()
f = File()
api = Blueprint("api", __name__)
method = Method()


@api.before_request
def _start_api_telemetry():
    if (
        request.path.startswith('/apm/')
        and request.path != '/apm/telemetry'
    ):
        g.solox_api_telemetry = (
            request.path,
            telemetry.begin_api(request.path),
        )


@api.after_request
def _finish_api_telemetry(response):
    request_telemetry = getattr(g, 'solox_api_telemetry', None)
    if request_telemetry is not None:
        route, started = request_telemetry
        duration_ms = telemetry.end_api(route, started)
        if duration_ms is not None:
            response.headers['X-SoloX-Response-Time-Ms'] = '{:.3f}'.format(
                duration_ms,
            )
    return response


def _safe_report_scene_path(report_dir, scene):
    if (
        not scene
        or scene in ('.', '..')
        or '/' in scene
        or '\\' in scene
        or ':' in scene
        or os.path.isabs(scene)
    ):
        return None
    report_root = os.path.realpath(report_dir)
    scene_path = os.path.realpath(os.path.join(report_root, scene))
    if scene_path == report_root:
        return None
    try:
        if os.path.commonpath((report_root, scene_path)) != report_root:
            return None
    except ValueError:
        return None
    return scene_path


def _positive_int_request_value(name, default, maximum=None):
    raw_value = request.values.get(name)
    if raw_value in (None, ''):
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    if maximum is not None:
        return min(value, maximum)
    return value


def _optional_positive_int_request_value(name, maximum=None):
    raw_value = request.values.get(name)
    if raw_value in (None, ''):
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    if maximum is not None:
        return min(value, maximum)
    return value


@api.route('/health', methods=['get'])
def health_check():
    """Liveness probe for Docker, dev.sh status, and load balancers."""
    return {'status': 1, 'msg': 'ok', 'version': __version__}


@api.route('/apm/telemetry', methods=['get'])
def getPerformanceTelemetry():
    """Return bounded in-process API and ADB performance statistics."""
    if request.args.get('reset') == '1':
        telemetry.reset()
    result = {'status': 1}
    result.update(telemetry.snapshot())
    return result


def _fps_big_jank(monitor):
    val = getattr(monitor, 'big_jank', 0)
    return int(val) if isinstance(val, (int, float)) else 0


@api.route('/apm/cookie', methods=['post', 'get'])
def setCookie():
    """set apm data to cookie"""
    cpuWarning = request.args.get('cpuWarning')
    memWarning = request.args.get('memWarning')
    fpsWarning = request.args.get('fpsWarning')
    netdataRecvWarning = request.args.get('netdataRecvWarning')
    netdataSendWarning = request.args.get('netdataSendWarning')
    betteryWarning = request.args.get('betteryWarning')
    gpuWarning = request.args.get('gpuWarning')
    duration = request.args.get('duration')
    solox_host = request.args.get('solox_host')
    host_switch = request.args.get('host_switch')

    resp = make_response('set cookie ok')
    resp.set_cookie('cpuWarning', cpuWarning)
    resp.set_cookie('memWarning', memWarning)
    resp.set_cookie('fpsWarning', fpsWarning)
    resp.set_cookie('netdataRecvWarning', netdataRecvWarning)
    resp.set_cookie('netdataSendWarning', netdataSendWarning)
    resp.set_cookie('betteryWarning', betteryWarning)
    resp.set_cookie('gpuWarning', gpuWarning)
    resp.set_cookie('duration', duration)
    resp.set_cookie('solox_host', solox_host)
    resp.set_cookie('host_switch', host_switch)
    return resp

@api.route('/solox/version', methods=['post', 'get'])
def version():
    try:
        pypi = json.loads(requests.get(url='https://pypi.org/pypi/solox/json',timeout=3).text)
        version = pypi['info']['version']
        result = {'status': 1, 'lastest_version': version, 'current_version': __version__}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result    

@api.route('/apm/initialize', methods=['post', 'get'])
def initialize():
    """initialize apm env"""
    try:
        f.clear_file()
        result = {'status': 1, 'msg': 'initialize env success'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/device/info', methods=['post', 'get'])
def deviceinfo():
    """get devices info"""
    platform = method._request(request, 'platform')
    try:
        match(platform):
            case Platform.Android:
                deviceids = d.getDeviceIds()
                devices = d.getDevices()
                if len(deviceids) > 0:
                    pkgnames = d.getPkgname(deviceids[0])
                    device_detail = d.getDdeviceDetail(deviceId=deviceids[0], platform=platform)
                    result = {'status': 1,
                              'deviceids': deviceids,
                              'devices': devices,
                              'pkgnames': pkgnames,
                              'device_detail': device_detail}
                else:
                    result = {'status': 0, 'msg': 'no devices'}
            case Platform.iOS:
                deviceinfos = d.getDeviceInfoByiOS()
                if len(deviceinfos) > 0:
                    pkgnames = d.getPkgnameByiOS(deviceinfos[0])
                    device_detail = d.getDdeviceDetail(deviceId=deviceinfos[0], platform=platform)
                    result = {'status': 1,
                              'deviceids': deviceinfos,
                              'devices': deviceinfos,
                              'pkgnames': pkgnames,
                              'device_detail': device_detail}
                else:
                    result = {'status': 0, 'msg': 'no devices'}
            case _:
                result = {'status': 0, 'msg': f'no this platform = {platform}'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': 'devices connect error!'}
    return result

@api.route('/device/cpucore', methods=['post', 'get'])
def cpucore():
    try:
        deviceId = d.getDeviceIds()[0]
        num = d.getCpuCores(deviceId)
        result = {'status': 1, 'num': num}
    except Exception as e:
        result = {'status': 1, 'num': 0}    
    return result

@api.route('/device/package', methods=['post', 'get'])
def packageNames():
    """get devices packageNames"""
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    match(platform):
        case Platform.Android:
            deviceId = d.getIdbyDevice(device, platform)
            pkgnames = d.getPkgname(deviceId)
        case Platform.iOS:
            pkgnames = d.getPkgnameByiOS(device)
        case _:
            result = {'status': 0, 'msg': 'platform is undefined'}
            return result
    result = {'status': 1, 'pkgnames': pkgnames} if len(pkgnames) > 0 else  {'status': 0, 'msg': 'no pkgnames'}
    return result

@api.route('/package/pids', methods=['post', 'get'])
def getPackagePids():
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    pkgname = method._request(request, 'pkgname')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        pids = d.getPid(deviceId, pkgname)
        if len(pids) > 0:
            result = {'status': 1, 'pids': pids}
        else:
            result = {'status': 0, 'msg': 'No process found, please start the app first.'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': 'No process found, please start the app first.'}
    return result

@api.route('/package/activity', methods=['post', 'get'])
def getPackageActivity():
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        activity = d.getCurrentActivity(deviceId)
        result = {'status': 1, 'activity': activity}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': 'no activity found'}
    return result

@api.route('/apm/device/home', methods=['post', 'get'])
def sendDeviceHome():
    """Send HOME key to background the current app."""
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        d.sendHomeKey(deviceId)
        result = {'status': 1, 'msg': 'Home key sent'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/package/start/time/android', methods=['post', 'get'])
def getStartupTimeByAndroid():
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    activity = method._request(request, 'activity')
    launch_type = method._request(request, 'launch_type') or 'cold'
    try:
        deviceId = d.getIdbyDevice(device, platform)
        data = d.getStartupTimeByAndroid(activity, deviceId, launch_type)
        result = {'status': 1, 'data': data}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': 'no result found'}
    return result

@api.route('/package/start/time/ios', methods=['post', 'get'])
def getStartupTimeByiOS():
    pkgname = method._request(request, 'pkgname')
    try:
        time = d.getStartupTimeByiOS(pkgname)
        result = {'status': 1, 'time': time}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': 'no result found'}
    return result

@api.route('/apm/cpu', methods=['post', 'get'])
def getCpuRate():
    """get process cpu rate"""
    model = method._request(request, 'model')
    platform = method._request(request, 'platform')
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    try:
        match(model):
            case '2-devices':
                pkgNameList = []
                pkgNameList.append(pkgname)
                deviceId1 = d.getIdbyDevice(device.split(',')[0], 'Android')
                deviceId2 = d.getIdbyDevice(device.split(',')[1], 'Android')
                cpu = CPU_PK(pkgNameList=pkgNameList, deviceId1=deviceId1, deviceId2=deviceId2)
                first, second = cpu.getAndroidCpuRate()
                result = {'status': 1, 'first': first, 'second': second}
            case '2-app':
                pkgNameList = pkgname.split(',')
                deviceId1 = d.getIdbyDevice(device.split(',')[0], 'Android')
                deviceId2 = d.getIdbyDevice(device.split(',')[1], 'Android')
                cpu = CPU_PK(pkgNameList=pkgNameList, deviceId1=deviceId1, deviceId2=deviceId2)
                first, second = cpu.getAndroidCpuRate()
                result = {'status': 1, 'first': first, 'second': second}
            case _:
                process = method._request(request, 'process')
                pid = None
                deviceId = d.getIdbyDevice(device, platform)
                if process and platform == Platform.Android :
                    pid = process.split(':')[0]
                cpu = CPU(pkgName=pkgname, deviceId=deviceId, platform=platform, pid=pid)
                appCpuRate, systemCpuRate = cpu.getCpuRate()
                result = {'status': 1, 'appCpuRate': appCpuRate, 'systemCpuRate': systemCpuRate}
    except Exception as e:
        logger.error('get cpu failed')
        logger.exception(e)
        result = {'status': 1, 'appCpuRate': 0, 'systemCpuRate': 0}
    return result

@api.route('/apm/corecpu', methods=['post', 'get'])
def getCoreCpuRate():
    """get process cpu core rate"""
    platform = method._request(request, 'platform')
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    cores = method._request(request, 'cores')
    process = method._request(request, 'process')
    try:
        cores = int(cores)
        pid = None
        deviceId = d.getIdbyDevice(device, platform)
        if process and platform == Platform.Android :
            pid = process.split(':')[0]
        corecpu = CPU(pkgName=pkgname, deviceId=deviceId, platform=platform, pid=pid)
        coreCpuRate = corecpu.getCoreCpuRate(cores)
        result = {'status': 1, 'coreCpuRate': coreCpuRate}
    except Exception as e:
        logger.error('get core cpu failed')
        logger.exception(e)
        coreCpuRate = list()
        while cores > 0:
            coreCpuRate.append(0)
            cores = cores -1
        result = {'status': 1, 'coreCpuRate': coreCpuRate}
    return result

@api.route('/apm/mem', methods=['post', 'get'])
def getMemory():
    """get memery data"""
    model = method._request(request, 'model')
    platform = method._request(request, 'platform')
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    try:
        match(model):
            case '2-devices':
                pkgNameList = []
                pkgNameList.append(pkgname)
                deviceId1 = d.getIdbyDevice(device.split(',')[0], 'Android')
                deviceId2 = d.getIdbyDevice(device.split(',')[1], 'Android')
                mem = MEM_PK(pkgNameList=pkgNameList, deviceId1=deviceId1, deviceId2=deviceId2)
                first, second = mem.getProcessMemory()
                result = {'status': 1, 'first': first, 'second': second}
            case '2-app':
                pkgNameList = pkgname.split(',')
                deviceId1 = d.getIdbyDevice(device.split(',')[0], 'Android')
                deviceId2 = d.getIdbyDevice(device.split(',')[1], 'Android')
                mem = MEM_PK(pkgNameList=pkgNameList, deviceId1=deviceId1, deviceId2=deviceId2)
                first, second = mem.getProcessMemory()
                result = {'status': 1, 'first': first, 'second': second}
            case _:
                process = method._request(request, 'process')
                pid = None
                deviceId = d.getIdbyDevice(device, platform)
                if process and platform == Platform.Android :
                    pid = process.split(':')[0]
                mem = Memory(pkgName=pkgname, deviceId=deviceId, platform=platform, pid=pid)
                totalPass, swapPass = mem.getProcessMemory()
                result = {'status': 1, 'totalPass': totalPass, 'swapPass': swapPass}
    except Exception as e:
        logger.error('get memory data failed')
        logger.exception(e)
        result = {'status': 1, 'totalPass': 0, 'swapPass': 0}
    return result

@api.route('/apm/mem/detail', methods=['post', 'get'])
def getMemoryDetail():
    """get memery detail data"""
    platform = method._request(request, 'platform')
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    process = method._request(request, 'process')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        pid = process.split(':')[0]
        memory = Memory(pkgName=pkgname, deviceId=deviceId, platform=platform, pid=pid)
        memory_detail = memory.getAndroidMemoryDetail()
        result = {'status': 1, 'memory_detail': memory_detail}
    except Exception as e:
        logger.error('get memory detail data failed')
        logger.exception(e)
        result = {'status': 1, 'memory_detail': memory_detail}
    return result

@api.route('/apm/set/network', methods=['post', 'get'])
def setNetWorkData():
    """set network data"""
    platform = method._request(request, 'platform')
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    wifi_switch = method._request(request, 'wifi_switch')
    type = method._request(request, 'type')
    process = method._request(request, 'process')
    try:
        wifi = False if wifi_switch == 'false' else True
        deviceId = d.getIdbyDevice(device, platform)
        pid = None
        if process and platform == Platform.Android :
            pid = process.split(':')[0]
        network = Network(pkgName=pkgname, deviceId=deviceId, platform=platform, pid=pid)
        data = network.setAndroidNet(wifi=wifi)
        f.record_net(type, data[0], data[1])
        result = {'status': 1, 'msg':'set network data success'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg':'set network data failed'}
    return result

@api.route('/apm/network', methods=['post', 'get'])
def getNetWorkData():
    """get network data"""
    model = method._request(request, 'model')
    platform = method._request(request, 'platform')
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    wifi_switch = method._request(request, 'wifi_switch')
    try:
        wifi = False if wifi_switch == 'false' else True
        match(model):
            case '2-devices':
                pkgNameList = []
                pkgNameList.append(pkgname)
                deviceId1 = d.getIdbyDevice(device.split(',')[0], 'Android')
                deviceId2 = d.getIdbyDevice(device.split(',')[1], 'Android')
                network = Flow_PK(pkgNameList=pkgNameList, deviceId1=deviceId1, deviceId2=deviceId2)
                first, second = network.getNetWorkData()
                result = {'status': 1, 'first': first, 'second': second}
            case '2-app':
                pkgNameList = pkgname.split(',')
                deviceId1 = d.getIdbyDevice(device.split(',')[0], 'Android')
                deviceId2 = d.getIdbyDevice(device.split(',')[1], 'Android')
                network = Flow_PK(pkgNameList=pkgNameList, deviceId1=deviceId1, deviceId2=deviceId2)
                first, second = network.getNetWorkData()
                result = {'status': 1, 'first': first, 'second': second}
            case _:
                process = method._request(request, 'process')
                pid = None
                deviceId = d.getIdbyDevice(device, platform)
                if process and platform == Platform.Android :
                    pid = process.split(':')[0]
                network = Network(pkgName=pkgname, deviceId=deviceId, platform=platform, pid=pid)
                data = network.getNetWorkData(wifi=wifi,noLog=False)
                result = {'status': 1, 'upflow': data[0], 'downflow': data[1]}
    except Exception as e:
        logger.error('get network data failed')
        logger.exception(e)
        result = {'status': 1, 'upflow': 0, 'downflow': 0, 'first': 0, 'second': 0}
    return result

@api.route('/apm/fps', methods=['post', 'get'])
def getFps():
    """get fps data"""
    model = method._request(request, 'model')
    platform = method._request(request, 'platform')
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    surv = method._request(request, 'surv')
    try:
        surfaceview = False if surv == 'false' else True
        match(model):
            case '2-devices':
                pkgNameList = []
                pkgNameList.append(pkgname)
                deviceId1 = d.getIdbyDevice(device.split(',')[0], 'Android')
                deviceId2 = d.getIdbyDevice(device.split(',')[1], 'Android')
                fps = FPS_PK(pkgNameList=pkgNameList, deviceId1=deviceId1, deviceId2=deviceId2, surfaceview=surfaceview)
                first, second = fps.getFPS()
                result = {'status': 1, 'first': first, 'second': second}
            case '2-app':
                pkgNameList = pkgname.split(',')
                deviceId1 = d.getIdbyDevice(device.split(',')[0], 'Android')
                deviceId2 = d.getIdbyDevice(device.split(',')[1], 'Android')
                fps = FPS_PK(pkgNameList=pkgNameList, deviceId1=deviceId1, deviceId2=deviceId2, surfaceview=surfaceview)
                first, second = fps.getFPS()
                result = {'status': 1, 'first': first, 'second': second}
            case _:
                deviceId = d.getIdbyDevice(device, platform)
                fps_monitor = FPS.getObject(pkgName=pkgname, deviceId=deviceId, surfaceview=surfaceview, platform=platform)
                fps, jank = fps_monitor.getFPS()
                result = {'status': 1, 'fps': fps, 'jank': jank}
                result['big_jank'] = _fps_big_jank(fps_monitor)
                if hasattr(fps_monitor, 'fps_meta') and fps_monitor.fps_meta:
                    result['fps_meta'] = fps_monitor.fps_meta
    except Exception as e:
        logger.error('get fps failed')
        logger.exception(e)
        result = {'status': 1, 'fps': 0, 'jank': 0, 'big_jank': 0}
    return result
def getBattery():
    """get Battery data"""
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        battery_monitor = Battery(deviceId=deviceId, platform=platform)
        final = battery_monitor.getBattery()
        if platform == Platform.Android:
            result = {'status': 1, 'level': final[0], 'temperature': final[1]}
        else:
            result = {
                'status': 1,
                'temperature': final[0],
                'current': final[1],
                'voltage': final[2],
                'power': final[3]}
    except Exception as e:
        logger.exception(e)
        result = {'status': 1, 'level': 0, 'temperature': 0, 'current':0, 'voltage':0 , 'power':0}
    return result

@api.route('/apm/gpu', methods=['post', 'get'])
def getGpu():
    """get gpu data"""
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    platform = method._request(request, 'platform')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        gpu = GPU(pkgName=pkgname, deviceId=deviceId, platform=platform)
        value = gpu.getGPU()
        result = {'status': 1, 'gpu': value}
    except Exception as e:
        logger.exception(e)
        result = {'status': 1, 'gpu': 0}
    return result

@api.route('/apm/energy', methods=['post', 'get'])
def getEnergy():
    """get energy data"""
    pkgname = method._request(request, 'pkgname')
    device = method._request(request, 'device')
    platform = method._request(request, 'platform')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        enery = Energy(deviceId=deviceId, packageName=pkgname)
        value = enery.getEnergy()
        result = {'status': 1, 'value': value}
    except Exception as e:
        logger.exception(e)
        value = {
            "energy.overhead": 0,
            "energy.version": 0,
            "energy.gpu.cost": 0,
            "energy.cpu.cost": 0,
            "energy.appstate.cost": 0,
            "energy.thermalstate.cost": 0,
            "energy.networking.cost": 0,
            "energy.cost": 0,
            "energy.display.cost": 0,
            "energy.location.cost": 0,
        }
        result = {'status': 1, 'value': value}
    return result

@api.route('/apm/disk', methods=['post', 'get'])
def getDisk():
    """get disk data"""
    device = method._request(request, 'device')
    platform = method._request(request, 'platform')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        disk = Disk(deviceId=deviceId, platform=platform)
        value = disk.getDisk()
        result = {'status': 1, 'used': value['used'], 'free':value['free']}
    except Exception as e:
        logger.exception(e)
        result = {'status': 1, 'used': 0, 'free':0}
    return result

@api.route('/apm/set/disk', methods=['post', 'get'])
def setDiskData():
    """set disk data"""
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        disk = Disk(deviceId=deviceId)
        disk.setInitialDisk()
        result = {'status': 1, 'msg':'set disk data success'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg':'set disk data failed'}
    return result 

@api.route('/apm/set/thermal', methods=['post', 'get'])
def setThermalData():
    """set thermal data"""
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        thermal = ThermalSensor(deviceId=deviceId)
        thermal.setInitalThermalTemp()
        result = {'status': 1, 'msg':'set thermal data success'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg':'set thermal data failed'}
    return result

@api.route('/apm/scene/tag', methods=['post', 'get'])
def addSceneTag():
    """Add PerfDog-style scene label marker during live collection."""
    label = method._request(request, 'label')
    try:
        tag = f.add_scene_tag(label)
        result = {'status': 1, 'tag': tag}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result


@api.route('/apm/scene/tags', methods=['post', 'get'])
def listSceneTags():
    """List scene tags for current session or a saved report."""
    scene = request.args.get('scene') or request.form.get('scene')
    try:
        tags = f.get_scene_tags(scene if scene else None)
        result = {'status': 1, 'tags': tags}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result


@api.route('/apm/scene/stats', methods=['post', 'get'])
def getSceneStats():
    """Get min/max/avg stats and per-scene breakdown for a report."""
    try:
        scene = request.args.get('scene') or request.form.get('scene')
        platform = request.args.get('platform') or request.form.get('platform') or Platform.Android
        if not scene:
            return {'status': 0, 'msg': 'scene is required'}
        perf_stats = f._read_scene_json(scene, 'perf_stats.json')
        if perf_stats is None:
            perf_stats = f.build_perf_stats(scene, platform)
        tag_stats = f._read_scene_json(scene, 'scene_tag_stats.json')
        if tag_stats is None:
            tag_stats = f.build_scene_tag_stats(scene, platform)
        result = {
            'status': 1,
            'perf_stats': perf_stats,
            'scene_tag_stats': tag_stats,
        }
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result


@api.route('/apm/create/report', methods=['post', 'get'])
def makeReport():
    """Create test report records"""
    platform = method._request(request, 'platform')
    app = method._request(request, 'app')
    model = method._request(request, 'model')
    devices = method._request(request, 'devices')
    wifi_switch = method._request(request, 'wifi_switch')
    record_switch = method._request(request, 'record_switch')
    thermal_switch = method._request(request, 'thermal_switch')
    process = method._request(request, 'process')
    cores = method._request(request, 'cores')
    try:
        video = 0
        if platform == Platform.Android and model == 'normal':
            deviceId = d.getIdbyDevice(devices, platform)
            battery_monitor = Battery(deviceId=deviceId)
            battery_monitor.recoverBattery()
            wifi = False if wifi_switch == 'false' else True
            pid = None
            if process and platform == Platform.Android :
                pid = process.split(':')[0]
            
            # set current natwork
            network = Network(pkgName=app, deviceId=deviceId, platform=platform, pid=pid)
            data = network.setAndroidNet(wifi=wifi)
            f.record_net('end', data[0], data[1])
            
            # set current disk
            disk = Disk(deviceId=deviceId)
            disk.setCurrentDisk()

            # set current thermal
            thermal_checked = False if thermal_switch == 'false' else True
            if thermal_checked:
                thermal = ThermalSensor(deviceId=deviceId)
                thermal.setCurrentThermalTemp()

            record = False if record_switch == 'false' else True
            if record:
                video = 1
                Scrcpy.stop_record()        
        f.make_report(app=app, devices=devices, video=video, platform=platform, model=model, cores=cores)
        result = {'status': 1}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/edit/report', methods=['post', 'get'])
def editReport():
    """Edit test report records"""
    old_scene = method._request(request, 'old_scene')
    new_scene = method._request(request, 'new_scene')
    report_dir = os.path.join(os.getcwd(), 'report')
    if old_scene == new_scene:
        result = {'status': 0, 'msg': 'scene not changed'}
    elif os.path.exists(os.path.join(report_dir, new_scene)):
        result = {'status': 0, 'msg': 'scene existed'}
    else:
        try:
            new_scene = new_scene.replace('/', '_').replace(' ', '').replace('&', '_')
            os.rename(os.path.join(report_dir, old_scene), os.path.join(report_dir, new_scene))
            result = {'status': 1}
        except Exception as e:
            logger.exception(e)
            result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/export/report', methods=['post', 'get'])
def exportReport():
    platform = method._request(request, 'platform')
    scene = method._request(request, 'scene')
    try:
        path = f.export_excel(platform=platform, scene=scene)
        result = {'status': 1, 'msg':'success', 'path': path}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg':str(e)}
    return result

@api.route('/apm/export/html/android', methods=['post', 'get'])
def exportAndroidHtml():
    scene = method._request(request, 'scene')
    cpu_app = method._request(request, 'cpu_app')
    cpu_sys = method._request(request, 'cpu_sys')
    mem_total = method._request(request, 'mem_total')
    mem_swap = method._request(request, 'mem_swap')
    fps = method._request(request, 'fps')
    jank = method._request(request, 'jank')
    level = method._request(request, 'level')
    temperature = method._request(request, 'temperature')
    net_send = method._request(request, 'net_send')
    net_recv = method._request(request, 'net_recv')
    gpu = method._request(request, 'gpu')
    try:
        summary_dict = dict()
        summary_dict['app'] = f.readJson(scene).get('app')
        summary_dict['platform'] = f.readJson(scene).get('platform')
        summary_dict['devices'] = f.readJson(scene).get('devices')
        summary_dict['ctime'] = f.readJson(scene).get('ctime')
        summary_dict['cpu_app'] = cpu_app
        summary_dict['cpu_sys'] = cpu_sys
        summary_dict['mem_total'] = mem_total
        summary_dict['mem_swap'] = mem_swap
        summary_dict['fps'] = fps
        summary_dict['jank'] = jank
        summary_dict['level'] = level
        summary_dict['tem'] = temperature
        summary_dict['net_send'] = net_send
        summary_dict['net_recv'] = net_recv
        summary_dict['gpu'] = gpu
        summary_dict['cpu_charts'] = f.getCpuLog(Platform.Android, scene)
        summary_dict['mem_charts'] = f.getMemLog(Platform.Android, scene)
        summary_dict['mem_detail_charts'] = f.getMemDetailLog(Platform.Android, scene)
        summary_dict['net_charts'] = f.getFlowLog(Platform.Android, scene)
        summary_dict['battery_charts'] = f.getBatteryLog(Platform.Android, scene)
        summary_dict['fps_charts'] = f.getFpsLog(Platform.Android, scene)['fps']
        summary_dict['jank_charts'] = f.getFpsLog(Platform.Android, scene)['jank']
        summary_dict['gpu_charts'] = f.getGpuLog(Platform.Android, scene)
        path = f.make_android_html(scene, summary_dict)
        result = {'status': 1, 'msg':'success', 'path':path}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg':str(e)}
    return result

@api.route('/apm/export/html/ios', methods=['post', 'get'])
def exportiOSHtml():
    scene = method._request(request, 'scene')
    cpu_app = method._request(request, 'cpu_app')
    cpu_sys = method._request(request, 'cpu_sys')
    mem_total = method._request(request, 'mem_total')
    gpu = method._request(request, 'gpu')
    fps = method._request(request, 'fps')
    temperature = method._request(request, 'temperature')
    current = method._request(request, 'current')
    voltage = method._request(request, 'voltage')
    power = method._request(request, 'power')
    net_send = method._request(request, 'net_send')
    net_recv = method._request(request, 'net_recv')
    try:
        summary_dict = dict()
        summary_dict['app'] = f.readJson(scene).get('app')
        summary_dict['platform'] = f.readJson(scene).get('platform')
        summary_dict['devices'] = f.readJson(scene).get('devices')
        summary_dict['ctime'] = f.readJson(scene).get('ctime')
        summary_dict['cpu_app'] = cpu_app
        summary_dict['cpu_sys'] = cpu_sys
        summary_dict['mem_total'] = mem_total
        summary_dict['gpu'] = gpu
        summary_dict['fps'] = fps
        summary_dict['tem'] = temperature
        summary_dict['current'] = current
        summary_dict['voltage'] = voltage
        summary_dict['power'] = power
        summary_dict['net_send'] = net_send
        summary_dict['net_recv'] = net_recv
        summary_dict['cpu_charts'] = f.getCpuLog(Platform.iOS, scene)
        summary_dict['mem_charts'] = f.getMemLog(Platform.iOS, scene)
        summary_dict['net_charts'] = f.getFlowLog(Platform.iOS, scene)
        summary_dict['battery_charts'] = f.getBatteryLog(Platform.iOS, scene)
        summary_dict['fps_charts'] = f.getFpsLog(Platform.iOS, scene)
        summary_dict['gpu_charts'] = f.getGpuLog(Platform.iOS, scene)
        path = f.make_ios_html(scene, summary_dict)
        result = {'status': 1, 'msg':'success', 'path':path}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg':str(e)}
    return result

@api.route('/apm/log', methods=['post', 'get'])
def getLogData():
    """Get apm detailed data"""
    scene = method._request(request, 'scene')
    target = method._request(request, 'target')
    platform = method._request(request, 'platform')
    max_points = _positive_int_request_value(
        'max_points',
        CHART_DEFAULT_MAX_POINTS,
        CHART_DEFAULT_MAX_POINTS,
    )
    try:
        handlers = {
            'cpu': f.getCpuLog,
            'mem': f.getMemLog,
            'mem_detail': f.getMemDetailLog,
            'battery': f.getBatteryLog,
            'flow': f.getFlowLog,
            'fps': f.getFpsLog,
            'gpu': f.getGpuLog,
            'disk': f.getDiskLog,
            'cpu_core': f.getCpuCoreLog,
        }
        handler = handlers.get(target)
        if handler is None:
            return {'status': 0, 'msg': 'no target found'}
        result = handler(platform, scene, max_points)
        if isinstance(result, dict) and max_points is not None:
            result['downsampled'] = True
            result['max_points'] = max_points
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/log/compare', methods=['post', 'get'])
def getLogCompareData():
    """Get apm detailed data"""
    scene1 = method._request(request, 'scene1')
    scene2 = method._request(request, 'scene2')
    target = method._request(request, 'target')
    platform = method._request(request, 'platform')
    max_points = _optional_positive_int_request_value(
        'max_points',
        CHART_DEFAULT_MAX_POINTS,
    )
    try:
        handlers = {
            Target.CPU: f.getCpuLogCompare,
            Target.Memory: f.getMemLogCompare,
            Target.Battery: f.getBatteryLogCompare,
            Target.FPS: f.getFpsLogCompare,
            Target.GPU: f.getGpuLogCompare,
            'net_send': f.getFlowSendLogCompare,
            'net_recv': f.getFlowRecvLogCompare,
        }
        handler = handlers.get(target)
        if handler is None:
            return {'status': 0, 'msg': 'no target found'}
        result = handler(platform, scene1, scene2, max_points)
        if isinstance(result, dict) and max_points is not None:
            result['downsampled'] = True
            result['max_points'] = max_points
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/log/pk', methods=['post', 'get'])
def getpkLogData():
    """Get apm detailed data"""
    scene = method._request(request, 'scene')
    target1 = method._request(request, 'target1')
    target2 = method._request(request, 'target2')
    max_points = _optional_positive_int_request_value(
        'max_points',
        CHART_DEFAULT_MAX_POINTS,
    )
    try:
        first = f.readLog(
            scene=scene,
            filename=f'{target1}.log',
            max_points=max_points,
        )[0]
        second = f.readLog(
            scene=scene,
            filename=f'{target2}.log',
            max_points=max_points,
        )[0]
        result = {
            'status': 1,
            'first': first,
            'second': second,
        }
        if max_points is not None:
            result['downsampled'] = True
            result['max_points'] = max_points
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/remove/report', methods=['post', 'get'])
def removeReport():
    """Remove test report record"""
    scene = method._request(request, 'scene')
    report_dir = os.path.join(os.getcwd(), 'report')
    try:
        scene_path = _safe_report_scene_path(report_dir, scene)
        if scene_path is None:
            return {'status': 0, 'msg': 'invalid scene'}
        shutil.rmtree(scene_path, True)
        result = {'status': 1}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/report/list', methods=['get'])
def getReportList():
    """Get paginated report list"""
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    report_dir = os.path.join(os.getcwd(), 'report')
    os.makedirs(report_dir, exist_ok=True)
    report_entries = []
    excluded_extensions = {'.log', '.json', '.mkv', '.mp4'}
    for entry in os.scandir(report_dir):
        try:
            if not entry.is_dir():
                continue
            if os.path.splitext(entry.name)[1] in excluded_extensions:
                continue
            report_entries.append((entry.stat().st_mtime, entry.name))
        except OSError:
            continue
    report_entries.sort(key=lambda item: item[0], reverse=True)
    total = len(report_entries)
    start = (page - 1) * size
    items = []
    valid_index = 0
    for _, dir_name in report_entries:
        try:
            fpath = os.path.join(report_dir, dir_name, 'result.json')
            with open(fpath, encoding='utf-8') as fp:
                json_data = json.load(fp)
            if not isinstance(json_data, dict):
                continue
            duration = json_data.get('duration', '')
            duration_label = json_data.get('duration_label', '')
            duration_seconds = json_data.get('duration_seconds')
            if not duration_label:
                if duration_seconds is None:
                    duration_seconds = f.getDurationSeconds(dir_name)
                if not duration:
                    duration = f.format_duration_hms(duration_seconds)
                duration_label = f.format_duration_label(duration_seconds)
            item = {
                'scene': dir_name,
                'app': json_data.get('app', ''),
                'platform': json_data.get('platform', ''),
                'model': json_data.get('model', ''),
                'devices': json_data.get('devices', ''),
                'ctime': json_data.get('ctime', ''),
                'video': json_data.get('video', 0),
                'duration': duration,
                'duration_label': duration_label,
            }
        except Exception:
            continue
        if valid_index >= start:
            items.append(item)
            if len(items) >= size:
                break
        valid_index += 1
    return {'status': 1, 'data': items, 'total': total, 'page': page, 'size': size}

@api.route('/apm/collect', methods=['post', 'get'])
def apmCollect():
    """apm common api"""
    platform = method._request(request, 'platform')
    deviceid = method._request(request, 'deviceid')
    pkgname = method._request(request, 'pkgname')
    target = method._request(request, 'target')
    try:
        match(target):
            case Target.CPU:
                cpu = CPU(pkgName=pkgname, deviceId=deviceid, platform=platform)
                appCpuRate, systemCpuRate = cpu.getCpuRate(noLog=True)
                result = {'status': 1, 'appCpuRate': appCpuRate, 'systemCpuRate': systemCpuRate}
            case Target.Memory:
                mem = Memory(pkgName=pkgname, deviceId=deviceid, platform=platform)
                totalPass, swapPass = mem.getProcessMemory(noLog=True)
                result = {'status': 1, 'totalPass': totalPass, 'swapPass': swapPass}
            case Target.MemoryDetail:
                if platform == Platform.Android:
                    mem = Memory(pkgName=pkgname, deviceId=deviceid, platform=platform)
                    data = mem.getAndroidMemoryDetail(noLog=True)
                    result = {'status': 1, 'data': data} 
                else:
                    result = {'status': 0, 'msg': 'not support ios'}       
            case Target.Network:
                network = Network(pkgName=pkgname, deviceId=deviceid, platform=platform)
                data = network.getNetWorkData(wifi=True, noLog=True)
                result = {'status': 1, 'upflow': data[0], 'downflow': data[1]}
            case Target.FPS:
                fps_monitor = FPS(pkgName=pkgname, deviceId=deviceid, platform=platform)
                fps, jank = fps_monitor.getFPS(noLog=True)
                result = {'status': 1, 'fps': fps, 'jank': jank,
                          'big_jank': _fps_big_jank(fps_monitor)}
                if hasattr(fps_monitor, 'fps_meta') and fps_monitor.fps_meta:
                    result['fps_meta'] = fps_monitor.fps_meta
            case Target.Battery:
                battery_monitor = Battery(deviceId=deviceid)
                final = battery_monitor.getBattery(noLog=True)
                if platform == 'Android':
                    result = {'status': 1, 'level': final[0], 'temperature': final[1]}
                else:
                    result = {'status': 1, 'temperature': final[0], 'current': final[1], 'voltage': final[2], 'power': final[3]}
            case Target.GPU:
                gpu = GPU(pkgName=pkgname, deviceId=deviceid, platform=platform)
                final = gpu.getGPU(noLog=True)
                result = {'status': 1, 'gpu': final}
            case _:
                result = {'status': 0, 'msg': 'no this target'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/install/file', methods=['post', 'get'])
def installFile():
    """install apk/ipa from file"""
    platform = method._request(request, 'platform')
    file = request.files['file']
    currentPath = os.path.dirname(os.path.realpath(__file__))
    install = Install()
    unixtime = int(time.time())
    if platform == Platform.Android:
        file_path = os.path.join(currentPath, '{}.apk'.format(unixtime))
        if install.uploadFile(file_path, file):
            install_status = install.installAPK(file_path)
        else:
            result = {'status': 0, 'msg': 'install file failed'}
            return result
    else:
        file_path = os.path.join(currentPath, '{}.ipa'.format(unixtime))
        if install.uploadFile(file_path, file):
            install_status = install.installIPA(file_path)
        else:
            result = {'status': 0, 'msg': 'install file failed'}
            return result
    if install_status[0]:
        result = {'status': 1, 'msg': 'install sucess'}
    else:
        result = {'status': 0, 'msg': install_status[1]}
    return result

@api.route('/apm/install/link', methods=['post', 'get'])
def installLink():
    """install apk/ipa from link"""
    platform = method._request(request, 'platform')
    link = method._request(request, 'link')
    currentPath = os.path.dirname(os.path.realpath(__file__))
    install = Install()
    unixtime = int(time.time())
    if platform == Platform.Android:
        d_status = install.downloadLink(filelink=link, path=currentPath, name='{}.apk'.format(unixtime))
        if d_status:
            install_status = install.installAPK(os.path.join(currentPath, '{}.apk'.format(unixtime)))
        else:
            result = {'status': 0, 'msg': 'download link failed'}
            return result
    else:
        d_status = install.downloadLink(filelink=link, path=currentPath, name='{}.ipa'.format(unixtime))
        if d_status:
            install_status = install.installIPA(os.path.join(currentPath, '{}.ipa'.format(unixtime)))
        else:
            result = {'status': 0, 'msg': 'download link failed'}
            return result
    if install_status[0]:
        result = {'status': 1, 'msg': 'install sucess'}
    else:
        result = {'status': 0, 'msg': install_status[1]}
    return result

@api.route('/apm/record/start', methods=['post', 'get'])
def start_record():
    device = method._request(request, 'device')
    platform = method._request(request, 'platform')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        final = Scrcpy.start_record(deviceId)
        if final == 0:
            result = {'status': 1, 'msg': 'success'}
        else:
            result = {'status': 0, 'msg': 'record screen failed'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': 'record screen failed'}
    return result

@api.route('/apm/record/cast', methods=['post', 'get'])
def cast_screen():
    device = method._request(request, 'device')
    platform = method._request(request, 'platform')
    quality = request.args.get('quality', 'medium')
    if quality not in ('high', 'medium', 'low'):
        quality = 'medium'
    try:
        deviceId = d.getIdbyDevice(device, platform)
        final = Scrcpy.cast_screen(deviceId, quality=quality)
        if final == 0:
            result = {'status': 1, 'msg': 'success'}
        else:
            result = {'status': 0, 'msg': 'cast screen failed'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': 'cast screen failed'}
    return result

@api.route('/apm/record/cast/stop', methods=['post', 'get'])
def stop_cast_screen():
    try:
        Scrcpy._stop_cast_process()
        result = {'status': 1, 'msg': 'cast stopped'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/record/cast/status', methods=['post', 'get'])
def cast_screen_status():
    try:
        running = Scrcpy._cast_running
        recording = Scrcpy._is_recording()
        result = {'status': 1, 'casting': running, 'recording': recording}
    except Exception as e:
        result = {'status': 0, 'casting': False, 'recording': False}
    return result

@api.route('/apm/record/info', methods=['post', 'get'])
def record_info():
    """Return recording metadata for in-browser vs system player routing."""
    scene = method._request(request, 'scene')
    info = f.resolve_record_video(scene)
    if not info:
        return {'status': 0, 'msg': 'video not found'}
    return {
        'status': 1,
        'format': info['format'],
        'browser_playable': info['browser_playable'],
        'size': info['size'],
        'size_mb': info['size_mb'],
    }


@api.route('/apm/record/stream', methods=['get'])
def record_stream():
    """Stream report recording with HTTP Range support for seeking."""
    scene = method._request(request, 'scene')
    info = f.resolve_record_video(scene)
    if not info:
        return make_response('video not found', 404)
    mimetype = 'video/mp4' if info['format'] == 'mp4' else 'video/x-matroska'
    return send_file(
        info['path'],
        mimetype=mimetype,
        conditional=True,
        download_name='record.{}'.format(info['format']),
    )


@api.route('/apm/record/play', methods=['post', 'get'])
def play_record():
    """Open recording in the OS default video player (fallback for mkv / decode errors)."""
    scene = method._request(request, 'scene')
    info = f.resolve_record_video(scene)
    if not info:
        return {'status': 0, 'msg': 'video not found'}
    try:
        Scrcpy.play_video(info['path'])
        result = {'status': 1, 'msg': 'success', 'format': info['format']}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': 'play video failed'}
    return result

@api.route('/apm/weaknet/presets', methods=['post', 'get'])
def weaknet_presets():
    lan = request.args.get('lan', 'cn')
    return {'status': 1, 'presets': WeakNetworkManager.list_presets(lan=lan)}


@api.route('/apm/weaknet/capabilities', methods=['post', 'get'])
def weaknet_capabilities():
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    try:
        if platform != Platform.Android:
            return {'status': 1, 'simulation_supported': False, 'mode': 'unsupported',
                    'msg': 'weak network simulation is Android-only; iOS use Network Link Conditioner on macOS host'}
        device_id = d.getIdbyDevice(device, platform)
        cap = WeakNetworkManager.get_capabilities(device_id)
        return {'status': 1, **cap}
    except Exception as e:
        logger.exception(e)
        return {'status': 0, 'msg': str(e)}


@api.route('/apm/weaknet/status', methods=['post', 'get'])
def weaknet_status():
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    try:
        device_id = d.getIdbyDevice(device, platform)
        return {'status': 1, **WeakNetworkManager.get_status(device_id)}
    except Exception as e:
        logger.exception(e)
        return {'status': 0, 'msg': str(e)}


@api.route('/apm/weaknet/apply', methods=['post', 'get'])
def weaknet_apply():
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    preset = request.args.get('preset') or request.form.get('preset') or ''
    try:
        if platform != Platform.Android:
            return {'status': 0, 'msg': 'Android only'}
        device_id = d.getIdbyDevice(device, platform)
        if preset and preset != 'custom':
            data = WeakNetworkManager.apply_preset(device_id, preset)
        else:
            delay_ms = int(request.args.get('delay_ms', 0) or request.form.get('delay_ms', 0) or 0)
            jitter_ms = int(request.args.get('jitter_ms', 0) or request.form.get('jitter_ms', 0) or 0)
            loss_pct = float(request.args.get('loss_pct', 0) or request.form.get('loss_pct', 0) or 0)
            rate = request.args.get('rate') or request.form.get('rate') or None
            iface = request.args.get('interface') or request.form.get('interface') or None
            data = WeakNetworkManager.apply_custom(
                device_id,
                preset_id='custom',
                delay_ms=delay_ms,
                jitter_ms=jitter_ms,
                loss_pct=loss_pct,
                rate=rate,
                interface=iface,
            )
        return {'status': 1, **data}
    except Exception as e:
        logger.exception(e)
        return {'status': 0, 'msg': str(e)}


@api.route('/apm/weaknet/clear', methods=['post', 'get'])
def weaknet_clear():
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    try:
        device_id = d.getIdbyDevice(device, platform)
        data = WeakNetworkManager.clear(device_id)
        return data
    except Exception as e:
        logger.exception(e)
        return {'status': 0, 'msg': str(e)}


@api.route('/apm/weaknet/probe', methods=['post', 'get'])
def weaknet_probe():
    platform = method._request(request, 'platform')
    device = method._request(request, 'device')
    host = request.args.get('host') or WeakNetworkManager.DEFAULT_PROBE_HOST
    count = request.args.get('count', 10)
    try:
        device_id = d.getIdbyDevice(device, platform)
        probe = WeakNetworkManager.probe(device_id, host=host, count=count)
        return {'status': 1, 'probe': probe.to_dict()}
    except Exception as e:
        logger.exception(e)
        return {'status': 0, 'msg': str(e)}


@api.route('/apm/logcat/start', methods=['post', 'get'])
def startLogcat():
    """Start logcat error log capture"""
    device = method._request(request, 'device')
    platform = method._request(request, 'platform')
    severity = request.args.get('severity', 'E')
    try:
        deviceId = d.getIdbyDevice(device, platform)
        mgr = LogcatManager.get_instance()
        mgr.start(deviceId, severity=severity)
        result = {'status': 1, 'msg': 'logcat started'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/logcat/stop', methods=['post', 'get'])
def stopLogcat():
    """Stop logcat error log capture"""
    try:
        mgr = LogcatManager.get_instance()
        mgr.stop()
        result = {'status': 1, 'msg': 'logcat stopped'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/logcat/get', methods=['post', 'get'])
def getLogcat():
    """Get logcat lines via polling with optional filtering"""
    offset = request.args.get('offset', 0, type=int)
    severity = request.args.get('severity', None)
    tag = request.args.get('tag', None)
    keyword = request.args.get('keyword', None)
    try:
        mgr = LogcatManager.get_instance()
        lines, new_offset, total = mgr.get_lines(
            offset, severity=severity, tag=tag, keyword=keyword
        )
        result = {
            'status': 1, 'lines': lines, 'offset': new_offset,
            'total': total, 'running': mgr.is_running
        }
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result

@api.route('/apm/logcat/export', methods=['post', 'get'])
def exportLogcat():
    """Export all logcat lines as downloadable text file"""
    severity = request.args.get('severity', None)
    tag = request.args.get('tag', None)
    keyword = request.args.get('keyword', None)
    try:
        mgr = LogcatManager.get_instance()
        all_lines = mgr.get_all_lines(severity=severity, tag=tag, keyword=keyword)
        content = '\n'.join(all_lines)
        from flask import Response
        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': 'attachment; filename=logcat_export.txt'}
        )
    except Exception as e:
        logger.exception(e)
        return {'status': 0, 'msg': str(e)}

@api.route('/apm/logcat/clear', methods=['post', 'get'])
def clearLogcatBuffer():
    """Clear logcat buffer"""
    try:
        mgr = LogcatManager.get_instance()
        mgr.clear()
        result = {'status': 1, 'msg': 'logcat cleared'}
    except Exception as e:
        logger.exception(e)
        result = {'status': 0, 'msg': str(e)}
    return result
