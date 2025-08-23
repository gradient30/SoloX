# 性能监控详解

## 🎯 监控指标概述

SoloX 提供全面的移动应用性能监控，涵盖 CPU、内存、网络、渲染、电池等关键指标。

## 📊 CPU 监控

### 监控原理

#### Android 平台实现

**系统CPU使用率获取**:

通过读取 `/proc/stat` 文件获取系统CPU信息：

```
cpu  2490696 175785 2873834 17973539 12823 680472 230184 0 0 0
cpu0 621631 33199 739364 12893642 10736 365458 86720 0 0 0
...
```

每行CPU数据的字段含义：
- `user`: 从系统启动开始累计到当前时刻，处于用户态的运行时间
- `nice`: 从系统启动开始累计到当前时刻的nice时间
- `system`: 从系统启动开始累计到当前时刻，处于核心态的运行时间
- `idle`: 从系统启动开始累计到当前时刻，除IO等待时间以外的其它等待时间
- `iowait`: 从系统启动开始累计到当前时刻，IO等待时间
- `irq`: 从系统启动开始累计到当前时刻，硬中断时间
- `softirq`: 从系统启动开始累计到当前时刻，软中断时间

计算方式：
- CPU运行时长: `cpu = user + nice + system + iowait + irq + softirq`
- 总时长: `cpu_total = cpu + idle`
- 系统CPU使用率: `(cpu - cpu_pre) / (cpu_total - cpu_total_pre)`

**应用CPU使用率获取**:

通过读取 `/proc/pid/stat` 文件获取进程CPU信息：

```
6873 (a.out) R 6723 6873 6723 34819 6873 8388608 77 0 0 0 41958 31 0 0 25 0 3 0 5882654 1409024 56 4294967295...
```

关键字段：
- `utime(41958)`: 该任务在用户态运行的时间，单位为jiffies
- `stime(31)`: 该任务在核心态运行的时间，单位为jiffies

计算方式：
- 进程CPU使用率: `((utime + stime) - (utime_pre + stime_pre)) / (cpu_total - cpu_total_pre)`

#### iOS 平台实现

- 使用 `tidevice` 工具获取应用 CPU 使用率
- 通过系统 API 获取精确的 CPU 数据

### 数据格式

```json
{
  "appCpuRate": 25.5,    // 应用 CPU 使用率 (%)
  "systemCpuRate": 45.2  // 系统 CPU 使用率 (%)
}
```

### 使用示例

```python
# Python API
app_cpu, sys_cpu = apm.collectCpu()
print(f"应用 CPU: {app_cpu}%, 系统 CPU: {sys_cpu}%")

# HTTP API
curl "http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=cpu"
```

### 性能分析

- **正常范围**: 应用 CPU < 30%，系统 CPU < 70%
- **性能问题**: 持续高 CPU 使用率可能导致发热和耗电
- **优化建议**: 
  - 减少主线程计算
  - 优化算法复杂度
  - 使用异步处理

## 🧠 内存监控

### 监控原理

#### Android 平台实现

通过 `adb shell dumpsys meminfo pid` 获取详细内存信息：

```
Applications Memory Usage (in Kilobytes):
** MEMINFO in pid 23178 [com.example.app] **
                   Pss  Private  Private  SwapPss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------
  Native Heap       99       96        0     2028     6656     4327     2328
  Dalvik Heap        4        0        0      754     3078     1030     2048
 Dalvik Other        4        4        0      366
        Stack        8        8        0       26
    Other dev        4        0        4        0
     .so mmap      535        4        0      319
    .jar mmap      114        0        0        0
    .apk mmap        2        0        0        0
    .dex mmap      622        0        4     2617
    .oat mmap      409        0        0        0
    .art mmap      259       16        0     2183
   Other mmap       14        0        0        6
      Unknown       28       28        0      455
        TOTAL    10856      156        8     8754     9734     5357     4376

App Summary
                       Pss(KB)
                        ------
           Java Heap:       16
         Native Heap:       96
                Code:        8
               Stack:        8
            Graphics:        0
       Private Other:       36
              System:    10692
               TOTAL:    10856       TOTAL SWAP PSS:     8754
```

**关键指标说明**:
- **TotalPss**: 应用实际占用物理内存
- **NativePss**: Native内存使用量
- **DalvikPss**: Java内存使用量(OOM的主要原因)
- **Private Dirty**: 进程私有的脏页内存
- **Private Clean**: 进程私有的干净页内存

#### iOS 平台实现

- 使用 Instruments 相关 API 获取内存数据
- 监控应用的内存占用和系统可用内存

### 数据格式

```json
// 基础内存信息
{
  "pss": 156.8,      // PSS 内存 (MB)
  "private": 128.4,  // 私有内存 (MB)
  "total": 2048.0    // 总内存 (MB)
}

// 详细内存信息
{
  "java_heap": 45.2,     // Java 堆内存
  "native_heap": 23.1,   // Native 堆内存
  "code": 12.5,          // 代码段内存
  "stack": 2.3,          // 栈内存
  "graphics": 18.7,      // 图形内存
  "private_other": 15.4, // 其他私有内存
  "system": 8.9          // 系统内存
}
```

### 使用示例

```python
# 基础内存监控
pss, private, total = apm.collectMemory()
print(f"PSS: {pss}MB, Private: {private}MB")

# 详细内存监控
memory_detail = apm.collectMemoryDetail()
print(f"Java Heap: {memory_detail['java_heap']}MB")
```

### 内存泄漏检测

```python
import time

# 连续监控内存变化
memory_history = []
for i in range(60):  # 监控 1 分钟
    pss, _, _ = apm.collectMemory()
    memory_history.append(pss)
    time.sleep(1)

# 分析内存趋势
if len(memory_history) > 10:
    recent_avg = sum(memory_history[-10:]) / 10
    early_avg = sum(memory_history[:10]) / 10
    growth_rate = (recent_avg - early_avg) / early_avg * 100
    
    if growth_rate > 20:  # 内存增长超过 20%
        print(f"⚠️ 可能存在内存泄漏，增长率: {growth_rate:.2f}%")
```

## 🌐 网络监控

### 监控原理

#### Android 平台实现

通过读取 `/proc/pid/net/dev` 文件获取网络流量数据：

```
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
rmnet0:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0
wlan0: 1241518561  840807    0    0    0     0          0         7  7225770   73525    0    6    0     0       0          0
rmnet1:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0
```

**接口说明**:
- **wlan0**: WiFi流量接口
- **rmnet0/rmnet1**: 移动网络流量接口
- **bytes**: 接收/发送的字节数

**数据计算**:
- **recv**: 被测应用的下行流量
- **send**: 被测应用的上行流量
- 通过前后两次采样的差值计算流量增量

#### iOS 平台实现

- 使用系统 API 获取网络统计信息
- 监控应用级别的网络使用情况

### 数据格式

```json
{
  "upflow": 1024.5,    // 上行流量 (KB)
  "downflow": 2048.3   // 下行流量 (KB)
}
```

### 使用示例

```python
# 网络流量监控
upflow, downflow = apm.collectNetwork(wifi=True)
print(f"上行: {upflow}KB, 下行: {downflow}KB")

# 网络速度计算
import time

# 第一次测量
up1, down1 = apm.collectNetwork()
time.sleep(1)
# 第二次测量
up2, down2 = apm.collectNetwork()

# 计算速度 (KB/s)
upload_speed = up2 - up1
download_speed = down2 - down1
print(f"上传速度: {upload_speed}KB/s, 下载速度: {download_speed}KB/s")
```

## 🎮 FPS 监控

### 监控原理

#### Android 平台实现

Android提供两种FPS监控方式：

**SurfaceView 模式**:

通过 `dumpsys SurfaceFlinger --latency SurfaceView` 获取帧率：

```bash
adb shell dumpsys SurfaceFlinger --latency SurfaceView com.example.app/com.example.activity
```

- SurfaceFlinger 接受来自多个数据源的数据缓冲区，通过GPU合成并发送给显示设备
- 这是用户真实可视可体验到的帧数数据
- 游戏、视频类应用都是通过SurfaceView来进行绘制，优先获取SurfaceView的FPS

**GfxInfo 模式**:

通过 `dumpsys gfxinfo packageName` 获取渲染信息：

```
Applications Graphics Acceleration Info:
** Graphics info for pid 13422 [com.example.app] **
Total frames rendered: 110
Janky frames: 7 (6.36%)
50th percentile: 9ms
90th percentile: 13ms
95th percentile: 18ms
99th percentile: 36ms
Number Missed Vsync: 2
Number High input latency: 0
Number Slow UI thread: 6
```

**JANK 计算**:

重新定义jank的计算方式：
- **视觉连续性问题**: 帧时长 > 前三帧平均时长 × 2
- **卡顿问题**: 帧时长 > 电影帧时长(41.67ms) × 2

理解jank需要理解Google设计的三重缓存机制，当GPU未能在一次VSync时间内完成处理时，会产生视觉卡顿。

#### iOS 平台实现

- 使用 Core Animation 相关 API
- 监控主线程的渲染性能

### 数据格式

```json
{
  "fps": 60,    // 当前帧率 (Hz)
  "jank": 2     // 卡顿次数
}
```

### 使用示例

```python
# FPS 监控
fps, jank = apm.collectFps()
print(f"FPS: {fps}, 卡顿: {jank}")

# 流畅度分析
def analyze_smoothness(fps_values):
    avg_fps = sum(fps_values) / len(fps_values)
    low_fps_count = sum(1 for fps in fps_values if fps < 30)
    
    if avg_fps >= 55:
        return "流畅"
    elif avg_fps >= 45:
        return "一般"
    else:
        return "卡顿"

# 收集 FPS 数据
fps_history = []
for _ in range(30):  # 收集 30 秒数据
    fps, _ = apm.collectFps()
    fps_history.append(fps)
    time.sleep(1)

smoothness = analyze_smoothness(fps_history)
print(f"应用流畅度: {smoothness}")
```

## 🔋 电池监控

### 监控原理

#### Android 平台实现

通过 `adb shell dumpsys battery` 获取电池状态信息：

```
AC powered: false
USB powered: true
Wireless powered: false
Max charging current: 500000         # 最大充电电流
Max charging voltage: 5000000        # 最大充电电压
Charge counter: 1973820
status: 2                           # 电池状态：2=充电状态，其他=非充电状态   
health: 2                           # 电池健康状态：2=good
present: true                       # 电池是否安装在机身
level: 67                          # 当前电量百分比
scale: 100                         # 最大电量百分比
voltage: 4066                      # 当前电压(mV)
temperature: 330                   # 当前温度，单位为0.1摄氏度(要除以10)
technology: Li-ion
```

**关键指标说明**:
- **Level**: 电量百分比
- **Temperature**: 电池温度(需除以10得到摄氏度)
- **Voltage**: 电压(mV)
- **Current**: 电流(mA，可通过其他方式获取)
- **Power**: 功耗计算(功率 = 电压 × 电流)

**监控策略**:
- 电量收集时SoloX会在执行前断开充电
- 执行结束才恢复充电，确保数据准确性

#### iOS 平台实现

- 使用 IOKit 框架获取电池信息
- 监控电池健康状态和充电状态

### 数据格式

```json
{
  "level": 85,        // 电量百分比 (%)
  "temperature": 32.5, // 温度 (°C)
  "current": -150,    // 电流 (mA，负值表示放电)
  "voltage": 4200,    // 电压 (mV)
  "power": 0.63       // 功耗 (W)
}
```

### 使用示例

```python
# 电池监控
battery_info = apm.collectBattery()
print(f"电量: {battery_info['level']}%")
print(f"温度: {battery_info['temperature']}°C")
print(f"功耗: {battery_info['power']}W")

# 电池健康分析
def analyze_battery_health(battery_data):
    level = battery_data['level']
    temperature = battery_data['temperature']
    power = battery_data['power']
    
    issues = []
    
    if level < 20:
        issues.append("电量过低")
    if temperature > 40:
        issues.append("温度过高")
    if power > 2.0:
        issues.append("功耗过大")
    
    return issues if issues else ["电池状态正常"]

health_issues = analyze_battery_health(battery_info)
print(f"电池健康: {', '.join(health_issues)}")
```

## 🎨 GPU 监控 (仅 Android)

### 监控原理

- 通过 `dumpsys gpu` 获取 GPU 使用率
- 监控 GPU 渲染负载和频率
- 分析图形性能瓶颈

### 数据格式

```json
{
  "gpu_usage": 45.2  // GPU 使用率 (%)
}
```

### 使用示例

```python
# GPU 监控 (仅 Android)
if platform == 'Android':
    gpu_usage = apm.collectGpu()
    print(f"GPU 使用率: {gpu_usage}%")
    
    if gpu_usage > 80:
        print("⚠️ GPU 负载过高，可能影响渲染性能")
```

## 💾 磁盘 I/O 监控

### 监控原理

- 监控应用的磁盘读写操作
- 分析 I/O 性能瓶颈
- 检测频繁的文件操作

### 使用示例

```python
# 磁盘 I/O 监控
disk_io = apm.collectDisk()
print(f"磁盘 I/O: {disk_io}")
```

## 🌡️ 温度监控

### 监控原理

- 监控设备各个传感器的温度
- 包括 CPU、电池、GPU 等组件温度
- 分析设备热管理状态

### 使用示例

```python
# 温度监控
thermal_data = apm.collectThermal()
print(f"设备温度: {thermal_data}")
```

## 📈 性能分析最佳实践

### 1. 监控策略

```python
# 全面性能监控
def comprehensive_monitoring(apm, duration=300):
    """全面性能监控"""
    start_time = time.time()
    performance_data = {
        'cpu': [],
        'memory': [],
        'network': [],
        'fps': [],
        'battery': []
    }
    
    while time.time() - start_time < duration:
        # 收集各项指标
        app_cpu, sys_cpu = apm.collectCpu()
        pss, private, total = apm.collectMemory()
        upflow, downflow = apm.collectNetwork()
        fps, jank = apm.collectFps()
        battery = apm.collectBattery()
        
        # 记录数据
        performance_data['cpu'].append({
            'timestamp': time.time(),
            'app_cpu': app_cpu,
            'sys_cpu': sys_cpu
        })
        
        performance_data['memory'].append({
            'timestamp': time.time(),
            'pss': pss,
            'private': private
        })
        
        # ... 记录其他数据
        
        time.sleep(1)  # 1秒采样间隔
    
    return performance_data
```

### 2. 异常检测

```python
def detect_performance_issues(performance_data):
    """性能问题检测"""
    issues = []
    
    # CPU 异常检测
    cpu_values = [d['app_cpu'] for d in performance_data['cpu']]
    avg_cpu = sum(cpu_values) / len(cpu_values)
    if avg_cpu > 50:
        issues.append(f"CPU 使用率过高: {avg_cpu:.1f}%")
    
    # 内存异常检测
    memory_values = [d['pss'] for d in performance_data['memory']]
    if len(memory_values) > 10:
        memory_growth = (memory_values[-1] - memory_values[0]) / memory_values[0] * 100
        if memory_growth > 30:
            issues.append(f"内存增长过快: {memory_growth:.1f}%")
    
    # FPS 异常检测
    fps_values = [d['fps'] for d in performance_data['fps']]
    low_fps_ratio = sum(1 for fps in fps_values if fps < 30) / len(fps_values)
    if low_fps_ratio > 0.2:
        issues.append(f"低帧率比例过高: {low_fps_ratio*100:.1f}%")
    
    return issues
```

### 3. 报告生成

```python
def generate_performance_report(performance_data, output_path):
    """生成性能报告"""
    import json
    from datetime import datetime
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'duration': len(performance_data['cpu']),
            'avg_cpu': sum(d['app_cpu'] for d in performance_data['cpu']) / len(performance_data['cpu']),
            'max_memory': max(d['pss'] for d in performance_data['memory']),
            'avg_fps': sum(d['fps'] for d in performance_data['fps']) / len(performance_data['fps'])
        },
        'issues': detect_performance_issues(performance_data),
        'raw_data': performance_data
    }
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"性能报告已生成: {output_path}")
```

## 📊 监控场景示例

### 1. 应用启动性能监控

```python
def monitor_app_startup(device_id, package_name, platform='Android'):
    """监控应用启动性能"""
    apm = AppPerformanceMonitor(
        pkgName=package_name,
        platform=platform,
        deviceId=device_id,
        duration=30  # 监控30秒
    )
    
    startup_data = []
    start_time = time.time()
    
    while time.time() - start_time < 30:
        cpu_data = apm.collectCpu()
        memory_data = apm.collectMemory()
        
        startup_data.append({
            'timestamp': time.time() - start_time,
            'cpu': cpu_data[0],  # 应用CPU
            'memory': memory_data[0]  # PSS内存
        })
        
        time.sleep(0.5)  # 500ms采样
    
    # 分析启动性能
    max_cpu = max(d['cpu'] for d in startup_data)
    final_memory = startup_data[-1]['memory']
    
    print(f"启动过程最大CPU: {max_cpu}%")
    print(f"启动完成内存: {final_memory}MB")
    
    return startup_data
```

### 2. 长时间稳定性测试

```python
def stability_test(device_id, package_name, duration=3600):
    """长时间稳定性测试 (1小时)"""
    apm = AppPerformanceMonitor(
        pkgName=package_name,
        platform='Android',
        deviceId=device_id,
        duration=duration
    )
    
    # 每分钟记录一次数据
    test_data = []
    for i in range(duration // 60):
        memory_data = apm.collectMemory()
        battery_data = apm.collectBattery()
        
        test_data.append({
            'minute': i,
            'memory_pss': memory_data[0],
            'battery_level': battery_data['level'],
            'battery_temp': battery_data['temperature']
        })
        
        time.sleep(60)  # 等待1分钟
    
    # 分析稳定性
    memory_trend = [d['memory_pss'] for d in test_data]
    memory_growth = (memory_trend[-1] - memory_trend[0]) / memory_trend[0] * 100
    
    battery_drain = test_data[0]['battery_level'] - test_data[-1]['battery_level']
    max_temp = max(d['battery_temp'] for d in test_data)
    
    print(f"内存增长: {memory_growth:.2f}%")
    print(f"电池消耗: {battery_drain}%")
    print(f"最高温度: {max_temp}°C")
    
    return test_data
```

---

*相关文档: [API文档](./api-documentation.md) • [Web界面使用](./web-interface-guide.md)*
