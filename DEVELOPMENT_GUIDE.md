# 股票数据采集系统 - 开发规范

## 📋 规范概述

本文档定义了 stock-collector 项目的开发规范，所有代码贡献者必须遵循。

---

## 🎯 代码规范

### 1. Python 代码风格

#### 1.1 基础规范
- **遵循 PEP 8** - 使用 4 空格缩进
- **行长度限制** - 最大 100 字符
- **编码格式** - UTF-8
- **文件结尾** - 保留一个空行

#### 1.2 导入规范
```python
# 标准库导入
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# 第三方库导入
import akshare as ak
import pandas as pd
from loguru import logger

# 本地模块导入
from database.db_manager import get_db_manager
```

#### 1.3 命名规范
| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `StockCollector` |
| 函数/方法 | snake_case | `collect_realtime_data` |
| 变量 | snake_case | `stock_code` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| 私有方法 | _snake_case | `_load_config` |

#### 1.4 类型注解
**所有函数必须添加类型注解：**
```python
def collect_realtime_data(self) -> Optional[pd.DataFrame]:
    """采集实时行情数据"""
    pass

def insert_stock(self, code: str, name: str, market: str) -> bool:
    """插入股票信息"""
    pass
```

#### 1.5 文档字符串
**使用 Google Style：**
```python
def fetch_stock_data(
    symbol: str, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    获取股票历史数据
    
    Args:
        symbol: 股票代码，如 "000001"
        start_date: 开始日期，格式 "YYYYMMDD"，默认为 None
        end_date: 结束日期，格式 "YYYYMMDD"，默认为 None
    
    Returns:
        包含股票数据的 DataFrame，列包括：
        - date: 交易日期
        - open: 开盘价
        - high: 最高价
        - low: 最低价
        - close: 收盘价
        - volume: 成交量
    
    Raises:
        ValueError: 股票代码格式错误
        DataFetchError: 数据获取失败
    
    Example:
        >>> df = fetch_stock_data("000001", "20240101", "20240131")
        >>> print(len(df))
        22
    """
```

### 2. 错误处理规范

#### 2.1 异常层次
```python
# 自定义异常
class StockCollectorError(Exception):
    """基础异常类"""
    pass

class ConfigError(StockCollectorError):
    """配置错误"""
    pass

class DataFetchError(StockCollectorError):
    """数据获取错误"""
    pass

class DatabaseError(StockCollectorError):
    """数据库错误"""
    pass
```

#### 2.2 异常处理原则
```python
# ✅ 正确 - 具体异常处理
try:
    df = ak.stock_zh_a_spot_em()
except requests.RequestException as e:
    logger.error(f"网络请求失败: {e}")
    raise DataFetchError(f"获取股票数据失败: {e}")
except pd.errors.EmptyDataError:
    logger.warning("返回数据为空")
    return None

# ❌ 错误 - 捕获所有异常
try:
    df = ak.stock_zh_a_spot_em()
except:  # 不要这样做
    pass
```

#### 2.3 日志记录规范
```python
# 使用 loguru，不要直接使用 print
from loguru import logger

# 不同级别的日志
logger.debug("调试信息 - 开发时使用")
logger.info("一般信息 - 程序正常流程")
logger.warning("警告信息 - 需要注意但不是错误")
logger.error("错误信息 - 程序可以继续运行")
logger.exception("异常信息 - 自动包含堆栈")
logger.critical("严重错误 - 程序可能无法继续")

# 日志格式
logger.info(f"采集完成: {stock_code}, 价格: {price}")
logger.error(f"数据库连接失败: {e}, 重试次数: {retry_count}")
```

### 3. 数据库操作规范

#### 3.1 连接管理
```python
# 使用上下文管理器
with get_db_manager() as db:
    db.insert_stock(code, name, market)
    # 自动提交和关闭

# 或者使用 try-finally
db = get_db_manager()
try:
    db.insert_stock(code, name, market)
    db.commit()
except Exception as e:
    db.rollback()
    raise
finally:
    db.close()
```

#### 3.2 SQL 规范
```python
# ✅ 使用参数化查询
sql = "SELECT * FROM stocks WHERE code = %s"
cursor.execute(sql, (stock_code,))

# ❌ 不要拼接 SQL
sql = f"SELECT * FROM stocks WHERE code = '{stock_code}'"  # 安全风险
```

### 4. 性能优化规范

#### 4.1 批量操作
```python
# ✅ 批量插入 - 更高效
price_data = []
for row in df.iterrows():
    price_data.append((code, price, volume))
db.insert_batch(price_data)  # 一次性插入

# ❌ 逐条插入 - 慢
for row in df.iterrows():
    db.insert_one(code, price, volume)  # 多次数据库操作
```

#### 4.2 并发处理
```python
from concurrent.futures import ThreadPoolExecutor

# 使用线程池并发处理
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(fetch_index, idx) 
        for idx in indexes
    ]
    results = [f.result() for f in futures]
```

---

## 🧪 测试规范

### 1. 测试结构
```
tests/
├── __init__.py
├── test_collectors/
│   ├── __init__.py
│   └── test_stock_collector.py
├── test_database/
│   ├── __init__.py
│   └── test_db_manager.py
├── conftest.py          # pytest 配置文件
└── fixtures/            # 测试数据
    └── sample_data.json
```

### 2. 测试命名规范
```python
# 测试文件: test_被测模块.py
# 测试函数: test_被测功能_条件_预期结果

def test_collect_realtime_data_success():
    """测试正常采集实时数据"""
    pass

def test_collect_realtime_data_network_error():
    """测试网络错误时的处理"""
    pass

def test_insert_stock_duplicate():
    """测试插入重复股票的处理"""
    pass
```

### 3. 测试覆盖率要求
- **单元测试覆盖率** - 不低于 80%
- **关键路径** - 必须 100% 覆盖
- **异常分支** - 必须测试

---

## 📝 文档规范

### 1. README 规范
必须包含以下部分：
- 项目简介
- 安装说明
- 快速开始
- 配置说明
- API 文档链接
- 贡献指南
- 许可证

### 2. 代码注释规范
```python
# ✅ 好的注释 - 解释为什么
# 使用批量插入减少数据库往返次数
self.db_manager.insert_batch(data)

# ❌ 不好的注释 - 重复代码
# 插入数据到数据库
self.db_manager.insert(data)
```

### 3. 变更日志 (CHANGELOG.md)
```markdown
# Changelog

## [1.1.0] - 2024-02-11
### Added
- 添加 PostgreSQL 数据库支持
- 实现批量数据插入功能

### Changed
- 优化股票数据采集性能
- 改进错误处理机制

### Fixed
- 修复指数数据为空时的崩溃问题
```

---

## 🔄 Git 工作流规范

### 1. 分支策略
```
main          # 生产分支，永远可部署
develop       # 开发分支，集成测试
feature/*     # 功能分支，从 develop 创建
hotfix/*      # 热修复分支，从 main 创建
release/*     # 发布分支，从 develop 创建
```

### 2. 提交信息规范
```
类型: 简短描述（不超过50字符）

详细描述（可选，每行不超过72字符）

关联 issue: #123
```

**类型说明：**
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式调整（不影响功能）
- `refactor:` 重构
- `perf:` 性能优化
- `test:` 测试相关
- `chore:` 构建/工具相关

**示例：**
```bash
git commit -m "feat: 添加股票批量插入功能

- 实现 insert_stock_prices_batch 方法
- 使用 execute_values 提高插入性能
- 添加批量插入的单元测试

关联 issue: #45"
```

### 3. 代码审查清单
- [ ] 代码符合 PEP 8 规范
- [ ] 所有函数都有类型注解
- [ ] 添加了适当的错误处理
- [ ] 包含单元测试
- [ ] 更新了相关文档
- [ ] 没有硬编码的敏感信息
- [ ] 日志记录适当

---

## 🛠️ 工具配置

### 1. Pre-commit 钩子
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

### 2. IDE 配置
推荐使用 VS Code，配置如下：
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [100]
}
```

---

## 🤖 Claude Code 使用规范

### 1. 启动 Claude Code
```bash
cd /source_code/stock-collector
claude
```

### 2. 常用指令
```
/review          # 代码审查
/test            # 运行测试
/doc             # 生成文档
/refactor        # 重构代码
/fix             # 修复问题
```

### 3. 最佳实践
- 使用 `/init` 创建 CLAUDE.md 配置文件
- 定期使用 `/review` 检查代码质量
- 使用 `/test` 确保修改不破坏现有功能
- 提交前使用 `/doc` 更新文档

---

## ✅ 检查清单

在提交代码前，请确认：

- [ ] 代码遵循 PEP 8 规范
- [ ] 所有函数都有类型注解和文档字符串
- [ ] 添加了适当的单元测试
- [ ] 通过了所有测试
- [ ] 更新了 README 和 CHANGELOG
- [ ] 没有安全漏洞（SQL注入、硬编码密码等）
- [ ] 日志记录适当
- [ ] 提交信息符合规范

---

## 📚 参考资源

- [PEP 8 - Python 代码风格指南](https://pep8.org/)
- [Google Python 风格指南](https://google.github.io/styleguide/pyguide.html)
- [Python 类型注解最佳实践](https://docs.python.org/3/library/typing.html)
- [Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code)

---

**最后更新：** 2024-02-11
**维护者：** OpenClaw Agent
**版本：** 1.0.0
