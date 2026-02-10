# Stock Collector 📈

定时收集股票信息的数据采集与监控系统。

## 🎯 项目简介

本项目用于定时采集股票市场的实时数据和历史数据，支持多种数据源，并提供数据存储和分析功能。

## 📁 项目结构

```
stock-collector/
├── config/                 # 配置文件
│   ├── stocks.json        # 关注的股票列表
│   └── settings.json      # 采集设置
├── src/                    # 源代码
│   ├── collectors/        # 数据采集模块
│   │   ├── stock_collector.py     # 股票数据采集器
│   │   └── news_collector.py      # 新闻采集器 ⭐ NEW
│   ├── database/          # 数据库模块 (PostgreSQL)
│   │   └── db_manager.py  # 数据库管理器
│   ├── storage/           # 数据存储模块
│   └── utils/             # 工具函数
├── data/                   # 数据存储目录
│   ├── raw/               # 原始数据
│   ├── processed/         # 处理后的数据
│   └── news/              # 新闻数据 ⭐ NEW
├── scripts/                # 脚本文件
│   ├── daily_collect.sh   # 定时采集脚本
│   ├── init_db.py         # 数据库初始化脚本
│   ├── collect_news.py    # 新闻采集脚本 ⭐ NEW
│   └── news_cron.sh       # 新闻定时任务 ⭐ NEW
├── logs/                   # 日志文件
├── requirements.txt        # Python依赖
├── .env.example           # 环境变量示例
├── README.md              # 项目说明
└── .gitignore             # Git忽略文件
```

## 🚀 功能特性

- 📊 **多数据源支持**：东方财富、同花顺、新浪财经等
- 📰 **新闻采集**：自动采集股票相关新闻和财经要闻
- ⏰ **定时采集**：支持定时任务，自动获取股票数据
- 💾 **数据存储**：支持 CSV、JSON、SQLite、PostgreSQL 等多种格式
- 🗄️ **PostgreSQL 数据库**：专业的数据库支持，高效的数据查询
- 📈 **数据监控**：实时监控股价变动，异常提醒
- 🔧 **可扩展**：模块化设计，易于添加新的数据源

## 📦 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt
```

## ⚙️ 配置说明

1. 编辑 `config/stocks.json` 添加关注的股票：
```json
{
  "stocks": [
    {"code": "000001", "name": "平安银行", "market": "sz"},
    {"code": "600000", "name": "浦发银行", "market": "sh"},
    {"code": "00700", "name": "腾讯控股", "market": "hk"}
  ]
}
```

2. 编辑 `config/settings.json` 设置采集参数：
```json
{
  "collection_interval": 300,
  "data_format": "csv",
  "storage_path": "./data",
  "log_level": "INFO"
}
```

### 3. PostgreSQL 数据库配置（可选）

1. 安装 PostgreSQL 并创建数据库：
```bash
# Ubuntu/Debian
sudo apt install postgresql

# CentOS/RHEL
sudo yum install postgresql-server
```

2. 创建数据库和用户：
```sql
CREATE DATABASE stockdb;
CREATE USER stockuser WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE stockdb TO stockuser;
```

3. 复制环境变量文件并配置密码：
```bash
cp .env.example .env
# 编辑 .env 文件，设置 DB_PASSWORD
```

4. 初始化数据库表：
```bash
python scripts/init_db.py
```

## 🏃 使用方法

### 手动运行采集

#### 股票数据采集
```bash
python src/collectors/stock_collector.py
```

#### 新闻数据采集 ⭐ NEW
```bash
# 采集所有新闻（财经要闻 + 股票新闻）
python scripts/collect_news.py

# 仅采集财经要闻
python scripts/collect_news.py --financial

# 仅采集关注股票的新闻
python scripts/collect_news.py --stocks

# 采集指定股票的新闻
python scripts/collect_news.py --code 000001

# 指定采集最近几天的新闻（默认3天）
python scripts/collect_news.py --days 7

# 仅保存到 CSV，不写入数据库
python scripts/collect_news.py --no-db
```

#### 组合采集（股票 + 新闻）
```bash
# 同时采集股票数据和新闻
python src/collectors/stock_collector.py

# 只采集股票数据，不采集新闻
python src/collectors/stock_collector.py --no-news

# 仅采集新闻
python src/collectors/stock_collector.py --news-only
```

### 数据库操作示例

#### 股票数据操作
```python
from src.database.db_manager import DatabaseManager

# 创建数据库管理器
db = DatabaseManager()

# 初始化表结构
db.init_tables()

# 插入股票数据
db.insert_stock("000001", "平安银行", "sz")

# 插入价格数据
db.insert_stock_price("000001", 12.50, 1.25, 1000000, 12500000.00)

# 查询最新数据
prices = db.get_latest_prices(stock_code="000001", limit=10)

# 关闭连接
db.close()
```

#### 新闻数据操作 ⭐ NEW
```python
from src.database.db_manager import DatabaseManager
from src.collectors.news_collector import NewsCollector

# 创建新闻采集器
news_collector = NewsCollector()

# 采集个股新闻
df = news_collector.collect_individual_news("000001", days=7)

# 保存到数据库
news_collector.save_news_to_database(df, stock_code="000001")

# 使用数据库管理器查询新闻
db = DatabaseManager()

# 获取指定股票的最新新闻
news = db.get_stock_news(stock_code="000001", limit=50)

# 获取最近7天的新闻（所有股票）
recent_news = db.get_stock_news(days=7, limit=100)

# 获取新闻统计
stats = db.get_news_stats(days=7)
print(f"最近7天共采集 {stats['total_count']} 条新闻")

# 批量插入新闻
news_data = [
    {
        "news_id": "md5_hash_id",
        "stock_code": "000001",
        "title": "新闻标题",
        "content": "新闻内容摘要",
        "url": "https://example.com/news/1",
        "source": "新浪财经",
        "published_at": datetime(2024, 1, 15, 10, 30, 0)
    }
]
db.insert_stock_news_batch(news_data)
```

### 设置定时任务

#### 股票数据采集
```bash
# 添加到 crontab（每5分钟采集一次）
*/5 * * * * cd /path/to/stock-collector && python src/collectors/stock_collector.py >> logs/cron.log 2>&1
```

#### 新闻数据采集 ⭐ NEW
```bash
# 编辑 crontab
crontab -e

# 早间开盘前采集财经要闻（每天 8:00）
0 8 * * 1-5 /source_code/stock-collector/scripts/news_cron.sh --morning >> /source_code/stock-collector/logs/news_cron.log 2>&1

# 盘中定期采集新闻（每30分钟）
*/30 9-15 * * 1-5 /source_code/stock-collector/scripts/news_cron.sh >> /source_code/stock-collector/logs/news_cron.log 2>&1

# 收盘后完整采集（每天 18:00）
0 18 * * 1-5 /source_code/stock-collector/scripts/news_cron.sh --evening >> /source_code/stock-collector/logs/news_cron.log 2>&1
```

## 📊 数据源

- [东方财富](https://www.eastmoney.com/)
- [同花顺](https://www.10jqka.com.cn/)
- [新浪财经](https://finance.sina.com.cn/)
- [腾讯财经](https://finance.qq.com/)

## 🛠️ 技术栈

- **Python 3.9+**
- **akshare**: 股票数据采集
- **pandas**: 数据处理
- **schedule**: 定时任务
- **requests**: HTTP 请求

## 📝 开发计划

- [x] 基础数据采集功能
- [x] 支持多数据源
- [x] **新闻采集功能** ✅ 已完成
- [ ] 数据可视化面板
- [ ] 股价异常提醒
- [ ] 历史数据分析
- [ ] Docker 部署支持

## 📄 许可证

MIT License

## 👤 作者

Created by OpenClaw Agent
