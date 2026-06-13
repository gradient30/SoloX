# 兼容矩阵与发版门禁

本文档定义 SoloX 对 **2026 年新手游** 的系统版本覆盖策略、测试深度与发版验收标准。机器可读配置见 [`tests/compatibility_matrix.yaml`](../tests/compatibility_matrix.yaml)，CI 通过 `tests/test_compatibility_matrix.py` 自动校验文档与配置一致性。

## 发版规则

| 规则 | 说明 |
|------|------|
| **发版门禁** | `P0_all_pass` — P0 矩阵全绿方可发版 |
| **P1 失败** | 可发版，但必须记录已知问题 |
| **P2/P3 失败** | 不阻断发版，更新 FAQ / 降级说明 |

## Google Play 2026 对齐

- 新应用 **targetSdk ≥ API 35（Android 15）**
- SoloX P0 必须包含 **API 35、36**，确保与上架基线系统行为一致

---

## Android 覆盖区间

### P0 — 发版门禁（每版必测，3D 全指标 60s）

| API | 系统 | 档位 | 说明 |
|-----|------|------|------|
| 33 | Android 13 | 3D | 存量主力 |
| 34 | Android 14 | 3D | 存量主力 |
| **35** | **Android 15** | **3D** | **Google Play 2026 target 基准** |
| **36** | **Android 16** | **3D** | **2026 新系统主线** |

### P1 — 每周抽测

| API | 系统 | 档位 | 说明 |
|-----|------|------|------|
| 30 | Android 11 | 3d_baseline | 3D 最低保底 |
| 31 | Android 12 | 3D | BLAST Surface 起点 |
| 32 | Android 12L | 3D | 12L 变体 |

### P2 — 月度 smoke（2D 轻量）

| API | 系统 | 档位 |
|-----|------|------|
| 28 | Android 9 | 2D |
| 29 | Android 10 | 2D |

### P3 — 文档降级（不阻断发版）

| API | 系统 | FPS 策略 |
|-----|------|----------|
| 26 | Android 8.0 | page_flip_only |
| 27 | Android 8.1 | page_flip_only |

> **3D 重度游戏**：深测区间 **API 31–36**；Android 11（API 30）仅保底；Android 10 以下不建议深测。

---

## iOS 覆盖区间

### P0 — 发版门禁

| 系统 | 建议机型 | 档位 | 芯片 |
|------|----------|------|------|
| **iOS 18** | iPhone 15 Pro | 3D | A17 |
| **iOS 26** | iPhone 16 | 3D | A18 |

### P1 — 每周抽测

| 系统 | 建议机型 | 档位 |
|------|----------|------|
| iOS 17 | iPhone 14 | 3D |

### P2 — 月度 smoke

| 系统 | 建议机型 | 档位 |
|------|----------|------|
| iOS 16 | iPhone 12 | 2D |

### P3 — 不阻断发版

| 系统 | 建议机型 | 档位 |
|------|----------|------|
| iOS 15 | iPhone XS | 2d_smoke |

> **3D 建议最低**：iPhone 11 / A13 或 iPhone 12 / A14 起更稳。  
> **2D 轻量**：可下探 iPhone XS / XR / SE 2，但不作为发版门禁。

> **风险项**：iOS 17+ 依赖 tidevice 链路，**iOS 26 需 P0 真机专项验证**。

---

## 测试深度分层

```
L1 单元测试（CI 每次 PR，无真机）
  ├─ FPS Surface 命名 / API 策略（test_surface_by_api.py）
  ├─ CPU / Memory mock（test_apm_cpu_memory.py）
  └─ 联合验收交叉检查（test_joint_acceptance.py）

L2 集成测试（CI 每次 PR，无真机）
  └─ /apm/collect Flask 路由（test_apm_collect_api.py）

L3 设备实验室（发版前，P0 真机矩阵）
  └─ 3D 游戏 60s 全指标，fps_meta.confidence ≥ medium

L4 探索性（P2/P3，月度）
  └─ 2D smoke，记录 degraded
```

### 指标 × 版本敏感度

| 指标 | 敏感度 | L1 mock API | L3 P0 必测 |
|------|--------|-------------|------------|
| FPS | 高 | 28, 30, 31, 34, 36 | ✅ |
| CPU | 低 | 28, 30, 35 | ✅ |
| Memory | 低 | 30, 34, 35 | ✅ |
| Network | 中 | — | ✅ |
| GPU | 中（仅 Android） | — | 抽测 |
| Battery | 低 | — | 抽测 |
| Scrcpy | 中 | — | API 34/35 抽测 |

---

## Surface 命名与 API 对应关系

SoloX FPS 引擎（`android_fps.py`）按系统版本处理不同 Surface 格式：

| API 区间 | 典型 Surface 格式 | 示例 |
|----------|-------------------|------|
| 28–30 | `SurfaceView - pkg/Activity#N` | `SurfaceView - com.game/com.unity3d.player.UnityPlayerActivity#0` |
| 31–33 | `SurfaceView[pkg](BLAST)#N` | `SurfaceView[com.game](BLAST)#0` |
| 34–36 | `pkg/Activity#N`（可省略 SurfaceView 前缀） | `com.game/com.unity3d.player.UnityPlayerActivity#0` |
| ≤ 27 | page flip 兜底 | `service call SurfaceFlinger 1013` |

游戏引擎自动识别：Unity、Unreal Engine 4/5、Cocos2d-x/Creator、Laya。

---

## 发版前验收清单

### CI 自动项（必须通过）

```bash
pip install pyyaml pytest pytest-cov pytest-mock
python -m pytest tests/ -v
flake8 solox/ --count --select=E9,F63,F7,F82 --show-source --statistics
```

### 真机实验室项（P0 矩阵）

- [ ] Android API 33 / 34 / **35** / **36** 各 1 台，Unity 或 UE 3D 样本，FPS ≠ 0
- [ ] iOS **18** + **iOS 26** 各 1 台，FPS / CPU / Memory 正常
- [ ] `/apm/collect?target=fps` 返回 `fps_meta.confidence` ≥ `medium`
- [ ] 投屏 API 34/35 三档画质 smoke
- [ ] 报告分页 `/apm/report/list?page=1&size=20` 正常

---

## 相关文档

- [联合验收报告（研发/产品/测试）](./acceptance/joint-review-2026-compatibility.md)
- [L3 设备实验室清单](./acceptance/l3-device-lab-checklist.md)
- [FPS 游戏引擎采集](./01-architecture/technical-architecture.md) · [实施计划索引](./plans/README.md)
- [性能监控指南](./04-user-guides/performance-monitoring.md)
- [API 文档](./04-user-guides/api-documentation.md)
- [FAQ — FPS 为 0](./05-issues/faq.md)

---

*配置版本：schema_version 1 · 发版门禁：P0_all_pass*
