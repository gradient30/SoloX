# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 游戏引擎 FPS 采集支持 (Unity, Unreal Engine 4/5, Cocos2d-x/Creator, Laya)
- `GameSurfaceDetector` 类：自动识别游戏引擎渲染 Surface
- 游戏引擎自动检测：当 `surfaceview=False` 时，自动检测游戏引擎并切换到 SurfaceView 模式
- 多 Surface 回退机制：依次尝试所有候选 Surface 直到获取有效帧数据
- Page flip count 回退 (`service call SurfaceFlinger 1013`)：兜底 FPS 采集方案
- Android 12+ BLAST Surface 格式支持 (`SurfaceView[pkg](BLAST)#N`)
- Android 14+ activity-level Surface 格式支持 (`pkg/Activity#N`)
- Android 8.x (API 26-27) 自动识别不可靠的 SurfaceFlinger 数据并切换策略
- `get_focus_activity()` 增强：支持 `dumpsys window windows` 和 `dumpsys window` 双命令回退
- FPS 数据可信度元数据：采集来源、帧数、置信度等级
- 报告分页 API (`/apm/report/list`)：支持 page/size 参数，解决大量报告时页面加载缓慢
- 报告持续时长列：替代冗余的 Scene 名称，通过日志首尾行时间戳计算
- 投屏画质选择：高清 (1080p/60fps/6M)、标清 (720p/60fps/3M)、流畅 (480p/30fps/1M)
- 投屏软件编码器回退：默认使用 `c2.android.avc.encoder` 避免高通硬件编码器崩溃
- Error Log 增强面板：严重级别过滤 (V/D/I/W/E/F)、标签过滤、关键词搜索、暂停/恢复、导出
- WiFi ADB 连接模态框：本地化双语内容，替换外部 adbshell.com iframe 依赖
- 设置面板功能说明：定时器和远程连接设置增加操作说明
- 21 个 FPS 计算单元测试
- CLAUDE.md 项目指导文件
- 完整的技术文档体系 (docs/ 目录)
- 依赖问题解决方案文档 (DEPENDENCIES.md)
- 现代化项目配置 (pyproject.toml)
- Docker 容器化支持

### Changed
- 增强 `get_surfaceview()` 方法：支持游戏引擎 Surface 和 Android 12+ 格式
- 重构 `_get_surfaceflinger_frame_data()` 为策略分发器，分离 gfxinfo 和 SurfaceFlinger 路径
- `_collector_thread()` 支持 page flip 回退数据
- `_calculator_thread()` 支持处理 page flip 数据元组
- `LogcatManager` 重构：结构化日志解析 (时间/级别/标签/消息)，支持服务端和客户端双重过滤
- `Scrcpy._get_cast_params()` 接受 quality 参数，支持三档画质预设
- `Scrcpy._cast_monitor_thread()` 增加编码器回退逻辑
- 报告页面从服务端渲染改为 AJAX 分页加载
- 视频播放器从 cv2 切换为系统默认播放器 (os.startfile/open/xdg-open)

### Fixed
- 修复游戏类 APP (Unity/UE4/Cocos/Laya) FPS 始终返回 0 的问题
- 修复 `surfaceview=False` 时游戏应用无法采集 FPS 的问题
- 修复投屏频繁断开：高通 OMX.qcom.video.encoder.avc 硬件编码器崩溃 (0x80001009)
- 修复 `_get_page_flip_count()` 正则表达式匹配错误
- 修复 `_get_surface_stats_legacy()` page flip 解析错误处理
- 解决 Flask/Werkzeug 版本兼容性问题

### Technical Details
- 支持 Android 8.x-16.x (API 26+) 全版本 FPS 采集
- 游戏引擎模式识别: Unity, UE4/5, Cocos2d-x/Creator, Laya
- Surface 名称格式: `SurfaceView - pkg/Activity#N` (8-11), `SurfaceView[pkg](BLAST)#N` (12+), `pkg/Activity#N` (14+)
- 投屏默认使用软件编码器 `c2.android.avc.encoder`，硬件编码器失败时自动回退
- Flask 2.0.3 + Werkzeug 2.0.3 + Flask-SocketIO 4.3.1 兼容组合
- 支持 Python 3.10+ 版本

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

*最后更新: 2026-03-15*
