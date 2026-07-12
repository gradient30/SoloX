# 实施与验收计划

本目录存放**过程性**设计与实施文档（非用户手册）。用户文档入口见 [docs/README.md](../README.md)。

| 文档 | 状态 | 说明 |
|------|------|------|
| [2026-06-13 性能验收 — 方案设计](./2026-06-13-performance-acceptance-design.md) | ✅ 已实施 | 报告 API 惰性加载与列表优化 |
| [2026-06-13 性能验收 — 实施计划](./2026-06-13-performance-acceptance.md) | ✅ 已实施 | TDD 任务分解与验收步骤 |
| [2026-07-11 iOS 能力预研 spike](./2026-07-11-ios-gap-and-oss-survey.md) | ✅ 已关闭 | 默认链路不做真 Jank；OSS/许可证结论 |
| [2026-07-11 iOS pymobiledevice3 可选后端](./2026-07-11-ios-pmd3-backend.md) | 🔄 代码已 land | 真机标定待定；非默认安装路径 |
| [2026-07-12 双端对齐 Phase 2](./2026-07-12-android-ios-alignment-phase2.md) | 📋 待排期 | 录屏债务、CI 门禁、iOS probe、UI 提示、GPU 芯片级 |

游戏引擎 FPS 采集设计已并入 [技术架构](../01-architecture/technical-architecture.md) 与 `tests/test_fps_calculation.py`，不再单独保留 plans 副本。

Phase 1（指标诚实性、iOS GPU 三分量、CLI/MCP/分析）见 Cursor 计划 `android_ios_双端能力对标补齐_32f76756.plan.md` §七。

验收结论见 [联合验收报告 v2.4](../acceptance/joint-review-2026-compatibility.md)。
