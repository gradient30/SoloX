# SoloX 文档

> 唯一入口。子目录仅保留**不重复**的主题文档；目录结构与脚本见 [工程化说明](./06-engineering/project-layout.md)。

## 快速链接

| 角色 | 从这里开始 |
|------|------------|
| 新用户 | [快速启动](./02-development/quick-start.md) → [API](./04-user-guides/api-documentation.md) |
| 开发者 | [CLAUDE.md](../CLAUDE.md) → [开发指南](./02-development/development-guide.md) → [脚本索引](../scripts/README.md) |
| 发版/测试 | [兼容矩阵](./compatibility-matrix.md) → [预发布审核](./06-engineering/pre-publish-checklist.md) → `bash scripts/release_gate.sh` |
| 运维 | [部署指南](./03-deployment/deployment-guide.md) → [故障排除](./05-issues/troubleshooting.md) |

## 目录

### 01 架构

- [项目概述](./01-architecture/project-overview.md)
- [技术架构](./01-architecture/technical-architecture.md) — 架构、技术栈、模块职责

### 02 开发

- [快速启动](./02-development/quick-start.md) — 安装、依赖、验证（**环境配置已合并于此**）
- [开发指南](./02-development/development-guide.md)
- [Git 远程与编码](./02-development/git-remote-setup.md)

### 03 部署 · 04 用户 · 05 问题

- [部署指南](./03-deployment/deployment-guide.md)
- [API 文档](./04-user-guides/api-documentation.md) — 含弱网、录屏、Logcat
- [性能监控](./04-user-guides/performance-monitoring.md)
- [FAQ](./05-issues/faq.md) · [故障排除](./05-issues/troubleshooting.md) · [贡献指南](./05-issues/contribution-guide.md)

### 工程化与验收

- [实施与验收计划](./plans/README.md) — 性能验收等过程文档
- [项目目录与日志](./06-engineering/project-layout.md)
- [本地开发 vs 线上发布](./06-engineering/release-and-dev-standards.md)
- [预发布审核清单](./06-engineering/pre-publish-checklist.md)
- [兼容矩阵与发版门禁](./compatibility-matrix.md)
- [联合验收报告 v2.3](./acceptance/joint-review-2026-compatibility.md)
- [L3 真机清单](./acceptance/l3-device-lab-checklist.md)

### 其他

- [依赖问题](./DEPENDENCIES.md) · [CHANGELOG](../CHANGELOG.md)

## 监控指标（摘要）

CPU · Memory · Network · FPS/Jank · Battery · GPU(Android) · Disk · Thermal · **弱网(Android Root+探测)** · 录屏回放 · 场景标签 · Big Jank

## 本地门禁

```bash
bash scripts/release_gate.sh
python scripts/validate_compatibility_matrix.py
python -m pytest tests/ -q --disable-warnings
```

*最后更新: 2026-06-13 · 文档 v2.4*
