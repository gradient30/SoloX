# 项目目录与日志规范

本文说明 SoloX 仓库目录划分、运行时产物与日志位置，便于研发 / 测试 / 运维统一维护。

## 顶层目录

```
SoloX/
├── solox/                 # 应用源码（Flask、采集引擎、模板、静态资源）
├── tests/                 # 自动化测试 + compatibility_matrix.yaml
├── scripts/               # 开发/验收/打包脚本（见 scripts/README.md）
├── docs/                  # 技术文档、兼容矩阵、联合验收
├── runtime/               # 本地运行时文件（gitignore，见 runtime/README.md）
├── report/                # APM 采集报告（gitignore，运行时生成）
├── .github/workflows/     # CI/CD
├── CLAUDE.md              # AI / 贡献者快速指引
├── README.md / README.zh.md
├── pyproject.toml
├── requirements.txt
├── Makefile
└── docker-compose.yml
```

## 源码模块（`solox/`）

| 路径 | 职责 |
|------|------|
| `view/apis.py` | REST API（采集、报告、logcat、录屏、弱网等） |
| `view/pages.py` | HTML 页面路由 |
| `public/apm.py` | 指标采集类 |
| `public/android_fps.py` | Android FPS / 游戏 Surface |
| `public/weak_network.py` | 弱网 tc/netem + ping 探测 |
| `public/common.py` | 设备、报告 I/O、Scrcpy、Logcat |
| `templates/` | Jinja2 前端 |
| `public/scrcpy/` | 内置 scrcpy 二进制（Windows） |
| `public/ffmpeg/` | 可选 ffmpeg（录屏 remux；二进制不入库，见目录 README） |

## 日志与运行时产物

| 位置 | 内容 | 版本控制 |
|------|------|----------|
| `runtime/logs/solox-dev.log` | `dev.sh start` 服务日志 | 忽略（保留 `logs/.gitkeep`） |
| `runtime/pids/solox.pid` | 开发服务器 PID | 忽略（保留 `pids/.gitkeep`） |
| `runtime/cache/` | Android 应用名持久化缓存（按设备） | 忽略（保留 `cache/.gitkeep`） |
| `runtime/*.py` | 个人临时启动脚本 | 忽略 |
| `solox/public/ffmpeg/bin/` | 可选内置 ffmpeg（录屏 remux） | 忽略二进制；见 `ffmpeg/README.md` |
| `report/apm_*/` | 单次采集的 `*.log`、`result.json`、录屏 | 忽略 |
| `solox/logs/` | 应用内部日志目录 | 忽略 |
| `adblog/` | Logcat 导出 | 忽略 |
| `report/apm_*/*.log` | CPU/FPS/jank 等时序数据 | 忽略 |

**注意**：性能分析依赖 `report/` 下原始 `.log` 文件；图表 API 降采样**不修改**磁盘 log。

## 文档索引

| 目录 | 说明 |
|------|------|
| `docs/01-architecture/` | 架构与设计 |
| `docs/02-development/` | 开发、Git、快速启动 |
| `docs/03-deployment/` | 部署与 Docker |
| `docs/04-user-guides/` | API、性能监控指南 |
| `docs/05-issues/` | FAQ、故障排除 |
| `docs/06-engineering/` | 工程化、目录规范（本文） |
| `docs/acceptance/` | 联合验收、L3 真机清单 |
| `docs/plans/` | 实施与验收过程文档（见 `plans/README.md`） |
| `docs/compatibility-matrix.md` | 2026 兼容矩阵 |

> 已移除重复文档：`system-design`（并入技术架构）、`module-structure`、`technology-stack`、`environment-setup`。

## 2026 特性与文档对应

| 特性 | 代码 | 文档 / 验收 |
|------|------|-------------|
| 兼容矩阵 + 发版门禁 | `tests/compatibility_matrix.yaml` | `docs/compatibility-matrix.md` |
| 弱网测试 | `weak_network.py` · `/apm/weaknet/*` | 帮助手册 · 联合验收 v2.3 |
| 混合录屏播放器 | `/apm/record/*` | 联合验收 v2.2 |
| 报告时长 / 降采样 | `common.py` · `/apm/report/list` | 联合验收 v2.1 |
| Big Jank / 场景标签 | `apm.py` · `metric_stats.py` | API 文档 · Excel 导出 |

## 本地发版检查

```bash
bash scripts/release_gate.sh
# Windows: .\scripts\release_gate.ps1
```

等价于 CI 中的矩阵校验 + 全量 pytest。

---

*最后更新: 2026-06-13*
