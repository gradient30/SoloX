<p align="center">
  <a>English</a> | <a href="./README.zh.md">中文</a> | <a href="./docs/05-issues/faq.md">FAQ</a> | <a href="./docs/README.md">📖 完整文档</a>
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

## 🔎 Preview

SoloX - Real-time collection and analysis tool for Android/iOS performance data.

Quickly locate and analyze performance issues to improve application performance and quality. Core performance collection is plug and play without Android Root or iOS jailbreak. Android weak-network simulation is also available through the non-Root QAS Network Agent, while the older Root `tc netem` engine remains for compatible rooted devices.

![SoloX Interface](https://github.com/smart-test-ti/SoloX/assets/24454096/61a0b801-23b4-4711-8215-51cd7bc9dc04)

## 📦 Requirements

- Install Python 3.10+ [**Download**](https://www.python.org/downloads/)
- Install adb and configure environment variables [**Download**](https://developer.android.com/studio/releases/platform-tools)

💡 Windows users need to install iTunes for iOS testing [**Documentation**](https://github.com/alibaba/taobao-iphone-device) (iOS 17 not supported)

## 📥 Installation

### Default

```shell
pip install -U solox
```

### Using mirrors

```shell
pip install -i https://mirrors.ustc.edu.cn/pypi/web/simple -U solox
```

💡 If your network cannot download through `pip install -U solox`, try using mirrors, but SoloX may not be the latest version.

## 🚀 Quick Start

### Default

```shell
python -m solox
```

### Customize

```shell
python -m solox --host=ip --port=port
```

## 🐍 Python API

```python
from solox.public.apm import AppPerformanceMonitor
from solox.public.common import Devices

# Get device list
d = Devices()
devices = d.getDeviceIds()
print(f"Connected devices: {devices}")

# Get app processes
processes = d.getPid(deviceId='ca6bd5a5', pkgName='com.example.app')
print(f"App processes: {processes}")

# Create performance monitor
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='ca6bd5a5',
    surfaceview=True,
    noLog=False
)

# Collect performance data
cpu = apm.collectCpu()          # CPU usage %
memory = apm.collectMemory()    # Memory usage MB
network = apm.collectNetwork()  # Network traffic KB
fps = apm.collectFps()          # FPS Hz
battery = apm.collectBattery()  # Battery info
```

## 🔥 Features

* **No Root/Jailbreak for core monitoring**: Android/iOS performance collection runs without device Root or jailbreak
* **Comprehensive Monitoring**: CPU, Memory, Network, FPS/Jank, Battery, GPU, Disk, Thermal and more
* **Real-time Analysis**: Beautiful real-time data visualization and analysis
* **Cross-platform**: Support both Android and iOS platforms
* **Android Weak Network**: QAS Network Agent supports per-App non-Root weak-network simulation with explicit VPN authorization; Root `tc netem` and probe modes remain available
* **Easy Integration**: Python API and RESTful interface for CI/CD integration
* **Beautiful Reports**: Detailed performance analysis reports

## 📚 Documentation

### 📖 [Complete Documentation](./docs/README.md)

- 📐 [**Architecture**](./docs/01-architecture/) - Technical architecture and system design
- 🛠️ [**Development**](./docs/02-development/) - Development guide and environment setup  
- 🚀 [**Deployment**](./docs/03-deployment/) - Production deployment and Docker
- 📖 [**User Guides**](./docs/04-user-guides/) - API documentation and monitoring guides
- ❓ [**Issues**](./docs/05-issues/) - Troubleshooting and FAQ

### Quick Links

- 🚀 [Quick Start Guide](./docs/02-development/quick-start.md)
- 📊 [API Documentation](./docs/04-user-guides/api-documentation.md)
- 📶 [Weak Network Testing](./docs/04-user-guides/weak-network-testing.md)
- 🔧 [Troubleshooting](./docs/05-issues/troubleshooting.md)
- ❓ [FAQ](./docs/05-issues/faq.md)

## 🔧 Service API

### Start service in background

```shell
# macOS/Linux
nohup python3 -m solox &

# Windows  
start /min python3 -m solox &
```

### Request performance data

```shell
# Android
http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=cpu

# iOS
http://localhost:50003/apm/collect?platform=iOS&pkgname=com.example.app&target=cpu

# Available targets include: cpu, memory, network, fps, battery, gpu
```

## 🎯 Use Cases

- **Mobile App Performance Testing**: Startup performance, memory leaks, CPU monitoring
- **Android Weak-Network Testing**: Per-App network degradation through QAS Network Agent or Root `tc netem`
- **Automated Testing Integration**: CI/CD pipeline integration, regression testing
- **Development Debugging**: Real-time monitoring, performance optimization
- **Competitive Analysis**: Performance comparison between different apps

## 🌟 Supported Metrics

| Metric | Android | iOS | Description |
|--------|---------|-----|-------------|
| 🔥 CPU Usage | ✅ | ✅ | App and system CPU usage |
| 🧠 Memory | ✅ | ✅ | Memory usage and detailed analysis |
| 🌐 Network | ✅ | ✅ | Upload/download traffic |
| 🎮 FPS | ✅ | ✅ | Frame rate and jank detection |
| 🔋 Battery | ✅ | ✅ | Battery level, temperature, power |
| 🎨 GPU | ✅ | ❌ | GPU usage (Android only) |
| 📶 Weak Network | ✅ | External tools | Android Agent / Root tc / probe; iOS uses Network Link Conditioner or similar external tooling |

## 🤝 Contributing

We welcome contributions! Please see our [Contribution Guide](./docs/05-issues/contribution-guide.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 💕 Thanks

- [taobao-iphone-device](https://github.com/alibaba/taobao-iphone-device)
- [scrcpy](https://github.com/Genymobile/scrcpy)

---

⭐ **Star this project if it helps you!**
