# L3 设备实验室验收清单

> 来源：`tests/compatibility_matrix.yaml` · 发版门禁：**P0_all_pass**  
> 执行环境：SoloX 最新 RC 构建 · 样本：Unity 或 UE 3D 手游

---

## 执行说明

- **通过标准**：P0 全部勾选；任一项失败则 **不可正式发布**
- **记录要求**：每项填写设备型号、序列号、包名、FPS 截图或日志
- **推荐命令**：
  ```bash
  curl "http://localhost:50003/apm/collect?platform=Android&deviceid={id}&pkgname={pkg}&target=fps"
  curl "http://localhost:50003/apm/collect?platform=Android&deviceid={id}&pkgname={pkg}&target=cpu"
  ```

---

## Android P0（发版门禁 — 4 项）

| ☐ | API | 系统 | 档位 | 设备型号 | 序列号 | FPS≠0 | fps_meta.confidence | CPU | Memory | 备注 |
|---|-----|------|------|----------|--------|-------|---------------------|-----|--------|------|
| ☐ | 33 | Android 13 | 3D | | | | | | | |
| ☐ | 34 | Android 14 | 3D | | | | | | | |
| ☐ | 35 | Android 15 | 3D | | | | | | | Play 2026 target 基准 |
| ☐ | 36 | Android 16 | 3D | | | | | | | 2026 新系统 |

**3D 样本要求**：Unity `UnityPlayerActivity` 或 UE `GameActivity`，前台运行 ≥ 60s。

**FPS 通过**：`status=1` 且 `fps > 0` 且 `fps_meta.confidence` ≥ `medium`（如有）。

---

## iOS P0（发版门禁 — 2 项）

| ☐ | 系统 | 建议机型 | 芯片 | UDID | FPS | CPU | Memory | 备注 |
|---|------|----------|------|------|-----|-----|--------|------|
| ☐ | iOS 18 | iPhone 15 Pro | A17 | | | | | |
| ☐ | iOS 26 | iPhone 16 | A18 | | | | | tidevice 专项 |

```bash
curl "http://localhost:50003/apm/collect?platform=iOS&pkgname={bundle}&target=fps"
```

---

## Android P1 抽测（每周 — 可选本次 RC）

| ☐ | API | 系统 | 档位 |
|---|-----|------|------|
| ☐ | 30 | Android 11 | 3d_baseline |
| ☐ | 31 | Android 12 | 3D |
| ☐ | 32 | Android 12L | 3D |

---

## 附加 smoke（推荐）

| ☐ | 项 | 说明 |
|---|-----|------|
| ☐ | 投屏 high/medium/low | API 34 或 35 设备 |
| ☐ | `/apm/report/list?page=1&size=20` | 报告分页；**持续时长**列为 `apm_MM:SS`，非时间戳 |
| ☐ | **长时跑测分析页** | ≥30min session，点击「分析」10s 内图表可交互 |
| ☐ | **时长 tooltip** | 悬停持续时长列，显示完整 scene 目录 ID |
| ☐ | Logcat 启动/停止/导出 | Error Log 面板 |
| ☐ | `/apm/collect?target=gpu` | GPU 回归（RC 修复项） |
| ☐ | **Live Stats Min/Max** | 采集中侧边栏 CPU/MEM/FPS 滚动统计更新 |
| ☐ | **场景标签** | 采集中标记 2+ 场景 → 停止 → 分析页场景表有数据 |
| ☐ | **Big Jank** | 3D 高负载场景 `big_jank` API/log Σ > 0 |
| ☐ | **Excel 导出** | 报告页导出 `.xls` 含 `scene_tags` / `scene_stats` / `big_jank` sheet |
| ☐ | **弱网探测** | 非 Root 设备：弱网面板 → 探测 → 返回 RTT/丢包 |
| ☐ | **弱网模拟（Agent 非 Root）** | 安装 QAS Network Agent → 授权 VPN → 对目标 App 应用弱网 → `dumpsys connectivity` 显示 `tun0` 绑定目标 UID |
| ☐ | **弱网模拟（Root tc 兼容）** | Root 设备应用「3G」预设 → `adb shell su -c "tc qdisc show dev wlan0"` 含 netem → ping RTT 升高 |
| ☐ | **弱网清除** | Agent 模式 clear 后无 `tun0/VPN` 残留；Root tc 模式清除 tc 规则，网络恢复基线 |

---

## 验收结论

| 项 | 结果 |
|----|------|
| P0 Android 4/4 通过 | ☐ 是 ☐ 否 |
| P0 iOS 2/2 通过 | ☐ 是 ☐ 否 |
| 是否批准正式发布 | ☐ 是 ☐ 否 |

**测试负责人**: _______________ **日期**: _______________

---

*联合验收报告: [joint-review-2026-compatibility.md](./joint-review-2026-compatibility.md)*
