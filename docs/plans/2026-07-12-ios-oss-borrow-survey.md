# iOS 能力借鉴调研：pymobiledevice3 / go-ios / sonic-ios-bridge

- **日期**：2026-07-12
- **目的**：以事实为依据，梳理三个开源 iOS 调试项目中**对 SoloX iOS 推进有价值、
  可学习或可直接借鉴使用**的技术方案与代码，并明确**许可证边界**。
- **适用前提**：SoloX 的 `solox[ios]` 可选后端仅供**个人、非商业、纯本地使用**
  （见 [ios-pmd3-backend.md](./2026-07-11-ios-pmd3-backend.md)）。

---

## 0. 许可证边界（先行约束）

| 项目 | 许可证 | 对 SoloX 的可用方式 |
|------|--------|---------------------|
| **pymobiledevice3** | **GPL-3.0** | 作为**可选依赖**惰性调用（`solox[ios]`）；**不**把其源码复制进以 MIT 分发的核心 |
| **go-ios** | **MIT** | **可直接移植代码**（保留版权声明/署名）；协议最宽松 |
| **sonic-ios-bridge** | **AGPL-3.0** | 仅作**思路参考**；不复制代码、不作为分发依赖 |

结论：**代码级直接借鉴优先 go-ios（MIT）**；pymobiledevice3 走"可选依赖调用"；
sonic 仅学习其封装思路。

---

## 1. 已借鉴并落地（P2-T4）

### 1.1 iOS 被动 RTT —— 借鉴 pymobiledevice3 `NetworkMonitor`

- **来源**：`pymobiledevice3/services/dvt/instruments/network_monitor.py`
  （DTX 通道 `com.apple.instruments.server.services.networking`）。
- **关键事实**：其 `ConnectionUpdateEvent` 每条 TCP 连接携带
  `min_rtt` / `avg_rtt` / `rx_bytes` / `tx_bytes` / `rx_dups` / `tx_retx` 等
  **内核级统计**。其中 `min_rtt` / `avg_rtt` 即**真实往返时延**。
- **为何重要**：非越狱 iOS **没有 shell**，无法像 Android 那样 `ping` 主动探测；
  但 `NetworkMonitor` 提供**被动** RTT（读取设备上已存在连接的内核测量），是
  iOS 上唯一可无越狱获取 RTT 的公开通道。
- **落地**：`solox/public/ios_ext/netprobe.py`（`sample_rtt` + 纯函数
  `aggregate_rtt`），经 `solox[ios]` 惰性调用；`/apm/weaknet/probe`（iOS 分支）
  在装了 `solox[ios]` 时返回被动 RTT，否则诚实 `probe_supported=false`。
- **诚实边界**：`min_rtt/avg_rtt` 为内核原始整数，单位（μs/ms）随 iOS 版本口径
  可能不同，故输出 `*_raw` + `unit='raw'`，**单位标定属真机待验收**，不臆造毫秒值。

### 1.2 iOS 程序化弱网 —— 已借鉴 pymobiledevice3 `ConditionInducer`（Phase 1）

- **来源**：`.../dvt/instruments/condition_inducer.py`
  （`com.apple.instruments.server.services.ConditionInducer`）。
- **落地**：`solox/public/ios_ext/weaknet.py`（Phase 1 已完成）。

---

## 2. 已借鉴（Phase 1，此处存档）

| 能力 | 来源（pymobiledevice3） | SoloX 落地 |
|------|------------------------|-----------|
| iOS 17+ 隧道/RSD 设备连接 | `tunneld` / `RemoteServiceDiscoveryService` | `ios_ext/device.py` |
| 截图 / 低帧录屏 | `services.screenshot` / dvt `screenshot` | `ios_ext/screen.py` |
| 真实 Jank（帧时序） | `CoreProfileSessionTap`（kdebug） | `ios_ext/frametime.py` |

---

## 3. 候选借鉴（尚未落地，价值与成本评估）

### 3.1 per-app 网络抓包 —— go-ios `pcap`（MIT，**可直接移植**）

- **来源**：`go-ios/ios/pcap/pcap.go` + `ipfinder.go`（服务 `com.apple.pcapd`）。
- **能力**：`IOSPacketHeader` 含 `Pid` / `ProcName` / `IFName` / `IO`（方向），可做
  **按进程/按 App 的抓包与流量方向拆分**，进而离线计算 RTT、重传、握手耗时。
- **对标价值**：PerfDog 的"网络请求瀑布/连接分析"级能力的基础数据源。
- **pymobiledevice3 等价**：`services/pcapd.py`（同一 `pcapd` 服务，Python 现成）。
- **建议**：若做 iOS 网络深分析，**优先用 pymobiledevice3 `pcapd`**（已是可选依赖，
  无需引入 Go）；go-ios 的 `IOSPacketHeader` 字段布局（MIT）可作为**解析参考**。
- **成本/风险**：抓包量大、需过滤；RTT 需自行做 TCP 状态机分析。列为 P3 可选。

### 3.2 设备 IP 发现 —— sonic `ip.go` / go-ios `ipfinder`

- **来源**：sonic `cmd/ip.go`（AGPL）→ 其实现**引用** go-ios `ipfinder.go`（MIT）。
- **能力**：通过 pcap 首包匹配 WiFiAddress(MAC) 得到设备当前 IPv4/IPv6。
- **建议**：若需要展示 iOS 设备 IP，**移植 go-ios `ipfinder`（MIT）**，不参考 sonic
  的 AGPL 封装。价值中等，列为 P3。

### 3.3 sysmontap 系统/进程指标 —— pymobiledevice3 `sysmontap`

- **来源**：`.../dvt/instruments/sysmontap.py`。
- **能力**：CPU/内存等系统与进程级采样；与 SoloX 现有 iOS 指标可交叉校准。
- **建议**：作为现有 `iosperf` 指标的**可选校准源**，非必需。P3。

---

## 4. 明确不借鉴 / 不纳入

- **sonic-ios-bridge 源码**：AGPL-3.0，除非 SoloX 整体改 AGPL，否则不复制其代码、
  不作分发依赖；仅可阅读其思路。
- **越狱类能力**：不在范围。
- **主动 ping**：iOS 非越狱无 shell，**不存在**设备侧主动 ping 方案；任何"iOS ping"
  UI 都应诚实标注为不支持或改用被动 RTT / NLC。

---

## 5. 与 P2-T4 的关系小结

- **核心已落地且可验证**：`/apm/weaknet/probe` 平台感知——Android 真实 ping、iOS
  诚实 `probe_supported=false` + NLC 指引；单测 + 真机 Android 联调通过。
- **可选已落地（真机待标定）**：`ios_ext/netprobe.py` 被动 RTT（借鉴
  pymobiledevice3 `NetworkMonitor`），mock 单测通过，真机 RTT 单位标定待验收。
- **后续可选（P3）**：go-ios `pcap`/`ipfinder`（MIT）做 per-app 网络深分析与设备 IP。

---

## 6. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-12 | 初版：三项目 iOS 能力与许可证边界调研，指导 P2-T4 及后续 |

---

*关联：[Phase 2 计划](./2026-07-12-android-ios-alignment-phase2.md) ·
[iOS pmd3 后端](./2026-07-11-ios-pmd3-backend.md) ·
[iOS 预研 spike](./2026-07-11-ios-gap-and-oss-survey.md)*
