# 热点板块及新闻采集功能说明

## 概述

本项目新增热点板块及新闻采集功能，支持自动采集涨幅前列的概念板块、行业板块及其相关新闻。

## 新增文件

### 1. 核心采集器
- `src/collectors/hot_sector_collector.py` - 热点板块采集器模块

### 2. 脚本工具
- `scripts/collect_hot_sectors.py` - 热点板块采集命令行工具
- `scripts/hot_sectors_cron.sh` - 热点板块定时任务脚本

### 3. 集成更新
- `src/collectors/stock_collector.py` - 集成热点板块采集功能

## 主要功能

### 1. 概念板块采集
- 采集所有概念板块数据
- 按涨跌幅排序
- 支持指定前N名

### 2. 行业板块采集
- 采集所有行业板块数据
- 按涨跌幅排序
- 支持指定前N名

### 3. 板块相关新闻采集
- 获取板块成分股
- 采集成分股相关新闻
- 自动去重和汇总

### 4. 数据输出
- 保存为CSV文件
- 生成摘要报告
- 支持数据库保存（可选）

## 使用方法

### 命令行工具

```bash
# 采集热点板块及新闻（完整模式）
python scripts/collect_hot_sectors.py

# 仅采集概念板块
python scripts/collect_hot_sectors.py --concept-only --top 20

# 仅采集行业板块
python scripts/collect_hot_sectors.py --industry-only --top 20

# 采集热点板块（不包含新闻）
python scripts/collect_hot_sectors.py --no-news --top 20

# 采集指定板块的新闻
python scripts/collect_hot_sectors.py --sector "AI语料" --sector-type concept
```

### 与主采集器集成

```bash
# 同时采集股票数据、新闻和热点板块
python src/collectors/stock_collector.py --hot-sectors

# 仅采集热点板块
python src/collectors/stock_collector.py --hot-sectors-only
```

### Python API

```python
from collectors.hot_sector_collector import HotSectorCollector

# 创建采集器
collector = HotSectorCollector()

# 采集概念板块前10名
df = collector.collect_concept_sectors(top_n=10)

# 采集行业板块前10名
df = collector.collect_industry_sectors(top_n=10)

# 采集热点板块及新闻
results = collector.collect_hot_sectors_with_news(top_n=10)

# 保存到CSV
collector.save_sectors_to_csv(df, "concept")

# 获取摘要报告
summary = collector.get_hot_sectors_summary(results["sectors"])
print(summary)
```

## 数据结构

### 板块数据字段

| 字段 | 说明 |
|------|------|
| 排名 | 板块排名 |
| 板块名称 | 板块名称 |
| 板块代码 | 板块代码 |
| 最新价 | 板块指数最新价 |
| 涨跌额 | 涨跌金额 |
| 涨跌幅 | 涨跌百分比 |
| 总市值 | 板块总市值 |
| 换手率 | 板块换手率 |
| 上涨家数 | 上涨股票数量 |
| 下跌家数 | 下跌股票数量 |
| 领涨股票 | 领涨股票名称 |
| 领涨股票-涨跌幅 | 领涨股票涨跌幅 |

### 文件输出

板块数据保存路径：`data/sectors/`
板块新闻保存路径：`data/sector_news/`

## 定时任务配置

```bash
# 编辑 crontab
crontab -e

# 每30分钟采集热点板块
*/30 9-15 * * 1-5 /path/to/stock-collector/scripts/hot_sectors_cron.sh >> /path/to/stock-collector/logs/hot_sectors_cron.log 2>&1

# 收盘后采集完整热点板块及新闻
0 18 * * 1-5 /path/to/stock-collector/scripts/hot_sectors_cron.sh --with-news >> /path/to/stock-collector/logs/hot_sectors_cron.log 2>&1
```

## 示例输出

```
📊 热点板块汇总
==================================================

🔥 概念板块 Top 10
----------------------------------------
 1. AI语料     | 涨幅: +6.82% | 领涨: 荣信文化 (+20.00%)
 2. 影视概念   | 涨幅: +5.43% | 领涨: 欢瑞世纪 (+10.06%)
 3. 数字阅读   | 涨幅: +4.98% | 领涨: 掌阅科技 (+10.00%)
...

🔥 行业板块 Top 10
----------------------------------------
 1. 文化传媒   | 涨幅: +4.52% | 领涨: 中文在线 (+15.30%)
 2. 计算机     | 涨幅: +3.21% | 领涨: 浪潮信息 (+10.00%)
...
```

## 注意事项

1. **网络依赖**: 数据采集依赖东方财富等数据源，需要稳定的网络连接
2. **频率限制**: 建议合理设置采集频率，避免过于频繁的请求
3. **数据去重**: 板块新闻会自动去重，同一条新闻不会重复保存
4. **错误处理**: 网络异常时会自动重试，最多重试3次

## 未来扩展

- [ ] 板块资金流向分析
- [ ] 板块热度趋势图
- [ ] 板块轮动分析
- [ ] 板块相关个股联动分析
- [ ] 板块新闻情感分析
