# runtime/

本地开发运行时目录。**除本 README 与 `.gitkeep` 外均不提交 Git。**

说明见 [docs/06-engineering/project-layout.md](../docs/06-engineering/project-layout.md)。

共享工具链约定：

- 推荐把 Android/Rust 共用工具链放在个人目录，例如 `%LOCALAPPDATA%\SoloX\toolchains\android-rust`。
- 如需在 `SoloX` 中启用共享工具链，设置 `SOLOX_SHARED_TOOLROOT` 指向该目录。
- 未设置或共享目录不完整时，当前项目继续回退到 `runtime/android-toolchain/`，保证现有仓库不受影响。
- `runtime/android-toolchain/` 仍保留为兼容模式，不要求立即迁移。
- 启用共享工具链后，Android Agent 的 Gradle 用户缓存保留在当前项目 `runtime/android-agent-gradle-user-home/`，避免共享目录中的本地缓存互相污染。

| 路径 | 用途 | Git |
|------|------|-----|
| `logs/` | `scripts/dev.sh start` 等服务日志 | 忽略内容，保留 `.gitkeep` |
| `pids/` | 开发服务 PID 文件 | 同上 |
| `cache/` | Android 应用名缓存（按设备） | 同上 |
| `android-toolchain/` | 项目内 Android/Rust 工具链兼容回退目录 | 忽略 |
| `android-agent-gradle-user-home/` | 共享工具链模式下的项目级 Gradle 缓存 | 忽略 |
| `*.py` | 个人临时启动脚本（如 `start_solox_service_50005.py`） | 忽略 |
| `*.log` | 验收/调试 stdout/stderr | 忽略 |

```bash
bash scripts/dev.sh start   # 日志 → logs/solox-dev.log
bash scripts/dev.sh stop
```

Windows：`./scripts/dev.ps1 start`（需 Git for Windows）。
