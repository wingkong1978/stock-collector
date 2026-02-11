```markdown
# Stock Collector

一个功能全面的股票数据采集与分析工具，集成了多源行情抓取、实时热点追踪、技术指标计算及新闻情感分析，助力量化投资与市场研究。

## ✨ 主要功能

-   **多源数据采集**：支持东方财富、新浪财经等主流数据源的实时行情与新闻采集。
-   **热点板块追踪**：自动捕捉市场热点板块及相关资讯。
-   **技术分析引擎**：内置 RSI、MACD、布林带（BOLL）、移动平均线（MA）等常用技术指标计算。
-   **情感分析**：基于自然语言处理技术分析股票新闻情感倾向。
-   **数据可视化**：自动生成 K 线图及技术指标分析图表。
-   **数据持久化**：基于 PostgreSQL 存储历史行情与新闻数据。
-   **报表导出**：支持将行情数据和分析结果导出为 Excel 文件。
-   **自动化任务**：内置定时任务，支持自动采集行情与新闻。

## 🛠️ 技术栈

-   **语言**: Python
-   **数据库**: PostgreSQL
-   **数据处理**: Pandas, NumPy
-   **可视化**: Matplotlib / Plotly
-   **网络爬虫**: Requests, BeautifulSoup / lxml
-   **任务调度**: APScheduler

## 🚀 快速开始

### 1. 环境准备
确保已安装 Python 3.8+ 和 PostgreSQL 数据库。

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置数据库
修改 `src/database/` 下的配置文件，填入您的 PostgreSQL 连接信息。

### 4. 运行采集
```bash
# 运行多源行情采集
python src/collectors/multi_source_collector.py

# 运行新闻情感分析
python src/analytics/sentiment_analyzer.py
```

更多详细文档请参考项目内部文档。
```