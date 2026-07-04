# SoloX 脚本

| 用途 | 命令 |
|------|------|
| 开发服务 | `bash scripts/dev.sh start\|stop\|status\|log` |
| 发版门禁 | `bash scripts/release_gate.sh` |
| 矩阵校验 | `python scripts/validate_compatibility_matrix.py` |
| 安装验证 | `python scripts/verify_setup.py` |
| 依赖安装 | `scripts/install_dependencies.sh` / `.ps1` |
| Android Agent 工具链准备 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/bootstrap.ps1` |
| Android Agent 共享工具链准备 | `$env:SOLOX_SHARED_TOOLROOT='<shared-root>'; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/bootstrap.ps1` |
| Android Agent 构建 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/build.ps1` |
| Android Agent 打包 | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/android_agent/package.ps1` |
| Android Agent 验收 | `python scripts/android_agent/acceptance.py --device SERIAL --package PACKAGE --profile lte_weak --smoke` |
| 打包 | `bash scripts/package.sh` |

共享工具链说明：

- 设置 `SOLOX_SHARED_TOOLROOT` 后，Android Agent 相关脚本优先使用该目录。
- 若共享目录不完整，脚本会自动回退到 `runtime/android-toolchain/`。
- 启用共享工具链时，Gradle 用户缓存使用当前项目 `runtime/android-agent-gradle-user-home/`。
- 推荐个人开发机使用 `%LOCALAPPDATA%\SoloX\toolchains\android-rust` 作为共享根目录。

详见 [docs/06-engineering/project-layout.md](../docs/06-engineering/project-layout.md)。
