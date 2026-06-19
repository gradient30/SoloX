# 弱网测试用户指南

本文面向 SoloX 使用者，说明如何在 Android 设备上使用弱网测试。研发实现细节见 [弱网工具技术说明](../06-engineering/weak-network-tooling.md)。

## 能力说明

弱网测试支持：

- 预设场景：WiFi、4G、3G、2G、高延迟、高丢包等。
- 自定义参数：延迟、抖动、丢包、带宽限制。
- 上下行独立配置：Agent 模式支持上行/下行分别设置。
- 网络质量探测：RTT、丢包、抖动。
- 非 Root Android App 级弱网：通过 QAS Network Agent + VPN 授权实现。

## 选择哪种模式

| 模式 | 何时使用 | 前置条件 |
|------|----------|----------|
| Agent | 推荐。非 Root 真机，对指定 App 生效 | 安装 Agent APK，手机上授权 VPN |
| Root tc | Root 设备，需对整机网络接口注入弱网 | 设备 Root，系统支持 `tc netem` |
| Probe | 只想检查网络质量，不模拟弱网 | 设备可用 ADB |

普通用户优先使用 Agent 模式。

## 前置条件

1. Android 设备已连接电脑。
2. 已开启 USB 调试。
3. SoloX 服务已启动。
4. 目标 App 已安装，并且知道包名。
5. 使用 Agent 模式时，需要在手机上确认 VPN 授权。

包名可以在 SoloX 页面选择 App，也可以用 ADB 查询当前前台 App：

```powershell
$adb = "D:\workDir\githubwork\SoloX\runtime\android-toolchain\android-sdk\platform-tools\adb.exe"
& $adb -s DEVICE_ID shell dumpsys activity activities | Select-String -Pattern "mResumedActivity"
```

## Web 页面操作

1. 打开 SoloX 首页。
2. 选择 Android 设备。
3. 选择目标 App 包名。
4. 打开“弱网测试”面板。
5. 弱网引擎选择 `Agent`。
6. 点击“安装 Agent”。首次使用或 Agent 更新后需要执行。
7. 点击“授权 VPN”。
8. 在手机上确认系统 VPN 授权弹窗。
9. 选择预设或填写自定义参数。
10. 点击“应用弱网”。
11. 测试完成后点击“清除弱网”。

不要跳过清除步骤。虽然 Agent 会尽量自动释放 VPN，但正式测试流程必须显式清理。

## Agent 安装与授权

Agent APK 内置在：

```text
solox/public/android_agent/
```

页面点击“安装 Agent”时，SoloX 会校验 `checksums.json` 中的 SHA-256 后安装 APK。

如果手机提示“已安装相同版本”，选择“重新安装”。

VPN 授权是 Android 系统安全要求，不能静默授权。点击“授权 VPN”后，请在手机上手动确认。

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| 延迟 | 每个方向增加固定耗时 | `100 ms` |
| 抖动 | 在固定延迟基础上增加随机变化 | `20 ms` |
| 丢包 | 按百分比丢弃流量 | `2%` |
| 带宽 | 限制吞吐 | `512kbit`、`5mbit` |
| 上行 | App 到服务器方向 | 登录、上传、发包 |
| 下行 | 服务器到 App 方向 | 下载、拉取资源、收包 |

建议先用低风险参数做确认，例如：

```text
delay_ms=100
jitter_ms=0
loss_pct=0
```

需要强验证时可短时间使用：

```text
loss_pct=100
```

强验证只建议持续几秒，并立即清除。

## API 使用

查询能力：

```bash
curl "http://localhost:50003/apm/weaknet/capabilities?platform=Android&device=DEVICE_ID&engine=agent"
```

安装 Agent：

```bash
curl -X POST "http://localhost:50003/apm/weaknet/agent/install" \
  -d "platform=Android" \
  -d "device=DEVICE_ID"
```

启动 VPN 授权：

```bash
curl -X POST "http://localhost:50003/apm/weaknet/agent/prepare" \
  -d "platform=Android" \
  -d "device=DEVICE_ID"
```

应用预设：

```bash
curl "http://localhost:50003/apm/weaknet/apply?platform=Android&device=DEVICE_ID&engine=agent&target_package=com.example.app&preset=lte_weak"
```

应用自定义参数：

```bash
curl "http://localhost:50003/apm/weaknet/apply?platform=Android&device=DEVICE_ID&engine=agent&target_package=com.example.app&delay_ms=100&jitter_ms=20&loss_pct=1"
```

上下行独立配置：

```bash
curl "http://localhost:50003/apm/weaknet/apply?platform=Android&device=DEVICE_ID&engine=agent&target_package=com.example.app&uplink_delay_ms=200&downlink_delay_ms=50&uplink_rate=512kbit&downlink_rate=5mbit"
```

清除弱网：

```bash
curl "http://localhost:50003/apm/weaknet/clear?platform=Android&device=DEVICE_ID"
```

网络探测：

```bash
curl "http://localhost:50003/apm/weaknet/probe?platform=Android&device=DEVICE_ID&host=8.8.8.8&count=10"
```

## 如何确认真的生效

Agent 模式不要用 `adb shell curl` 判断是否生效，因为它不是目标 App UID。

推荐确认方式：

1. 让目标 App 在前台运行。
2. 应用弱网。
3. 观察 App 内网络行为，例如登录、切图、加载、重连、消息收发。
4. 使用系统网络栈确认 VPN 绑定 UID：

```powershell
$adb = "D:\workDir\githubwork\SoloX\runtime\android-toolchain\android-sdk\platform-tools\adb.exe"
& $adb -s DEVICE_ID shell dumpsys package com.example.app | Select-String -Pattern "userId="
& $adb -s DEVICE_ID shell dumpsys connectivity | Select-String -Pattern "type: VPN|Interface: tun0|UIDs: \\[|WIFI\\|VPN" -Context 0,1
```

生效时应看到：

```text
Interface: tun0
UIDs: [目标UID-目标UID]
```

清理后再次执行检查，应不再出现 `tun0` 或目标 UID 的 VPN 绑定。

## 如何打包 Agent APK

研发或测试需要更新 Agent APK 时，使用以下命令。

调试构建：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1 native assembleDebug
```

正式打包到 SoloX 内置分发目录：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/package.ps1
```

打包成功后生成：

```text
solox/public/android_agent/qas-network-agent-<version>.apk
solox/public/android_agent/checksums.json
```

手动安装：

```powershell
$adb = "D:\workDir\githubwork\SoloX\runtime\android-toolchain\android-sdk\platform-tools\adb.exe"
$apk = "D:\workDir\githubwork\SoloX\solox\public\android_agent\qas-network-agent-0.1.0.apk"
& $adb -s DEVICE_ID install -r $apk
```

签名校验：

```powershell
$apksigner = "D:\workDir\githubwork\SoloX\runtime\android-toolchain\android-sdk\build-tools\36.0.0\apksigner.bat"
& $apksigner verify --verbose $apk
```

## 常见问题

### 点击授权后没有反应

处理步骤：

1. 看手机是否弹出 VPN 授权页。
2. 如果没有弹出，重新点击“授权 VPN”。
3. 如果仍无反应，强停 Agent 后重试：

```powershell
$adb = "D:\workDir\githubwork\SoloX\runtime\android-toolchain\android-sdk\platform-tools\adb.exe"
& $adb -s DEVICE_ID shell am force-stop io.solox.networkagent
```

### 应用弱网后 App 没变化

排查：

- 是否选错包名。
- 目标 App 是否真的在前台运行。
- 是否已经授权 VPN。
- `dumpsys connectivity` 是否显示 `UIDs: [目标UID-目标UID]`。
- App 是否通过其他进程或 SDK 包名发起网络。

### 清除后网络仍异常

先点击“清除弱网”。如仍异常：

```powershell
$adb = "D:\workDir\githubwork\SoloX\runtime\android-toolchain\android-sdk\platform-tools\adb.exe"
& $adb -s DEVICE_ID shell am force-stop io.solox.networkagent
```

再确认：

```powershell
& $adb -s DEVICE_ID shell dumpsys connectivity | Select-String -Pattern "type: VPN|Interface: tun0"
```

无输出表示 VPN 已清理。

### 为什么需要 VPN 授权

Android 非 Root 条件下，按 App 捕获网络流量的标准方式是 `VpnService`。系统要求用户显式授权，这是平台安全限制。

### iOS 是否支持

当前 SoloX 弱网模拟主要支持 Android。iOS 可使用系统或 Xcode 的 Network Link Conditioner 做外部弱网环境。
