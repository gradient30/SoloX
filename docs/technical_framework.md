# 技术架构

## 1. 整体架构

SoloX 是一个基于 Flask 构建的轻量级 Web 服务，前端使用 Tabler 框架渲染页面，后端提供 RESTful API 接口，支持本地运行或远程调用。

```
┌─────────────────┐    HTTP    ┌──────────────────┐    ADB     ┌──────────────┐
│   Web 浏览器     │ ──────────▶│   Flask 服务      │ ──────────▶│ Android 设备  │
└─────────────────┘            └──────────────────┘            └──────────────┘
                                          │
                                          │ tidevice
                                          ▼
                               ┌──────────────────┐
                               │    iOS 设备       │
                               └──────────────────┘
```

## 2. 技术选型

### 2.1 后端技术栈

- **语言**: Python 3.10+
- **Web框架**: Flask
- **设备通信**:
  - Android: ADB 命令
  - iOS: 基于 tidevice 和 libimobiledevice 的私有协议
- **进程管理**: multiprocessing
- **日志**: logzero
- **WebSocket**: flask-socketio (部分功能)

### 2.2 前端技术栈

- **UI框架**: Tabler
- **图表库**: ApexCharts
- **主要依赖**: jQuery, socket.io.js

### 2.3 数据存储

- 无持久化存储，数据临时保存在内存中
- 性能数据通过文件系统临时存储
- 报告生成基于 HTML 模板引擎

## 3. 核心模块介绍

### 3.1 主要目录结构

```
solox/
├── public/              # 核心功能模块
│   ├── apm.py          # 性能采集核心逻辑
│   ├── apm_pk.py       # PK模式性能对比逻辑
│   ├── common.py       # 通用工具类
│   ├── android_fps.py  # Android FPS 监控
│   ├── _iosPerf.py     # iOS 性能监控
│   └── adb/            # ADB 相关工具
├── view/               # Flask 视图模块
│   ├── apis.py         # API 接口
│   └── pages.py        # 页面路由
├── static/             # 静态资源文件
└── templates/          # HTML 模板文件
```

### 3.2 核心类说明

#### 3.2.1 APM 性能监控类

- **CPU**: 处理 CPU 使用率收集
- **Memory**: 处理内存使用情况收集
- **Network**: 处理网络流量数据收集
- **FPS**: 处理帧率数据收集
- **Battery**: 处理电池状态收集
- **GPU**: 处理 GPU 使用率收集
- **Disk**: 处理磁盘使用情况收集

#### 3.2.2 设备管理类

- **Devices**: 设备连接和信息获取
- **File**: 文件操作管理
- **Method**: 通用方法封装
- **Platform**: 平台类型定义

## 4. 架构模式

### 4.1 MVC 模式

- **Model**: 封装在 [apm.py](file:///D:/workDir/githubwork/solox/solox/public/apm.py) 中，负责性能数据采集逻辑
- **View**: 由 Flask 路由处理，模板文件位于 [templates/](file:///D:/workDir/githubwork/solox/solox/templates/) 目录
- **Controller**: 逻辑分散在 [apis.py](file:///D:/workDir/githubwork/solox/solox/view/apis.py) 和 [pages.py](file:///D:/workDir/githubwork/solox/solox/view/pages.py) 中

### 4.2 模块化设计

功能划分为多个模块:
- [public](file:///D:/workDir/githubwork/solox/solox/public/): 核心功能模块
- [view](file:///D:/workDir/githubwork/solox/solox/view/): 视图模块
- [static](file:///D:/workDir/githubwork/solox/solox/static/): 静态资源
- [templates](file:///D:/workDir/githubwork/solox/solox/templates/): 模板文件

### 4.3 事件驱动

通过 WebSocket 实现实时数据推送功能。

## 5. 主要组件交互流程

1. 用户通过浏览器访问 Web 界面或调用 API 接口
2. 后端接收请求后调用 [apm.py](file:///D:/workDir/githubwork/solox/solox/public/apm.py) 中的方法执行性能数据采集
3. 数据采集通过 ADB（Android）或 iOS 私有协议完成
4. 结果返回给前端并渲染为图表或 HTML 报告

## 6. 性能指标计算方法

### 6.1 Android

#### CPU

- **appCpu**: 测试进程 CPU 使用率
- **systemCpu**: 整机 CPU 使用率

通过读取 `/proc/stat` 和 `/proc/pid/stat` 文件计算得出。

#### Memory

- **TotalPss**: 应用实际占用物理内存
- **NativePss**: native 内存
- **DalvikPss**: java 内存

通过 `adb shell dumpsys meminfo pid` 命令获取。

#### Network

- **recv**: 被测应用的下行流量
- **send**: 被测应用的上行流量

通过读取 `/proc/pid/net/dev` 文件获取。

#### FPS

支持 SurfaceView 和 gfxinfo 两种方式，默认优先获取 SurfaceView 的 FPS。

#### Jank

重新定义 jank 的计算方式：
- 视觉连续性问题：帧时长 > 前三帧平均时长 * 2
- 卡顿问题：帧时长 > 电影帧时长 * 2

#### Battery

- **Level**: 电量
- **Temperature**: 电池温度

通过 `adb shell dumpsys battery` 命令获取。

### 6.2 iOS

基于 tidevice 和 libimobiledevice 实现，通过私有协议获取设备性能数据。