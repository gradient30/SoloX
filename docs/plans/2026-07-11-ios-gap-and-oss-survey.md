# iOS 能力预研 spike 与开源方案调研（2026-07-11）

> 目的：以事实为依据，评估 iOS 侧 Jank/弱网/录屏等能力的可行性，并调研 3 个主流开源
> iOS 调试项目可借鉴的范围与**许可证边界**。本文为结论性文档，指导后续是否投入。

## 1. 结论摘要

| 议题 | 结论 | 依据 |
|------|------|------|
| iOS 真实 Jank/BigJank/Stutter | **暂不支持，维持诚实标注** | 现有数据源只有聚合 FPS 标量，无逐帧时间戳；主流 OSS 也未通过公开通道暴露逐帧渲染时序 |
| iOS 设备侧弱网 | 手动 Network Link Conditioner 可用；程序化需 iOS 17+ Condition Inducer（未集成） | go-ios `devicestate`、pymobiledevice3 `developer dvt condition` |
| iOS 视频录屏 | 能力边界，非暂未实现；仅截图/MJPEG | go-ios `screenshot`(MJPEG)、sonic `screenshoot`、tidevice 截图 |
| 借鉴范围 | 仅可移植 **MIT** 的 go-ios 代码（署名）；GPL/AGPL 两者仅作思路/可选依赖 | 见第 4 节许可证 |

## 2. iOS Jank 预研（spike 结论：不做真 Jank，维持"暂不支持"）

### 事实链
- SoloX iOS FPS 唯一来源：`solox/public/iosperf/_instruments.py` 的 `iter_opengl_data()`
  （graphics.opengl DTX 通道），字段 `CoreAnimationFramesPerSecond` 是**每采样区间的聚合
  帧率标量**，**没有逐帧 display 时间戳**。
- Android 的 PerfDog 兼容 Jank 算法 `_calculate_jank_ex()`
  （`solox/public/android_fps.py`）要求输入 `timestamps: [app_ts, display_ts, vsync_ts]`
  逐帧序列。二者数据形态不同，**无法直接复用**。
- `solox/public/iosperf/_proto.py` 仅有 `graphics.opengl` 通道，无 coreanimation / 帧级
  渲染时序服务。

### OSS 交叉验证
- **go-ios**（MIT）：CLI 提供 `sysmontap`（CPU/内存）、`screenshot`、`instruments
  notifications` 等，**未提供**逐帧 FPS/Jank 命令；其 FPS 同样源自 GPU 采样器。
- **tidevice / sonic-ios-bridge**：iOS FPS 亦来自同一 GPU 聚合采样器。
- 即 PerfDog 式 iOS 逐帧 Jank，**不在这些工具通过公开 API 暴露的能力范围内**。PerfDog 采用
  的是其专有实现，无法据公开资料在 tidevice 0.9.7 链路上等价复刻。

### 决策
维持任务 1 的处理：iOS `jank/big_jank` 返回 `null` + `jank_supported=false`，UI 不显示伪值。
若未来迁移到 iOS 17+ 隧道链路并确认可取得帧级时序，再重启该能力。**当前不投入。**

## 3. iOS 设备侧弱网（程序化路径存在，但成本高、暂缓）

- iOS 17+ 的 Instruments **Condition Inducer** 可程序化启用网络/热条件，对应：
  - go-ios：`ios devicestate list` / `ios devicestate enable`
  - pymobiledevice3：`pymobiledevice3 developer dvt condition ...`
- 集成障碍（事实）：
  1. 现链路锁定 `tidevice==0.9.7`，不含 Condition Inducer 与 RemoteXPC 隧道；
  2. iOS 17+ 需 `sudo ios tunnel start` 守护进程，Windows 还需 `wintun.dll`；
  3. 许可证（见第 4 节）。
- 当前交付：文档引导用户走系统 Network Link Conditioner（见 `docs/05-issues/faq.md` §20）。

## 4. 开源项目许可证边界（决定"借鉴"方式的硬约束）

SoloX 自身为 **MIT**（`pyproject.toml` / `LICENSE`）。

| 项目 | 许可证 | 可否将其**源码**并入 SoloX | 说明 |
|------|--------|---------------------------|------|
| [go-ios](https://github.com/danielpaulus/go-ios) | **MIT** | ✅ 可移植（保留版权声明/署名） | 与 MIT 兼容；注意 Go→Python 属重写 |
| [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) | **GPL-3.0** | ❌ 不可并入 | 并入会使 SoloX 被迫 GPL；可作**可选外部依赖**或思路参考 |
| [sonic-ios-bridge](https://github.com/SonicCloudOrg/sonic-ios-bridge) | **AGPL-3.0** | ❌ 不可并入 | 比 GPL 更严格（网络服务传染）；仅思路参考 |

原则：**思路 / 协议知识可自由学习**（不受版权保护），但**受版权保护的源码**必须遵守其
许可证。对 MIT 的 SoloX 而言，仅 go-ios 的代码可在署名前提下移植。

## 5. 本轮实际落地范围

- 任务 4：iOS 录屏/弱网边界文档（faq §18/§20）— 已完成。
- 任务 5：本预研文档 — 已完成，结论为"iOS 真 Jank 不投入、弱网走手动引导"。
- 方案 B：CLI / MCP / 规则引擎分析 / 报告回归 diff —— 均为**平台无关、只处理已采集数据**，
  不触碰 iOS 设备库与上述许可证约束，另见各自实现与测试。
