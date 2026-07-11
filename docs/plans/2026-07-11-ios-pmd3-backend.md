# iOS 能力补齐：基于 pymobiledevice3 的隔离后端（A/B/C/D）

- 日期：2026-07-11
- 状态：实施中（代码落地，真机验收待定）
- 适用前提：**仅个人、非商业、纯本地使用，永不对外分发**。此前提下 GPL-3.0
  （pymobiledevice3）/AGPL-3.0（sonic-ios-bridge）的私有使用例外成立，可直接
  依赖/借鉴其代码。若将来对外分发，本模块必须移除或整仓改用兼容许可证。

## 背景与目标

现有 iOS 链路（`solox/public/iosperf/`，基于 tidevice 0.9.7 思路）在 iOS 17+
上受限：无程序化弱网、无录屏、无真实 Jank、隧道链路缺失。本方案引入
`pymobiledevice3`（Python，pip 可装）作为**完全可选、隔离、惰性导入**的扩展
后端，补齐四项能力：

- A：iOS 17+ 设备连接（usbmux + tunneld/RSD），设备与版本发现
- B：程序化弱网（Instruments Condition Inducer）
- C：截图单帧 + 截图序列录制 → ffmpeg 合成视频
- D：真实 Jank（CoreProfileSessionTap 内核帧时序 → 复用 Android 抖动算法）

## 关键 API 证据（本机 pymobiledevice3 9.33.1 实测 introspection）

- 设备：`pymobiledevice3.usbmux.list_devices(usbmux_address=None) -> [MuxDevice]`
- 隧道：`pymobiledevice3.tunneld.api.get_tunneld_devices(addr=('127.0.0.1',49151))
  -> [RemoteServiceDiscoveryService]`；`get_tunneld_device_by_udid(udid)`
- 弱网：`services.dvt.instruments.condition_inducer.ConditionInducer`
  - `.list() -> list[dict]`、`.set(profile_identifier)`、`.clear()`
- 截图：
  - `services.screenshot.ScreenshotService(lockdown).take_screenshot() -> bytes`
  - `services.dvt.instruments.screenshot.Screenshot(dvt).get_screenshot() -> bytes`
- 帧时序：`services.dvt.instruments.core_profile_session_tap.CoreProfileSessionTap`
  - `.get_stackshot(timeout)`、`.get_kdbuf_stream(queue)`、`.pump_kdbuf_chunks(queue)`
  - `.get_trace_codes(dvt) -> dict[int,str]`、`.get_time_config(dvt)`

## 与此前结论的关系（诚实修正）

此前 `2026-07-11-ios-gap-and-oss-survey.md` 结论"iOS 无法复用 Android Jank 算
法"**仅对 Instruments opengl 采样器成立**——该通道只给聚合 FPS 标量，无逐帧时
戳。`CoreProfileSessionTap`（kdebug 内核追踪）是**另一条更丰富的数据源**，理论
上可提取 CoreAnimation 逐帧时间戳，从而复用
`android_fps._calculate_jank_ex()`。此前因许可证不能移植 pymobiledevice3；现私
有使用前提解除该限制，故 D 从"不可行"上调为"可行，但需真机标定帧事件码"。

## 架构

隔离包 `solox/public/ios_ext/`（所有 `pymobiledevice3` 导入均在函数内部惰性完
成，缺失时核心 SoloX 不受影响）：

- `__init__.py`：`is_available()` / `capabilities()` 能力探测
- `device.py`：设备枚举、版本、service-provider 工厂（<17 lockdown，17+ RSD）
- `weaknet.py`：Condition Inducer 封装（list/apply/clear/probe）
- `screen.py`：单帧截图 + 截图序列录制线程 → ffmpeg 合成 mp4
- `frametime.py`：CoreProfileSessionTap 帧时序采集 + Jank 计算（复用 Android）

集成点：
- 弱网：API 层按平台把 iOS 路由到 `ios_ext.weaknet`
- 截图/录屏、帧时序：经后端暴露，前端沿用既有 iOS 分支

## 交付形态与验收边界（重要）

- 当前开发环境为 Windows + Android 真机，**无 iOS 设备**。
- 各模块提供**真实 pymobiledevice3 调用代码 + mock 单测 + 文档**。
- **真机验收待定**项（需 iOS 17+ 真机 + `sudo` 隧道守护 + Windows wintun）：
  - A 隧道链路联通性；B 各 profile 实际生效；C 帧率/清晰度；
  - D 的 kdebug CoreAnimation 帧事件码与 Jank 阈值标定。
- 不以任何模拟/假数据冒充真机验证结果。

## 任务

1. `ios_ext` 能力探测骨架（可选依赖、惰性）
2. A device.py
3. B weaknet.py
4. C screen.py
5. D frametime.py
6. pyproject `ios` extra
7. API/弱网层平台路由集成
8. mock 单测 + 全量回归
9. 文档更新（faq/README）
