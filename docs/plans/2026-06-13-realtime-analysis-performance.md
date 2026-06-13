# SoloX 实时采集与分析性能实施计划

> 每项先补失败测试，再做最小实现，完成后运行聚焦回归。

**关联设计：** [实时采集与分析性能设计](./2026-06-13-realtime-analysis-performance-design.md)

### 任务 1：建立失败测试与静态契约

**文件：**
- 新增：`tests/test_frontend_performance.py`
- 新增：`tests/test_performance_telemetry.py`
- 修改：`tests/test_report_management.py`

覆盖实时 timer 隔离、页面隐藏暂停、分析页并发队列、compare/pk 参数透传和遥测快照。

### 任务 2：实时采集调度

**文件：**
- 修改：`solox/templates/index.html`

引入 `metricTimers`、`scheduleMetricPoll`、`clearAllMetricTimers`，替换共享 timer 和立即调用写法。

### 任务 3：compare/pk 降采样

**文件：**
- 修改：`solox/public/common.py`
- 修改：`solox/view/apis.py`
- 修改：`solox/view/pages.py`
- 修改：`solox/templates/analysis_compare.html`
- 修改：`solox/templates/analysis_pk.html`

将 `max_points` 从页面传到 API，再传到所有日志读取函数；API 仅对显式正数参数降采样，缺失或非法参数保持旧客户端全量行为。

### 任务 4：分析页并发队列

**文件：**
- 修改：`solox/templates/analysis.html`

最大同时执行 3 个图表初始化请求，并保持现有任务顺序。

### 任务 5：性能遥测

**文件：**
- 新增：`solox/public/performance_telemetry.py`
- 修改：`solox/public/adb.py`
- 修改：`solox/view/apis.py`

记录 API 与 ADB 的有界运行时统计，暴露诊断端点和响应耗时头。

### 任务 6：验收

```powershell
python -m pytest tests/test_frontend_performance.py tests/test_performance_telemetry.py tests/test_report_management.py -q
python -m pytest -q
python scripts/validate_compatibility_matrix.py
python -m compileall solox
```

启动本地服务后，用浏览器确认首页和分析页无控制台错误，并检查 `/apm/telemetry`。
