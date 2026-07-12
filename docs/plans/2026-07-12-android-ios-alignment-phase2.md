# Android / iOS 双端能力对齐 — Phase 2 实施计划

- **日期**：2026-07-12
- **状态**：待排期
- **前置**：Phase 1 已完成项见 Cursor 计划 `android_ios_双端能力对标补齐_32f76756.plan.md` §七，以及提交 `5665f67`、`a7fd988`、`b97f5da`
- **目标**：收口 Phase 1 遗留的**录屏债务、CI 真机门禁、iOS 弱网探测产品化、前端诚实提示、Android GPU 芯片级指标**；不重复 Phase 1 已完成的指标诚实性与 CLI/MCP 建设

## 1. Phase 1 与 Phase 2 边界

| 类别 | Phase 1（已完成） | Phase 2（本文） |
|------|-------------------|-----------------|
| iOS Jank 默认链路 | `null` + `jank_supported=false` | 前端显式「暂不支持」文案（非静默） |
| iOS GPU | Renderer/Tiler API + 图表 | — |
| Android GPU | 非 root 时 `gpu_supported=false` | Adreno/Mali **芯片级**只读指标 |
| 弱网 | FAQ NLC 文档引导 | iOS **probe 端点** + UI 入口 |
| 录屏 | — | R1/R4/R5 真机回归 + R7 release gate |
| 自动化 | CLI / MCP / 回归 diff | 录屏验收脚本进 `release_gate` |
| 可选扩展 | `ios_ext` 代码骨架 | **真机标定**（独立轨道，见 §6） |

**明确不纳入 Phase 2**：iOS Logcat、iOS PK 对比、云端真机机房、Frame Capture 逐帧分析（与 SoloX 本地工具定位不符）。

---

## 2. 任务总览（建议顺序）

| ID | 优先级 | 任务 | 预估 | 阻塞 |
|----|--------|------|------|------|
| P2-T1 | **P0** | 录屏网页全流程真机回归（R1/R4/R5） | 0.5–1 天（需真机） | — |
| P2-T2 | **P0** | 录屏验收脚本 + 纳入 release gate（R7） | 1–2 天 | 依赖 T1 验收标准 |
| P2-T3 | **P1** | 前端平台限制显式提示（Jank / GPU / Swap） | 1 天 | — |
| P2-T4 | **P1** | iOS 弱网 probe 端点 + 弱网面板入口 | 1–2 天 | — |
| P2-T5 | **P2** | Android GPU 芯片级指标（gpuclk / Mali 分量） | 2–3 天 | 需多机型真机 |
| P2-T6 | 可选 | `ios_ext` 真机标定（Jank trace / Condition Inducer） | 3–5 天 | 见 §6 |

---

## 3. 任务分解与验收标准

### P2-T1 录屏网页全流程真机回归（R1 / R4 / R5）

**背景**：[`docs/视频问题.md`](../视频问题.md) §9 P0；当前 pytest 用 fake moov，**不能**替代 scrcpy 真机路径。

**2026-07-12 验收进展**（vivo V1936A / Android 11 / Cocos `com.lyjz.chqsy.vivo`）：

- [x] R1：MP4 合法、ffprobe 66.5s — 见 [recording-web-flow-2026-07-12.md](../acceptance/recording-web-flow-2026-07-12.md)
- [x] R5：`/apm/record/stream` HTTP Range 206
- [x] R4：报告页播放器铺满弹窗 — 2026-07-12 人工确认
- [x] 自动化脚本：`python scripts/accept_record_e2e.py`

**步骤**（按 `docs/视频问题.md` §6）：

1. 启动 SoloX Web，连接 Android 真机，选择 **Cocos 游戏**（或已知 SurfaceView 游戏）。
2. 网页点击开始采集 + **录屏**，持续 **≥ 60s**，网页点击停止并保存报告。
3. 在报告页打开录屏：验证 **MP4 可播放**（R1）、播放器 **铺满弹窗**（R4）、**duration/seek** 正常（R5）。
4. 将结果（设备型号、Android 版本、scrcpy 质量档、MP4 路径、`ffprobe` 输出摘要）写入 `docs/acceptance/` 下新验收记录（建议文件名：`recording-web-flow-YYYY-MM-DD.md`）。

**验收**：

- [ ] MP4 `ffprobe` 显示合法 moov + duration ≥ 60s
- [ ] 浏览器内 seek 到 30s 可播放
- [ ] 验收记录 markdown 已提交仓库

**涉及文件**：`solox/public/common.py`（Scrcpy）、`solox/templates/index.html`、`solox/view/apis.py`（录屏 API）

---

### P2-T2 录屏验收脚本 + release gate（R7）

**背景**：避免仅 `tests/test_record_player.py` fake 数据导致「CI 绿、真机坏」。

**实施**：

1. 新增 `scripts/accept_record.ps1`（Windows 真机）与 `scripts/accept_record.sh`（Linux/macOS + adb）。
2. 脚本逻辑（最小）：
   - 检查 `adb devices` 有设备；
   - 调用现有录屏 stop/pull 路径或 REST API；
   - 对产出 MP4 跑 `ffprobe -v error -show_entries format=duration`（或 Python 等价）；
   - 非零 exit = 失败。
3. 在 `scripts/release_gate.sh` / `release_gate.ps1` 增加 **可选** 第 4 步：`SOLOX_RECORD_ACCEPT=1` 时执行（默认跳过，免 CI/无设备环境失败）。
4. 在 [`docs/06-engineering/release-and-dev-standards.md`](../06-engineering/release-and-dev-standards.md) 与 [`ci-gate-playbook.md`](../06-engineering/ci-gate-playbook.md) 注明：发版前若动过录屏链路，须 `SOLOX_RECORD_ACCEPT=1 bash scripts/release_gate.sh`。
5. 补 `tests/test_accept_record_script.py`：mock ffprobe/adb，验证脚本参数与退出码逻辑（**不**在 CI 跑真 scrcpy）。

**验收**：

- [x] 无设备时默认 release gate 仍通过（`SOLOX_RECORD_ACCEPT` 未设）
- [x] `validate_record_file` 对坏文件非零退出（单测覆盖）
- [x] 文档已更新

**涉及文件**：`scripts/accept_record.sh`、`scripts/accept_record.ps1`、`scripts/accept_record_gate.py`、`scripts/release_gate.sh`、`scripts/release_gate.ps1`

---

### P2-T3 前端平台限制显式提示

**背景**：后端已返回 `jank_supported=false`、`gpu_supported=false` 等，但 [`index.html`](../../solox/templates/index.html) 对 iOS Jank 是**静默不画曲线**，用户可能误以为「没有卡顿数据 = 很流畅」。

**实施**：

1. **FPS 卡片 / Jank 行**：当 `jank_supported === false` 时，显示 badge「iOS 暂不支持 Jank 测量」并禁用 Jank/BigJank 曲线更新（保持 Android 逻辑不变）。
2. **GPU 卡片**：已有 `gpu_supported === false` 分支；补充固定说明文案（非 root / 无 kgsl）。
3. **内存 Swap**：iOS 不展示 Swap 系列时，在 mem 区域 footnote「Swap 仅 Android」。
4. 文案与 [`faq.md`](../05-issues/faq.md) §22 一致。

**验收**（2026-07-12 完成）：

- [x] iOS 选中设备后 FPS 区域可见「暂不支持 Jank / BigJank」静态提示；内存区可见「Swap 仅 iOS 不提供」
- [x] GPU 运行时 `gpu_supported=false` 显示持久内联提示（含真实原因），恢复时自动隐藏
- [x] Android 行为无回归（`test_frontend_performance.py` + 全量 pytest 绿）
- [x] Flask 实渲染 Android/iOS × cn/en 通过；真机 `/apm/gpu` 返回 `gpu_supported=false` 验证提示为真实原因

**涉及文件**：`solox/templates/index.html`、`tests/test_frontend_performance.py`

---

### P2-T4 iOS 弱网 probe 端点 + UI

**背景**：Phase 1 已在 FAQ 写 Network Link Conditioner 引导；Android 有 `WeakNetworkManager.probe()`，iOS 缺对称能力。

**实施**：

1. 新增 API：`GET/POST /apm/weaknet/probe` 在 `platform=iOS` 时走 **设备 shell ping**（经 tidevice / lockdown 等价路径，复用现有 ping 解析逻辑）；返回 RTT/loss/jitter，**不**尝试 tc/netem/Condition Inducer。
2. `apis.py` 响应增加 `platform`、`probe_supported`、`guide_url`（链到 FAQ §20）。
3. 前端弱网面板：iOS 设备时隐藏「应用预设/Agent」注入控件，展示 **探测结果** + 「在设置中启用 NLC」外链/折叠说明。
4. 单测：mock ping 输出，覆盖 iOS/Android 分支（**setUp 禁止真实 adb**，见 [`ci-gate-playbook.md`](../06-engineering/ci-gate-playbook.md)）。

**2026-07-12 落地（诚实修正）**：核实发现——**非越狱 iOS 无 shell，不存在设备侧主动 ping**。原计划"设备 shell ping"技术上不成立，已改为诚实实现：

- **核心（已验证）**：`/apm/weaknet/probe` 改为平台感知——Android 走真实 adb ping（真机联调 RTT 38–52ms/0% loss）；iOS 返回 `probe_supported=false` + NLC 指引 + `guide_doc`，**绝不调用 adb**（CI 无真机不阻塞）。
- **可选（借鉴 pymobiledevice3 `NetworkMonitor`，真机单位待标定）**：`solox/public/ios_ext/netprobe.py` 被动 RTT（读取现有连接内核 `min_rtt/avg_rtt`）；装了 `solox[ios]` 时 iOS probe 返回被动 RTT，失败则诚实降级不伪造。
- **前端**：探测结果渲染新增 `probe_supported=false` 分支（展示指引而非空 RTT）。iOS 专属弱网面板（当前 offcanvas 为 Android-gated）**延后**至有 iOS 真机可验证时再做。

**验收**：

- [x] iOS 探测返回诚实不支持 + NLC 指引（不触 adb）；装 solox[ios] 时走被动 RTT
- [x] Android 真机 probe 联调通过（真实 ping）
- [x] pytest 新增 9 用例（netprobe 纯函数 3 + probe 端点 5 + 前端 1），CI 无 adb 阻塞
- [ ] iOS 专属弱网 UI 面板（延后，需 iOS 真机验证）

**涉及文件**：`solox/view/apis.py`、`solox/public/ios_ext/netprobe.py`、`solox/templates/index.html`、`tests/test_ios_netprobe.py`、`tests/test_weaknet_probe_api.py`、`tests/test_frontend_performance.py`

**借鉴调研**：见 [2026-07-12-ios-oss-borrow-survey.md](./2026-07-12-ios-oss-borrow-survey.md)（pymobiledevice3 / go-ios / sonic-ios-bridge 的可借鉴技术与许可证边界）。

**备注**：程序化 Condition Inducer 与被动 RTT 均属 [`2026-07-11-ios-pmd3-backend.md`](./2026-07-11-ios-pmd3-backend.md) 可选轨道。

---

### P2-T5 Android GPU 芯片级指标（方案 B 余量）

**背景**：PerfDog 展示 Adreno GPU Frequency、Mali Non-fragment/Fragment 等；当前 SoloX 仅 `gpubusy` 利用率，且非 root 常不可用。

**实施**：

1. 在 `solox/public/apm.py` `GPU` 类增加只读探测（节点存在才启用）：
   - Adreno：`/sys/class/kgsl/kgsl-3d0/gpuclk` 或 `gpu_busy_percentage`（按机型文档选型）
   - Mali：`/sys/class/misc/mali0/device/` 下 Non-fragment/Fragment 相关节点（机型差异大，需 graceful skip）
2. API `/apm/gpu` 扩展字段：`gpu_frequency_mhz`、`gpu_non_fragment_pct`、`gpu_fragment_pct`、`*_supported` 布尔。
3. 前端 GPU 图表：有次级指标时增加 series；不支持时不画假 0。
4. 单测：mock `adb.shell` 返回样本 sysfs 文本；无节点时 `*_supported=false`。

**验收**：

- [ ] 至少 1 台 Adreno 或 Mali 真机有非空读数（写入验收记录）
- [ ] 无节点机型返回 supported=false
- [ ] 与 Phase 1 `gpu_supported=false` 语义不冲突

**涉及文件**：`solox/public/apm.py`、`solox/view/apis.py`、`solox/templates/index.html`、`tests/test_apm_collect_api.py`

---

## 4. 测试与 CI 约束（Phase 2 通用）

1. **单测 setUp/tearDown 不得调用真实 `adb.shell`**（见 `ci-gate-playbook.md` §3.1）。
2. 真机验收与 CI 分离：T1/T2 真机脚本默认 **opt-in**（`SOLOX_RECORD_ACCEPT=1`）。
3. 每个任务合并前：`python scripts/verify_setup.py`、`python -m pytest tests/ -q`、`python -m build`（与 CI build job 对齐）。

---

## 5. 完成定义（Phase 2 Done）

满足以下全部项可关闭 Phase 2，并回写 Cursor plan 对应 todo 为 `completed`：

- [x] P2-T1 验收记录入库
- [x] P2-T2 release gate 可选录屏步 + 文档
- [x] P2-T3 iOS/Android UI 提示无伪 0 回归
- [x] P2-T4 iOS probe 诚实实现 + 被动 RTT（借鉴 pmd3）；iOS 专属 UI 面板延后（需真机）
- [ ] P2-T4 iOS probe API + UI + 单测
- [ ] P2-T5 GPU 芯片级指标（或显式 defer 并记录原因）

---

## 6. 可选扩展轨道（不阻塞 Phase 2 P0）

与 Phase 2 **并行、独立排期**：

| 文档 | 内容 | 状态 |
|------|------|------|
| [2026-07-11-ios-pmd3-backend.md](./2026-07-11-ios-pmd3-backend.md) | pymobiledevice3：隧道、Condition Inducer、截图录屏、CoreProfileSessionTap Jank | 代码骨架已 land（`a7fd988`），**真机标定待定** |
| [2026-07-11-ios-gap-and-oss-survey.md](./2026-07-11-ios-gap-and-oss-survey.md) | 默认 tidevice 链路不做真 Jank 的结论依据 | ✅ 已关闭 |

**原则**：默认安装路径（`pip install solox`）的行为以 Phase 2 为准；`pip install "solox[ios]"` 能力单独验收、单独文档，不算「双端默认对齐完成」。

---

## 7. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-12 | 初版：从双端对齐 Phase 1 未落地项拆分 |

---

*关联：[CI 门禁排查手册](../06-engineering/ci-gate-playbook.md) · [视频问题](../视频问题.md) · [FAQ §18/§20/§22](../05-issues/faq.md)*
