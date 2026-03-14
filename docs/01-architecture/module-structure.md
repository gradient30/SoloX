# 模块结构

## 📁 项目目录结构

```
solox/
├── __init__.py              # 包初始化，版本信息
├── __main__.py              # 命令行入口
├── web.py                   # Web 服务主入口
├── debug.py                 # 开发调试模式
├── public/                  # 核心业务模块
│   ├── __init__.py
│   ├── apm.py              # 性能监控核心模块
│   ├── apm_pk.py           # 对比测试模块
│   ├── android_fps.py      # Android FPS 采集引擎 (含游戏引擎支持)
│   ├── common.py           # 公共工具类
│   ├── adb/                # Android ADB 工具
│   ├── scrcpy/             # 屏幕录制工具
│   ├── iosperf/            # iOS 性能监控模块
│   └── report_template/    # 报告模板
├── view/                    # Web 视图层
│   ├── __init__.py
│   ├── apis.py             # API 路由
│   └── pages.py            # 页面路由
├── templates/               # HTML 模板
├── static/                  # 静态资源
└── __pycache__/            # Python 缓存
```

## 🔧 核心模块详解

### 1. 入口模块

#### `__main__.py` - 命令行入口
```python
from __future__ import absolute_import
import fire as fire
from solox import __version__
from solox.web import main

if __name__ == '__main__':
    fire.Fire(main)
```

**功能**: 
- 使用 Fire 库自动生成命令行接口
- 调用 web.py 中的 main 函数启动服务

#### `web.py` - Web 服务主入口
```python
app = Flask(__name__, template_folder='templates', static_folder='static')
app.register_blueprint(api)    # 注册 API 路由
app.register_blueprint(page)   # 注册页面路由

def main(host=ip(), port=50003):
    # 多进程启动 Web 服务和浏览器
```

**功能**:
- Flask 应用初始化和配置
- 路由注册和中间件配置
- 多进程服务启动管理
- 自动打开浏览器

### 2. 性能监控核心模块

#### `public/apm.py` - 应用性能监控
```python
class AppPerformanceMonitor:
    """应用性能监控核心类"""
    
    def __init__(self, pkgName, platform, deviceId, ...):
        # 初始化监控参数
        
    def collectCpu(self):
        """CPU 使用率收集"""
        
    def collectMemory(self):
        """内存使用收集"""
        
    def collectNetwork(self):
        """网络流量收集"""
        
    def collectFps(self):
        """FPS 帧率收集"""
        
    def collectBattery(self):
        """电池信息收集"""
        
    def collectAll(self, report_path=None):
        """全量性能数据收集 - 多进程并发执行"""
        process_num = 8 if self.record else 7
        pool = multiprocessing.Pool(processes=process_num)
        pool.apply_async(self.collectCpu)
        pool.apply_async(self.collectMemory)
        # ... 其他性能指标收集
```

**功能**:
- 跨平台性能数据收集
- 多进程并发数据采集
- 实时数据处理和分析
- 性能报告生成

#### `public/apm_pk.py` - 对比测试模块
**功能**:
- 双设备性能对比测试
- 性能基准建立
- 对比报告生成

#### `public/android_fps.py` - Android FPS 采集引擎
```python
# 游戏引擎 Activity 模式匹配
GAME_ENGINE_PATTERNS = {
    'unity': ['com.unity3d.player.UnityPlayerActivity', ...],
    'unreal': ['com.epicgames.ue4.GameActivity', ...],
    'cocos': ['org.cocos2dx.lib.Cocos2dxActivity', ...],
    'laya': ['com.layabox.game', ...],
}

class GameSurfaceDetector:
    """游戏引擎渲染 Surface 检测器
    - 解析 dumpsys SurfaceFlinger --list
    - 识别游戏引擎 Surface 命名模式
    - 支持 Android 8.x-16.x 全版本格式
    - 返回优先级排序的候选 Surface 列表
    """

class SurfaceStatsCollector:
    """FPS 帧率采集器
    - SurfaceFlinger --latency 模式 (SurfaceView)
    - gfxinfo framestats 模式 (标准应用)
    - 游戏引擎自动检测和模式切换
    - 多 Surface 回退机制
    - Page flip count 兜底方案
    """
```

**功能**:
- Android FPS 和 Jank 采集
- 游戏引擎 (Unity/UE4/UE5/Cocos/Laya) 自动识别
- 多 Surface 回退策略
- Android 8.x-16.x 全版本兼容
- Page flip count 兜底 FPS 采集

### 3. 设备管理模块

#### `public/common.py` - 公共工具类
```python
class Platform:
    Android = 'Android'
    iOS = 'iOS'
    Mac = 'MacOS'
    Windows = 'Windows'

class Devices:
    """设备管理类"""
    
    def getDeviceIds(self):
        """获取连接的设备列表"""
        
    def getPid(self, deviceId, pkgName):
        """获取应用进程 ID"""
        
    def devicesCheck(self, platform, deviceid, pkgname):
        """设备环境检查"""
        
    def getDdeviceDetail(self, deviceId, platform):
        """获取设备详细信息"""
```

**功能**:
- 跨平台设备管理
- 设备信息获取
- 应用进程管理
- 设备环境检查

### 4. 平台特定模块

#### `public/adb/` - Android ADB 工具
**功能**:
- Android 设备通信
- ADB 命令封装
- Shell 命令执行

#### `public/iosperf/` - iOS 性能监控
```python
from solox.public.iosperf._device import BaseDevice as Device
from solox.public.iosperf._usbmux import Usbmux, ConnectionType
from solox.public.iosperf._perf import Performance, DataType
```

**子模块**:
- `_device.py`: iOS 设备管理
- `_usbmux.py`: USB 多路复用通信
- `_perf.py`: iOS 性能数据收集
- `_sync.py`: 文件同步操作
- `__main__.py`: iOS 工具命令行接口

#### `public/scrcpy/` - 屏幕录制工具
**功能**:
- Android 屏幕录制
- 实时屏幕镜像
- 录制文件管理

### 5. Web 视图层

#### `view/apis.py` - API 路由
**功能**:
- RESTful API 接口定义
- 性能数据 API
- 设备管理 API
- 文件操作 API

#### `view/pages.py` - 页面路由
**功能**:
- Web 页面路由
- 模板渲染
- 静态资源服务

### 6. 前端资源

#### `templates/` - HTML 模板
**包含**:
- 主界面模板
- 性能监控页面
- 设备管理页面
- 报告展示页面

#### `static/` - 静态资源
**包含**:
- CSS 样式文件
- JavaScript 脚本
- 图片和图标
- 第三方库文件

## 🔄 模块间交互关系

### 数据流向
```
命令行入口 (__main__.py)
    ↓
Web 服务 (web.py)
    ↓
视图层 (view/)
    ↓
业务逻辑层 (public/)
    ↓
设备通信层 (adb/, iosperf/)
```

### 依赖关系
```
web.py
├── view/apis.py
├── view/pages.py
└── public/
    ├── apm.py
    │   └── android_fps.py (GameSurfaceDetector, SurfaceStatsCollector)
    ├── common.py
    ├── adb/
    └── iosperf/
```

## 📊 模块职责划分

### 核心业务模块 (`public/`)
- **职责**: 性能监控核心逻辑
- **特点**: 平台无关的业务逻辑
- **依赖**: 最小化外部依赖

### 视图层模块 (`view/`)
- **职责**: Web 接口和页面渲染
- **特点**: 轻量级，专注于数据展示
- **依赖**: Flask 框架

### 平台适配模块 (`adb/`, `iosperf/`)
- **职责**: 平台特定的设备通信
- **特点**: 封装平台差异
- **依赖**: 平台特定的工具和库

## 🔧 扩展性设计

### 新增性能指标
1. 在 `apm.py` 中添加收集方法
2. 在 `apis.py` 中添加对应接口
3. 在前端添加展示组件

### 新增平台支持
1. 创建平台特定模块
2. 实现设备通信接口
3. 在 `common.py` 中注册平台

### 新增功能模块
1. 在 `public/` 下创建功能模块
2. 在 `view/` 中添加对应接口
3. 更新前端界面

---

**相关文档**:
- [项目概述](./overview.md) - 项目基本介绍
- [系统设计](./system-design.md) - 系统架构设计
- [技术栈](./technology-stack.md) - 技术选型详情

*最后更新: 2026-03-14*
