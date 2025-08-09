# 部署指南

## 1. 系统要求

### 1.1 软件依赖

- **Python**: 3.10 或更高版本
- **ADB**: Android Debug Bridge (SoloX 自带 ADB，但可能不适用于所有系统)
- **iTunes**: Windows 用户如需测试 iOS 需要安装 (不支持 iOS17)

### 1.2 硬件要求

- 支持的操作系统:
  - Windows 10 或更高版本
  - macOS 10.15 或更高版本
  - Linux (Ubuntu 18.04 或更高版本推荐)

## 2. 安装方式

### 2.1 默认安装

```shell
pip install -U solox
```

### 2.2 镜像安装

```shell
pip install -i https://mirrors.ustc.edu.cn/pypi/web/simple -U solox
```

> 如果网络无法通过默认方式下载，请尝试使用镜像安装，但可能无法获取最新版本。

## 3. 快速启动

### 3.1 默认启动

```shell
python -m solox
```

### 3.2 自定义启动

```shell
python -m solox --host=ip --port=port
```

## 4. 部署选项

### 4.1 后台运行

#### macOS/Linux

```shell
nohup python3 -m solox &
```

#### Windows

```shell
start /min python3 -m solox &
```

### 4.2 Docker 部署

#### 使用 Dockerfile 构建

```shell
docker build -t solox .
docker run -d -p 50003:50003 solox
```

#### 使用 docker-compose

```shell
docker-compose up -d
```

### 4.3 Gunicorn 部署

```shell
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:50003 solox.web:app
```

## 5. 远程访问配置

### 5.1 本地设备远程访问

需要在连接移动设备的 PC 机器启动 solox 服务，然后将 host 配置在 SoloX 设置页的 Agent 中（右上角红点的设置按钮可查看）。

可以不用在同一个局域网，但是要保证本地的网络防火墙是放开的，可以让云机器访问。

### 5.2 云服务器部署

1. 在云服务器上安装 SoloX
2. 启动服务并绑定公网 IP
3. 配置安全组开放相应端口（默认 50003）
4. 通过浏览器访问 `http://your-server-ip:50003`

## 6. 环境变量配置

### 6.1 可配置参数

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| SOLOX_HOST | 监听主机地址 | 0.0.0.0 |
| SOLOX_PORT | 监听端口 | 50003 |
| ADB_PATH | ADB 可执行文件路径 | None |

### 6.2 设置示例

```bash
export SOLOX_HOST=0.0.0.0
export SOLOX_PORT=8080
python -m solox
```

## 7. 系统服务部署（Linux）

创建 systemd 服务文件 `/etc/systemd/system/solox.service`：

```ini
[Unit]
Description=SoloX Performance Monitoring Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/solox
ExecStart=/usr/bin/python3 -m solox
Restart=always

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable solox
sudo systemctl start solox
```

## 8. 性能优化建议

1. **资源分配**: 确保服务器有足够的内存和 CPU 资源
2. **并发控制**: 根据硬件配置限制同时连接的设备数量
3. **存储管理**: 定期清理日志和报告文件
4. **网络优化**: 在局域网内部署以减少网络延迟