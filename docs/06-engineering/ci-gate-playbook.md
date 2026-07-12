# CI 门禁排查手册

面向 `.github/workflows/ci.yml` 与本地发版门禁的对照记录。  
**目的**：归纳已验证的修复方案，避免同类问题在 test / build / 平台政策层反复出现。

**适用范围**：SoloX 主仓库 GitHub Actions；本地等价命令见 [release-and-dev-standards.md](./release-and-dev-standards.md)。

**最后更新**：2026-07-12 · **基线 commit**：`be63dc1` 及此前 CI 修复链

---

## 1. Pipeline 结构与认知

CI 不是单一「测试 job」，而是多层 **gate**。前面一层失败时，后面一层往往**从未执行**，因此会感觉「修这里才暴露那里」——属于 pipeline 成熟度爬升，不一定是回归。

```text
push / PR
  ├─ test（矩阵 7 job：Linux/Windows × 3.10/3.11/3.12 + macOS × 3.11）
  ├─ dependency-check（并行）
  ├─ documentation（并行，校验必需文档/脚本存在）
  ├─ build（needs: test）→ python -m build + upload-artifact@v4
  ├─ docker（needs: test，continue-on-error）
  └─ publish（release 事件，needs: test + build）
```

| 结论 | 说明 |
|------|------|
| test 全绿 ≠ CI 全绿 | `build`、`documentation`、GitHub Actions 弃用策略是独立 gate |
| 本地 pytest 通过不够 | 还需 `python -m build`、脚本 UTF-8、flake8 |
| macOS 仅冒烟 | runner 稀缺 + fork 风险，矩阵只保留 Python 3.11 |

---

## 2. 问题登记与已验证方案

| # | 现象 | 根因 | 标准方案 | 关联 commit |
|---|------|------|----------|-------------|
| 1 | flake8 失败 | 未使用 `global`；正则未用 raw string | 删除多余 `global`；正则改为 `r"..."` | `0eeaf52` |
| 2 | iOS/Java 相关测试 fail | CI 无 JDK / 无 pymobiledevice3 | `java_toolchain_available()` + `pytest.importorskip` / `@pytest.mark.skipif` | `3c52d83` |
| 3 | Linux 上 Windows 专属测试 fail | 假设 Windows 控制台/进程语义 | `@pytest.mark.skipif(sys.platform != "win32")` | `bbe18a9` |
| 4 | mock 子进程 AttributeError | Fake 未实现完整 `Popen` 协议 | 补全 `__enter__`/`__exit__` 等上下文管理器 | `a741f06` |
| 5 | Linux 录屏测试异常 | mock `Popen` 仍触发 `platform.architecture()` | mock 时固定 `Scrcpy.scrcpy_path()` | `40aaf79` |
| 6 | Windows runner 脚本 UnicodeEncodeError | stdout 默认 CP1252，脚本含中文/emoji | 脚本入口 `stdout.reconfigure(encoding="utf-8")` | `d876598`, `714fde5` |
| 7 | macOS 路径断言 fail | `/var` resolve 为 `/private/var` | 断言前 `os.path.realpath()` | `8aba397` |
| 8 | macOS pytest 挂 40+ 分钟 | fork + PIL/Objective-C + pytest-cov 死锁 | macOS 矩阵仅 3.11；`OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`；`--timeout=180`；job `timeout-minutes: 25` | `804b4e4` |
| 9 | Windows job 180s 超时 | `setUp` 调真实 `WeakNetworkManager.clear()` → adb 阻塞 | **setUp/tearDown 只清内存状态**；单测内 `@patch` adb | `8220a75` |
| 10 | workflow 直接 fail | GitHub 禁用 `actions/upload-artifact@v3` | 升级到 `@v4` | `90a2236` |
| 11 | `python -m build`：`No module named 'solox'` | `setup.py` 在 PEP 517 隔离环境 `import solox` | `setup.py` 最小 stub；元数据/依赖以 `pyproject.toml` 为准；`packages.find` 含 `solox*` | `be63dc1` |
| 12 | 本地 `?? solox/_version.py` | `setuptools_scm` 构建时生成 | **不提交**；`.gitignore` 忽略 | `.gitignore` |

---

## 3. 分类标准方案（新增代码时必须遵守）

### 3.1 单测：CI 无真机、无 root

**禁止**在 `setUp` / `tearDown` / 模块 import 时调用会走 adb、subprocess、网络的 API。

```python
# ❌ 错误
def setUp(self):
    WeakNetworkManager.clear("dev1")

# ✅ 正确
def setUp(self):
    import solox.public.weak_network as wn
    wn._active.clear()
    wn._active_engines.clear()
```

需要 adb 的路径一律 `@patch("solox.public.weak_network.adb.shell")` 或 `@patch.object(..., "_run_root")`。

**参考**：`tests/test_weak_network.py` → `TestWeakNetApplyClear`；对比 `TestWeakNetEngineSelection.setUp`。

### 3.2 跨平台：显式 skip，禁止隐式假设

| 场景 | 标准方案 |
|------|----------|
| Windows 控制台/编码 | `skipif(not win32)` 或脚本强制 UTF-8 stdout |
| macOS 路径 | `os.path.realpath()` 后再断言 |
| 可选依赖（JDK、pmd3、ffmpeg） | `importorskip` / `skipif` → **缺依赖 = skip，不是 fail** |
| mock 子进程 | Fake 实现完整协议（含 context manager） |

### 3.3 macOS CI 约束

1. **矩阵**：`macos-latest` 仅 Python **3.11**（见 `ci.yml` matrix `include`）。
2. **fork 安全**：在 import `solox`（经 apm → iosperf → PIL）**之前**设置环境变量：
   - `tests/conftest.py`：`OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`
   - `ci.yml` test step 同名 `env`
3. **超时**：`pytest --timeout=180`（需 `pytest-timeout`）；job 级 `timeout-minutes: 25`。

### 3.4 Windows / 脚本输出编码

凡被 CI 直接执行的脚本（`scripts/verify_setup.py`、`scripts/validate_compatibility_matrix.py` 等），若含中文或 emoji：

```python
def configure_utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass
```

**回归测试**：`tests/test_verify_setup_script.py`（CP1252 环境子进程调用）。

### 3.5 打包（PEP 517）

| 规则 | 说明 |
|------|------|
| `setup.py` 不 import 本包 | 隔离 build 时包尚不存在 |
| 依赖锁定源 | `pyproject.toml` → `[project].dependencies` |
| 依赖校验 | `python scripts/verify_setup.py` 解析 **pyproject.toml**（非 setup.py） |
| 子包 | `[tool.setuptools.packages.find]`，`include = ["solox*"]` |
| `solox/_version.py` | setuptools_scm 构建产物，**gitignore，不提交** |
| 本地验证 | `pip install build && python -m build` |

### 3.6 GitHub Actions 平台政策

- 关注 [GitHub Changelog](https://github.blog/changelog/)（artifact、Node、runner 镜像弃用）。
- 第三方 action 优先 `@v4` 等当前支持版本；避免已标记 deprecated 的版本。
- **test 绿了务必看 build / documentation job**。

---

## 4. 发版前自检清单

与 [pre-publish-checklist.md](./pre-publish-checklist.md) 配合使用：

```bash
# 1. 依赖与矩阵
python scripts/verify_setup.py
python scripts/validate_compatibility_matrix.py

# 2. 静态检查
flake8 solox/ --count --select=E9,F63,F7,F82 --show-source --statistics

# 3. 测试（建议本地也装 pytest-timeout）
python -m pytest tests/ -q

# 4. 打包（易在 CI 才暴露）
pip install build
python -m build

# 5. 仓库卫生
git status   # 不应有 solox/_version.py、dist/、build/ 等待提交项

# 6. （改录屏链路时）真机录屏验收
# SOLOX_RECORD_ACCEPT=1 bash scripts/release_gate.sh
# 或: python scripts/accept_record_gate.py --validate-only report/apm_*/record.mp4
```

**新增单测/code review 必问**：

- [ ] `setUp`/`tearDown` 是否调用了 adb / 真实 subprocess？
- [ ] 是否假设特定 OS 而未 `skipif`？
- [ ] 可选依赖缺失时是 skip 还是 fail？
- [ ] 脚本是否能在 Windows CP1252 stdout 下运行？
- [ ] workflow 是否使用已弃用 action 版本？

---

## 5. 当前稳定配置摘要

| 项 | 值 |
|----|-----|
| 测试矩阵 | `ubuntu-latest` / `windows-latest` × 3.10/3.11/3.12；`macos-latest` × 3.11 |
| pytest | `--timeout=180`，依赖 `pytest-timeout` |
| 覆盖率 | `--cov=solox`，Codecov `fail_ci_if_error: false` |
| artifact | `actions/upload-artifact@v4`，name=`dist` |
| 版本 | `setuptools_scm` → `solox/_version.py`（构建时）；运行时 `solox/__init__.py` 仍维护展示版本 |

---

## 6. 相关文件索引

| 文件 | 用途 |
|------|------|
| `.github/workflows/ci.yml` | CI 定义 |
| `pyproject.toml` | 依赖锁定、打包、setuptools_scm |
| `setup.py` | PEP 517 兼容 stub（`setuptools.setup()`） |
| `scripts/verify_setup.py` | 关键依赖版本门禁 |
| `scripts/release_gate.sh` | 本地发版门禁（可选 `SOLOX_RECORD_ACCEPT=1` 录屏步） |
| `scripts/accept_record_gate.py` | 录屏真机验收 / `--validate-only` |
| `tests/conftest.py` | macOS fork 安全、Flask fixtures |
| `tests/test_weak_network.py` | 弱网单测 mock 范例 |
| `tests/test_verify_setup_script.py` | 脚本 UTF-8 回归 |

---

## 7. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-12 | 初版：汇总 2026-07 CI 全绿攻坚（test/build/platform 共 12 类问题） |
| 2026-07-12 | 补充 P2-T2：`SOLOX_RECORD_ACCEPT` 录屏真机门禁 |

---

*关联: [本地开发 vs 线上发布](./release-and-dev-standards.md) · [预发布审核清单](./pre-publish-checklist.md) · [项目目录](./project-layout.md)*
