# SoloX Makefile
# 简化常用的开发和部署任务

.PHONY: help install install-dev clean test lint format check build run docs verify

# 默认目标
help:
	@echo "SoloX 开发工具"
	@echo "=============="
	@echo ""
	@echo "可用命令:"
	@echo "  install      - 安装项目依赖"
	@echo "  install-dev  - 安装开发依赖"
	@echo "  clean        - 清理构建文件"
	@echo "  test         - 运行测试"
	@echo "  lint         - 代码检查"
	@echo "  format       - 代码格式化"
	@echo "  check        - 完整代码检查"
	@echo "  build        - 构建项目"
	@echo "  run          - 启动 SoloX 服务"
	@echo "  docs         - 生成文档"
	@echo "  verify       - 验证安装"
	@echo ""

# 安装项目依赖
install:
	@echo "📦 安装 SoloX 依赖..."
	pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 安装开发依赖
install-dev:
	@echo "🔧 安装开发依赖..."
	pip install -e ".[dev,test]"
	@echo "✅ 开发环境安装完成"

# 清理构建文件
clean:
	@echo "🧹 清理构建文件..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✅ 清理完成"

# 运行测试
test:
	@echo "🧪 运行测试..."
	python -m pytest tests/ -v --cov=solox --cov-report=html --cov-report=term
	@echo "✅ 测试完成"

# 代码检查
lint:
	@echo "🔍 代码检查..."
	flake8 solox/
	mypy solox/
	@echo "✅ 代码检查完成"

# 代码格式化
format:
	@echo "🎨 代码格式化..."
	black solox/
	isort solox/
	@echo "✅ 代码格式化完成"

# 完整代码检查
check: format lint test
	@echo "✅ 所有检查完成"

# 构建项目
build: clean
	@echo "🏗️ 构建项目..."
	python -m build
	@echo "✅ 构建完成"

# 启动 SoloX 服务
run:
	@echo "🚀 启动 SoloX 服务..."
	python -m solox

# 启动调试模式
debug:
	@echo "🐛 启动调试模式..."
	cd solox && python debug.py

# 生成文档
docs:
	@echo "📚 生成文档..."
	@echo "文档已在 docs/ 目录中"
	@echo "主要文档:"
	@echo "  - docs/README.md - 文档总览"
	@echo "  - docs/DEPENDENCIES.md - 依赖问题解决方案"
	@echo "  - docs/03-快速启动.md - 快速启动指南"

# 验证安装
verify:
	@echo "✅ 验证 SoloX 安装..."
	python scripts/verify_setup.py
	python -c "import solox; print(f'SoloX 版本: {solox.__version__}')"

# 安装脚本 (Linux/macOS)
install-script:
	@echo "🔧 运行依赖安装脚本..."
	chmod +x scripts/install_dependencies.sh
	./scripts/install_dependencies.sh

# 发布到 PyPI (需要配置 token)
publish: build
	@echo "📦 发布到 PyPI..."
	python -m twine upload dist/*

# 开发环境设置
setup-dev: install-dev
	@echo "⚙️ 设置开发环境..."
	pre-commit install
	@echo "✅ 开发环境设置完成"

# 健康检查
health:
	@echo "🏥 SoloX 健康检查..."
	@echo "Python 版本:"
	@python --version
	@echo ""
	@echo "依赖检查:"
	@python -c "import flask, werkzeug; print(f'Flask: {flask.__version__}, Werkzeug: {werkzeug.__version__}')" 2>/dev/null || echo "❌ Flask/Werkzeug 未安装"
	@python -c "import solox; print(f'✅ SoloX: {solox.__version__}')" 2>/dev/null || echo "❌ SoloX 未安装"
	@echo ""
	@echo "ADB 检查:"
	@adb version 2>/dev/null || echo "⚠️ ADB 未安装或不在 PATH 中"

# 快速启动 (包含依赖检查)
quick-start: verify run

# 显示项目信息
info:
	@echo "📋 SoloX 项目信息"
	@echo "=================="
	@echo "项目名称: SoloX"
	@echo "描述: 实时收集 Android/iOS 性能数据的工具"
	@echo "Python 要求: >= 3.10"
	@echo "主要功能: CPU、内存、网络、FPS、电池监控"
	@echo ""
	@echo "🔗 相关链接:"
	@echo "  GitHub: https://github.com/smart-test-ti/SoloX"
	@echo "  PyPI: https://pypi.org/project/solox/"
	@echo ""
	@echo "📚 文档:"
	@echo "  快速启动: docs/03-快速启动.md"
	@echo "  API 文档: docs/05-API文档.md"
	@echo "  故障排除: docs/08-故障排除.md"
