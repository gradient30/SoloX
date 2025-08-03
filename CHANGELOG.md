# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 完整的技术文档体系 (docs/ 目录)
- 依赖问题解决方案文档 (DEPENDENCIES.md)
- 自动化依赖安装脚本 (Linux/macOS/Windows)
- setup.py 依赖版本验证脚本
- 现代化项目配置 (pyproject.toml)
- Makefile 开发工具集
- Docker 容器化支持
- Docker Compose 多服务部署
- Nginx 反向代理配置
- GitHub Actions CI/CD 流水线
- 代码质量检查工具配置

### Changed
- 更新 setup.py 为兼容的依赖版本组合
- 创建 requirements.txt 文件
- 优化项目结构和配置

### Fixed
- 解决 Flask/Werkzeug 版本兼容性问题
- 修复 Flask-SocketIO 4.3.1 与新版本 Flask 的冲突
- 统一依赖版本管理

### Technical Details
- Flask 2.0.3 + Werkzeug 2.0.3 + Flask-SocketIO 4.3.1 兼容组合
- 支持 Python 3.10+ 版本
- 完整的开发环境配置

## [2.9.3] - 2023-XX-XX

### Added
- 基础的移动设备性能监控功能
- Android 和 iOS 设备支持
- Web 界面和 API 接口
- CPU、内存、网络、FPS、电池监控
- 实时数据可视化

### Features
- 支持 Android 设备通过 ADB 连接
- 支持 iOS 设备通过 tidevice 连接
- 提供 RESTful API 接口
- WebSocket 实时数据推送
- 性能数据报告生成

## [Previous Versions]

详细的历史版本信息请参考 [GitHub Releases](https://github.com/smart-test-ti/SoloX/releases)

---

## 版本说明

### 版本号格式
- **主版本号**: 重大架构变更或不兼容的 API 变更
- **次版本号**: 新功能添加，向后兼容
- **修订号**: Bug 修复和小的改进

### 变更类型
- **Added**: 新增功能
- **Changed**: 现有功能的变更
- **Deprecated**: 即将废弃的功能
- **Removed**: 已移除的功能
- **Fixed**: Bug 修复
- **Security**: 安全相关的修复

### 依赖版本策略
- 关键依赖使用固定版本确保兼容性
- 非关键依赖允许小版本更新
- 定期评估和更新依赖版本

### 发布流程
1. 更新 CHANGELOG.md
2. 更新版本号 (solox/__init__.py)
3. 运行完整测试套件
4. 创建 Git 标签
5. 发布到 PyPI
6. 更新 Docker 镜像

---

*最后更新: 2025-08-03*
