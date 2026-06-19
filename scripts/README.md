# SoloX 脚本

| 用途 | 命令 |
|------|------|
| 开发服务 | `bash scripts/dev.sh start\|stop\|status\|log` |
| 发版门禁 | `bash scripts/release_gate.sh` |
| 矩阵校验 | `python scripts/validate_compatibility_matrix.py` |
| 安装验证 | `python scripts/verify_setup.py` |
| 依赖安装 | `scripts/install_dependencies.sh` / `.ps1` |
| 打包 | `bash scripts/package.sh` |
| Android Agent 构建 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1` |
| Android Agent 打包 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/package.ps1` |
| Android Agent 验收 | `python scripts/android_agent/acceptance.py --device SERIAL --package PACKAGE --profile lte_weak --smoke` |

详见 [docs/06-engineering/project-layout.md](../docs/06-engineering/project-layout.md)。
