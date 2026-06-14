# 公开发布前最终审核清单

**目标仓库**: [github.com/smart-test-ti/SoloX](https://github.com/smart-test-ti/SoloX)  
**审核日期**: 2026-06-13  
**结论**: ✅ **通过自动化门禁** · ⚠️ **L3 真机签字仍待 QA**（不阻断 push 公共仓库）

---

## 1. 自动化门禁（已通过）

| 检查 | 结果 | 证据 |
|------|------|------|
| 兼容矩阵 + L1 模块 | ✅ | `python scripts/validate_compatibility_matrix.py` |
| 全量单元/集成测试 | ✅ | 123 tests passed |
| setup.py 依赖锁定 | ✅ | `python scripts/verify_setup.py` |
| `/health` 探活 | ✅ | `GET /health` → `{status:1, version}` |

```bash
bash scripts/release_gate.sh
```

---

## 2. 仓库卫生（已通过）

| 项 | 状态 |
|----|------|
| 根目录无 `.log` / `err.txt` / 个人脚本残留 | ✅ 已清理 |
| `.gitignore` 覆盖 runtime/report/密钥/ffmpeg 二进制 | ✅ |
| `dev.ps1` 无本机绝对路径 | ✅ |
| Git 文档改为上游 Fork 工作流 | ✅ |
| 冗余 MD 已删除（system-design 等）；plans 保留中文过程文档 | ✅ |

---

## 3. 文档完整性（已通过）

| 文档 | 用途 |
|------|------|
| `docs/README.md` | 唯一入口 |
| `docs/06-engineering/release-and-dev-standards.md` | 本地开发 vs 线上发布 |
| `docs/06-engineering/project-layout.md` | 目录与日志 |
| `docs/compatibility-matrix.md` | 发版门禁 |
| `docs/acceptance/joint-review-2026-compatibility.md` | 三方验收 v2.3 |
| `CLAUDE.md` | 贡献者/AI 速查 |

---

## 4. 本地开发可用性（已通过）

| 步骤 | 验证 |
|------|------|
| 可编辑安装 | `pip install -e .` |
| 直接启动 | `python -m solox --port=50003` |
| 脚本启动 | `scripts/dev.sh start\|status\|stop` |
| 探活 | `curl http://127.0.0.1:50003/health` |
| 采集 API | 需连接真机：`/apm/collect?target=cpu` |

---

## 5. 线上发布差异提醒

| 风险 | 缓解 |
|------|------|
| 无 API 鉴权 | 内网部署或反向代理加认证 |
| 弱网需 Root | 文档与 UI 已说明 |
| Docker healthcheck 依赖 `/health` | 已实现 |
| PyPI 发布需 `PYPI_API_TOKEN` | 仅 CI secret，不入库 |

---

## 6. 推送 GitHub 前最后一遍

```bash
git status                    # 无 report/runtime 产物/.env/ffmpeg 二进制
bash scripts/release_gate.sh
git push origin main          # 或你的发布分支
```

**禁止 push**：`.env`、`.solox.log`、`report/`、`.claude/`、个人 `err.txt`。

---

## 7. 签字

| 角色 | 发布公共仓库 | 日期 |
|------|--------------|------|
| 研发 | ☐ | |
| 测试 | ☐ | |
| 维护者 | ☐ | |

---

*维护规范: [release-and-dev-standards.md](./release-and-dev-standards.md)*
