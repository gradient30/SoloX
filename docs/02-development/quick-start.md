# 快速启动指南

## 📋 环境要求

### 系统要求
- **操作系统**: Windows 10+, macOS 10.14+, Ubuntu 18.04+
- **Python**: 3.10 或更高版本
- **内存**: 最少 4GB RAM
- **存储**: 至少 1GB 可用空间

### 必需工具

#### 1. Python 环境
```bash
# 检查 Python 版本
python --version
# 或
python3 --version

# 如果版本低于 3.10，请从官网下载最新版本
# https://www.python.org/downloads/
```

#### 2. ADB 工具 (Android 测试必需)
```bash
# 下载 Android Platform Tools
# https://developer.android.com/studio/releases/platform-tools

# 配置环境变量 (Windows)
# 将 platform-tools 目录添加到 PATH

# 验证安装
adb version
```

#### 3. iTunes (iOS 测试，仅 Windows)
```bash
# Windows 用户测试 iOS 设备需要安装 iTunes
# https://www.apple.com/itunes/download/
# 注意: 不支持 iOS 17
```

## 🚀 安装步骤

### 方法一: PyPI 安装 (推荐)

```bash
# 安装最新版本
pip install -U solox

# 安装指定版本
pip install solox==2.9.3

# 使用国内镜像 (网络较慢时)
pip install -i https://mirrors.ustc.edu.cn/pypi/web/simple -U solox
```

### 方法二: 源码安装

```bash
# 克隆项目
git clone https://github.com/smart-test-ti/SoloX.git
cd SoloX

# 安装依赖
pip install -r requirements.txt

# 安装项目
pip install -e .
```

### 方法三: 手动安装依赖 (推荐用于开发环境)

如果遇到权限问题或版本冲突，可以手动安装兼容的依赖版本：

```bash
# 克隆项目
git clone https://github.com/smart-test-ti/SoloX.git
cd SoloX

# 安装核心依赖 (使用用户级安装避免权限问题)
pip install --user fire logzero

# 安装 Web 框架依赖 (指定兼容版本)
pip install --user Flask==2.0.3 Werkzeug==2.0.3
pip install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2

# 安装设备通信依赖
pip install --user tidevice==0.9.7

# 安装其他依赖
pip install --user pyfiglet psutil opencv-python

# 验证安装
python -c "import solox; print('SoloX 安装成功')"
```

### 方法四: 开发环境安装

```bash
# 克隆项目
git clone https://github.com/smart-test-ti/SoloX.git
cd SoloX

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 🎯 启动服务

### 默认启动

```bash
# 使用默认配置启动
python -m solox

# 服务将在以下地址启动:
# http://localhost:50003/?platform=Android&lan=en
```

### 自定义配置启动

```bash
# 指定 IP 和端口
python -m solox --host=0.0.0.0 --port=8080

# 访问地址:
# http://0.0.0.0:8080/?platform=Android&lan=en
```

### 后台服务启动

```bash
# macOS/Linux
nohup python3 -m solox &

# Windows
start /min python3 -m solox &
```

## 📱 设备连接

### Android 设备

1. **开启开发者选项**
   - 设置 → 关于手机 → 连续点击版本号 7 次

2. **开启 USB 调试**
   - 设置 → 开发者选项 → USB 调试

3. **连接设备**
   ```bash
   # 检查设备连接
   adb devices
   
   # 应该看到类似输出:
   # List of devices attached
   # ca6bd5a5    device
   ```

4. **授权调试**
   - 首次连接会弹出授权对话框，点击"确定"

### iOS 设备

1. **安装依赖** (macOS)
   ```bash
   # 安装 libimobiledevice
   brew install libimobiledevice
   
   # 安装 tidevice
   pip install tidevice
   ```

2. **连接设备**
   ```bash
   # 检查设备连接
   tidevice list
   
   # 应该看到设备信息
   ```

3. **信任电脑**
   - 连接时选择"信任此电脑"

## 🌐 Web 界面使用

### 1. 访问界面

打开浏览器访问: `http://localhost:50003`

### 2. 选择平台

- **Android**: 选择 Android 平台进行测试
- **iOS**: 选择 iOS 平台进行测试

### 3. 选择设备

- 在设备列表中选择要测试的设备
- 确保设备已正确连接并授权

### 4. 选择应用

- 输入应用包名 (如: `com.example.app`)
- 或从已安装应用列表中选择

### 5. 配置监控参数

```javascript
// 监控配置示例
{
  "duration": 60,           // 监控时长 (秒)
  "cpuWarning": 80,        // CPU 告警阈值 (%)
  "memoryWarning": 1024,   // 内存告警阈值 (MB)
  "fpsWarning": 30,        // FPS 告警阈值
  "batteryWarning": 20,    // 电池告警阈值 (%)
  "gpuWarning": 80         // GPU 告警阈值 (%)
}
```

### 6. 开始监控

点击"开始监控"按钮，系统将开始收集性能数据并实时展示。

## 🔧 命令行使用

### 基本命令

```bash
# 查看帮助
python -m solox --help

# 启动服务
python -m solox

# 指定配置
python -m solox --host=192.168.1.100 --port=8080
```

### 开发调试模式

```bash
# 进入项目目录
cd solox

# 启动调试模式
python debug.py
```

## 🐍 Python API 使用

### 基本使用

```python
from solox.public.apm import AppPerformanceMonitor
from solox.public.common import Devices

# 获取设备信息
d = Devices()
devices = d.getDeviceIds()
print(f"连接的设备: {devices}")

# 获取应用进程
processList = d.getPid(deviceId='ca6bd5a5', pkgName='com.example.app')
print(f"应用进程: {processList}")

# 创建性能监控实例
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='ca6bd5a5',
    surfaceview=True,
    noLog=False,
    duration=60
)

# 收集单项性能数据
cpu = apm.collectCpu()          # CPU 使用率
memory = apm.collectMemory()    # 内存使用
network = apm.collectNetwork()  # 网络流量
fps = apm.collectFps()          # FPS 帧率
battery = apm.collectBattery()  # 电池信息

print(f"CPU: {cpu}%")
print(f"内存: {memory}MB")
print(f"网络: {network}KB")
print(f"FPS: {fps}Hz")
print(f"电池: {battery}")
```

### 全量监控

```python
# 全量性能监控
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='ca6bd5a5',
    collect_all=True,
    duration=300,  # 监控 5 分钟
    record=True    # 同时录制屏幕
)

# 开始监控并生成报告
apm.collectAll(report_path='/path/to/report.html')
```

## 🔍 验证安装

### 1. 检查服务状态

```bash
# 访问健康检查接口
curl http://localhost:50003/health

# 预期返回: {"status": "ok"}
```

### 2. 检查设备连接

```bash
# Android
adb devices

# iOS
tidevice list
```

### 3. 测试 API

```bash
# 测试 CPU 监控 API
curl "http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=cpu"
```

---

*相关文档: [开发指南](./development-guide.md) • [API文档](../04-user-guides/api-documentation.md)*
