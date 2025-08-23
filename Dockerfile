# SoloX Docker 镜像
# 基于 Python 3.10 构建，包含所有必需依赖

FROM python:3.10-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    android-tools-adb \
    wget \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY setup.py .
COPY pyproject.toml .

# 复制源代码
COPY solox/ ./solox/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs && \
    chmod 755 /app/data /app/logs

# 创建非 root 用户
RUN useradd -m -u 1000 solox && \
    chown -R solox:solox /app

# 切换到非 root 用户
USER solox

# 暴露端口
EXPOSE 50003

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:50003/health || exit 1

# 启动命令
CMD ["python", "-m", "solox", "--host=0.0.0.0", "--port=50003"]

# 元数据标签
LABEL maintainer="SoloX Team <rafacheninc@gmail.com>" \
      version="2.9.3" \
      description="SoloX - Real-time collection tool for Android/iOS performance data" \
      org.opencontainers.image.source="https://github.com/smart-test-ti/SoloX" \
      org.opencontainers.image.documentation="https://github.com/smart-test-ti/SoloX/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT"
