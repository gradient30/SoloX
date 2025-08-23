# 贡献指南

## 🤝 欢迎贡献

感谢您对 SoloX 项目的关注！我们欢迎各种形式的贡献，包括但不限于：

- 🐛 Bug 报告和修复
- ✨ 新功能开发
- 📚 文档改进
- 🧪 测试用例编写
- 🌐 国际化支持
- 💡 功能建议

## 📋 贡献流程

### 1. 准备工作

```bash
# 1. Fork 项目到您的 GitHub 账户
# 2. 克隆您的 Fork
git clone https://github.com/YOUR_USERNAME/SoloX.git
cd SoloX

# 3. 添加上游仓库
git remote add upstream https://github.com/smart-test-ti/SoloX.git

# 4. 创建开发环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 5. 安装开发依赖
pip install -e .
pip install pytest pytest-cov black flake8 mypy
```

### 2. 开发流程

```bash
# 1. 同步最新代码
git fetch upstream
git checkout main
git merge upstream/main

# 2. 创建功能分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix

# 3. 进行开发
# 编写代码、测试、文档

# 4. 提交代码
git add .
git commit -m "feat: 添加新功能描述"

# 5. 推送到您的 Fork
git push origin feature/your-feature-name

# 6. 创建 Pull Request
# 在 GitHub 上创建 PR
```

## 📝 代码规范

### 1. Python 代码风格

我们使用 [Black](https://black.readthedocs.io/) 进行代码格式化：

```bash
# 格式化代码
black solox/

# 检查代码风格
flake8 solox/

# 类型检查
mypy solox/
```

**代码风格要求**:
- 使用 4 个空格缩进
- 行长度限制为 88 字符
- 使用类型注解
- 遵循 PEP 8 规范

### 2. 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
# 功能添加
git commit -m "feat: 添加 iOS 设备温度监控功能"

# Bug 修复
git commit -m "fix: 修复 Android 内存数据获取异常"

# 文档更新
git commit -m "docs: 更新 API 使用文档"

# 测试添加
git commit -m "test: 添加 CPU 监控单元测试"

# 重构
git commit -m "refactor: 重构设备管理模块"

# 性能优化
git commit -m "perf: 优化内存数据收集性能"

# 构建相关
git commit -m "build: 更新依赖包版本"

# CI/CD
git commit -m "ci: 添加自动化测试流程"
```

### 3. 代码示例

```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """性能监控基类
    
    Args:
        device_id: 设备 ID
        package_name: 应用包名
        platform: 平台类型 ('Android' 或 'iOS')
    
    Example:
        >>> monitor = PerformanceMonitor('device123', 'com.example.app', 'Android')
        >>> cpu_data = monitor.collect_cpu()
        >>> print(f"CPU 使用率: {cpu_data['app_cpu']}%")
    """
    
    def __init__(
        self, 
        device_id: str, 
        package_name: str, 
        platform: str
    ) -> None:
        self.device_id = device_id
        self.package_name = package_name
        self.platform = platform
        self._validate_parameters()
    
    def _validate_parameters(self) -> None:
        """验证初始化参数"""
        if not self.device_id:
            raise ValueError("device_id 不能为空")
        
        if not self.package_name:
            raise ValueError("package_name 不能为空")
        
        if self.platform not in ['Android', 'iOS']:
            raise ValueError("platform 必须是 'Android' 或 'iOS'")
    
    def collect_cpu(self) -> Dict[str, float]:
        """收集 CPU 使用率数据
        
        Returns:
            包含 app_cpu 和 sys_cpu 的字典
            
        Raises:
            RuntimeError: 当数据收集失败时
        """
        try:
            if self.platform == 'Android':
                return self._collect_android_cpu()
            else:
                return self._collect_ios_cpu()
        except Exception as e:
            logger.error(f"CPU 数据收集失败: {e}")
            raise RuntimeError(f"CPU 数据收集失败: {e}")
    
    def _collect_android_cpu(self) -> Dict[str, float]:
        """收集 Android CPU 数据"""
        # 实现 Android CPU 数据收集
        pass
    
    def _collect_ios_cpu(self) -> Dict[str, float]:
        """收集 iOS CPU 数据"""
        # 实现 iOS CPU 数据收集
        pass
```

## 🧪 测试要求

### 1. 单元测试

```python
# tests/test_performance_monitor.py
import unittest
from unittest.mock import patch, MagicMock
from solox.public.apm import PerformanceMonitor

class TestPerformanceMonitor(unittest.TestCase):
    
    def setUp(self):
        """测试前准备"""
        self.monitor = PerformanceMonitor(
            device_id='test_device',
            package_name='com.test.app',
            platform='Android'
        )
    
    def test_init_valid_parameters(self):
        """测试有效参数初始化"""
        self.assertEqual(self.monitor.device_id, 'test_device')
        self.assertEqual(self.monitor.package_name, 'com.test.app')
        self.assertEqual(self.monitor.platform, 'Android')
    
    def test_init_invalid_platform(self):
        """测试无效平台参数"""
        with self.assertRaises(ValueError):
            PerformanceMonitor('device', 'app', 'InvalidPlatform')
    
    @patch('solox.public.apm.PerformanceMonitor._collect_android_cpu')
    def test_collect_cpu_android(self, mock_collect):
        """测试 Android CPU 数据收集"""
        # 模拟返回数据
        mock_collect.return_value = {'app_cpu': 25.5, 'sys_cpu': 45.2}
        
        result = self.monitor.collect_cpu()
        
        self.assertEqual(result['app_cpu'], 25.5)
        self.assertEqual(result['sys_cpu'], 45.2)
        mock_collect.assert_called_once()
    
    def test_collect_cpu_exception_handling(self):
        """测试异常处理"""
        with patch.object(self.monitor, '_collect_android_cpu', 
                         side_effect=Exception("Test error")):
            with self.assertRaises(RuntimeError):
                self.monitor.collect_cpu()

if __name__ == '__main__':
    unittest.main()
```

### 2. 集成测试

```python
# tests/test_integration.py
import unittest
import requests
import time
from solox.web import main
import multiprocessing

class TestAPIIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """启动测试服务器"""
        cls.server_process = multiprocessing.Process(
            target=main, 
            args=('127.0.0.1', 50004)
        )
        cls.server_process.start()
        time.sleep(2)  # 等待服务器启动
        cls.base_url = 'http://127.0.0.1:50004'
    
    @classmethod
    def tearDownClass(cls):
        """关闭测试服务器"""
        cls.server_process.terminate()
        cls.server_process.join()
    
    def test_health_endpoint(self):
        """测试健康检查端点"""
        response = requests.get(f'{self.base_url}/health')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'ok')
    
    def test_collect_api(self):
        """测试性能数据收集 API"""
        params = {
            'platform': 'Android',
            'deviceid': 'test_device',
            'pkgname': 'com.test.app',
            'target': 'cpu'
        }
        
        response = requests.get(f'{self.base_url}/apm/collect', params=params)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('code', data)
        self.assertIn('data', data)
```

### 3. 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试文件
python -m pytest tests/test_performance_monitor.py

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=solox --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

## 📚 文档贡献

### 1. 文档结构

```
docs/
├── 01-architecture/          # 架构设计
│   ├── project-overview.md   # 项目概述
│   ├── technical-architecture.md  # 技术架构
│   └── system-design.md      # 系统设计
├── 02-development/           # 开发指南
│   ├── quick-start.md        # 快速启动
│   ├── development-guide.md  # 开发指南
│   └── environment-setup.md  # 环境配置
├── 03-deployment/            # 部署指南
│   ├── deployment-guide.md   # 部署指南
│   └── docker-guide.md       # Docker 指南
├── 04-user-guides/           # 用户指南
│   ├── api-documentation.md  # API 文档
│   └── performance-monitoring.md  # 性能监控
└── 05-issues/                # 问题解决
    ├── troubleshooting.md    # 故障排除
    ├── contribution-guide.md # 贡献指南
    └── faq.md                # 常见问题
```

### 2. 文档规范

- 使用 Markdown 格式
- 包含代码示例
- 添加适当的图表和截图
- 保持内容准确和最新
- 使用清晰的标题结构

### 3. API 文档示例

```markdown
## 获取 CPU 使用率

**接口地址**: `/apm/collect`

**请求方式**: `GET`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| platform | string | 是 | 平台类型: `Android` 或 `iOS` |
| deviceid | string | 是 | 设备 ID |
| pkgname | string | 是 | 应用包名 |
| target | string | 是 | 固定值: `cpu` |

**请求示例**:

```bash
curl "http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=cpu"
```

**响应示例**:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "appCpuRate": 25.5,
    "systemCpuRate": 45.2
  }
}
```
```

## 🐛 Bug 报告

### 1. 报告模板

```markdown
## Bug 描述
简要描述遇到的问题

## 复现步骤
1. 执行步骤 1
2. 执行步骤 2
3. 看到错误

## 预期行为
描述您期望发生的情况

## 实际行为
描述实际发生的情况

## 环境信息
- 操作系统: [例如 Ubuntu 20.04]
- Python 版本: [例如 3.10.0]
- SoloX 版本: [例如 2.9.3]
- 设备类型: [例如 Android 13]

## 错误日志
```
粘贴相关的错误日志
```

## 附加信息
添加任何其他有助于解决问题的信息
```

### 2. 提交 Bug

1. 在 [GitHub Issues](https://github.com/smart-test-ti/SoloX/issues) 创建新 Issue
2. 使用 Bug 报告模板
3. 添加适当的标签
4. 提供详细的复现步骤

## ✨ 功能请求

### 1. 请求模板

```markdown
## 功能描述
简要描述您希望添加的功能

## 使用场景
描述这个功能的使用场景和价值

## 详细设计
详细描述功能的实现方案

## 替代方案
描述您考虑过的其他解决方案

## 附加信息
添加任何其他相关信息
```

### 2. 功能开发

1. 创建功能请求 Issue
2. 等待维护者确认
3. Fork 项目并创建功能分支
4. 实现功能并添加测试
5. 提交 Pull Request

## 🔄 Pull Request 流程

### 1. PR 检查清单

- [ ] 代码遵循项目规范
- [ ] 添加了适当的测试
- [ ] 测试全部通过
- [ ] 更新了相关文档
- [ ] 提交信息符合规范
- [ ] 没有合并冲突

### 2. PR 模板

```markdown
## 变更描述
简要描述这个 PR 的变更内容

## 变更类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 性能优化
- [ ] 代码重构

## 测试
- [ ] 添加了新的测试
- [ ] 所有测试通过
- [ ] 手动测试通过

## 相关 Issue
关闭 #issue_number

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 添加了适当的文档
- [ ] 没有破坏性变更
```

### 3. 代码审查

1. 维护者会审查您的代码
2. 根据反馈进行修改
3. 通过审查后合并到主分支

## 🏆 贡献者认可

### 1. 贡献者列表

我们会在项目中维护贡献者列表，感谢每一位贡献者的付出。

### 2. 贡献统计

- 代码贡献
- 文档贡献
- Bug 报告
- 功能建议
- 社区支持

## 📞 联系方式

- **GitHub Issues**: https://github.com/smart-test-ti/SoloX/issues
- **项目主页**: https://github.com/smart-test-ti/SoloX
- **邮箱**: rafacheninc@gmail.com

## 📄 许可证

通过贡献代码，您同意您的贡献将在 [MIT 许可证](../../LICENSE) 下发布。

---

感谢您对 SoloX 项目的贡献！🎉
