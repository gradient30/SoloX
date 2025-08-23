# 故障排除

## 🔧 常见问题诊断

### 1. 服务启动问题

#### 问题: 端口被占用

**错误信息**:
```
OSError: [Errno 98] Address already in use
```

**解决方案**:
```bash
# 查看端口占用
netstat -tulpn | grep :50003
# 或
lsof -i :50003

# 杀死占用进程
kill -9 <PID>

# 或使用其他端口
python -m solox --port=50004
```

#### 问题: Python 版本不兼容

**错误信息**:
```
SyntaxError: invalid syntax
```

**解决方案**:
```bash
# 检查 Python 版本
python --version

# 安装 Python 3.10+
# Ubuntu/Debian
sudo apt install python3.10

# 使用正确的 Python 版本
python3.10 -m solox
```

#### 问题: 依赖包安装失败

**错误信息**:
```
ERROR: Could not install packages due to an EnvironmentError
```

**解决方案**:
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像
pip install -i https://mirrors.aliyun.com/pypi/simple/ solox

# 清理缓存
pip cache purge

# 使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
pip install solox

# 如果遇到权限问题，使用用户级安装
pip install --user solox
```

#### 问题: Flask/Werkzeug 版本兼容性

**错误信息**:
```
ImportError: cannot import name 'url_quote' from 'werkzeug.urls'
AttributeError: 'Flask' object has no attribute 'before_first_request'
```

**原因**: Flask-SocketIO 4.3.1 与新版本的 Flask/Werkzeug 不兼容

**解决方案**:
```bash
# 方案一: 降级到兼容版本 (推荐)
pip install --user Flask==2.0.3 Werkzeug==2.0.3
pip install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2

# 方案二: 升级到最新版本
pip install --user Flask-SocketIO>=5.0.0

# 验证版本
python -c "import flask, werkzeug; print(f'Flask: {flask.__version__}, Werkzeug: {werkzeug.__version__}')"
```

#### 问题: 缺少核心依赖模块

**错误信息**:
```
ModuleNotFoundError: No module named 'fire'
ModuleNotFoundError: No module named 'pyfiglet'
ModuleNotFoundError: No module named 'cv2'
```

**解决方案**:
```bash
# 安装缺失的核心依赖
pip install --user fire pyfiglet psutil

# 安装 OpenCV
pip install --user opencv-python

# 安装设备通信依赖
pip install --user tidevice==0.9.7

# 验证安装
python -c "import fire, pyfiglet, cv2, tidevice; print('所有依赖安装成功')"
```

#### 问题: 一键解决所有依赖问题

**完整依赖安装脚本**:
```bash
#!/bin/bash
# 创建并保存为 fix_solox_deps.sh

echo "🔧 修复 SoloX 依赖问题..."

# 1. 升级 pip
python -m pip install --upgrade pip

# 2. 安装核心依赖
echo "📦 安装核心依赖..."
pip install --user fire logzero pyfiglet psutil

# 3. 安装兼容的 Web 框架
echo "🌐 安装 Web 框架依赖..."
pip install --user Flask==2.0.3 Werkzeug==2.0.3
pip install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2

# 4. 安装设备通信依赖
echo "📱 安装设备通信依赖..."
pip install --user tidevice==0.9.7

# 5. 安装图像处理依赖
echo "🖼️ 安装图像处理依赖..."
pip install --user opencv-python

# 6. 验证安装
echo "✅ 验证安装..."
python -c "
try:
    import fire, logzero, pyfiglet, psutil
    import flask, werkzeug
    import tidevice, cv2
    import solox
    print('🎉 所有依赖安装成功！')
    print(f'Flask: {flask.__version__}')
    print(f'Werkzeug: {werkzeug.__version__}')
    print(f'SoloX: {solox.__version__}')
except ImportError as e:
    print(f'❌ 依赖验证失败: {e}')
"

echo "🚀 现在可以启动 SoloX: python -m solox"
```

**Windows PowerShell 版本**:
```powershell
# 创建并保存为 fix_solox_deps.ps1
Write-Host "🔧 修复 SoloX 依赖问题..." -ForegroundColor Cyan

# 1. 升级 pip
python -m pip install --upgrade pip

# 2. 安装核心依赖
Write-Host "📦 安装核心依赖..." -ForegroundColor Yellow
pip install --user fire logzero pyfiglet psutil

# 3. 安装兼容的 Web 框架
Write-Host "🌐 安装 Web 框架依赖..." -ForegroundColor Yellow
pip install --user Flask==2.0.3 Werkzeug==2.0.3
pip install --user Flask-SocketIO==4.3.1 python-socketio==4.6.0 python-engineio==3.13.2

# 4. 安装设备通信依赖
Write-Host "📱 安装设备通信依赖..." -ForegroundColor Yellow
pip install --user tidevice==0.9.7

# 5. 安装图像处理依赖
Write-Host "🖼️ 安装图像处理依赖..." -ForegroundColor Yellow
pip install --user opencv-python

# 6. 验证安装
Write-Host "✅ 验证安装..." -ForegroundColor Yellow
python -c "
try:
    import fire, logzero, pyfiglet, psutil
    import flask, werkzeug
    import tidevice, cv2
    import solox
    print('🎉 所有依赖安装成功！')
    print(f'Flask: {flask.__version__}')
    print(f'Werkzeug: {werkzeug.__version__}')
    print(f'SoloX: {solox.__version__}')
except ImportError as e:
    print(f'❌ 依赖验证失败: {e}')
"

Write-Host "🚀 现在可以启动 SoloX: python -m solox" -ForegroundColor Green
```

### 2. 设备连接问题

#### 问题: Android 设备未识别

**错误信息**:
```
no devices found
```

**诊断步骤**:
```bash
# 1. 检查 ADB 连接
adb devices

# 2. 重启 ADB 服务
adb kill-server
adb start-server

# 3. 检查 USB 调试是否开启
adb shell settings get global development_settings_enabled

# 4. 检查设备授权
adb devices
# 应该显示 "device" 而不是 "unauthorized"
```

**解决方案**:
1. **开启开发者选项**: 设置 → 关于手机 → 连续点击版本号 7 次
2. **开启 USB 调试**: 设置 → 开发者选项 → USB 调试
3. **授权调试**: 连接时选择"始终允许"
4. **更换 USB 线**: 使用数据线而非充电线
5. **更换 USB 端口**: 尝试不同的 USB 端口

#### 问题: iOS 设备连接失败

**错误信息**:
```
Could not connect to iOS device
```

**解决方案**:
```bash
# 1. 安装 tidevice (macOS)
pip install tidevice

# 2. 检查设备连接
tidevice list

# 3. 信任电脑
# 在设备上选择"信任此电脑"

# 4. Windows 用户安装 iTunes
# 下载并安装最新版 iTunes

# 5. 检查 iOS 版本
# 注意: 不支持 iOS 17
```

### 3. 性能数据收集问题

#### 问题: CPU 数据为 0

**可能原因**:
- 应用未运行
- 权限不足
- 进程 ID 错误

**解决方案**:
```python
# 1. 检查应用是否运行
from solox.public.common import Devices
d = Devices()
processes = d.getPid(deviceId='your_device', pkgName='com.example.app')
print(f"应用进程: {processes}")

# 2. 检查权限
# 确保设备已授权 USB 调试

# 3. 手动指定进程 ID
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='your_device',
    pid=12345  # 手动指定 PID
)
```

#### 问题: 内存数据异常

**错误信息**:
```
Memory data collection failed
```

**解决方案**:
```bash
# 1. 检查 dumpsys 权限
adb shell dumpsys meminfo com.example.app

# 2. 检查应用包名
adb shell pm list packages | grep example

# 3. 重启应用
adb shell am force-stop com.example.app
adb shell am start -n com.example.app/.MainActivity
```

#### 问题: FPS 数据获取失败

**可能原因**:
- SurfaceView 模式不支持
- 应用未在前台
- 权限不足

**解决方案**:
```python
# 1. 切换到 GfxInfo 模式
apm = AppPerformanceMonitor(
    pkgName='com.example.app',
    platform='Android',
    deviceId='your_device',
    surfaceview=False  # 使用 gfxinfo 模式
)

# 2. 确保应用在前台
# 手动打开应用到前台

# 3. 检查开发者选项
# 开发者选项 → GPU 呈现模式分析 → 在 adb shell dumpsys gfxinfo 中
```

### 4. Web 界面问题

#### 问题: 页面无法访问

**错误信息**:
```
This site can't be reached
```

**解决方案**:
```bash
# 1. 检查服务状态
curl http://localhost:50003/health

# 2. 检查防火墙
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 50003

# CentOS/RHEL
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=50003/tcp --permanent
sudo firewall-cmd --reload

# 3. 检查网络配置
netstat -tulpn | grep :50003
```

#### 问题: 实时数据不更新

**可能原因**:
- WebSocket 连接失败
- 浏览器缓存问题
- 网络连接不稳定

**解决方案**:
```javascript
// 1. 检查 WebSocket 连接
const socket = io('/logcat');
socket.on('connect', function() {
    console.log('WebSocket connected');
});
socket.on('disconnect', function() {
    console.log('WebSocket disconnected');
});

// 2. 清理浏览器缓存
// Ctrl+F5 强制刷新

// 3. 检查网络连接
// 确保网络稳定
```

### 5. API 调用问题

#### 问题: API 返回 500 错误

**错误信息**:
```json
{
  "code": 500,
  "msg": "Internal server error"
}
```

**解决方案**:
```bash
# 1. 查看服务器日志
tail -f /var/log/solox/solox.log

# 2. 检查参数格式
curl -X GET "http://localhost:50003/apm/collect?platform=Android&deviceid=ca6bd5a5&pkgname=com.example.app&target=cpu"

# 3. 验证设备和应用
# 确保设备连接正常，应用正在运行
```

#### 问题: API 返回空数据

**可能原因**:
- 设备未连接
- 应用未运行
- 权限不足

**解决方案**:
```python
# 1. 验证设备连接
from solox.public.common import Devices
d = Devices()
devices = d.getDeviceIds()
if not devices:
    print("没有连接的设备")

# 2. 验证应用状态
processes = d.getPid(deviceId='your_device', pkgName='com.example.app')
if not processes:
    print("应用未运行")

# 3. 检查权限
# 确保 USB 调试已授权
```

### 6. 性能问题

#### 问题: 数据收集延迟高

**解决方案**:
```python
# 1. 调整采样频率
import time

def optimized_monitoring():
    # 降低采样频率
    while True:
        data = apm.collectCpu()
        time.sleep(2)  # 2秒间隔而非1秒

# 2. 使用多进程
import multiprocessing

def collect_cpu():
    return apm.collectCpu()

def collect_memory():
    return apm.collectMemory()

# 并行收集数据
pool = multiprocessing.Pool(processes=4)
cpu_result = pool.apply_async(collect_cpu)
memory_result = pool.apply_async(collect_memory)
```

#### 问题: 内存使用过高

**解决方案**:
```python
# 1. 限制数据缓存
MAX_DATA_POINTS = 1000
performance_data = []

def add_data_point(data):
    performance_data.append(data)
    if len(performance_data) > MAX_DATA_POINTS:
        performance_data.pop(0)  # 移除最旧的数据

# 2. 定期清理日志
import os
import glob

def cleanup_logs():
    log_files = glob.glob('/path/to/logs/*.log')
    for log_file in log_files:
        if os.path.getsize(log_file) > 100 * 1024 * 1024:  # 100MB
            os.remove(log_file)
```

## 🔍 调试工具

### 1. 日志分析

```bash
# 实时查看日志
tail -f /var/log/solox/solox.log

# 搜索错误
grep -i error /var/log/solox/solox.log

# 分析访问日志
awk '{print $1}' access.log | sort | uniq -c | sort -nr
```

### 2. 网络诊断

```bash
# 检查端口连通性
telnet localhost 50003

# 检查 HTTP 响应
curl -I http://localhost:50003

# 检查 WebSocket 连接
wscat -c ws://localhost:50003/socket.io/
```

### 3. 性能分析

```python
# 性能分析工具
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 执行需要分析的代码
    apm.collectAll()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # 显示前10个最耗时的函数
```

## 📋 故障排除清单

### 启动前检查

- [ ] Python 版本 >= 3.10
- [ ] 所有依赖包已安装
- [ ] 端口 50003 未被占用
- [ ] 防火墙已配置
- [ ] ADB 工具已安装并配置

### 设备连接检查

- [ ] USB 调试已开启
- [ ] 设备已授权调试
- [ ] ADB 可以识别设备
- [ ] 目标应用正在运行
- [ ] 应用包名正确

### 数据收集检查

- [ ] 设备权限充足
- [ ] 应用在前台运行
- [ ] 网络连接稳定
- [ ] 存储空间充足
- [ ] 系统资源充足

### API 调用检查

- [ ] 请求参数正确
- [ ] 设备 ID 有效
- [ ] 应用包名正确
- [ ] 监控目标支持
- [ ] 网络连接正常

## 🆘 获取帮助

### 1. 收集诊断信息

```bash
#!/bin/bash
# collect_debug_info.sh

echo "=== SoloX 诊断信息 ==="
echo "时间: $(date)"
echo "系统: $(uname -a)"
echo "Python 版本: $(python --version)"
echo "SoloX 版本: $(python -c 'from solox import __version__; print(__version__)')"
echo

echo "=== 设备信息 ==="
adb devices
echo

echo "=== 端口状态 ==="
netstat -tulpn | grep :50003
echo

echo "=== 进程状态 ==="
ps aux | grep solox
echo

echo "=== 最近日志 ==="
tail -50 /var/log/solox/solox.log
```

### 2. 提交问题

提交 Issue 时请包含:
1. 详细的错误信息
2. 系统环境信息
3. 复现步骤
4. 相关日志
5. 设备信息

### 3. 社区支持

- **GitHub Issues**: https://github.com/smart-test-ti/SoloX/issues
- **文档**: https://github.com/smart-test-ti/SoloX/blob/main/README.md
- **FAQ**: https://github.com/smart-test-ti/SoloX/blob/main/FAQ.md

---

*相关文档: [贡献指南](./contribution-guide.md) • [FAQ](./faq.md) • [部署指南](../03-deployment/deployment-guide.md)*
