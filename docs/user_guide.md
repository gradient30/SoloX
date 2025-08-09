# 用户指南

## 1. 快速入门

### 1.1 基本使用流程

1. 点击 Connect 连接移动设备（第一次会自动连接，如果选择框显示了设备信息表示连接成功）
2. 选择需要测试的包名
3. 选择包名对应的进程（一个 app 有可能有多个进程，比如微信小程序，如果没有进程说明这个 app 没有在运行）
4. 点击 Start 开始收集性能指标
5. 点击 Stop 结束收集，生成报告跳转到报告管理页

### 1.2 界面介绍

SoloX 界面主要分为以下几个部分：

1. **顶部导航栏**: 包含项目 Logo、版本信息和设置按钮
2. **设备连接区**: 显示连接的设备列表，支持手动连接
3. **应用选择区**: 选择要测试的应用包名和进程
4. **指标配置区**: 选择要收集的性能指标
5. **控制区**: 开始/停止收集按钮
6. **实时数据显示区**: 以图表形式展示实时性能数据
7. **报告管理区**: 查看和管理已生成的测试报告

## 2. 性能指标详解

### 2.1 CPU

显示应用进程 CPU 使用率和整机 CPU 使用率。

- **appCpu**: 应用进程 CPU 使用百分比
- **systemCpu**: 整机 CPU 使用百分比

### 2.2 Memory

显示应用内存使用情况。

- **TotalPss**: 应用实际占用物理内存(MB)
- **NativePss**: Native 内存(MB)
- **DalvikPss**: Java 内存(MB)

### 2.3 Network

显示应用网络流量使用情况。

- **recv**: 下行流量(KB)
- **send**: 上行流量(KB)

### 2.4 FPS

显示应用帧率。

- **FPS**: 每秒显示帧数(HZ)
- **Jank**: 卡顿次数

### 2.5 Battery

显示设备电池状态。

- **level**: 电量百分比(%)
- **temperature**: 电池温度(°C)

### 2.6 GPU

显示 GPU 使用率(%)。

> 仅支持部分高通芯片设备

### 2.7 其他指标

- **Disk**: 磁盘使用情况
- **Thermal**: 设备温度传感器数据

## 3. 高级功能

### 3.1 PK 模式

支持两种 PK 模式：

1. **2-devices**: 两个不同设备上的同一应用对比
2. **2-apps**: 同一设备上的两个不同应用对比

使用步骤：
1. 在首页选择 PK 模式
2. 按照提示连接设备或选择应用
3. 开始收集数据
4. 查看对比报告

### 3.2 启动时间测试

#### Android

1. 首先打开目标 app 的启动到达界面
2. 在 Start-up Time 弹窗点击按钮"Get current activity"
3. 如果要测试热启动就直接点 Start 按钮
4. 如果测试冷启动就杀掉 app 点击 Start 按钮

#### iOS

1. 事先安装模块 `pip install py-ios-device`
2. 点击 Start

### 3.3 屏幕录制

#### 启用录制

1. 在首页打开"Record Screen"开关
2. 点击 Start 开始收集数据并同时录制视频
3. 结束后 Report 管理页会显示播放按钮

#### 注意事项

- 目前仅支持 Android 端录制
- Mac 电脑需要检查 Scrcpy 是否安装成功，可使用 `brew install scrcpy` 安装

### 3.4 自定义时长收集

在设置中可以配置收集时长，支持设置执行时长以自动停止收集。

## 4. 报告管理

### 4.1 报告查看

1. 收集完成后自动跳转到报告页面
2. 也可通过顶部导航栏的"Report"进入报告管理页
3. 报告以列表形式展示，包含时间、设备、应用等信息

### 4.2 报告操作

- **查看**: 点击报告条目查看详细数据和图表
- **导出**: 支持导出 HTML 格式报告
- **删除**: 可删除不需要的报告
- **截图**: 支持对报告进行截图保存

### 4.3 报告内容

报告包含以下内容：
1. 性能指标图表展示
2. 统计数据汇总
3. 详细数据表格
4. 设备和应用信息

## 5. 设置和配置

### 5.1 性能告警设置

可为各项指标设置告警阈值：
- CPU 使用率告警
- 内存使用量告警
- FPS 告警
- 网络流量告警
- 电池电量告警
- GPU 使用率告警

### 5.2 远程设备设置

可配置远程设备 Agent：
1. 点击右上角设置按钮
2. 配置远程设备 IP 和端口
3. 保存设置

### 5.3 其他设置

- 收集时长设置
- 主题切换
- 语言设置

## 6. Python API 使用

### 6.1 基本用法

```python
from solox.public.apm import AppPerformanceMonitor

apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android', 
    deviceId='device_id'
)

# 收集单个指标
cpu = apm.collectCpu()
memory = apm.collectMemory()

# 收集所有指标
apm.collectAll()
```

### 6.2 参数说明

| 参数 | 说明 | 类型 | 必填 |
|------|------|------|------|
| pkgName | 应用包名 | str | 是 |
| platform | 平台类型(Android/iOS) | str | 是 |
| deviceId | 设备ID | str | 否 |
| surfaceview | 是否使用SurfaceView | bool | 否 |
| noLog | 是否保存日志文件 | bool | 否 |
| pid | 进程ID | str | 否 |
| record | 是否录制屏幕 | bool | 否 |
| collect_all | 是否收集所有指标 | bool | 否 |
| duration | 运行时间(秒) | int | 否 |

### 6.3 收集方法

```python
# 各项指标收集方法
cpu = apm.collectCpu()           # CPU使用率
memory = apm.collectMemory()     # 内存使用情况
memory_detail = apm.collectMemoryDetail()  # 内存详细信息
network = apm.collectNetwork()   # 网络流量
fps = apm.collectFps()           # 帧率
battery = apm.collectBattery()   # 电池状态
gpu = apm.collectGpu()           # GPU使用率
disk = apm.collectDisk()         # 磁盘使用情况
thermal = apm.collectThermal()   # 温度传感器数据

# 收集所有指标
apm.collectAll(report_path='/path/to/report.html')
```

## 7. 最佳实践

### 7.1 测试环境准备

1. 确保设备已开启开发者选项和 USB 调试
2. 使用原装数据线连接设备
3. 关闭设备省电模式
4. 关闭不必要的后台应用

### 7.2 测试场景设计

1. **冷启动测试**: 杀掉应用后重新启动
2. **热启动测试**: 应用在后台时重新启动
3. **功能操作测试**: 模拟用户典型操作流程
4. **长时间运行测试**: 监控应用长时间运行的稳定性

### 7.3 数据分析建议

1. 关注 CPU 和内存峰值
2. 观察 FPS 稳定性
3. 注意电池消耗情况
4. 分析网络流量合理性
5. 对比不同设备和系统版本的表现