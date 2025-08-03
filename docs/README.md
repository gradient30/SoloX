# SoloX 项目技术文档

## 📋 目录结构

```
docs/
├── README.md                    # 文档总览
├── DEPENDENCIES.md              # 依赖问题解决方案 ⭐
├── 01-项目概述.md               # 项目介绍和特性
├── 02-技术架构.md               # 技术栈和架构设计
├── 03-快速启动.md               # 安装和启动指南
├── 04-开发指南.md               # 开发环境配置
├── 05-API文档.md                # API接口文档
├── 06-性能监控.md               # APM模块详解
├── 07-部署指南.md               # 生产环境部署
├── 08-故障排除.md               # 常见问题解决
└── 09-贡献指南.md               # 开发贡献规范

scripts/
├── install_dependencies.sh     # Linux/macOS 依赖安装脚本
└── install_dependencies.ps1    # Windows 依赖安装脚本
```

## 🚀 快速开始

1. **环境要求**
   - Python 3.10+
   - ADB 工具 (Android 测试)
   - iTunes (iOS 测试，Windows)

2. **安装依赖**
   ```bash
   # 方法一: 标准安装
   pip install -r requirements.txt

   # 方法二: 一键解决依赖问题 (推荐)
   # Linux/macOS
   chmod +x scripts/install_dependencies.sh
   ./scripts/install_dependencies.sh

   # Windows
   PowerShell -ExecutionPolicy Bypass -File scripts\install_dependencies.ps1
   ```

3. **启动服务**
   ```bash
   python -m solox
   ```

4. **访问界面**
   - 默认地址: http://localhost:50003
   - 支持自定义 host 和 port

### ⚠️ 常见依赖问题快速修复

如果遇到版本冲突或模块缺失错误，使用以下命令快速修复：

```bash
# 安装兼容版本的依赖
pip install --user Flask==2.0.3 Werkzeug==2.0.3
pip install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2
pip install --user fire pyfiglet psutil opencv-python tidevice==0.9.7
```

详细解决方案请参考 [故障排除文档](./08-故障排除.md#依赖问题)

## 📚 文档说明

- **依赖问题解决方案**: ⭐ 解决常见的依赖冲突和安装问题
- **项目概述**: 了解 SoloX 的核心功能和应用场景
- **技术架构**: 深入了解系统设计和技术选型
- **快速启动**: 从零开始搭建开发环境
- **开发指南**: 代码结构和开发规范
- **API文档**: 接口使用说明和示例
- **性能监控**: APM 模块的实现原理
- **部署指南**: 生产环境配置和优化
- **故障排除**: 常见问题的解决方案
- **贡献指南**: 参与项目开发的规范

## 🔗 相关链接

- [项目主页](https://github.com/smart-test-ti/SoloX)
- [PyPI 包](https://pypi.org/project/solox/)
- [使用文档](https://mp.weixin.qq.com/s?__biz=MzkxMzYyNDM2NA==&mid=2247484506&idx=1&sn=b7eb6de68f84bed03001375d08e08ce9&chksm=c17b9819f60c110fd14e652c104237821b95a13da04618e98d2cf27afa798cb45e53cf50f5bd&token=1402046775&lang=zh_CN&poc_token=HKmRi2WjP7gf9CVwvLWQ2cRhrUR3wmbB9-fNZdD4)

---

*最后更新: 2025-08-03*
