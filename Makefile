# SoloX Makefile
# 简化常用的开发和部署任务

.PHONY: help install install-dev clean test lint format check build run docs verify matrix release-gate

help:
	@echo "SoloX 开发工具"
	@echo "=============="
	@echo ""
	@echo "可用命令:"
	@echo "  install       - 安装项目依赖"
	@echo "  install-dev   - 安装开发依赖"
	@echo "  clean         - 清理构建文件"
	@echo "  test          - 运行测试"
	@echo "  matrix        - 校验兼容矩阵"
	@echo "  release-gate  - 矩阵 + 全量测试（发版门禁）"
	@echo "  lint          - 代码检查"
	@echo "  format        - 代码格式化"
	@echo "  check         - 完整代码检查"
	@echo "  build         - 构建项目"
	@echo "  run           - 启动 SoloX 服务"
	@echo "  verify        - 验证安装"
	@echo ""

install:
	@echo "📦 安装 SoloX 依赖..."
	pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

install-dev:
	@echo "🔧 安装开发依赖..."
	pip install -e ".[dev,test]"
	@echo "✅ 开发环境安装完成"

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

test:
	@echo "🧪 运行测试..."
	python -m pytest tests/ -v --cov=solox --cov-report=html --cov-report=term
	@echo "✅ 测试完成"

matrix:
	python scripts/validate_compatibility_matrix.py

release-gate:
	bash scripts/release_gate.sh

lint:
	@echo "🔍 代码检查..."
	flake8 solox/ --count --select=E9,F63,F7,F82 --show-source --statistics
	@echo "✅ 代码检查完成"

format:
	@echo "🎨 代码格式化..."
	black solox/
	isort solox/
	@echo "✅ 代码格式化完成"

check: format lint test
	@echo "✅ 所有检查完成"

build: clean
	@echo "🏗️ 构建项目..."
	python -m build
	@echo "✅ 构建完成"

run:
	@echo "🚀 启动 SoloX 服务..."
	python -m solox

debug:
	@echo "🐛 启动调试模式..."
	cd solox && python debug.py

docs:
	@echo "📚 文档入口: docs/README.md"
	@echo "  - docs/06-engineering/project-layout.md"
	@echo "  - docs/compatibility-matrix.md"
	@echo "  - scripts/README.md"

verify:
	@echo "✅ 验证 SoloX 安装..."
	python scripts/verify_setup.py
	python -c "import solox; print(f'SoloX 版本: {solox.__version__}')"

install-script:
	chmod +x scripts/install_dependencies.sh
	./scripts/install_dependencies.sh

publish: build
	python -m twine upload dist/*

setup-dev: install-dev
	pre-commit install

health:
	@python --version
	@python -c "import flask; print('Flask OK')" 2>/dev/null || echo "Flask missing"
	@python -c "import solox; print(f'SoloX {solox.__version__}')" 2>/dev/null || echo "SoloX missing"
	@adb version 2>/dev/null || echo "ADB not in PATH"

quick-start: verify run

info:
	@echo "SoloX — 移动性能采集 (Android/iOS)"
	@echo "文档: docs/README.md"
	@echo "脚本: scripts/README.md"
