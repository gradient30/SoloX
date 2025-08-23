<p align="center">
  <a>中文</a> | <a href="./README.md">English</a> | <a href="./docs/05-issues/faq.md">FAQ</a> | <a href="./docs/README.md">📖 完整文档</a>
</p>

<p align="center">
<a href="#">
<img src="https://cdn.nlark.com/yuque/0/2024/png/153412/1715927541315-fb4f7662-d8bb-4d3e-a712-13a3c3073ac8.png?x-oss-process=image%2Fformat%2Cwebp" alt="SoloX" width="100">
</a>
<br>
</p>

<p align="center">
<a href="https://pypi.org/project/solox/" target="__blank"><img src="https://img.shields.io/pypi/v/solox" alt="solox preview"></a>
<a href="https://pepy.tech/project/solox" target="__blank"><img src="https://static.pepy.tech/personalized-badge/solox?period=total&units=international_system&left_color=grey&right_color=orange&left_text=downloads"></a>
<br>
</p>

## 🔎 简介

SoloX 是一个专业的移动应用性能监控工具，可以实时收集 Android/iOS 性能数据。

快速定位分析性能问题，提升应用的性能和品质。无需 ROOT/越狱，即插即用。

![SoloX 界面](https://github.com/smart-test-ti/SoloX/assets/24454096/603895cd-730f-434c-807f-22333d10e633)

## 📦 环境要求

- 安装 Python 3.10+ [**下载**](https://www.python.org/downloads/)
- 安装 adb 和配置环境变量 [**下载**](https://developer.android.com/studio/releases/platform-tools)

💡 Windows 用户测试 iOS 需要先安装 iTunes [**参考**](https://github.com/alibaba/taobao-iphone-device) （不支持 iOS 17）

## 📥 安装

### 默认安装

```shell
pip install -U solox
```

### 使用镜像

```shell
pip install -i https://mirrors.ustc.edu.cn/pypi/web/simple -U solox
```

💡 如果网络无法通过 `pip install -U solox` 下载，可以尝试使用镜像下载，但可能不是最新版本。

## 🚀 快速启动

### 默认启动

```shell
python -m solox
```

### 自定义启动

```shell
python -m solox --host={ip} --port={port}
```

## 🐍 Python API 使用

```python
from solox.public.apm import AppPerformanceMonitor
from solox.public.common import Devices

# 获取设备列表
d = Devices()
devices = d.getDeviceIds()
print(f"连接的设备: {devices}")

# 获取应用进程
processes = d.getPid(deviceId='ca6bd5a5', pkgName='com.example.app')
print(f"应用进程: {processes}")

# 创建性能监控实例
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='ca6bd5a5',
    surfaceview=True,
    noLog=False
)

# 收集性能数据
cpu = apm.collectCpu()          # CPU 使用率 %
memory = apm.collectMemory()    # 内存使用 MB
network = apm.collectNetwork()  # 网络流量 KB
fps = apm.collectFps()          # FPS 帧率
battery = apm.collectBattery()  # 电池信息
```

## 🔥 核心功能

* **无需 ROOT/越狱**: Android 设备无需 ROOT，iOS 设备无需越狱
* **全面监控**: 支持 CPU、内存、网络、FPS、电池、GPU 等多维度监控
* **实时分析**: 美观的实时数据可视化和性能分析
* **跨平台支持**: 同时支持 Android 和 iOS 平台
* **易于集成**: 提供 Python API 和 RESTful 接口，便于 CI/CD 集成
* **美观报告**: 详细的性能分析报告和数据可视化

## 📚 文档中心

### 📖 [完整文档](./docs/README.md)

- 📐 [**架构设计**](./docs/01-architecture/) - 技术架构和系统设计
- 🛠️ [**开发指南**](./docs/02-development/) - 开发环境和编码规范  
- 🚀 [**部署运维**](./docs/03-deployment/) - 生产部署和 Docker 配置
- 📖 [**用户指南**](./docs/04-user-guides/) - API 文档和监控指南
- ❓ [**问题解决**](./docs/05-issues/) - 故障排除和常见问题

### 快速链接

- 🚀 [快速启动指南](./docs/02-development/quick-start.md)
- 📊 [API 接口文档](./docs/04-user-guides/api-documentation.md)
- 🔧 [故障排除指南](./docs/05-issues/troubleshooting.md)
- ❓ [常见问题 FAQ](./docs/05-issues/faq.md)

## 🔧 API 服务

### 后台启动服务

```shell
# macOS/Linux
nohup python3 -m solox &

# Windows
start /min python3 -m solox &
```

### 通过 API 请求数据

```shell
# Android
http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=cpu

# iOS
http://localhost:50003/apm/collect?platform=iOS&pkgname=com.example.app&target=cpu

# 支持的监控目标: cpu, memory, network, fps, battery, gpu
```

## 🎯 应用场景

- **移动应用性能测试**: 启动性能分析、内存泄漏检测、CPU 监控
- **自动化测试集成**: CI/CD 流水线集成、性能回归测试
- **开发调试辅助**: 实时性能监控、问题定位分析
- **竞品性能分析**: 不同应用间的性能对比测试

## 🌟 支持的监控指标

| 监控指标 | Android | iOS | 说明 |
|---------|---------|-----|------|
| 🔥 CPU 使用率 | ✅ | ✅ | 应用和系统 CPU 占用 |
| 🧠 内存使用 | ✅ | ✅ | 内存占用和详细分析 |
| 🌐 网络流量 | ✅ | ✅ | 上行/下行流量统计 |
| 🎮 FPS 帧率 | ✅ | ✅ | 界面渲染帧率和卡顿检测 |
| 🔋 电池信息 | ✅ | ✅ | 电量、温度、功耗等 |
| 🎨 GPU 使用率 | ✅ | ❌ | GPU 占用率（仅 Android） |

## 🤝 参与贡献

我们欢迎各种形式的贡献！请查看 [贡献指南](./docs/05-issues/contribution-guide.md) 了解详情。

## 📄 开源许可

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 💕 致谢

- [taobao-iphone-device](https://github.com/alibaba/taobao-iphone-device)
- [scrcpy](https://github.com/Genymobile/scrcpy)

## 📞 联系我们

关注公众号，直接发私信，作者看到就回复：

<img src="https://github.com/smart-test-ti/.github/assets/24454096/fadb328d-c136-460a-b30d-a98d9036d882" alt="SmartTest" width="300">

---

⭐ **如果这个项目对你有帮助，请给我们一个 Star！**