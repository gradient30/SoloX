# QAS Network Agent 汉化与 4 Tab 设计

## 背景

QAS Network Agent 是 SoloX Android 弱网能力的端侧代理。当前 APK 已具备基于 VpnService 的按包名捕获、tun2proxy 数据面、本地 SOCKS5 shaper、前台服务后台运行能力，但界面仍偏 Demo，英文文案较多，不利于测试部门现场使用和验收。

## 目标

- APK 面向用户的内容汉化，保留系统或逻辑必须使用的英文标识。
- 使用移动端主流 App 布局：顶部标题栏、中间内容流、底部 Tab Bar。
- 底部 Tab 控制 4 个一级功能：总览、弱网、日志、设置。
- 列表内容使用轻量 Card/Cell；后续详情页使用顶部返回导航。
- Android 交互参考 Material Design 3 的层级、间距、触控目标和状态反馈，但继续使用无外部依赖的原生 Java 实现。
- 保持终端代理定位：状态清晰、操作克制、日志可查、控制链路稳定。

## 汉化边界

应汉化：

- 应用标题、通知标题/内容、通知渠道名称/描述。
- 顶部标题栏、Tab 文案、按钮、状态说明、空状态、操作提示。
- 日志页筛选标签可以展示中文，同时保留英文日志级别作为诊断标识。

必须保留英文：

- Android 包名 `io.solox.networkagent`。
- 控制 socket `solox.networkagent.control`。
- 协议字段、命令字、状态 wire name。
- 日志级别 `ERROR`、`WARN`、`INFO`、`DEBUG`。
- 第三方/系统名称，例如 `VPN`、`UID`、`SOCKS5`、`tun2proxy`、`START_STICKY`。

## 信息架构

### 总览

展示端侧运行总状态，包含：

- VPN 授权状态。
- 前台服务/后台运行状态说明。
- 快捷操作：授权并启动、停止服务、刷新。
- 安全提示：弱网由 SoloX 控制端下发，端侧只负责执行和显示。

### 弱网

展示数据面与目标信息，包含：

- 当前目标 App 包名由 SoloX 控制端指定。
- UID 按 VpnService per-app capture 绑定。
- 延迟、抖动、丢包、带宽、乱序由 native 数据面执行。
- 保留 `tun2proxy`、`SOCKS5` 等诊断关键词。

### 日志

展示 Agent 独立日志流，包含：

- `全部`、`错误`、`警告`、`信息`、`调试` 分级筛选。
- 日志 Cell 显示序号、级别、来源、消息。
- 空状态根据筛选条件展示中文说明。

### 设置

展示可验收的诊断信息，包含：

- 应用名称和版本。
- 包名和控制 socket。
- 后台运行方式：前台服务、通知、`START_STICKY`。
- 运行边界：端侧不主动选择模板，由 SoloX 控制端下发。

## UI 实现策略

- 保持 `Activity` + 原生 View 构建方式，不引入 AppCompat 或 Material 依赖。
- 根布局使用垂直 `LinearLayout`：顶部标题栏、中部 `ScrollView`、底部 `LinearLayout` Tab Bar。
- Tab 使用固定高度按钮样式，选中态通过背景色和文字色区分。
- 内容区使用轻量 Card/Cell：白底、细分隔、8dp 内圆角以内或等效背景。
- 文案短句化，避免说明文字挤占移动端空间。

## 验收点

- 源码测试可证明用户可见英文已收敛到允许列表。
- 源码测试可证明 4 个一级 Tab 均存在且无 Demo 文案。
- Android release 构建成功。
- 公开 APK 更新为 `qas-network-agent-0.1.0.apk`。
- `aapt2 dump badging` 可证明应用 label 为 `QAS Network Agent` 或确认产品命名要求变更后同步调整。
- 真机安装启动后可看到顶部标题栏、4 个底部 Tab、中文内容和日志筛选。
