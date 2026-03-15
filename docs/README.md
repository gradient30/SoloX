# SoloX 项目技术文档

## 📋 文档总览

欢迎使用 SoloX 移动应用性能监控工具！本文档采用标准化的项目文档框架，帮助您快速了解和使用 SoloX。

## 🗂️ 文档结构

```
docs/
├── 01-architecture/          # 📐 架构设计
├── 02-development/           # 🛠️ 开发指南  
├── 03-deployment/            # 🚀 部署运维
├── 04-user-guides/           # 📖 用户指南
└── 05-issues/                # ❓ 问题解决
```

## 📐 01-架构设计

深入了解 SoloX 的系统设计和技术架构：

- **[项目概述](./01-architecture/project-overview.md)** - 项目简介、核心特性、应用场景
- **[技术架构](./01-architecture/technical-architecture.md)** - 整体架构、技术栈、模块设计
- **[系统设计](./01-architecture/system-design.md)** - 数据流、接口设计、扩展性设计

### 快速了解项目
- 🎯 专业的移动应用性能监控工具
- 📊 支持 Android 和 iOS 双平台
- 🔓 免 ROOT/越狱，即插即用
- 📈 实时数据可视化和分析

## 🛠️ 02-开发指南

开发环境搭建和代码贡献指南：

- **[快速启动](./02-development/quick-start.md)** - 环境要求、安装配置、基本使用
- **[开发指南](./02-development/development-guide.md)** - 项目结构、模块开发、代码规范
- **[环境配置](./02-development/environment-setup.md)** - 详细的开发环境配置

### 5分钟快速开始
```bash
# 安装 SoloX
pip install -U solox

# 启动服务
python -m solox

# 访问界面
http://localhost:50003
```

## 🚀 03-部署运维

生产环境部署和运维管理：

- **[部署指南](./03-deployment/deployment-guide.md)** - 生产部署、Docker 容器化、系统服务配置

### Docker 一键部署
```bash
# 使用 Docker Compose
docker-compose up -d

# 访问服务
http://localhost:50003
```

## 📖 04-用户指南

API 使用和性能监控指南：

- **[API 文档](./04-user-guides/api-documentation.md)** - RESTful API、Python SDK、WebSocket 接口
- **[性能监控](./04-user-guides/performance-monitoring.md)** - 监控指标详解、最佳实践、分析方法

### API 快速示例
```python
from solox.public.apm import AppPerformanceMonitor

# 创建监控实例
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='ca6bd5a5'
)

# 收集性能数据
cpu_data = apm.collectCpu()
memory_data = apm.collectMemory()
```

## ❓ 05-问题解决

故障排除和社区支持：

- **[故障排除](./05-issues/troubleshooting.md)** - 常见问题、错误诊断、解决方案
- **[贡献指南](./05-issues/contribution-guide.md)** - 代码贡献、文档编写、社区参与
- **[FAQ](./05-issues/faq.md)** - 常见问题快速解答

### 常见问题快速解决
- 🔧 [依赖安装问题](./05-issues/troubleshooting.md#依赖安装问题)
- 📱 [设备连接问题](./05-issues/troubleshooting.md#设备连接问题)
- 🌐 [Web界面问题](./05-issues/troubleshooting.md#Web界面问题)

## 🚀 快速导航

### 新手用户
1. **开始使用** → [快速启动](./02-development/quick-start.md)
2. **了解功能** → [项目概述](./01-architecture/project-overview.md)
3. **API使用** → [API文档](./04-user-guides/api-documentation.md)

### 开发者
1. **架构了解** → [技术架构](./01-architecture/technical-architecture.md)
2. **开发环境** → [开发指南](./02-development/development-guide.md)
3. **代码贡献** → [贡献指南](./05-issues/contribution-guide.md)

### 运维人员
1. **生产部署** → [部署指南](./03-deployment/deployment-guide.md)
2. **故障处理** → [故障排除](./05-issues/troubleshooting.md)

## 📊 支持的监控指标

| 指标类型 | Android | iOS | 说明 |
|---------|---------|-----|------|
| 🔥 CPU 使用率 | ✅ | ✅ | 应用和系统 CPU 占用 |
| 🧠 内存使用 | ✅ | ✅ | PSS、私有内存、详细分析 |
| 🌐 网络流量 | ✅ | ✅ | 上行/下行流量统计 |
| 🎮 FPS 帧率 | ✅ | ✅ | 界面渲染性能 (含游戏引擎支持) |
| 🔋 电池信息 | ✅ | ✅ | 电量、温度、功耗 |
| 🎨 GPU 使用率 | ✅ | ❌ | GPU 渲染负载 |
| 💾 磁盘 I/O | ✅ | ❌ | 磁盘读写性能 |
| 🌡️ 设备温度 | ✅ | ❌ | 设备温度传感器 |

## 🔗 相关链接

### 项目资源
- **[GitHub 主页](https://github.com/smart-test-ti/SoloX)** - 源码和 Issue 管理
- **[PyPI 包](https://pypi.org/project/solox/)** - Python 包发布
- **[更新日志](../CHANGELOG.md)** - 版本更新记录
- **[许可证](../LICENSE)** - MIT 开源许可

### 快速工具
- **[依赖修复脚本](../scripts/install_dependencies.sh)** - 一键解决依赖问题
- **[验证脚本](../scripts/verify_setup.py)** - 安装验证工具
- **[Docker 配置](../docker-compose.yml)** - 容器化部署文件

## 💡 获取帮助

### 社区支持
- **GitHub Issues**: 报告 Bug 和功能请求
- **讨论区**: 技术交流和使用心得
- **邮箱**: rafacheninc@gmail.com

### 文档反馈
如果您在使用文档过程中遇到问题或有改进建议，欢迎：
1. 提交 [GitHub Issue](https://github.com/smart-test-ti/SoloX/issues)
2. 发送邮件反馈
3. 贡献文档改进

---

📝 **文档更新**: 本文档持续更新，确保与最新版本保持同步
🕒 **最后更新**: 2026-03-15
📋 **文档版本**: v2.9.3+

*Happy Testing with SoloX! 🎉*