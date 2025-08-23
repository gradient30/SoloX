# 部署指南

## 🚀 生产环境部署

### 1. 服务器要求

**硬件要求**:
- CPU: 2 核心以上
- 内存: 4GB 以上
- 存储: 20GB 以上可用空间
- 网络: 稳定的网络连接

**软件要求**:
- 操作系统: Ubuntu 18.04+, CentOS 7+, Windows Server 2019+
- Python: 3.10+
- ADB: 最新版本
- 防火墙: 开放服务端口

### 2. 环境准备

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-pip python3.10-venv
sudo apt install android-tools-adb

# CentOS/RHEL
sudo yum install python3 python3-pip
# 手动安装 ADB

# 创建服务用户
sudo useradd -m -s /bin/bash solox
sudo su - solox
```

### 3. 应用部署

```bash
# 创建应用目录
mkdir -p /opt/solox
cd /opt/solox

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装 SoloX
pip install -U solox

# 或从源码安装
git clone https://github.com/smart-test-ti/SoloX.git
cd SoloX
pip install -e .
```

## 🐳 Docker 部署

### 1. Dockerfile

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    android-tools-adb \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录
WORKDIR /app

# 复制应用文件
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 50003

# 设置环境变量
ENV PYTHONPATH=/app
ENV SOLOX_HOST=0.0.0.0
ENV SOLOX_PORT=50003

# 启动命令
CMD ["python", "-m", "solox", "--host=0.0.0.0", "--port=50003"]
```

### 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  solox:
    build: .
    ports:
      - "50003:50003"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - /dev/bus/usb:/dev/bus/usb  # USB 设备访问
    devices:
      - /dev/bus/usb  # USB 设备权限
    privileged: true  # 需要设备访问权限
    environment:
      - SOLOX_HOST=0.0.0.0
      - SOLOX_PORT=50003
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - solox
    restart: unless-stopped
```

### 3. 构建和运行

```bash
# 构建镜像
docker build -t solox:latest .

# 运行容器
docker run -d \
  --name solox \
  -p 50003:50003 \
  -v $(pwd)/data:/app/data \
  -v /dev/bus/usb:/dev/bus/usb \
  --privileged \
  solox:latest

# 使用 Docker Compose (推荐)
docker-compose up -d

# 包含 Nginx 反向代理
docker-compose --profile production up -d

# 包含 Redis 缓存
docker-compose --profile cache up -d

# 完整部署 (Nginx + Redis)
docker-compose --profile production --profile cache up -d
```

### 4. 容器管理

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f solox

# 重启服务
docker-compose restart solox

# 更新镜像
docker-compose pull
docker-compose up -d

# 清理
docker-compose down
docker system prune -f
```

## ⚙️ 系统服务配置

### 1. Systemd 服务 (Linux)

```ini
# /etc/systemd/system/solox.service
[Unit]
Description=SoloX Performance Monitor
After=network.target

[Service]
Type=simple
User=solox
Group=solox
WorkingDirectory=/opt/solox
Environment=PATH=/opt/solox/venv/bin
ExecStart=/opt/solox/venv/bin/python -m solox --host=0.0.0.0 --port=50003
Restart=always
RestartSec=10

# 日志配置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=solox

# 安全配置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/solox/data /opt/solox/logs

[Install]
WantedBy=multi-user.target
```

```bash
# 启用和启动服务
sudo systemctl daemon-reload
sudo systemctl enable solox
sudo systemctl start solox

# 查看服务状态
sudo systemctl status solox

# 查看日志
sudo journalctl -u solox -f
```

### 2. Windows 服务

```python
# solox_service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
from solox.web import main

class SoloXService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SoloXService"
    _svc_display_name_ = "SoloX Performance Monitor"
    _svc_description_ = "SoloX mobile performance monitoring service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        # 启动 SoloX 服务
        main(host='0.0.0.0', port=50003)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(SoloXService)
```

```cmd
# 安装服务
python solox_service.py install

# 启动服务
python solox_service.py start

# 停止服务
python solox_service.py stop

# 卸载服务
python solox_service.py remove
```

## 🔒 安全配置

### 1. 防火墙配置

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 50003/tcp
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=50003/tcp
sudo firewall-cmd --reload

# Windows
netsh advfirewall firewall add rule name="SoloX" dir=in action=allow protocol=TCP localport=50003
```

### 2. SSL/TLS 配置

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    location / {
        proxy_pass http://127.0.0.1:50003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. 访问控制

```python
# 在 solox/web.py 中添加认证中间件
from functools import wraps
from flask import request, abort

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_token = request.headers.get('Authorization')
        if not auth_token or not validate_token(auth_token):
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

def validate_token(token):
    # 实现 token 验证逻辑
    return token == "your-secret-token"

# 在 API 路由中使用
@api.route('/apm/collect')
@require_auth
def collect_performance():
    # API 实现
    pass
```

## 📊 监控和日志

### 1. 应用监控

```python
# 健康检查端点
@app.route('/health')
def health_check():
    return {
        'status': 'ok',
        'timestamp': time.time(),
        'version': __version__,
        'uptime': time.time() - start_time
    }

# 指标端点
@app.route('/metrics')
def metrics():
    return {
        'active_connections': get_active_connections(),
        'total_requests': get_total_requests(),
        'memory_usage': get_memory_usage(),
        'cpu_usage': get_cpu_usage()
    }
```

### 2. 日志配置

```python
# 日志配置
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

# 文件日志
file_handler = RotatingFileHandler(
    '/opt/solox/logs/solox.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'
))

app.logger.addHandler(file_handler)
```

## 🔧 性能优化

### 1. 应用优化

```python
# 连接池配置
from flask import Flask
from werkzeug.serving import WSGIRequestHandler

class CustomRequestHandler(WSGIRequestHandler):
    def setup(self):
        super().setup()
        # 设置 TCP_NODELAY
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

# 启动配置
app.run(
    host='0.0.0.0',
    port=50003,
    threaded=True,
    request_handler=CustomRequestHandler
)
```

### 2. 负载均衡

```nginx
# nginx 负载均衡配置
upstream solox_backend {
    server 127.0.0.1:50003;
    server 127.0.0.1:50004;
    server 127.0.0.1:50005;
}

server {
    listen 80;
    location / {
        proxy_pass http://solox_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔄 备份和恢复

### 1. 数据备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/solox/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="solox_backup_${DATE}.tar.gz"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据
tar -czf $BACKUP_DIR/$BACKUP_FILE \
    /opt/solox/data \
    /opt/solox/logs \
    /opt/solox/config

# 清理旧备份 (保留最近 7 天)
find $BACKUP_DIR -name "solox_backup_*.tar.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_DIR/$BACKUP_FILE"
```

### 2. 自动备份

```bash
# 添加到 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * /opt/solox/scripts/backup.sh
```

### 3. 恢复流程

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "用法: $0 <backup_file>"
    exit 1
fi

# 停止服务
sudo systemctl stop solox

# 恢复数据
tar -xzf $BACKUP_FILE -C /

# 启动服务
sudo systemctl start solox

echo "恢复完成"
```

---

*相关文档: [Docker配置](./docker-guide.md) • [运维监控](./monitoring-guide.md) • [故障排除](../05-issues/troubleshooting.md)*
