# SoloX 脚本索引

本目录包含开发、发版、打包与弱网/Android Agent 相关脚本。日志与 PID 写入 `runtime/`（见 [runtime/README.md](../runtime/README.md)）。

## 日常开发

 用途 | Linux / macOS / Git Bash | Windows PowerShell |
|------|--------------------------|-------------------|
| 启动/停止/状态 | `bash scripts/dev.sh start\|stop\|status\|log\|fg` | `.\scripts\dev.ps1 start\|stop\|status\|log\|fg` |
| 安装依赖 | `bash scripts/install_dependencies.sh` | `.\scripts\install_dependencies.ps1` |
| 安装依赖（含 dev/test） | `python scripts/install_dependencies.py --dev` | `.\scripts\install_dependencies.ps1 -Dev` |
| 验证 setup.py 版本 | `python scripts/verify_setup.py` | 同左 |
| 发版门禁 | `bash scripts/release_gate.sh` | `.\scripts\release_gate.ps1` |
| 兼容矩阵 | `python scripts/validate_compatibility_matrix.py` | 同左 |
| 打包 wheel/sdist | `bash scripts/package.sh` | 同左（需 Git Bash 或 WSL） |
| Headless 采集/分析 CLI | `python -m solox.cli collect --device <id> --pkg <pkg> --duration 60` | 同左 |
| 报告分析（离线规则引擎） | `python -m solox.cli analyze --scene <apm_dir>` | 同左 |
| 报告回归对比 | `python -m solox.cli compare --base <a> --target <b>` | 同左 |
| MCP 服务（可选，需 `pip install "mcp>=1.0"`） | `python -m solox.mcp.server` | 同左 |

**Windows 说明：** 请勿在 PowerShell 中直接运行 `bash scripts/dev.sh`（可能进入 WSL 且找不到 Python），应使用 `.\scripts\dev.ps1`。

## 脚本说明

| 文件 | 说明 |
|------|------|
| `dev.sh` | 开发服务主逻辑（中文化输出、/health 探活） |
| `dev.ps1` | Windows 薄包装：Git Bash + Python 路径 + 默认 127.0.0.1:50003 |
| `install_dependencies.py` | **依赖安装核心**（`requirements.txt`，可选 `-Dev`） |
| `install_dependencies.sh` / `.ps1` | 调用 `install_dependencies.py` 的入口 |
| `release_gate.sh` / `.ps1` | 发版门禁：verify_setup → 兼容矩阵 → pytest |
| `verify_setup.py` | 校验 setup.py 关键依赖版本 |
| `validate_compatibility_matrix.py` | 校验 `tests/compatibility_matrix.yaml` |
| `package.sh` | `python -m build` 构建 dist |
| `benchmark_report_api.py` | 报告 API 性能基准（开发调优用） |
| `lib/git_bash.ps1` | Windows 共享：定位 Git Bash |
| `lib/python.ps1` | Windows 共享：解析可执行的 Python 路径 |

## Android Agent / 弱网（可选）

| 用途 | 命令 |
|------|------|
| 工具链准备 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/bootstrap.ps1` |
| 共享工具链 | `$env:SOLOX_SHARED_TOOLROOT='<path>'; … bootstrap.ps1` |
| 构建 | `… -File scripts/android_agent/build.ps1` |
| 打包 APK | `… -File scripts/android_agent/package.ps1` |
| 真机验收 | `python scripts/android_agent/acceptance.py --device SERIAL --package PKG --profile lte_weak --smoke` |
| Linux 网关校准 | `scripts/weaknet_gateway/*.sh`（见该目录 README） |

共享工具链：设置 `SOLOX_SHARED_TOOLROOT` 后优先使用共享目录；不完整时回退 `runtime/android-toolchain/`。

## 环境变量

| 变量 | 用途 | 默认 |
|------|------|------|
| `SOLOX_HOST` | 监听地址 | `0.0.0.0`（dev.ps1 默认 `127.0.0.1`） |
| `SOLOX_PORT` | 端口 | `50003`（50003 占用时 dev.ps1 用 `50005`） |
| `SOLOX_PYTHON` | Python 可执行文件 | `python` / `python3` |
| `GIT_BASH` | 指定 Git Bash 路径 | 自动探测 |
| `SOLOX_SHARED_TOOLROOT` | Android Agent 共享工具链根目录 | 无 |

## 与 Makefile 对应

```bash
make install-dev    # pip install -e ".[dev,test]"
make release-gate   # bash scripts/release_gate.sh
make verify         # python scripts/verify_setup.py
make matrix         # python scripts/validate_compatibility_matrix.py
```

详见 [docs/06-engineering/project-layout.md](../docs/06-engineering/project-layout.md)。
