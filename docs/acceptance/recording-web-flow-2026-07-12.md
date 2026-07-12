# Android 录屏网页路径 E2E 验收记录

- **日期**：2026-07-12
- **任务**：P2-T1（R1 / R5 自动化；R4 待浏览器目视）
- **执行方式**：`python scripts/accept_record_e2e.py`（REST 路径与 Web UI 一致）
- **结论**：✅ **R1 / R4 / R5 全部通过**

---

## 环境

| 项 | 值 |
|----|-----|
| 主机 OS | Windows 10 |
| SoloX | `http://127.0.0.1:50003` |
| 设备 | `ecc3b00e` · vivo **V1936A** |
| Android | **11** |
| 目标 App | `com.lyjz.chqsy.vivo`（Cocos 游戏） |
| 录屏画质 | **720p** |
| 录屏时长 | **65s**（要求 ≥60s） |

---

## 执行命令

```powershell
# 1. 启动服务（另开终端）
python -c "from solox.web import start; start('127.0.0.1', 50003)"

# 2. E2E 验收
python scripts/accept_record_e2e.py --duration 65 --quality 720p `
  --json-out runtime/cache/e2e_record_result.json
```

---

## 结果摘要

| 检查项 | 结果 | 证据 |
|--------|------|------|
| **R1** MP4 合法可 finalize | ✅ | `valid_mp4=True`，`moov` 校验通过 |
| **R1** 时长 ≥60s | ✅ | `ffprobe_duration_sec=66.537` |
| **R5** 流式 API / Range | ✅ | `GET /apm/record/stream?scene=...` + `Range: bytes=0-1023` → **206** |
| **R5** 报告 `video` 标记 | ✅ | `result.json` → `"video": 1` |
| 录屏进程健康 | ✅ | 65s 内 `healthy=True` |
| **R4** 播放器铺满弹窗 | ✅ | 2026-07-12 报告页人工确认 |

**报告目录**：`report/apm_2026-07-12-18-21-46/`

**视频文件**：`report/apm_2026-07-12-18-21-46/record.mp4`（约 66.5s）

**结构化结果**：`runtime/cache/e2e_record_result.json`

---

## 备注

1. **第一次运行**：stop/remux 阶段 Flask 进程异常退出（WinError 10054），但 `report/record.mkv`（≈33MB）已落盘且 `valid_mkv=True`；手动 remux 后 `record.mp4` 亦 `valid_mp4=True`。
2. **第二次运行**（加长 `/apm/create/report` 超时至 185s）：全流程通过，报告已归档至 `apm_*` 目录。
3. **后续**：P2-T2 已落地 — `accept_record_gate.py` + `release_gate` 可选 `SOLOX_RECORD_ACCEPT=1` 第 4 步。

4. **R4**（2026-07-12 补验）：报告页播放 `apm_2026-07-12-18-21-46`，视频区域铺满弹窗，seek 正常。

---

## R4 人工补验

~~待补验~~ **已通过**（2026-07-12）

---

*关联：[Phase 2 计划](../plans/2026-07-12-android-ios-alignment-phase2.md) · [视频问题](../视频问题.md) §6*
