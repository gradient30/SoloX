# SoloX 依赖安装脚本 (Windows PowerShell)
# 用于解决常见的依赖版本冲突和安装问题
# 
# 使用方法:
#   PowerShell -ExecutionPolicy Bypass -File scripts\install_dependencies.ps1

param(
    [switch]$Force = $false
)

Write-Host "🚀 SoloX 依赖安装脚本 (Windows)" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 版本
Write-Host "🔍 检查 Python 版本..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+\.\d+)") {
        $version = [version]$matches[1]
        $requiredVersion = [version]"3.10"
        
        if ($version -lt $requiredVersion) {
            Write-Host "❌ Python 版本过低: $($version) (需要 >= 3.10)" -ForegroundColor Red
            Write-Host "请升级 Python 版本: https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
        Write-Host "✅ Python 版本: $($version)" -ForegroundColor Green
    } else {
        throw "无法获取 Python 版本"
    }
} catch {
    Write-Host "❌ Python 未安装或不在 PATH 中" -ForegroundColor Red
    Write-Host "请安装 Python 3.10+: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 升级 pip
Write-Host "📦 升级 pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --user
Write-Host ""

# 安装核心依赖
Write-Host "🔧 安装核心依赖..." -ForegroundColor Yellow
pip install --user fire logzero pyfiglet psutil
Write-Host ""

# 安装兼容的 Web 框架依赖
Write-Host "🌐 安装 Web 框架依赖 (兼容版本)..." -ForegroundColor Yellow
pip install --user Flask==2.0.3 Werkzeug==2.0.3
pip install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2
Write-Host ""

# 安装设备通信依赖
Write-Host "📱 安装设备通信依赖..." -ForegroundColor Yellow
pip install --user tidevice==0.9.7
Write-Host ""

# 安装图像处理依赖
Write-Host "🖼️ 安装图像处理依赖..." -ForegroundColor Yellow
pip install --user opencv-python
Write-Host ""

# 安装其他可选依赖
Write-Host "🔗 安装其他依赖..." -ForegroundColor Yellow
pip install --user requests
Write-Host ""

# 验证安装
Write-Host "✅ 验证依赖安装..." -ForegroundColor Yellow
$verificationScript = @"
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
    print('  python -m solox')
    print('  或')
    print('  cd solox && python -m solox')
    exit(0)
else:
    print('⚠️ 部分依赖安装失败，请检查错误信息')
    exit(1)
"@

$result = python -c $verificationScript
Write-Host $result

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "🎯 安装完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Cyan
    Write-Host "1. 连接 Android 设备并开启 USB 调试" -ForegroundColor White
    Write-Host "2. 运行: python -m solox" -ForegroundColor White
    Write-Host "3. 访问: http://localhost:50003" -ForegroundColor White
    Write-Host ""
    Write-Host "如果遇到问题，请查看文档: docs\08-故障排除.md" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ 安装过程中遇到问题" -ForegroundColor Red
    Write-Host "请查看错误信息并参考文档: docs\08-故障排除.md" -ForegroundColor Yellow
    exit 1
}
