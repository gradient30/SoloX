# SoloX 2026 — 研发 / 产品 / 测试联合验收报告

**版本**: v2.4  
**日期**: 2026-06-14
**范围**: 兼容矩阵 · PerfDog 指标 · 报告管理 · UX 汉化/文档 · 混合录屏播放器 · 弱网测试 · **性能验收 A**  
**发版门禁**: `P0_all_pass`

---

## 1. 验收结论（汇总）

| 角色 | 结论 | 说明 |
|------|------|------|
| **研发 (R&D)** | ✅ **通过 L1/L2** | **192** 自动化用例全绿；报告 API 性能热点已完成定点优化 |
| **产品 (PM)** | ⚠️ **有条件通过** | 性能方案 A 的 API/报告行为保持兼容；**L3 Root 真机弱网 smoke 待签字** |
| **测试 (QA)** | ✅ **通过 L1/L2** | 报告管理模块增至 25 个用例；全量回归、兼容矩阵和编译检查通过 |

**综合判定**: **可进入预发布（RC）**。正式发布需 L3 P0 真机 + 第 5 节 smoke（含录屏回放 + 弱网 Root 设备）签字。

---

## 2. 产品验收 — 需求对齐

### 2.1 2026 手游版本策略（v1.0 基线）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| Android 主线 11–16 | ✅ | `compatibility_matrix.yaml` P0–P2 |
| Google Play target ≥ API 35 | ✅ | `google_play.target_api_min: 35` |
| iOS 主线 18 / 26 | ✅ | ios.P0 |

### 2.2 PerfDog 风格增强（v2.0）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| Min/Max/Avg 报告摘要 | ✅ | `perf_stats.json` + `analysis.html` |
| 实时 Live Stats | ✅ | `index.html` |
| 场景标签 + Excel | ✅ | `scene_tag_stats.json` · Excel sheets |
| Big Jank 独立计数 | ✅ | `big_jank.log` · API |

### 2.3 报告管理优化（v2.1）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| 列表显示真实持续时长 `apm_MM:SS` | ✅ | `result.json` · `/apm/report/list` · `report.html` |
| 长时跑测分析页加载优化 | ✅ | perf_stats 缓存 + 图表降采样 1500 点 |
| 原始 log 完整保留 | ✅ | 降采样仅 `/apm/log` 图表 API |

### 2.4 UX 文档与本地化（v2.2）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| 中文界面帮助/WiFi/设置说明 | ✅ | `base.html` 手册 · `index.html` WiFi 弹窗 |
| 采集指标文档与代码一致 | ✅ | CPU/GPU/Network/Disk/Thermal 来源已修正 |
| Android 11–16 无线调试步骤 | ✅ | `adb pair` + `adb connect` |
| 定时器 / 远程访问功能说明 | ✅ | 帮助手册「高级设置」 |

### 2.5 录屏混合播放器（v2.2）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| 报告页页内播放 mp4 | ✅ | `report.html` Modal + HTML5 video |
| 播放/暂停/停止 · 倍速 · 进度 | ✅ | 工具栏 + seek |
| mkv / 解码失败 fallback | ✅ | `/apm/record/play` 系统播放器 |
| 远程 Host 模式可播 | ✅ | `apiBase()` 统一 |

### 2.6 弱网测试（v2.3 新增）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| 弱网预设（WiFi/4G/3G/2G/高延迟/高丢包/极差） | ✅ | `WEAKNET_PRESETS` · `/apm/weaknet/presets` |
| 自定义延迟/抖动/丢包/带宽 | ✅ | offcanvas 自定义区 + `/apm/weaknet/apply` |
| 网络质量探测 RTT/丢包/抖动 | ✅ | `/apm/weaknet/probe` · 无 Root 可用 |
| 无 Root 明确提示「仅探测模式」 | ✅ | `capabilities.simulation_supported` + UI 告警 |
| 停止采集自动恢复网络 | ✅ | `stopTask()` → `clearWeakNet(true)` |
| 帮助手册弱网说明 | ✅ | `base.html` 中英文章节 |
| iOS 边界说明 | ✅ | capabilities 返回 Android-only 提示 |

### 2.7 性能验收 A（v2.4 新增）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| 单指标请求不加载无关指标 | ✅ | `/apm/log` 可调用对象分发 |
| 报告列表排序/分页不变 | ✅ | `os.scandir()` 单次扫描 + 回归测试 |
| 分析页避免重复目录扫描 | ✅ | 直接场景目录检查 |
| 非法/缺失场景不触发报告读取 | ✅ | `scene` 边界测试 |
| 大日志响应数据一致 | ✅ | 24 文件 × 20,000 行基准，响应完全一致 |

基准结果：CPU 图表请求中位耗时 **7.9672s → 0.6437s（-91.9%）**，
峰值跟踪内存 **13.11MB → 5.28MB（-59.7%）**。

报告列表按修改时间排序后惰性读取元数据，损坏项不占当前页槽位。
500 份报告、首页 20 条的中位响应为 **13.46ms**。

### 2.8 P0 发版门禁

Android P0：**4** 条（API 33 / 34 / 35 / 36）  
iOS P0：**2** 条（iOS 18 / iOS 26）

### 2.9 实时采集与分析性能（v2.5 新增）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| 实时指标按真实采样间隔轮询 | ✅ | 独立 `metricTimers`；回调传入 `setTimeout` |
| 指标之间不互相清理定时器 | ✅ | CPU/内存/FPS 等 10 个独立 timer key |
| 页面隐藏时暂停实际采集 | ✅ | `document.hidden` 调度检查 |
| compare/pk 大报告限制图表点数 | ✅ | 页面显式传参 → API → `readLog(max_points)` 全链路；旧客户端不传参保持全量兼容 |
| 分析页限制日志加载并发 | ✅ | FIFO 队列，最大并发 3 |
| API/ADB 性能可观测 | ✅ | `/apm/telemetry` + 响应耗时头 |
| 报告缺失/并发删除不返回 500 | ✅ | 单报告页、对比页空状态回归测试 |

浏览器验收：实时首页、普通分析、PK 分析、对比分析均正常渲染且无页面控制台错误；
普通分析空报告场景创建 6 个图表并完成 6 个 `/apm/log` 请求。

### 2.10 Android App / 进程选择优化（v2.6 新增）

| PM 需求 | 实现状态 | 证据 |
|---------|----------|------|
| App 列表支持第三方 / 系统 / 全部过滤 | ✅ | Android 首页默认第三方；可切换系统与全部 |
| App 搜索支持桌面名优先、包名兜底 | ✅ | 列表快返；`/device/package/labels` 异步用 `aapt` 补齐 label；成功结果持久缓存 30 天；Select2 同时匹配 label/package |
| App 下拉展示不超框 | ✅ | 下拉单行：应用名 · 包名；超长省略；蓝色高亮态统一白字；选中区仅显示应用名 |
| 旧接口字段兼容 | ✅ | `/device/info`、`/device/package` 保留 `pkgnames` |
| 单个前台第三方进程自动选中 | ✅ | `/package/foreground` + 前端静默自动选择 |
| 多前台/多进程时交给用户选择 | ✅ | 多进程返回全量 `pids`，不自动选具体进程 |
| 系统前台 App 不自动选中 | ✅ | helper 与前端均有保护 |

---

## 3. 测试验收 — 自动化覆盖

### 3.1 L1/L2 测试矩阵

| 模块 | 文件 | 用例数 | 类型 |
|------|------|--------|------|
| FPS 计算 + Big Jank | `test_fps_calculation.py` | 21 | L1 |
| Surface/API 分层 | `test_surface_by_api.py` | 13 | L1 |
| CPU/Memory mock | `test_apm_cpu_memory.py` | 8 | L1 |
| `/apm/collect` 集成 | `test_apm_collect_api.py` | 13 | L2 |
| Android App / 进程选择 | `test_android_app_selection.py` | 15 | L1/L2 |
| 矩阵 schema | `test_compatibility_matrix.py` | 11 | L1 |
| 指标统计 / 场景 | `test_metric_stats.py` | 8 | L1 |
| 报告管理 / 性能 | `test_report_management.py` | 37 | L1/L2 |
| 录屏播放器 | `test_record_player.py` | 16 | L2 |
| **弱网引擎** | `test_weak_network.py` | **11** | **L1** |
| 联合验收 | `test_joint_acceptance.py` | **23** | L1/L2 |
| 前端性能契约 | `test_frontend_performance.py` | 10 | L1 |
| 性能遥测 | `test_performance_telemetry.py` | 6 | L1/L2 |
| **合计** | | **192** | |

### 3.2 CI 门禁

```bash
pip install pyyaml pytest pytest-cov pytest-mock
python scripts/validate_compatibility_matrix.py
python -m pytest tests/ -v
```

L1 模块清单（10 个）：见 `tests/matrix_loader.py` `_L1_TEST_MODULES`

### 3.3 本次联合验收发现并修复的问题

| # | 发现方 | 严重度 | 问题 | 修复 |
|---|--------|--------|------|------|
| 1–21 | — | — | （v2.0–v2.2 项） | 见 git 历史 |
| 22 | PM | P1 | 弱网能力无产品文档 | `base.html` 弱网测试章节（中/英） |
| 23 | QA | P1 | 弱网未纳入 L1 门禁与联合验收 | `test_weak_network.py` + `TestWeakNetAcceptance` |
| 24 | QA | P2 | 矩阵未登记 weak_network 特性 | `compatibility_matrix.yaml` metrics.weak_network |
| 25 | R&D | P2 | apply API 缺少 preset 时 `_request` 抛错 | 改为 `request.args.get('preset')` 可选 |
| 26 | PM | P2 | 验收报告用例数未更新 | v2.3 文档 122 用例 |
| 27 | R&D | P2 | 根目录脚本/日志/文档分散 | `runtime/` + `scripts/README` + `docs/06-engineering/` |
| 28 | PM | P3 | 文档重复、断链、plans 过期 | 删除 6 份冗余 MD；`docs/README` 单入口；根目录 ~50MB 日志清理 |
| 29 | R&D | P1 | `/apm/log` 单指标请求预计算全部 9 类指标 | 改为可调用对象分发，仅执行请求目标 |
| 30 | QA | P2 | 报告列表会将无扩展名普通文件计入 total | `os.scandir()` 仅保留目录 |
| 31 | R&D/QA | P2 | 分析页重复扫描目录；直接优化需防缺失/越界 scene | 受限直接目录检查 + 4 个路由边界用例 |
| 32 | QA | P0 | 删除报告接口可通过 `scene=..` 越界删除目录 | realpath containment + 跨平台路径拒绝测试 |
| 33 | QA | P1 | 非正数 `max_points` 可关闭图表上限，POST 参数被忽略 | GET/POST 统一解析，非法值回落 1500 |
| 34 | PM/QA | P1 | 损坏报告占用分页槽位并造成空页 | 扫描阶段校验 UTF-8 JSON，仅统计有效报告 |
| 35 | QA | P2 | 报告目录扫描期间删除会触发 500 | 捕获目录项 I/O 竞态并跳过消失项 |
| 36 | QA | P1 | 分析页生成对比列表期间目录变化可触发 500 | 捕获列表竞态，保留当前报告分析 |
| 37 | R&D | P0 | 场景符号链接解析到报告根目录时可删除全部报告 | 显式拒绝解析结果等于报告根目录 |
| 38 | R&D | P1 | 全量校验元数据导致报告列表 O(N) 文件读取 | 排序后惰性读取，损坏项自动回填当前页 |
| 39 | R&D | P1 | 实时轮询把函数执行结果传给 `setTimeout`，请求无等待连续触发 | 独立 timer registry + 延迟回调 |
| 40 | R&D | P1 | Highcharts load 参数在图表创建前提前执行采集函数 | 传递采集回调函数 |
| 41 | QA | P1 | compare/pk 页面加载大报告时全量读取与返回 | 页面显式传 `max_points`，API 显式参数全链路降采样 |
| 42 | QA | P2 | 分析页首次同时发起最多 9 个日志请求 | 最大并发 3 的 FIFO 请求队列 |
| 43 | R&D/QA | P2 | 缺少 API/ADB 请求耗时与并发数据 | 有界进程内 telemetry |
| 44 | 浏览器验收 | P1 | 普通分析页访问缺失报告时磁盘变量未定义导致 500 | 初始化空磁盘摘要 |
| 45 | 浏览器验收 | P1 | 对比页任一报告缺失时摘要变量未定义导致 500 | 安全场景检查 + 空摘要 |
| 46 | 独立复核 | P1 | 手动刷新绕过分析页并发队列；CPU 核心刷新目标错误 | 所有刷新统一入队并修正目标 |
| 47 | 独立复核 | P1 | 超大 `max_points` 可绕过响应点数保护 | 服务端对显式正数参数统一封顶 1500 |
| 48 | 独立复核 | P2 | 遥测统计自身且路由维度理论上无界 | 排除 telemetry 端点；超限聚合到 `__other__` |
| 49 | PM | P1 | Android App 只能按包名选择，系统/第三方混杂 | 结构化 App 列表 + 首页过滤 |
| 50 | PM/QA | P1 | 前台运行 App 仍需手动选择 App 与进程 | 前台第三方 App 单进程自动选中，多进程保留人工选择 |
| 51 | R&D | P2 | 桌面名解析在不同 ROM 上不稳定 | 包列表快返；独立 label 接口优先 `aapt dump badging`，失败回退包名 |
| 52 | PM/QA | P2 | 应用名 + 长包名展示换行且高亮包名对比度不足 | Select2 单行 flex 模板 + 省略；高亮态应用名/包名统一白字 |
| 53 | R&D | P1 | 全量同步解析应用名导致初始化 10s 级阻塞 | 前台/手选 App 优先；label 小批次异步补齐 + 30 天持久缓存 + 单包超时；`/device/package` 不再触发慢扫描 |
| 54 | 浏览器验收 | P1 | 初始化成功后 SweetAlert loading 可能残留遮挡页面 | Android 初始化/包列表成功路径统一使用 `SwalCloseLoading()` |
| 55 | PM/QA | P0 | Windows scrcpy 直录 MP4 偶发无 `moov`；MKV 浏览器 seek/duration 不可靠 | 改为 scrcpy 录 MKV 后用 ffmpeg 无损封装 MP4；MP4 校验通过才网页播放，MKV 仅系统播放器兜底 |

---

## 4. 研发验收 — 技术一致性

| 检查项 | 状态 |
|--------|------|
| 弱网：`WeakNetworkManager` → tc netem on device iface | ✅ |
| 能力检测：root / tc / iface / active state | ✅ |
| API：presets · capabilities · status · apply · clear · probe | ✅ |
| 录屏 / 报告 / 时长 / 降采样（v2.1–v2.2） | ✅ |
| 性能 A：惰性指标加载 / 去除重复场景扫描 / 安全场景定位 | ✅ |
| 性能 B：实时调度 / compare-pk 降采样 / 分析并发队列 / 遥测 | ✅ |
| Flask 2.0.3 未变动 | ✅ |

---

## 5. L3 真机实验室 — 待签字项

> 使用 [L3 设备实验室清单](./l3-device-lab-checklist.md)

| 项 | 负责人 | 状态 |
|----|--------|------|
| Android P0 × 4 API 3D FPS | QA | ☐ |
| iOS P0 × 2 | QA | ☐ |
| PerfDog smoke（Live Stats / 场景 / Big Jank / Excel） | QA | ☐ |
| 报告 smoke：列表 `apm_*` 时长 | QA | ☐ |
| 报告 smoke：≥30min 分析页 10s 内可交互 | QA | ☐ |
| 实时采集 smoke：前台采样间隔稳定、切后台无新增请求、恢复后继续 | QA | ☐ |
| 对比/PK smoke：≥30min 两份报告加载与曲线首尾点正确 | QA | ☐ |
| 录屏 smoke：Record Screen ≥3min + 页内 mp4 播放 | QA | ☐ |
| 录屏 smoke：远程 Host 列表与播放 | QA | ☐ |
| **弱网 smoke（Root 机）**：应用 3G 预设 → ping RTT 明显升高 | QA | ☐ |
| **弱网 smoke**：停止采集 → `tc qdisc` 已清除 | QA | ☐ |
| **弱网 smoke（非 Root）**：探测模式可用，应用按钮禁用 | QA | ☐ |

---

## 6. 残留风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| 弱网模拟依赖 Root + netem | 中 | UI/手册明确；探测模式无 Root 可用 |
| 部分 OEM 内核无 tc 或 su 受限 | 中 | `capabilities` 前置检测 + 错误提示 |
| 弱网仅作用设备侧出口，非 PC 代理 | 低 | 文档说明；与 PerfDog 免 Root 方案路径不同 |
| iOS 无设备侧弱网 | 中 | 文档指向 Network Link Conditioner |
| 旧报告 mkv 浏览器不可播 | 低 | 系统播放器 fallback |
| iOS 26 + tidevice 未真机验证 | 高 | P0 必测 |
| Eventlet 与旧 Werkzeug 在 Python 3.12 出现弃用告警 | 中 | 当前回归通过；后续独立依赖升级验证 |
| `total` 保留候选报告目录语义，损坏元数据仅从页面数据跳过 | 低 | 保持旧契约；管理损坏目录可进一步清理 |
| 旧客户端省略或传非法 `max_points` 的 compare/pk API 仍保持全量返回 | 中 | 为兼容旧 API 契约保留；当前页面显式传参，长报告直连 API 风险通过文档和遥测观察 |
| 浏览器验收环境无真机，未验证真实 ADB 长命令与页面切后台时序 | 中 | L3 增加实时采集 smoke |
| telemetry 为进程内统计，多 worker 部署时每个 worker 独立 | 低 | 当前默认单进程；多 worker 方案另行评估聚合 |

---

## 7. 三方评估摘要

### 研发 (R&D)

- **通过项**：性能方案 A 响应一致；性能 B 修复无间隔轮询、限制分析并发并提供运行时遥测。
- **待 L3**：高通/联发科 Root 机各 1 台验证 rmnet 网卡识别。

### 产品 (PM)

- **通过项**：报告排序、分页、分析入口和图表字段保持兼容；对比/PK 页面显式限制 1500 点。
- **待 L3**：Root 实验室机验收「3G 预设下手游加载变慢」可感知。

### 测试 (QA)

- **通过项**：192 自动化；专项、全量、编译、兼容门禁和四类页面浏览器验收通过。
- **待 L3**：L3 清单三项弱网 smoke 真机签字。

---

## 8. 签字栏

| 角色 | 姓名 | 日期 | 签字 |
|------|------|------|------|
| 研发负责人 | | | |
| 产品负责人 | | | |
| 测试负责人 | | | |

---

*关联: [兼容矩阵](../compatibility-matrix.md) · [L3 清单](./l3-device-lab-checklist.md)*
