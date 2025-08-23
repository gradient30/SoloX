# 开发指南

## 🛠️ 开发环境搭建

### 1. 克隆项目

```bash
git clone https://github.com/smart-test-ti/SoloX.git
cd SoloX
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 安装开发依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装开发工具 (可选)
pip install pytest pytest-cov black flake8 mypy
```

### 4. 配置开发环境

```bash
# 设置 PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 或在 IDE 中配置项目根目录为源码目录
```

## 📁 项目结构详解

```
solox/
├── __init__.py              # 包初始化和版本信息
├── __main__.py              # 命令行入口点
├── web.py                   # 生产环境 Web 服务
├── debug.py                 # 开发调试 Web 服务
├── public/                  # 核心业务逻辑
│   ├── __init__.py
│   ├── apm.py              # 性能监控核心模块
│   ├── apm_pk.py           # 对比测试模块
│   ├── common.py           # 公共工具和设备管理
│   └── scrcpy/             # 屏幕录制工具
├── view/                    # Web 视图层
│   ├── __init__.py
│   ├── apis.py             # RESTful API 路由
│   └── pages.py            # Web 页面路由
├── templates/               # Jinja2 HTML 模板
│   ├── index.html          # 主页面
│   ├── 404.html            # 404 错误页
│   └── 500.html            # 500 错误页
├── static/                  # 静态资源
│   ├── css/                # 样式文件
│   ├── js/                 # JavaScript 文件
│   └── images/             # 图片资源
└── __pycache__/            # Python 字节码缓存
```

## 🔧 开发模式启动

### 调试模式

```bash
# 进入 solox 目录
cd solox

# 启动调试服务 (自动重载)
python debug.py

# 或指定参数
python debug.py --host=0.0.0.0 --port=5000
```

### 生产模式

```bash
# 使用生产配置启动
python -m solox

# 或直接运行 web.py
python solox/web.py
```

## 🏗️ 核心模块开发

### 1. APM 模块扩展

在 `solox/public/apm.py` 中添加新的性能监控功能:

```python
class AppPerformanceMonitor:
    
    def collectCustomMetric(self, noLog=False):
        """自定义性能指标收集"""
        try:
            # 实现自定义监控逻辑
            metric_value = self._getCustomMetric()
            
            if noLog is False:
                apm_time = datetime.datetime.now().strftime('%H:%M:%S.%f')
                f.add_log(os.path.join(f.report_dir, 'custom.log'), 
                         apm_time, metric_value)
            
            return metric_value
        except Exception as e:
            logger.exception(e)
            return 0
    
    def _getCustomMetric(self):
        """获取自定义指标的具体实现"""
        # 根据平台实现不同的获取逻辑
        if self.platform == Platform.Android:
            return self._getAndroidCustomMetric()
        elif self.platform == Platform.iOS:
            return self._getiOSCustomMetric()
        else:
            raise Exception(f"Unsupported platform: {self.platform}")
```

### 2. API 接口扩展

在 `solox/view/apis.py` 中添加新的 API 端点:

```python
@api.route('/apm/custom', methods=['GET', 'POST'])
def custom_metric():
    """自定义性能指标 API"""
    try:
        # 获取请求参数
        platform = request.args.get('platform', 'Android')
        deviceid = request.args.get('deviceid')
        pkgname = request.args.get('pkgname')
        
        # 参数验证
        if not all([deviceid, pkgname]):
            return make_response({'code': 400, 'msg': 'Missing parameters'})
        
        # 创建监控实例
        apm = AppPerformanceMonitor(
            pkgName=pkgname,
            platform=platform,
            deviceId=deviceid,
            noLog=True
        )
        
        # 收集数据
        metric_data = apm.collectCustomMetric()
        
        return make_response({
            'code': 200,
            'msg': 'success',
            'data': {
                'custom_metric': metric_data,
                'timestamp': time.time()
            }
        })
        
    except Exception as e:
        logger.exception(e)
        return make_response({'code': 500, 'msg': str(e)})
```

### 3. 设备管理扩展

在 `solox/public/common.py` 中扩展设备管理功能:

```python
class Devices:
    
    def getDeviceInfo(self, deviceId):
        """获取设备详细信息"""
        try:
            if self.platform == Platform.Android:
                return self._getAndroidDeviceInfo(deviceId)
            elif self.platform == Platform.iOS:
                return self._getiOSDeviceInfo(deviceId)
        except Exception as e:
            logger.exception(e)
            return {}
    
    def _getAndroidDeviceInfo(self, deviceId):
        """获取 Android 设备信息"""
        info = {}
        
        # 设备型号
        model = self.execCmd(f'{self.adb} -s {deviceId} shell getprop ro.product.model')
        info['model'] = model.strip()
        
        # Android 版本
        version = self.execCmd(f'{self.adb} -s {deviceId} shell getprop ro.build.version.release')
        info['android_version'] = version.strip()
        
        # CPU 架构
        abi = self.execCmd(f'{self.adb} -s {deviceId} shell getprop ro.product.cpu.abi')
        info['cpu_abi'] = abi.strip()
        
        # 屏幕分辨率
        resolution = self.execCmd(f'{self.adb} -s {deviceId} shell wm size')
        info['resolution'] = resolution.strip()
        
        return info
```

## 🎨 前端开发

### 1. 页面模板开发

在 `solox/templates/` 中创建新的页面模板:

```html
<!-- custom_monitor.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Custom Monitor - SoloX</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/tabler.min.css') }}">
</head>
<body>
    <div class="page">
        <div class="page-wrapper">
            <div class="container-xl">
                <div class="page-header">
                    <h1 class="page-title">自定义监控</h1>
                </div>
                
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-body">
                                <canvas id="customChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="{{ url_for('static', filename='js/chart.min.js') }}"></script>
    <script src="{{ url_for('static', filename='js/custom-monitor.js') }}"></script>
</body>
</html>
```

### 2. JavaScript 开发

在 `solox/static/js/` 中创建对应的 JavaScript 文件:

```javascript
// custom-monitor.js
class CustomMonitor {
    constructor() {
        this.chart = null;
        this.data = [];
        this.init();
    }
    
    init() {
        this.initChart();
        this.startMonitoring();
    }
    
    initChart() {
        const ctx = document.getElementById('customChart').getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Custom Metric',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    startMonitoring() {
        setInterval(() => {
            this.fetchData();
        }, 1000);
    }
    
    async fetchData() {
        try {
            const response = await fetch('/apm/custom?platform=Android&deviceid=xxx&pkgname=xxx');
            const result = await response.json();
            
            if (result.code === 200) {
                this.updateChart(result.data);
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        }
    }
    
    updateChart(data) {
        const now = new Date().toLocaleTimeString();
        
        this.chart.data.labels.push(now);
        this.chart.data.datasets[0].data.push(data.custom_metric);
        
        // 保持最近 20 个数据点
        if (this.chart.data.labels.length > 20) {
            this.chart.data.labels.shift();
            this.chart.data.datasets[0].data.shift();
        }
        
        this.chart.update();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new CustomMonitor();
});
```

## 🧪 测试开发

### 1. 单元测试

创建 `tests/` 目录并添加测试文件:

```python
# tests/test_apm.py
import unittest
from unittest.mock import patch, MagicMock
from solox.public.apm import AppPerformanceMonitor
from solox.public.common import Platform

class TestAppPerformanceMonitor(unittest.TestCase):
    
    def setUp(self):
        self.apm = AppPerformanceMonitor(
            pkgName='com.test.app',
            platform=Platform.Android,
            deviceId='test_device',
            noLog=True
        )
    
    @patch('solox.public.apm.AppPerformanceMonitor.getAndroidCpuRate')
    def test_collect_cpu(self, mock_cpu):
        # 模拟 CPU 数据
        mock_cpu.return_value = (50.5, 25.3)
        
        app_cpu, sys_cpu = self.apm.collectCpu()
        
        self.assertEqual(app_cpu, 50.5)
        self.assertEqual(sys_cpu, 25.3)
        mock_cpu.assert_called_once()
    
    @patch('solox.public.apm.AppPerformanceMonitor.getAndroidMem')
    def test_collect_memory(self, mock_memory):
        # 模拟内存数据
        mock_memory.return_value = (512, 1024, 2048)
        
        pss, private, total = self.apm.collectMemory()
        
        self.assertEqual(pss, 512)
        self.assertEqual(private, 1024)
        self.assertEqual(total, 2048)
        mock_memory.assert_called_once()

if __name__ == '__main__':
    unittest.main()
```

### 2. 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试文件
python -m pytest tests/test_apm.py

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=solox --cov-report=html
```

## 📝 代码规范

### 1. Python 代码风格

使用 Black 进行代码格式化:

```bash
# 格式化代码
black solox/

# 检查代码风格
flake8 solox/

# 类型检查
mypy solox/
```

### 2. 提交规范

```bash
# 提交信息格式
git commit -m "feat: 添加自定义性能监控功能"
git commit -m "fix: 修复 iOS 设备连接问题"
git commit -m "docs: 更新 API 文档"
git commit -m "test: 添加 APM 模块单元测试"
```

### 3. 分支管理

```bash
# 创建功能分支
git checkout -b feature/custom-monitoring

# 创建修复分支
git checkout -b fix/ios-connection

# 合并到主分支
git checkout main
git merge feature/custom-monitoring
```

## 🔍 调试技巧

### 1. 日志调试

```python
from logzero import logger

# 添加调试日志
logger.debug("Debug information")
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Exception with traceback")
```

### 2. 断点调试

```python
# 使用 pdb 调试
import pdb
pdb.set_trace()

# 或使用 IDE 断点调试
```

### 3. 性能分析

```python
import cProfile
import pstats

# 性能分析
profiler = cProfile.Profile()
profiler.enable()

# 执行代码
your_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

---

*相关文档: [快速启动](./quick-start.md) • [环境配置](./environment-setup.md) • [贡献指南](../05-issues/contribution-guide.md)*
