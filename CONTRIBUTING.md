# Contributing to SoloX

感谢您对 SoloX 项目的关注和贡献！本文档将指导您如何参与项目开发。

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/smart-test-ti/SoloX.git
cd SoloX

# 安装依赖
make install-dev
# 或
pip install -e ".[dev,test]"

# 验证安装
make verify
```

### 2. 开发工具

项目提供了 Makefile 来简化开发任务：

```bash
make help          # 查看所有可用命令
make test           # 运行测试
make lint           # 代码检查
make format         # 代码格式化
make run            # 启动服务
make clean          # 清理构建文件
```

## 📋 贡献类型

我们欢迎以下类型的贡献：

- 🐛 **Bug 报告和修复**
- ✨ **新功能开发**
- 📚 **文档改进**
- 🧪 **测试用例编写**
- 🌐 **国际化支持**
- 🔧 **工具和脚本改进**
- 💡 **功能建议和讨论**

## 🔄 开发流程

### 1. 创建 Issue

在开始开发之前，请先创建或查找相关的 Issue：

- 对于 Bug 修复：描述问题、复现步骤、期望行为
- 对于新功能：描述功能需求、使用场景、实现方案
- 使用适当的标签标记 Issue

### 2. 分支管理

```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 创建修复分支
git checkout -b fix/issue-description

# 创建文档分支
git checkout -b docs/update-readme
```

### 3. 开发规范

#### 代码风格

- 使用 [Black](https://black.readthedocs.io/) 进行代码格式化
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用类型注解 (Type Hints)
- 添加适当的文档字符串

```python
def collect_performance_data(
    device_id: str, 
    package_name: str, 
    duration: int = 60
) -> Dict[str, Any]:
    """收集设备性能数据
    
    Args:
        device_id: 设备 ID
        package_name: 应用包名
        duration: 监控时长 (秒)
    
    Returns:
        包含性能数据的字典
        
    Raises:
        DeviceNotFoundError: 设备未找到
        PermissionError: 权限不足
    """
    pass
```

#### 提交信息

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
```

### 4. 测试要求

#### 单元测试

```bash
# 运行所有测试
make test

# 运行特定测试
pytest tests/test_apm.py -v

# 生成覆盖率报告
pytest tests/ --cov=solox --cov-report=html
```

#### 测试编写

```python
import unittest
from unittest.mock import patch, MagicMock
from solox.public.apm import AppPerformanceMonitor

class TestAppPerformanceMonitor(unittest.TestCase):
    
    def setUp(self):
        self.apm = AppPerformanceMonitor(
            pkgName='com.test.app',
            platform='Android',
            deviceId='test_device'
        )
    
    @patch('solox.public.apm.AppPerformanceMonitor.getAndroidCpuRate')
    def test_collect_cpu(self, mock_cpu):
        mock_cpu.return_value = (50.5, 25.3)
        
        app_cpu, sys_cpu = self.apm.collectCpu()
        
        self.assertEqual(app_cpu, 50.5)
        self.assertEqual(sys_cpu, 25.3)
        mock_cpu.assert_called_once()
```

### 5. 文档要求

- 更新相关的 Markdown 文档
- 添加代码示例和使用说明
- 确保文档的准确性和完整性
- 使用清晰的标题结构和格式

## 🔍 代码审查

### Pull Request 检查清单

- [ ] 代码遵循项目规范
- [ ] 添加了适当的测试
- [ ] 测试全部通过
- [ ] 更新了相关文档
- [ ] 提交信息符合规范
- [ ] 没有合并冲突
- [ ] 通过了 CI/CD 检查

### 审查流程

1. 提交 Pull Request
2. 自动化测试运行
3. 代码审查和反馈
4. 根据反馈进行修改
5. 审查通过后合并

## 🛠️ 开发环境

### 推荐工具

- **IDE**: VS Code, PyCharm
- **Python**: 3.10+
- **Git**: 最新版本
- **Docker**: 用于容器化测试

### VS Code 配置

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

### 依赖管理

- 使用 `requirements.txt` 管理生产依赖
- 使用 `pyproject.toml` 管理开发依赖
- 定期更新依赖版本
- 确保依赖兼容性

## 🐛 Bug 报告

### 报告模板

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

## ✨ 功能请求

### 请求模板

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

## 📞 联系方式

- **GitHub Issues**: https://github.com/smart-test-ti/SoloX/issues
- **项目主页**: https://github.com/smart-test-ti/SoloX
- **邮箱**: rafacheninc@gmail.com

## 📄 许可证

通过贡献代码，您同意您的贡献将在 [MIT 许可证](LICENSE) 下发布。

## 🙏 致谢

感谢所有为 SoloX 项目做出贡献的开发者！

---

*最后更新: 2025-08-03*
