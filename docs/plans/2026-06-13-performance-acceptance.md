# SoloX 性能验收实施计划

> **执行说明：** 按任务逐步实施；每项先写失败测试，再最小实现，最后跑聚焦回归。

**目标：** 消除报告 API 与页面加载中的可避免开销，同时保留全部现有业务行为。

**架构：** 保持 Flask 路由与 `File` 接口不变。用可调用对象分发替代指标预计算；用直接路径检查替代目录成员扫描；报告列表改为单次 `scandir` 扫描。

**技术栈：** Python 3.10+、Flask 2.0.3、pytest/unittest、标准库文件 API。

---

### 任务 1：惰性指标分发

**涉及文件：**
- 修改：`tests/test_report_management.py`
- 修改：`solox/view/apis.py`

**步骤 1：编写失败测试**

新增 API 测试： mock 全部指标 getter，请求 `target=cpu`，断言**仅** `getCpuLog` 被调用。

**步骤 2：运行测试确认失败**

```bash
python -m pytest tests/test_report_management.py::TestLogApiPerformance -q
```

预期：**FAIL** — 当前会评估全部 metric getter。

**步骤 3：最小实现**

将绑定方法存入 target 映射，只调用所选方法：

```python
handlers = {
    'cpu': f.getCpuLog,
    # 其余已有 target
}
result = handlers[target](platform, scene, max_points)
```

**步骤 4：运行聚焦测试**

```bash
python -m pytest tests/test_report_management.py tests/test_joint_acceptance.py -q
```

预期：**PASS**。

### 任务 2：分析页直接报告查找

**涉及文件：**
- 修改：`tests/test_report_management.py`
- 修改：`solox/view/pages.py`

**步骤 1：编写失败测试**

Mock `os.listdir` 使其失败，验证 `/analysis` 与 `/pk_analysis` 仍能通过直接路径检查加载已有报告。

**步骤 2：运行测试确认失败**

```bash
python -m pytest tests/test_report_management.py::TestAnalysisLookupPerformance -q
```

预期：**FAIL** — 两路由当前均调用 `os.listdir`。

**步骤 3：最小实现**

加载报告数据前使用 `os.path.isdir(os.path.join(report_dir, scene))` 判断。

**步骤 4：运行聚焦测试**

```bash
python -m pytest tests/test_report_management.py -q
```

预期：**PASS**。

### 任务 3：报告列表单次扫描

**涉及文件：**
- 修改：`tests/test_report_management.py`
- 修改：`solox/view/apis.py`

**步骤 1：编写失败测试**

创建报告目录与无关文件，断言仅统计目录、按修改时间排序且分页正确。

**步骤 2：运行测试确认失败**

```bash
python -m pytest tests/test_report_management.py::TestReportListPerformance -q
```

预期：**FAIL** — 无扩展名普通文件当前可能被计入 total。

**步骤 3：最小实现**

使用 `os.scandir`，仅保留 `entry.is_dir()`，按 `entry.stat().st_mtime` 排序后分页名称。

**步骤 4：运行聚焦测试**

```bash
python -m pytest tests/test_report_management.py tests/test_joint_acceptance.py -q
```

预期：**PASS**。

### 任务 4：基准与联合验收

**涉及文件：**
- 修改：`docs/acceptance/joint-review-2026-compatibility.md`

**步骤 1：运行合成优化前后基准**

```bash
python scripts/benchmark_report_api.py --lines 20000 --repeats 3
```

对比优化前「全量预加载」与「仅目标加载」：记录响应一致性、耗时与峰值跟踪内存。

**步骤 2：运行全量回归**

```bash
python -m pytest -q
```

预期：全部测试通过。

**步骤 3：运行发版门禁**

```bash
python scripts/validate_compatibility_matrix.py
```

预期：发版就绪校验通过。

**步骤 4：记录验收结果**

在联合验收报告中记录根因、实现、实测结果、自动化用例数及剩余真机风险。

---

*状态：✅ 已于 v2.4 联合验收完成 · 详见 [方案设计](./2026-06-13-performance-acceptance-design.md)*
