# 本地开发 vs 线上发布维护规范

面向公开发布至 [smart-test-ti/SoloX](https://github.com/smart-test-ti/SoloX) 的协作约定。

## 环境对照

| 维度 | 本地开发 | 线上 / CI / 发版 |
|------|----------------|---------------------------|
| **目的** | 功能开发、真机联调 | 公共仓库、PyPI、Docker 用户 |
| **安装** | `pip install -e ".[dev,test]"` | `pip install solox` 或 `pip install -r requirements.txt` |
| **启动** | `python -m solox` 或 `bash scripts/dev.sh start` | `python -m solox --host=0.0.0.0 --port=50003` / Docker |
| **日志** | `runtime/logs/solox-dev.log` | 容器 stdout / 系统 journal |
| **报告数据** | `./report/`（gitignore） | 挂载卷或外部存储，**勿提交 Git** |
| **端口** | 默认 `50003`，可 `SOLOX_PORT` | 同左；生产前加反向代理与防火墙 |
| **依赖** | 可装 pytest/flake8 | **仅** `requirements.txt` / `pyproject.toml` 锁定版本 |
| **门禁** | `bash scripts/release_gate.sh` | GitHub Actions `.github/workflows/ci.yml` |

## 本地开发标准流程

```bash
# 1. 环境
python --version          # >= 3.10
adb devices             # Android 联调

# 2. 安装
pip install -e ".[dev,test]"

# 3. 验证
python scripts/verify_setup.py
python scripts/validate_compatibility_matrix.py
python -m pytest tests/ -q --disable-warnings
pip install build && python -m build   # 与 CI build job 对齐

# 4. 启动（二选一）
python -m solox
# 或后台 + 日志
bash scripts/dev.sh start
bash scripts/dev.sh status    # 含 HTTP /health 探活

# 5. 停止
bash scripts/dev.sh stop
```

Windows：`.\scripts\dev.ps1 start`（需 Git for Windows）。

## 禁止提交 Git 的内容

已在 `.gitignore` 覆盖，发布前自查：

- `runtime/logs/`、`runtime/pids/`、`runtime/cache/`（仅 `.gitkeep` 入库）
- `runtime/*.py`（个人临时启动脚本，如 `start_solox_service_50005.py`）
- `solox/public/ffmpeg/bin/`（本地 ffmpeg 二进制；可用 `SOLOX_FFMPEG` 或 PATH）
- 根目录 `.solox.*`
- `report/`、`adblog/`、`solox/logs/`
- `.env`、`.venv/`、`.claude/`、`err.txt`
- `build/`、`dist/`、`*.egg-info/`、`.pytest_cache/`
- `solox/_version.py`（setuptools_scm 构建时生成，勿提交）

## 公开发布前检查清单

| # | 项 | 命令 / 方法 |
|---|-----|-------------|
| 1 | 发版门禁全绿 | `bash scripts/release_gate.sh` |
| 2 | 无个人路径/账号 | 勿含 `D:\workDir\`、私人 fork 硬编码 |
| 3 | 无密钥 | 无 token、密码、`.env` 入库 |
| 4 | 文档入口统一 | 从 `docs/README.md` 可到达 API、验收、工程化 |
| 5 | Docker 健康检查 | `GET /health` 返回 `status: 1` |
| 6 | Shell 脚本 LF 行尾 | `.gitattributes` → `*.sh eol=lf` |
| 7 | 依赖版本锁定 | Flask 2.0.3 等与 `verify_setup.py` / `pyproject.toml` 一致 |
| 8 | 打包可构建 | `python -m build`（见 [CI 门禁排查手册](./ci-gate-playbook.md)） |
| 9 | L3 真机（发版） | [L3 清单](../acceptance/l3-device-lab-checklist.md) P0 签字 |

## CI 与本地对齐

GitHub Actions `ci.yml` 与本地门禁一致：

1. `python scripts/verify_setup.py`
2. `flake8`（E9/F63/F7/F82）
3. `python scripts/validate_compatibility_matrix.py`
4. `pytest tests/ -v --cov=solox --timeout=180`
5. `python -m build`（build job）

本地快速等价：`bash scripts/release_gate.sh`（不含 flake8/coverage/build 时可单独跑）。

CI 问题排查与历史修复方案见 [CI 门禁排查手册](./ci-gate-playbook.md)。

## 线上部署注意

- 绑定 `0.0.0.0` 时限制网络访问（内网/VPN/防火墙）
- SoloX **无内置鉴权**；公网暴露需 Nginx 认证或 IP 白名单
- 远程访问模式（前端 Host 代理）仅建议实验室内网
- 参考 [部署指南](../03-deployment/deployment-guide.md) 与根目录 `docker-compose.yml`

## 版本与 CHANGELOG

- 用户可见变更写入根目录 `CHANGELOG.md`
- 联合验收重大版本更新 `docs/acceptance/joint-review-*.md`

---

*关联: [项目目录](./project-layout.md) · [CI 门禁排查手册](./ci-gate-playbook.md) · [联合验收](../acceptance/joint-review-2026-compatibility.md) · [预发布审核](./pre-publish-checklist.md)*

*最后更新: 2026-07-12*
