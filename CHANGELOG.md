# 更新日志

本项目的所有重要变更均记录于此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- **弱网测试模块**：8 种预设 + 自定义 delay/jitter/loss/rate；`/apm/weaknet/*` API；Android Root 设备 `tc netem`；全员 ping 探测
- **混合录屏播放器**：报告页 HTML5 mp4 播放 + mkv 系统播放器 fallback；`/apm/record/info|stream|play`
- **工程化目录**：`runtime/` 开发日志与 PID；`scripts/release_gate.*` 本地发版门禁；`docs/06-engineering/`
- 报告持续时长 `apm_MM:SS`、图表降采样、场景标签 / Big Jank / Live Stats、Excel 多 sheet 导出
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
- 2026 手游兼容矩阵（`tests/compatibility_matrix.yaml` + `docs/compatibility-matrix.md`）
- 42 项 CI 自动化测试：Surface/API 分层、CPU/Memory mock、`/apm/collect` 集成
- **143 项** L1/L2 自动化 + 研发/产品/测试联合验收文档 v2.4
- 发版门禁脚本 `scripts/validate_compatibility_matrix.py`
- CLAUDE.md 项目指导文件
- 完整的技术文档体系 (docs/ 目录)
- 依赖问题解决方案文档 (DEPENDENCIES.md)
- 现代化项目配置 (pyproject.toml)
- Docker 容器化支持

### 变更
- 开发脚本 `dev.sh` 日志/PID 迁移至 `runtime/`（兼容根目录旧 `.solox.pid`）
- 根目录 `package.sh` 迁移至 `scripts/package.sh`；Git 协作文档迁入 `docs/02-development/`
- **文档收紧**：删除 `system-design`（并入技术架构）及重复 module 等；`docs/README.md` 单入口；`docs/plans/` 保留过程文档索引
- **`GET /health`**：Docker / dev.sh 探活（此前文档引用但未实现）
- 增强 `get_surfaceview()` 方法：支持游戏引擎 Surface 和 Android 12+ 格式
- 重构 `_get_surfaceflinger_frame_data()` 为策略分发器，分离 gfxinfo 和 SurfaceFlinger 路径
- `_collector_thread()` 支持 page flip 回退数据
- `_calculator_thread()` 支持处理 page flip 数据元组
- `LogcatManager` 重构：结构化日志解析 (时间/级别/标签/消息)，支持服务端和客户端双重过滤
- `Scrcpy._get_cast_params()` 接受 quality 参数，支持三档画质预设
- `Scrcpy._cast_monitor_thread()` 增加编码器回退逻辑
- 报告页面从服务端渲染改为 AJAX 分页加载
- 视频播放器从 cv2 切换为系统默认播放器 (os.startfile/open/xdg-open)

### 修复
- 修复 `/apm/collect?target=gpu` 参数错误导致 TypeError 的问题
- 修复游戏类 APP (Unity/UE4/Cocos/Laya) FPS 始终返回 0 的问题
- 修复 `surfaceview=False` 时游戏应用无法采集 FPS 的问题
- 修复投屏频繁断开：高通 OMX.qcom.video.encoder.avc 硬件编码器崩溃 (0x80001009)
- 修复 `_get_page_flip_count()` 正则表达式匹配错误
- 修复 `_get_surface_stats_legacy()` page flip 解析错误处理
- 解决 Flask/Werkzeug 版本兼容性问题

### 技术细节
- 支持 Android 8.x-16.x (API 26+) 全版本 FPS 采集
- 游戏引擎模式识别: Unity, UE4/5, Cocos2d-x/Creator, Laya
- Surface 名称格式: `SurfaceView - pkg/Activity#N` (8-11), `SurfaceView[pkg](BLAST)#N` (12+), `pkg/Activity#N` (14+)
- 投屏默认使用软件编码器 `c2.android.avc.encoder`，硬件编码器失败时自动回退
- Flask 2.0.3 + Werkzeug 2.0.3 + Flask-SocketIO 4.3.1 兼容组合
- 支持 Python 3.10+ 版本

## [2.9.3] - 2023-XX-XX

### 新增
- 基础的移动设备性能监控功能
- Android 和 iOS 设备支持
- Web 界面和 API 接口
- CPU、内存、网络、FPS、电池监控
- 实时数据可视化

### 特性
- 支持 Android 设备通过 ADB 连接
- 支持 iOS 设备通过 tidevice 连接
- 提供 RESTful API 接口
- WebSocket 实时数据推送
- 性能数据报告生成

## [历史版本]

详细的历史版本信息请参考 [GitHub Releases](https://github.com/smart-test-ti/SoloX/releases)

---

## 版本说明

### 版本号格式
- **主版本号**: 重大架构变更或不兼容的 API 变更
- **次版本号**: 新功能添加，向后兼容
- **修订号**: Bug 修复和小的改进

### 变更类型
- **新增**: 新功能
- **变更**: 现有功能的变更
- **弃用**: 即将废弃的功能
- **移除**: 已移除的功能
- **修复**: Bug 修复
- **安全**: 安全相关的修复

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

*最后更新: 2026-06-13*
