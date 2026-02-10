# CLAUDE.md - Claude Code 配置

这是 Claude Code 的配置文件，定义了在 stock-collector 项目中与 AI 助手协作的规范。

## 🎯 项目概述

**stock-collector** 是一个股票数据采集系统，使用 Python 开发，支持 PostgreSQL 数据库。

### 技术栈
- Python 3.9+
- PostgreSQL (psycopg2)
- akshare (股票数据)
- pandas (数据处理)
- loguru (日志)

## 📝 开发规范

### 代码风格
- **遵循 PEP 8** - 4空格缩进，最大100字符行宽
- **类型注解** - 所有函数必须添加类型提示
- **文档字符串** - 使用 Google Style
- **命名规范** - snake_case（函数/变量），PascalCase（类）

### 错误处理
```python
# 使用具体异常
try:
    df = ak.stock_zh_a_spot_em()
except requests.RequestException as e:
    logger.error(f"网络请求失败: {e}")
    raise DataFetchError(f"获取失败: {e}")

# 使用 loguru 记录日志
logger.info(f"采集完成: {stock_code}")
logger.exception("处理异常")  # 自动包含堆栈
```

### 数据库操作
- 使用上下文管理器或 try-finally 确保连接关闭
- 批量插入代替逐条插入
- 参数化查询防止 SQL 注入

## 🤖 与 Claude 协作指南

### 请求代码审查
当需要 Claude 审查代码时：
```
/review
请审查 src/collectors/stock_collector.py 的以下方面：
1. 是否符合 PEP 8 规范
2. 错误处理是否完善
3. 是否有性能问题
4. 类型注解是否正确
```

### 请求重构
```
/refactor
优化 src/database/db_manager.py 的批量插入方法：
- 添加事务支持
- 实现分批处理大数据量
- 添加性能计时
```

### 生成文档
```
/doc
为 DatabaseManager 类生成详细的 API 文档，包括：
- 所有方法的说明
- 参数和返回值
- 使用示例
```

### 运行测试
```
/test
运行所有测试并确保通过
```

## 📂 项目结构

```
stock-collector/
├── src/
│   ├── collectors/       # 数据采集模块
│   │   └── stock_collector.py
│   └── database/         # 数据库模块
│       └── db_manager.py
├── config/               # 配置文件
│   ├── stocks.json
│   └── settings.json
├── tests/                # 测试目录
├── scripts/              # 脚本文件
├── docs/                 # 文档
├── DEVELOPMENT_GUIDE.md  # 开发规范
└── README.md            # 项目说明
```

## 🔧 常用命令

```bash
# 运行采集程序
python src/collectors/stock_collector.py

# 初始化数据库
python scripts/init_db.py

# 运行测试
pytest tests/

# 代码格式化
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# 代码检查
flake8 src/ tests/
```

## ⚠️ 注意事项

1. **数据库连接** - 操作完成后必须关闭连接
2. **API 限制** - akshare 可能有请求频率限制，添加适当的延迟
3. **错误处理** - 不要捕获所有异常，要具体处理
4. **日志记录** - 关键操作必须记录日志
5. **类型安全** - 使用类型注解和 mypy 检查

## 🐛 调试技巧

### 查看日志
```bash
tail -f logs/stock_collector.log
tail -f logs/stock_collector_error.log
```

### 数据库调试
```python
# 启用 SQL 日志
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## 📚 参考

- **开发规范**: DEVELOPMENT_GUIDE.md
- **API 文档**: docs/api.md
- **变更日志**: CHANGELOG.md

---

**提示**: 在与 Claude 协作时，请清晰描述需求，提供必要的上下文，并遵循上述规范。
