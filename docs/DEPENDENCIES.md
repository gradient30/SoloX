# SoloX 依赖问题解决方案

## 📋 概述

SoloX 项目依赖多个 Python 包，由于版本兼容性问题，可能会遇到各种依赖冲突。本文档提供了完整的解决方案。

## 🎯 核心依赖列表

### 必需依赖

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| Python | >= 3.10 | 运行环境 |
| Flask | == 2.0.3 | Web 框架 |
| Werkzeug | == 2.0.3 | WSGI 工具 |
| Flask-SocketIO | == 4.3.1 | WebSocket 支持 |
| fire | latest | 命令行接口 |
| logzero | latest | 日志管理 |
| pyfiglet | latest | ASCII 艺术字 |
| psutil | latest | 系统信息 |

### 设备通信依赖

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| tidevice | == 0.9.7 | iOS 设备通信 |
| opencv-python | latest | 图像处理 |

### 可选依赖

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| requests | latest | HTTP 客户端 |

## ⚠️ 常见问题

### 1. Flask/Werkzeug 版本冲突

**错误信息**:
```
ImportError: cannot import name 'url_quote' from 'werkzeug.urls'
AttributeError: 'Flask' object has no attribute 'before_first_request'
```

**原因**: Flask-SocketIO 4.3.1 与新版本的 Flask/Werkzeug 不兼容

**解决方案**:
```bash
pip install --user Flask==2.0.3 Werkzeug==2.0.3
pip install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2
```

### 2. 缺少核心模块

**错误信息**:
```
ModuleNotFoundError: No module named 'fire'
ModuleNotFoundError: No module named 'pyfiglet'
ModuleNotFoundError: No module named 'cv2'
```

**解决方案**:
```bash
pip install --user fire pyfiglet psutil opencv-python tidevice==0.9.7
```

### 3. 权限问题

**错误信息**:
```
ERROR: Could not install packages due to an EnvironmentError
```

**解决方案**:
```bash
# 使用用户级安装
pip install --user <package_name>

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install <package_name>
```

## 🔧 一键解决方案

### Linux/macOS

```bash
#!/bin/bash
# 保存为 fix_deps.sh 并执行

# 升级 pip
python3 -m pip install --upgrade pip --user

# 安装核心依赖
pip3 install --user fire logzero pyfiglet psutil

# 安装兼容的 Web 框架
pip3 install --user Flask==2.0.3 Werkzeug==2.0.3
pip3 install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2

# 安装设备通信依赖
pip3 install --user tidevice==0.9.7 opencv-python

# 验证安装
python3 -c "import solox; print('✅ SoloX 依赖安装成功')"
```

### Windows

```powershell
# 保存为 fix_deps.ps1 并执行

# 升级 pip
python -m pip install --upgrade pip --user

# 安装核心依赖
pip install --user fire logzero pyfiglet psutil

# 安装兼容的 Web 框架
pip install --user Flask==2.0.3 Werkzeug==2.0.3
pip install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2

# 安装设备通信依赖
pip install --user tidevice==0.9.7 opencv-python

# 验证安装
python -c "import solox; print('✅ SoloX 依赖安装成功')"
```

## 🚀 自动化脚本

项目提供了自动化安装脚本：

```bash
# Linux/macOS
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh

# Windows
PowerShell -ExecutionPolicy Bypass -File scripts\install_dependencies.ps1
```

## 🔍 依赖验证

安装完成后，使用以下脚本验证依赖：

```python
# verify_deps.py
import sys

def verify_dependencies():
    """验证 SoloX 依赖是否正确安装"""
    dependencies = [
        ('fire', 'Fire'),
        ('logzero', 'LogZero'),
        ('pyfiglet', 'PyFiglet'),
        ('psutil', 'PSUtil'),
        ('flask', 'Flask'),
        ('werkzeug', 'Werkzeug'),
        ('flask_socketio', 'Flask-SocketIO'),
        ('tidevice', 'tidevice'),
        ('cv2', 'OpenCV'),
        ('requests', 'Requests')
    ]
    
    success_count = 0
    total_count = len(dependencies)
    
    print("🔍 验证 SoloX 依赖...")
    print("=" * 40)
    
    for module, name in dependencies:
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'unknown')
            print(f"✅ {name:<15} v{version}")
            success_count += 1
        except ImportError:
            print(f"❌ {name:<15} 未安装")
    
    print("=" * 40)
    print(f"结果: {success_count}/{total_count} 依赖安装成功")
    
    if success_count == total_count:
        print("🎉 所有依赖验证通过！可以启动 SoloX")
        return True
    else:
        print("⚠️ 部分依赖缺失，请参考解决方案")
        return False

if __name__ == "__main__":
    if verify_dependencies():
        print("\n启动命令: python -m solox")
    else:
        sys.exit(1)
```

## 📚 版本兼容性矩阵

| Python | Flask | Werkzeug | Flask-SocketIO | 状态 |
|--------|-------|----------|----------------|------|
| 3.10+ | 2.0.3 | 2.0.3 | 4.3.1 | ✅ 推荐 |
| 3.10+ | 2.1+ | 2.1+ | 5.0+ | ⚠️ 未测试 |
| 3.9 | 2.0.3 | 2.0.3 | 4.3.1 | ❌ 不支持 |

## 🆘 获取帮助

如果仍然遇到依赖问题：

1. 查看 [故障排除文档](./08-故障排除.md)
2. 提交 [GitHub Issue](https://github.com/smart-test-ti/SoloX/issues)
3. 包含以下信息：
   - 操作系统和版本
   - Python 版本
   - 完整的错误信息
   - 已尝试的解决方案

## 📝 更新日志

- **2025-08-03**: 创建依赖问题解决方案文档
- **2025-08-03**: 添加自动化安装脚本
- **2025-08-03**: 确认 Flask 2.0.3 + Werkzeug 2.0.3 + Flask-SocketIO 4.3.1 组合稳定

---

*最后更新: 2025-08-03*
