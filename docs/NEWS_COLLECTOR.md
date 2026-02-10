# 新闻采集功能说明

## 概述

本项目现已支持股票新闻采集功能，可自动采集财经要闻和个股相关新闻。

## 新增文件

### 1. 核心采集器
- `src/collectors/news_collector.py` - 新闻采集器模块

### 2. 数据库扩展
- `src/database/db_manager.py` - 新增新闻相关表和方法

### 3. 脚本工具
- `scripts/collect_news.py` - 新闻采集脚本
- `scripts/news_cron.sh` - 新闻定时任务脚本

### 4. 测试文件
- `tests/test_news_collector.py` - 新闻采集功能测试

## 数据库表结构

### stock_news 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| news_id | VARCHAR(32) | 新闻唯一标识（MD5） |
| stock_code | VARCHAR(20) | 关联股票代码（可选） |
| title | VARCHAR(500) | 新闻标题 |
| content | TEXT | 新闻内容摘要 |
| url | VARCHAR(1000) | 原文链接 |
| source | VARCHAR(100) | 新闻来源 |
| published_at | TIMESTAMP | 发布时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## 主要功能

### 1. 个股新闻采集
```python
from collectors.news_collector import NewsCollector

collector = NewsCollector()
df = collector.collect_individual_news("000001", days=7)
```

### 2. 财经要闻采集
```python
df = collector.collect_financial_news(num_pages=5)
```

### 3. 批量采集关注股票
```python
results = collector.collect_all_stocks_news(days=3)
```

### 4. 数据存储
```python
# 保存到数据库
collector.save_news_to_database(df, stock_code="000001")

# 保存到 CSV
collector.save_news_to_csv(df, prefix="news_000001")
```

## 命令行使用

### 采集所有新闻
```bash
python scripts/collect_news.py
```

### 仅采集财经要闻
```bash
python scripts/collect_news.py --financial
```

### 仅采集关注股票新闻
```bash
python scripts/collect_news.py --stocks
```

### 采集指定股票新闻
```bash
python scripts/collect_news.py --code 000001 --days 7
```

### 与股票数据一起采集
```bash
# 同时采集股票数据和新闻
python src/collectors/stock_collector.py

# 仅采集股票数据
python src/collectors/stock_collector.py --no-news

# 仅采集新闻
python src/collectors/stock_collector.py --news-only
```

## 定时任务配置

### 推荐配置

```bash
# 编辑 crontab
crontab -e

# 早间开盘前采集财经要闻（每天 8:00）
0 8 * * 1-5 /path/to/stock-collector/scripts/news_cron.sh --morning >> /path/to/stock-collector/logs/news_cron.log 2>&1

# 盘中定期采集新闻（每30分钟）
*/30 9-15 * * 1-5 /path/to/stock-collector/scripts/news_cron.sh >> /path/to/stock-collector/logs/news_cron.log 2>&1

# 收盘后完整采集（每天 18:00）
0 18 * * 1-5 /path/to/stock-collector/scripts/news_cron.sh --evening >> /path/to/stock-collector/logs/news_cron.log 2>&1
```

## 数据来源

- 东方财富
- 新浪财经
- 财联社
- 同花顺

## 注意事项

1. **去重机制**: 使用新闻标题、URL 和发布时间生成 MD5 哈希作为唯一标识
2. **重试机制**: 采集失败会自动重试（最多3次，指数退避）
3. **时间筛选**: 支持按天数筛选新闻，避免存储过期内容
4. **字段适配**: 自动适配不同数据源返回的不同字段名

## 未来扩展

- [ ] 新闻情感分析
- [ ] 关键词提取
- [ ] 与股价变动的关联分析
- [ ] 重要新闻推送提醒
