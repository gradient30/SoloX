# API 文档

## 📡 API 概述

SoloX 提供了完整的 RESTful API 接口，支持通过 HTTP 请求获取设备性能数据。所有 API 返回 JSON 格式数据。

### 基础信息

- **基础 URL**: `http://{host}:{port}`
- **默认端口**: `50003`
- **健康检查**: `GET /health` → `{ "status": 1, "msg": "ok", "version": "..." }`
- **数据格式**: JSON
- **字符编码**: UTF-8

### 通用响应格式

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    // 具体数据内容
  },
  "timestamp": 1691234567.123
}
```

## 🔧 性能监控 API

### 1. 收集性能数据

**接口地址**: `/apm/collect`

**请求方式**: `GET`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| platform | string | 是 | 平台类型: `Android` 或 `iOS` |
| deviceid | string | 是 | 设备 ID |
| pkgname | string | 是 | 应用包名 |
| target | string | 是 | 监控目标，见下表 |

**监控目标 (target) 参数**:

| 值 | 说明 | 支持平台 |
|----|------|----------|
| `cpu` | CPU 使用率 | Android, iOS |
| `memory` | 内存使用量 | Android, iOS |
| `memory_detail` | 内存详细信息 | Android, iOS |
| `network` | 网络流量 | Android, iOS |
| `fps` | 帧率 (含游戏引擎自动检测) | Android, iOS |
| `battery` | 电池信息 | Android, iOS |
| `gpu` | GPU 使用率 | Android |

**请求示例**:

```bash
# 获取 CPU 使用率
curl "http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=cpu"

# 获取内存使用量
curl "http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=memory"
```

**响应示例**:

```json
// CPU 响应
{
  "code": 200,
  "msg": "success",
  "data": {
    "appCpuRate": 25.5,
    "systemCpuRate": 45.2
  }
}

// 内存响应
{
  "code": 200,
  "msg": "success",
  "data": {
    "pss": 156.8,
    "private": 128.4,
    "total": 2048.0
  }
}

// 网络响应
{
  "code": 200,
  "msg": "success",
  "data": {
    "upflow": 1024.5,
    "downflow": 2048.3
  }
}

// FPS 响应
{
  "code": 200,
  "msg": "success",
  "data": {
    "fps": 60,
    "jank": 2
  }
}

// 电池响应
{
  "code": 200,
  "msg": "success",
  "data": {
    "level": 85,
    "temperature": 32.5,
    "current": -150,
    "voltage": 4200,
    "power": 0.63
  }
}
```

### 2. 获取设备列表

**接口地址**: `/apm/devices`

**请求方式**: `GET`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| platform | string | 是 | 平台类型: `Android` 或 `iOS` |

**请求示例**:

```bash
curl "http://localhost:50003/apm/devices?platform=Android"
```

**响应示例**:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "devices": [
      {
        "deviceId": "ca6bd5a5",
        "model": "Pixel 6",
        "android_version": "13",
        "status": "device"
      },
      {
        "deviceId": "emulator-5554",
        "model": "Android SDK built for x86_64",
        "android_version": "11",
        "status": "device"
      }
    ]
  }
}
```

### 3. 获取应用进程

**接口地址**: `/apm/processes`

**请求方式**: `GET`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| platform | string | 是 | 平台类型 |
| deviceid | string | 是 | 设备 ID |
| pkgname | string | 是 | 应用包名 |

**请求示例**:

```bash
curl "http://localhost:50003/apm/processes?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app"
```

**响应示例**:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "processes": [
      "12345:com.example.app",
      "12346:com.example.app:service"
    ]
  }
}
```

## 🐍 Python SDK

### 1. 基础使用

```python
from solox.public.apm import AppPerformanceMonitor
from solox.public.common import Devices

# 设备管理
devices = Devices()

# 获取设备列表
device_list = devices.getDeviceIds()
print(f"连接的设备: {device_list}")

# 获取应用进程
processes = devices.getPid(deviceId='ca6bd5a5', pkgName='com.example.app')
print(f"应用进程: {processes}")

# 创建性能监控实例
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='ca6bd5a5',
    surfaceview=True,
    noLog=False
)
```

### 2. 单项数据收集

```python
# CPU 使用率 (%)
app_cpu, sys_cpu = apm.collectCpu()
print(f"应用 CPU: {app_cpu}%, 系统 CPU: {sys_cpu}%")

# 内存使用 (MB)
pss, private, total = apm.collectMemory()
print(f"PSS: {pss}MB, Private: {private}MB, Total: {total}MB")

# 内存详细信息 (MB)
memory_detail = apm.collectMemoryDetail()
print(f"内存详情: {memory_detail}")

# 网络流量 (KB)
upflow, downflow = apm.collectNetwork(wifi=True)
print(f"上行: {upflow}KB, 下行: {downflow}KB")

# FPS 和卡顿
fps, jank = apm.collectFps()
print(f"FPS: {fps}, 卡顿: {jank}")

# 注意: 游戏引擎应用 (Unity/UE4/Cocos/Laya) 会自动检测并切换到 SurfaceView 模式
# 即使创建 APM 时未指定 surfaceview=True，游戏 FPS 也能正确采集

# 电池信息
battery_info = apm.collectBattery()
print(f"电池信息: {battery_info}")

# GPU 使用率 (%) - 仅 Android
gpu_usage = apm.collectGpu()
print(f"GPU: {gpu_usage}%")
```

### 3. 全量数据收集

```python
# 全量监控配置
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='ca6bd5a5',
    surfaceview=True,
    noLog=False,
    collect_all=True,
    duration=300,  # 监控 5 分钟
    record=True    # 同时录制屏幕
)

# 开始全量监控
apm.collectAll(report_path='/path/to/report.html')
```

### 4. 高级配置

```python
# iOS 设备监控
apm_ios = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='iOS',
    deviceId='00008030-001234567890123A',
    noLog=False,
    collect_all=True,
    duration=180
)

# 自定义监控参数
apm_custom = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='ca6bd5a5',
    surfaceview=False,  # 使用 gfxinfo 模式
    noLog=True,         # 不保存日志
    pid=12345,          # 指定进程 ID
    record=False,       # 不录制屏幕
    collect_all=False,  # 手动收集数据
    duration=0          # 无限时长
)
```

## 🔄 WebSocket API

### 1. 实时数据推送

**连接地址**: `ws://{host}:{port}/socket.io/`

**命名空间**: `/logcat`

**事件类型**:

| 事件名 | 说明 | 数据格式 |
|--------|------|----------|
| `connect` | 连接建立 | - |
| `disconnect` | 连接断开 | - |
| `performance_data` | 性能数据推送 | JSON |
| `device_status` | 设备状态变化 | JSON |

**JavaScript 客户端示例**:

```javascript
// 连接 WebSocket
const socket = io('/logcat');

// 监听连接事件
socket.on('connect', function() {
    console.log('Connected to SoloX');
});

// 监听性能数据
socket.on('performance_data', function(data) {
    console.log('Performance data:', data);
    updateChart(data);
});

// 监听设备状态
socket.on('device_status', function(data) {
    console.log('Device status:', data);
    updateDeviceStatus(data);
});

// 发送监控配置
socket.emit('start_monitoring', {
    platform: 'Android',
    deviceId: 'ca6bd5a5',
    pkgName: 'com.example.app',
    targets: ['cpu', 'memory', 'fps']
});
```

## 📊 批量操作 API

### 1. 批量设备监控

**接口地址**: `/apm/batch/collect`

**请求方式**: `POST`

**请求体**:

```json
{
  "devices": [
    {
      "platform": "Android",
      "deviceId": "ca6bd5a5",
      "pkgName": "com.example.app"
    },
    {
      "platform": "Android",
      "deviceId": "emulator-5554",
      "pkgName": "com.example.app"
    }
  ],
  "targets": ["cpu", "memory", "fps"],
  "duration": 60
}
```

**响应示例**:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "task_id": "batch_20230803_123456",
    "devices": [
      {
        "deviceId": "ca6bd5a5",
        "status": "started"
      },
      {
        "deviceId": "emulator-5554",
        "status": "started"
      }
    ]
  }
}
```

### 2. 获取批量任务状态

**接口地址**: `/apm/batch/status/{task_id}`

**请求方式**: `GET`

**响应示例**:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "task_id": "batch_20230803_123456",
    "status": "running",
    "progress": 75,
    "devices": [
      {
        "deviceId": "ca6bd5a5",
        "status": "running",
        "data_count": 45
      },
      {
        "deviceId": "emulator-5554",
        "status": "completed",
        "data_count": 60
      }
    ]
  }
}
```

## ❌ 错误码说明

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 200 | 成功 | - |
| 400 | 请求参数错误 | 检查请求参数格式和必填项 |
| 404 | 接口不存在 | 检查请求 URL 是否正确 |
| 500 | 服务器内部错误 | 查看服务器日志，检查设备连接 |
| 1001 | 设备未连接 | 检查设备连接状态 |
| 1002 | 应用未运行 | 确保目标应用正在运行 |
| 1003 | 权限不足 | 检查设备调试权限 |
| 1004 | 平台不支持 | 确认平台参数正确 |

## 🔧 API 调用示例

### cURL 示例

```bash
# 获取 CPU 数据
curl -X GET "http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=cpu"

# 获取设备列表
curl -X GET "http://localhost:50003/apm/devices?platform=Android"

# 批量监控
curl -X POST "http://localhost:50003/apm/batch/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "devices": [
      {
        "platform": "Android",
        "deviceId": "ca6bd5a5",
        "pkgName": "com.example.app"
      }
    ],
    "targets": ["cpu", "memory"],
    "duration": 60
  }'
```

### Python Requests 示例

```python
import requests

# 基础配置
base_url = "http://localhost:50003"
params = {
    "platform": "Android",
    "deviceid": "ca6bd5a5",
    "pkgname": "com.example.app"
}

# 获取 CPU 数据
response = requests.get(f"{base_url}/apm/collect", 
                       params={**params, "target": "cpu"})
cpu_data = response.json()
print(f"CPU 数据: {cpu_data}")

# 获取内存数据
response = requests.get(f"{base_url}/apm/collect", 
                       params={**params, "target": "memory"})
memory_data = response.json()
print(f"内存数据: {memory_data}")

# 批量监控
batch_data = {
    "devices": [params],
    "targets": ["cpu", "memory", "fps"],
    "duration": 60
}

response = requests.post(f"{base_url}/apm/batch/collect", 
                        json=batch_data)
batch_result = response.json()
print(f"批量任务: {batch_result}")
```

## 📶 弱网测试 API（Android）

> Root `tc netem` 保持兼容；Android Agent 需要显式安装 APK
> 并由用户在手机上授权 VPN。探测无需 Root。使用说明见
> [弱网测试用户指南](./weak-network-testing.md)，研发说明见
> [弱网工具技术说明](../06-engineering/weak-network-tooling.md)。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/apm/weaknet/presets` | GET | 预设列表，`lan=cn\|en` |
| `/apm/weaknet/capabilities` | GET | `platform` + `device` + `engine=auto|agent|root_tc` → root/tc/Agent/网卡/是否已应用 |
| `/apm/weaknet/status` | GET | 当前弱网状态 |
| `/apm/weaknet/apply` | GET/POST | `preset` 或 `delay_ms`/`jitter_ms`/`loss_pct`/`rate`；Agent 模式必须传 `target_package`，可传 `uplink_*` / `downlink_*` |
| `/apm/weaknet/clear` | GET/POST | 清除 tc 规则 |
| `/apm/weaknet/probe` | GET | `host`（默认 8.8.8.8）、`count` → RTT/丢包/抖动 |
| `/apm/weaknet/agent/status` | GET | 查询 Agent 安装、授权和控制通道状态 |
| `/apm/weaknet/agent/install` | POST | 显式安装内置 Agent APK，安装前校验 SHA-256 |
| `/apm/weaknet/agent/prepare` | POST | 显式启动手机端 VPN 授权页 |

```bash
curl "http://localhost:50003/apm/weaknet/presets?lan=cn"
curl "http://localhost:50003/apm/weaknet/capabilities?platform=Android&device=DEVICE_ID"
curl "http://localhost:50003/apm/weaknet/apply?platform=Android&device=DEVICE_ID&preset=3g"
curl "http://localhost:50003/apm/weaknet/apply?platform=Android&device=DEVICE_ID&engine=agent&target_package=com.example.app&preset=lte_weak"
curl "http://localhost:50003/apm/weaknet/probe?platform=Android&device=DEVICE_ID&host=8.8.8.8"
```

实验室校准使用 `scripts/weaknet_gateway/*.sh` 在 Linux 网关上配置双向 netem + IFB。
真机验收入口为 `python scripts/android_agent/acceptance.py --device SERIAL --package PACKAGE --profile lte_weak --smoke`。

## 🎬 录屏回放 API

| 接口 | 说明 |
|------|------|
| `/apm/record/info?scene=` | 解析 `report/` 下 mp4/mkv，返回 `browser_playable` |
| `/apm/record/stream?scene=` | 流式传输，支持 HTTP Range（页内播放器 seek） |
| `/apm/record/play?scene=` | 调用系统默认播放器（mkv fallback） |

## 📋 Logcat API

| 接口 | 说明 |
|------|------|
| `/apm/logcat/start` | 开始采集，`level` 可选 V–F |
| `/apm/logcat/stop` | 停止 |
| `/apm/logcat/get` | 轮询增量日志 |
| `/apm/logcat/export` | 导出 |

---

*相关文档: [性能监控详解](./performance-monitoring.md) • [项目目录与日志](../06-engineering/project-layout.md) • [快速启动](../02-development/quick-start.md)*
