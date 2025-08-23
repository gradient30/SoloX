# 开发环境配置

## 🛠️ 环境要求

### 系统要求
- **操作系统**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **Python**: 3.10+ (推荐 3.10 或 3.11)
- **内存**: 最少 4GB，推荐 8GB+
- **磁盘**: 至少 2GB 可用空间

### 必需工具
- **Git**: 版本控制
- **ADB**: Android 设备调试 (Android 开发)
- **iTunes**: iOS 设备支持 (Windows iOS 开发)

## 🚀 快速开始

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

### 3. 安装依赖

```bash
# 方法一: 使用 requirements.txt (推荐)
pip install -r requirements.txt

# 方法二: 使用自动化脚本
# Linux/macOS
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh

# Windows
PowerShell -ExecutionPolicy Bypass -File scripts\install_dependencies.ps1

# 方法三: 使用 setup.py
pip install -e ".[dev,test]"
```

### 4. 验证安装

```bash
# 验证核心依赖
python scripts/verify_setup.py

# 启动开发服务
python -m solox --host=127.0.0.1 --port=50003
```

## 🔧 开发工具配置

### VS Code 配置

创建 `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": ["--max-line-length=88"],
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "python.testing.unittestEnabled": false,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv": true,
        "**/.pytest_cache": true
    }
}
```

创建 `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "SoloX Debug",
            "type": "python",
            "request": "launch",
            "module": "solox",
            "args": ["--host=127.0.0.1", "--port=50003"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

### PyCharm 配置

1. **解释器配置**:
   - File → Settings → Project → Python Interpreter
   - 选择虚拟环境中的 Python 解释器

2. **代码风格配置**:
   - File → Settings → Editor → Code Style → Python
   - 设置 Line length: 88
   - 启用 Black 格式化

3. **运行配置**:
   - Run → Edit Configurations
   - 添加 Python 配置
   - Module name: `solox`
   - Parameters: `--host=127.0.0.1 --port=50003`

## 🔍 开发模式

### 调试模式启动

```bash
# 进入 solox 目录
cd solox

# 启动调试服务 (自动重载)
python debug.py

# 或指定参数
python debug.py --host=0.0.0.0 --port=5000
```

### 生产模式启动

```bash
# 使用生产配置启动
python -m solox

# 或直接运行 web.py
python solox/web.py --host=127.0.0.1 --port=50003
```

## 📦 依赖管理

### 核心依赖版本锁定

根据 SoloX 项目开发规范，严格锁定以下版本：

```bash
# Web 框架 (严格锁定)
pip install Flask==2.0.3 Werkzeug==2.0.3

# WebSocket 支持 (兼容版本组合)
pip install Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2

# iOS 设备通信 (锁定稳定版本)
pip install tidevice==0.9.7
```

### 开发依赖

```bash
# 代码质量工具
pip install black flake8 mypy isort

# 测试工具
pip install pytest pytest-cov pytest-mock

# 文档工具
pip install sphinx sphinx-rtd-theme

# 构建工具
pip install build twine
```

## 🛠️ Makefile 使用

项目提供了 Makefile 简化开发任务：

```bash
# 查看所有可用命令
make help

# 安装开发依赖
make install-dev

# 运行测试
make test

# 代码检查
make lint

# 代码格式化
make format

# 启动服务
make run

# 清理构建文件
make clean

# 构建项目
make build

# 完整检查 (格式化 + 检查 + 测试)
make check
```

## 🔧 环境变量配置

创建 `.env` 文件 (可选):

```bash
# 开发环境配置
SOLOX_HOST=127.0.0.1
SOLOX_PORT=50003
SOLOX_DEBUG=true

# 日志配置
LOG_LEVEL=DEBUG
LOG_FILE=solox_dev.log

# 设备配置
ADB_PATH=/usr/local/bin/adb
```

## 🐛 常见问题解决

### 1. 依赖冲突

```bash
# 清理环境重新安装
pip uninstall -y Flask Werkzeug Flask-SocketIO
pip install Flask==2.0.3 Werkzeug==2.0.3 Flask-SocketIO==4.3.1
```

### 2. 端口占用

```bash
# 查看端口占用
netstat -tulpn | grep :50003  # Linux/macOS
netstat -ano | findstr :50003  # Windows

# 使用其他端口
python -m solox --port=50004
```

### 3. 权限问题

```bash
# 使用用户级安装
pip install --user -r requirements.txt

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

## 📱 设备环境配置

### Android 开发

```bash
# 安装 ADB
# Ubuntu/Debian
sudo apt install android-tools-adb

# macOS
brew install android-platform-tools

# Windows
# 下载 Android SDK Platform Tools

# 验证 ADB
adb version
adb devices
```

### iOS 开发

```bash
# 安装 tidevice
pip install tidevice==0.9.7

# 验证 iOS 设备连接
tidevice list
tidevice info
```

---

**相关文档**:
- [代码规范](./coding-standards.md) - 编码规范和最佳实践
- [测试指南](./testing-guide.md) - 测试编写和执行
- [API 参考](./api-reference.md) - API 接口文档

*最后更新: 2025-08-23*
