#!/bin/bash
# SoloX 依赖安装脚本
# 用于解决常见的依赖版本冲突和安装问题
# 
# 使用方法:
#   chmod +x scripts/install_dependencies.sh
#   ./scripts/install_dependencies.sh

set -e  # 遇到错误时退出

echo "🚀 SoloX 依赖安装脚本"
echo "======================="
echo ""

# 检查 Python 版本
echo "🔍 检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 版本过低: $python_version (需要 >= $required_version)"
    echo "请升级 Python 版本: https://www.python.org/downloads/"
    exit 1
fi
echo "✅ Python 版本: $python_version"
echo ""

# 升级 pip
echo "📦 升级 pip..."
python3 -m pip install --upgrade pip --user
echo ""

# 安装核心依赖
echo "🔧 安装核心依赖..."
pip3 install --user fire logzero pyfiglet psutil
echo ""

# 安装兼容的 Web 框架依赖
echo "🌐 安装 Web 框架依赖 (兼容版本)..."
pip3 install --user Flask==2.0.3 Werkzeug==2.0.3
pip3 install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2
echo ""

# 安装设备通信依赖
echo "📱 安装设备通信依赖..."
pip3 install --user tidevice==0.9.7
echo ""

# 安装图像处理依赖
echo "🖼️ 安装图像处理依赖..."
pip3 install --user opencv-python
echo ""

# 安装其他可选依赖
echo "🔗 安装其他依赖..."
pip3 install --user requests
echo ""

# 验证安装
echo "✅ 验证依赖安装..."
python3 -c "
import sys
print(f'Python 版本: {sys.version}')
print('')

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

for module, name in dependencies:
    try:
        __import__(module)
        version = ''
        try:
            mod = __import__(module)
            if hasattr(mod, '__version__'):
                version = f' v{mod.__version__}'
        except:
            pass
        print(f'✅ {name}{version}')
        success_count += 1
    except ImportError:
        print(f'❌ {name} - 安装失败')

print('')
print(f'依赖安装结果: {success_count}/{total_count} 成功')

if success_count == total_count:
    print('🎉 所有依赖安装成功！')
    print('')
    print('现在可以启动 SoloX:')
    print('  python3 -m solox')
    print('  或')
    print('  cd solox && python3 -m solox')
else:
    print('⚠️ 部分依赖安装失败，请检查错误信息')
    sys.exit(1)
"

echo ""
echo "🎯 安装完成！"
echo ""
echo "下一步:"
echo "1. 连接 Android 设备并开启 USB 调试"
echo "2. 运行: python3 -m solox"
echo "3. 访问: http://localhost:50003"
echo ""
echo "如果遇到问题，请查看文档: docs/08-故障排除.md"
