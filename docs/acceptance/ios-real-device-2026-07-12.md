# iOS 真机验收尝试记录（2026-07-12）— 环境阻塞，转 macOS 续验

- **日期**：2026-07-12
- **目的**：在 iOS 真机上验收 `solox[ios]`（pymobiledevice3）能力：设备信息、
  截图、被动 RTT（P2-T4）、Condition Inducer 弱网、真实 Jank。
- **结论**：⛔ **被 Windows 环境阻塞，未能完成真机验收**；已定位根因，待转 macOS
  真机继续。**未以任何模拟数据冒充真机结果。**

---

## 1. 设备

| 项 | 值 |
|----|-----|
| 型号 | iPhone17,5 |
| 系统 | **iOS 26.5**（BuildVersion 23F77） |
| UDID | `00008140-001145DC2232801C` |
| 连接 | USB |

`python -m pymobiledevice3 usbmux list` **能枚举**到该设备（基础 usbmux 驱动存在）。

---

## 2. 阻塞现象

对设备做 lockdown 操作（设备信息 / 截图）均报：

```
MuxException: got an error message: {'MessageType': 'Result', 'Number': 183}
```

调用栈定位在 pairing 阶段的 **SavePairRecord**（保存配对记录）。已在 iPhone 上
点击「信任此电脑」并输入密码，问题依旧。

---

## 3. 根因（已确诊，非 SoloX 代码缺陷）

本机**缺少 "Apple Mobile Device Service"**：

```
sc query "Apple Mobile Device Service"  → 不存在
Get-Service *Apple*                      → 无
%ProgramData%\Apple\Lockdown            → 无配对目录
```

Windows 上 `usbmux list` 只需最简驱动即可枚举设备，但**保存配对记录**需要
Apple Mobile Device Service 处理，缺失即返回 `Number: 183`。该结论与
pymobiledevice3 官方 issue #1040 作者说明一致：Windows 下 pmd3/tidevice 均依赖
此服务。

**影响面**：阻塞**所有** pmd3 lockdown/DVT 能力（设备信息、截图、弱网、Jank、
被动 RTT），亦影响 tidevice 的 iOS 采集。属 **Windows 环境前置条件缺失**，
`solox.public.ios_ext` 代码本身已有 mock 单测覆盖，非代码问题。

尝试安装 Apple Mobile Device Service **失败**（用户环境），故本机无法继续。

---

## 4. 转 macOS 后的续验清单

macOS 原生支持 usbmux，且 pmd3 对 iOS 17.4+ 全支持，无需该 Windows 服务。届时按序验收：

### 无需隧道（lockdown）
- [ ] `ios_ext.device.get_device_info(udid)` 返回真实型号/版本
- [ ] `ios_ext.screen.save_screenshot(udid, out)` 生成合法 PNG

### 需 tunneld 隧道（iOS 17+ DVT；macOS：`sudo pymobiledevice3 remote tunneld`）
- [ ] 被动 RTT（P2-T4）：`/apm/weaknet/probe?platform=iOS` 返回
      `passive_rtt_supported=true` 且 `probe.avg_rtt_raw` 为真实值；
      **核对 `min_rtt/avg_rtt` 单位（μs/ms）以完成 netprobe 单位标定**
- [ ] Condition Inducer 弱网：`/apm/weaknet/ios/profiles` 列档位 → apply/clear 生效
- [ ] 真实 Jank（frametime）：`/apm/ios/jank` 在真机标定 trace code 后返回可信 Jank

### iOS 专属弱网 UI 面板（P2-T4 延后项）
- [ ] 有真机后再实现并目视验证 iOS 弱网面板（探测结果 + NLC 引导；隐藏注入控件）

---

## 5. 当前如实状态

| 能力 | 代码 | 单测 | Windows 真机 | 备注 |
|------|------|------|-------------|------|
| iOS 设备信息 | ✅ | ✅ | ⛔ 环境阻塞 | 待 macOS |
| iOS 截图 | ✅ | ✅ | ⛔ 环境阻塞 | 待 macOS |
| iOS 被动 RTT（P2-T4） | ✅ | ✅ | ⛔ 环境阻塞 | 单位标定待 macOS |
| iOS 弱网 Condition Inducer | ✅ | ✅ | ⛔ 环境阻塞 | 待 macOS |
| iOS 真实 Jank | ✅ | ✅ | ⛔ 环境阻塞 | trace code 标定待 macOS |

---

*关联：[Phase 2 计划](../plans/2026-07-12-android-ios-alignment-phase2.md) ·
[iOS pmd3 后端](../plans/2026-07-11-ios-pmd3-backend.md) ·
[iOS 借鉴调研](../plans/2026-07-12-ios-oss-borrow-survey.md)*
