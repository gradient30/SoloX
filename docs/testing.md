# 测试专用文档

## 1. 自动化测试集成

### 1.1 CI/CD 集成

SoloX 提供了 Python API，可以轻松集成到 CI/CD 流程中：

```python
import time
from solox.public.apm import AppPerformanceMonitor

def performance_test_in_ci():
    """在CI环境中运行性能测试的示例"""
    apm = AppPerformanceMonitor(
        pkgName='com.example.app',
        platform='Android',
        deviceId='emulator-5554',
        duration=60  # 运行60秒
    )
    
    # 收集所有性能指标
    apm.collectAll(report_path='./reports/performance_report.html')
    
    # 可以进一步分析报告或设置性能阈值检查
```

### 1.2 性能基准测试

```python
import time
from solox.public.apm import AppPerformanceMonitor

def baseline_performance_test():
    """建立性能基准测试"""
    # 第一次运行建立基准
    apm = AppPerformanceMonitor(
        pkgName='com.example.app',
        platform='Android',
        collect_all=True,
        duration=120
    )
    
    # 收集基准数据
    apm.collectAll(report_path='./reports/baseline.html')
```

## 2. 测试场景模板

### 2.1 启动性能测试

```python
import time
from solox.public.apm import AppPerformanceMonitor

def startup_performance_test():
    """应用启动性能测试"""
    apm = AppPerformanceMonitor(
        pkgName='com.example.app',
        platform='Android',
        # 配置启动测试特定参数
    )
    
    # 冷启动测试
    # 1. 杀掉应用
    # 2. 开始性能收集
    apm.collectAll(duration=30)  # 收集30秒内的数据
```

### 2.2 内存泄漏测试

```python
import time
from solox.public.apm import AppPerformanceMonitor

def memory_leak_test():
    """长时间运行以检测内存泄漏"""
    apm = AppPerformanceMonitor(
        pkgName='com.example.app',
        platform='Android',
        collect_all=True,
        duration=3600  # 运行1小时
    )
    
    apm.collectAll(report_path='./reports/memory_leak_test.html')
```

### 2.3 GPU 性能测试

```python
import time
from solox.public.apm import AppPerformanceMonitor

def gpu_performance_test():
    """GPU性能专项测试"""
    apm = AppPerformanceMonitor(
        pkgName='com.example.game',  # 游戏应用
        platform='Android',
        duration=180
    )
    
    # 专门收集GPU数据
    gpu_data = apm.collectGpu()
    return gpu_data
```

## 3. 多设备并行测试

### 3.1 并行设备管理

```python
import time
import threading
from solox.public.apm import AppPerformanceMonitor
from solox.public.common import Devices

def parallel_device_testing():
    """多设备并行测试示例"""
    d = Devices()
    device_ids = d.getDeviceIds()
    
    def test_on_device(device_id):
        apm = AppPerformanceMonitor(
            pkgName='com.example.app',
            platform='Android',
            deviceId=device_id,
            duration=300
        )
        apm.collectAll(report_path=f'./reports/device_{device_id}_report.html')
    
    # 为每个设备启动一个线程
    threads = []
    for device_id in device_ids:
        t = threading.Thread(target=test_on_device, args=(device_id,))
        threads.append(t)
        t.start()
    
    # 等待所有测试完成
    for t in threads:
        t.join()
```

## 4. 性能阈值验证

### 4.1 设置和检查性能阈值

```python
import time
from solox.public.apm import AppPerformanceMonitor

def performance_threshold_validation():
    """性能阈值验证"""
    apm = AppPerformanceMonitor(
        pkgName='com.example.app',
        platform='Android',
        duration=60
    )
    
    # 收集性能数据
    cpu_data = apm.collectCpu()
    memory_data = apm.collectMemory()
    fps_data = apm.collectFps()
    
    # 定义性能阈值
    thresholds = {
        'cpu': 50.0,      # CPU使用率不超过50%
        'memory': 500.0,  # 内存使用不超过500MB
        'fps': 55.0       # FPS不低于55Hz
    }
    
    # 验证阈值
    if cpu_data > thresholds['cpu']:
        raise Exception(f"CPU使用率超出阈值: {cpu_data}%")
    
    if memory_data > thresholds['memory']:
        raise Exception(f"内存使用超出阈值: {memory_data}MB")
    
    if fps_data < thresholds['fps']:
        raise Exception(f"FPS低于阈值: {fps_data}Hz")
```

## 5. 测试报告自动化分析

### 5.1 报告数据提取

```python
import time
import json
import os

def analyze_performance_report(report_path):
    """分析性能测试报告"""
    # 从报告中提取关键指标
    # 这里是示例逻辑，实际实现取决于报告格式
    
    # 检查报告是否存在
    if not os.path.exists(report_path):
        raise FileNotFoundError(f"报告文件不存在: {report_path}")
    
    # 解析报告并提取数据
    # 返回分析结果
    analysis_result = {
        'report_path': report_path,
        'analysis_time': time.time(),
        'findings': []
    }
    
    return analysis_result
```

## 6. 特定场景测试

### 6.1 网络条件测试

```python
import time
from solox.public.apm import AppPerformanceMonitor

def network_condition_test():
    """网络条件下的性能测试"""
    apm = AppPerformanceMonitor(
        pkgName='com.example.app',
        platform='Android',
        duration=120
    )
    
    # 在不同网络条件下测试应用性能
    # 可以结合网络模拟工具使用
    
    network_data = apm.collectNetwork()
    return network_data
```

### 6.2 电池性能测试

```python
import time
from solox.public.apm import AppPerformanceMonitor

def battery_performance_test():
    """电池性能测试"""
    apm = AppPerformanceMonitor(
        pkgName='com.example.app',
        platform='Android',
        duration=600  # 长时间测试
    )
    
    # 收集电池数据
    battery_data = apm.collectBattery()
    return battery_data
```

## 7. 测试数据后处理

### 7.1 数据聚合和分析

```python
import time

def aggregate_test_data(test_results):
    """聚合多次测试结果"""
    aggregated_data = {
        'cpu': {
            'min': min([r['cpu'] for r in test_results]),
            'max': max([r['cpu'] for r in test_results]),
            'avg': sum([r['cpu'] for r in test_results]) / len(test_results)
        },
        'memory': {
            'min': min([r['memory'] for r in test_results]),
            'max': max([r['memory'] for r in test_results]),
            'avg': sum([r['memory'] for r in test_results]) / len(test_results)
        },
        'fps': {
            'min': min([r['fps'] for r in test_results]),
            'max': max([r['fps'] for r in test_results]),
            'avg': sum([r['fps'] for r in test_results]) / len(test_results)
        }
    }
    
    return aggregated_data
```

## 8. 测试最佳实践

### 8.1 测试环境标准化

1. **设备标准化**: 使用相同型号和系统版本的设备进行测试
2. **环境清理**: 测试前清理后台应用和缓存
3. **网络环境**: 确保稳定的网络连接或使用模拟网络条件
4. **电量管理**: 保持设备电量充足（建议>50%）

### 8.2 测试执行建议

1. **预热**: 测试前先运行应用一段时间以达到稳定状态
2. **多次运行**: 同一测试场景建议多次运行取平均值
3. **数据保存**: 保存所有原始测试数据以便后续分析
4. **异常处理**: 实现适当的异常处理机制

### 8.3 测试报告要求

1. **完整性**: 报告应包含所有关键性能指标
2. **可读性**: 提供图表和数据表格两种展示方式
3. **可追溯性**: 记录测试环境、设备信息和应用版本
4. **对比性**: 支持与历史数据或基准数据进行对比

## 9. 常见测试用例

### 9.1 首屏加载测试

测试应用从启动到首屏完全加载的性能表现。

### 9.2 列表滑动测试

测试列表快速滑动时的流畅性和资源占用情况。

### 9.3 图片加载测试

测试大量图片加载时的内存和网络表现。

### 9.4 视频播放测试

测试视频播放时的CPU、内存和电池消耗情况。

### 9.5 网络请求测试

测试不同网络条件下应用的响应时间和稳定性。