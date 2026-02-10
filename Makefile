# Makefile - 常用命令 shortcuts

.PHONY: help install test lint format clean run db-init

# 默认目标
help:
	@echo "可用的命令："
	@echo "  make install      - 安装依赖"
	@echo "  make install-dev  - 安装开发依赖"
	@echo "  make test         - 运行测试"
	@echo "  make test-cov     - 运行测试并生成覆盖率报告"
	@echo "  make lint         - 运行代码检查"
	@echo "  make format       - 格式化代码"
	@echo "  make type-check   - 运行类型检查"
	@echo "  make clean        - 清理临时文件"
	@echo "  make run          - 运行采集程序"
	@echo "  make db-init      - 初始化数据库"
	@echo "  make claude       - 启动 Claude Code"

# 安装依赖
install:
	pip install -r requirements.txt

# 安装开发依赖
install-dev:
	pip install -r requirements.txt
	pre-commit install

# 运行测试
test:
	pytest tests/ -v

# 运行测试并生成覆盖率报告
test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# 代码检查
lint:
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

# 格式化代码
format:
	black src/ tests/
	isort src/ tests/

# 类型检查
type-check:
	mypy src/

# 清理临时文件
clean:
	rm -rf __pycache__ .pytest_cache htmlcov .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# 运行采集程序
run:
	python src/collectors/stock_collector.py

# 初始化数据库
db-init:
	python scripts/init_db.py

# 启动 Claude Code
claude:
	claude

# 提交前检查（运行所有检查）
check: format lint type-check test
	@echo "✅ 所有检查通过！"
