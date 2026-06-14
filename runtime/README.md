# runtime/

本地开发运行时目录。**除本 README 与 `.gitkeep` 外均不提交 Git。**

说明见 [docs/06-engineering/project-layout.md](../docs/06-engineering/project-layout.md)。

| 路径 | 用途 | Git |
|------|------|-----|
| `logs/` | `scripts/dev.sh start` 等服务日志 | 忽略内容，保留 `.gitkeep` |
| `pids/` | 开发服务 PID 文件 | 同上 |
| `cache/` | Android 应用名缓存（按设备） | 同上 |
| `*.py` | 个人临时启动脚本（如 `start_solox_service_50005.py`） | 忽略 |
| `*.log` | 验收/调试 stdout/stderr | 忽略 |

```bash
bash scripts/dev.sh start   # 日志 → logs/solox-dev.log
bash scripts/dev.sh stop
```

Windows：`.\scripts\dev.ps1 start`（需 Git for Windows）。
