# Android 芯片级 GPU 频率验收记录（P2-T5）

- **日期**：2026-07-12
- **任务**：P2-T5 —— Android 芯片级 GPU 指标（运行时/最大频率）
- **结论**：✅ 通过（诚实实现）——最大频率真机读到真实值；运行时频率非 root 如实不支持

---

## 环境

| 项 | 值 |
|----|-----|
| 设备 | `ecc3b00e` · vivo **V1936A** |
| SoC | `msmnile`（Snapdragon 855，Adreno 640，kgsl） |
| root | 否（非 root） |

---

## 真机 sysfs 探测实况

| 节点 | 结果 |
|------|------|
| `/sys/class/kgsl/kgsl-3d0/max_gpuclk` | **585000000**（可读 → 585.0 MHz） |
| `/sys/class/kgsl/kgsl-3d0/gpuclk`（当前频率） | **Permission denied** |
| `/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq` | Permission denied |
| `/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage` | Permission denied |
| `/sys/class/kgsl/kgsl-3d0/devfreq/gpu_load` | Permission denied |
| `/sys/class/kgsl/kgsl-3d0/clock_mhz` | Permission denied |

**结论**：现代 Android 非 root 设备的**运行时** GPU 频率/负载被 SELinux 限制为 root 可读（与 Phase 1 GPU 利用率同因）；**静态最大频率**（规格）可读。

---

## 代码行为（真机实测）

```text
runtime_mhz: None   supported: False   source: None      # 非 root，如实不支持
max_mhz:    585.0                                          # 真实规格，非空读数
```

---

## 实现要点（诚实边界）

1. **运行时频率**：按候选节点顺序（Adreno kgsl / Mali）尝试读取，首个可读者生效并按 deviceId 缓存；全部不可读 → `gpu_frequency_supported=false`，**不写入伪造值**。
2. **最大频率**：静态规格值，多数机型可读，单独字段 `gpu_max_frequency_mhz` 标注（明确非运行时遥测）。
3. **Mali Non-fragment/Fragment 占比**：经核实**无法经普通 sysfs 获取**（需 ARM Streamline / gatord 等厂商性能计数器）——**不伪造、不输出该字段**，honest 排除。
4. **前端**：`gpu-frequency-note` 如实展示——支持时显示运行时频率，否则显示"最大频率(规格) + 运行时需 root"。

---

## 顺带修复的可靠性问题

`adb.shell` 在 **Windows 宿主**下，命令若含 `2>/dev/null`，重定向会被宿主 cmd.exe 吞掉，导致**可读节点也返回空**。已在 `_read_freq_node` 去除 `2>/dev/null`（adb.shell 本就只取 stdout，非数值输出由数字校验拒绝）。

> 备注：仓库其他位置（如 `weak_network.py`）仍有 `2>/dev/null` 用法，在 Windows 宿主直连真机时可能同样失效；属既有跨平台隐患，未在本任务范围内改动，已记录备查。

---

## 测试

- `tests/test_apm_collect_api.py`：新增 `TestGpuFrequencyReading`（4）+ helper（2）——mock adb，覆盖 Hz→MHz、权限拒绝不支持、缓存零额外调用、MHz 节点不误缩放。
- `tests/test_frontend_performance.py`：GPU 频率提示渲染回归。
- 全量 `pytest tests/` 通过。

---

## 验收对照

- [x] 至少 1 台真机有非空读数（max 585 MHz）
- [x] 无节点/无权限机型返回 supported=false（不伪造）
- [x] 与 Phase 1 `gpu_supported=false` 语义一致

---

*关联：[Phase 2 计划](../plans/2026-07-12-android-ios-alignment-phase2.md) · [iOS 借鉴调研](../plans/2026-07-12-ios-oss-borrow-survey.md)*
