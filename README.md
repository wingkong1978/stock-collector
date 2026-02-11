<div align="center">

# 📈 Stock Collector

<!-- 徽章 -->
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL-blue.svg)
![Tests](https://img.shields.io/badge/tests-9%20passed-brightgreen.svg)

**功能全面的股票数据采集、分析与可视化工具**

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [使用文档](#-使用文档) • [项目结构](#-项目结构)

</div>

---

## 📖 项目简介

`stock-collector` 是一个基于 Python 开发的股票数据采集与分析系统。支持多数据源实时行情采集、新闻情感分析、技术指标计算和数据可视化，为量化投资和股票研究提供完整的数据解决方案。

**核心能力：**
- ✅ 多数据源自动切换（东方财富、新浪财经）
- ✅ 实时行情与新闻采集
- ✅ 技术指标计算（RSI、MACD、布林带、移动平均线）
- ✅ 新闻情感分析（正面/负面/中性分类）
- ✅ 数据可视化（价格图、技术指标图、情感分析图）
- ✅ Excel 数据导出
- ✅ 定时任务自动化

---

## ✨ 功能特性

### 📊 数据采集
- [x] **多源行情采集** - 支持东方财富、新浪财经，自动故障切换
- [x] **个股新闻采集** - 实时采集股票相关新闻资讯
- [x] **财经要闻采集** - 采集市场整体财经新闻
- [x] **热点板块追踪** - 概念板块、行业板块涨幅排行及新闻

### 🔬 数据分析
- [x] **技术指标计算**
  - RSI（相对强弱指数）
  - MACD（指数平滑异同移动平均线）
  - 布林带（Bollinger Bands）
  - 移动平均线（MA5/10/20/60）
- [x] **价格趋势分析** - 涨跌统计、波动率计算
- [x] **成交量分析** - 量能变化、买卖力量对比
- [x] **新闻情感分析** - 基于词典的情感分类，关键词提取

### 📈 数据可视化
- [x] **价格趋势图** - K线图 + 移动平均线 + 布林带
- [x] **技术指标图** - RSI、MACD、涨跌幅柱状图
- [x] **情感分析图** - 情感分布饼图、柱状图

### 💾 数据导出与存储
- [x] **Excel 导出** - 支持 .xlsx 格式，含统计信息
- [x] **PostgreSQL 存储** - 结构化数据持久化
- [x] **CSV 文件存储** - 轻量级数据保存

### ⏰ 自动化
- [x] **定时任务** - 系统 crontab 定时采集
- [x] **自动降级** - 主数据源失败自动切换备用源
- [x] **去重机制** - MD5 哈希去重，避免重复数据

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL（可选，支持 CSV 作为备选）

### 安装

```bash
# 克隆仓库
git clone https://github.com/wingkong1978/stock-collector.git
cd stock-collector

# 安装依赖
pip install -r requirements.txt
```

### 配置

编辑 `config/settings.json`：
```json
{
  "storage": {
    "type": "csv",
    "path": "data"
  }
}
```

### 运行

```bash
# 股票分析（含技术指标和情感分析）
python scripts/analyze_stock.py --code 600584 --all --chart

# 数据导出
python scripts/export_data.py --stock 600584

# 运行测试
pytest tests/ -v
```

---

## 📚 使用文档

### 1. 股票分析

分析指定股票的技术指标和新闻情感：

```bash
python scripts/analyze_stock.py --code 600584 --all --chart
```

输出：
- 价格趋势分析
- 技术指标（RSI、MACD、布林带）
- 成交量分析
- 新闻情感分析
- 可视化图表（PNG）

### 2. 数据导出

导出股票数据到 Excel：

```bash
# 导出所有数据
python scripts/export_data.py

# 导出指定股票
python scripts/export_data.py --stock 600584

# 只导出新闻
python scripts/export_data.py --type news
```

### 3. 定时任务配置

编辑 crontab：

```bash
# 工作日 8:30-17:00 每30分钟采集
0,30 8-17 * * 1-5 cd /source_code/stock-collector && bash scripts/collect_changdian.sh
```

### 4. 使用 Claude API

```bash
# 生成项目 README
python scripts/claude_api_client.py --generate-readme

# 直接提问
python scripts/claude_api_client.py --prompt "你的问题"
```

---

## 🏗️ 项目结构

```
stock-collector/
├── src/
│   ├── collectors/          # 数据采集模块
│   │   ├── multi_source_collector.py    # 多数据源采集
│   │   ├── news_collector.py            # 新闻采集
│   │   ├── hot_sector_collector.py      # 热点板块
│   │   └── data_exporter.py             # 数据导出
│   ├── analytics/           # 数据分析模块
│   │   ├── stock_analyzer.py            # 技术分析
│   │   ├── sentiment_analyzer.py        # 情感分析
│   │   └── chart_generator.py           # 图表生成
│   ├── database/            # 数据库模块
│   │   └── db_manager.py                # PostgreSQL 管理
│   └── storage/             # 存储模块
├── scripts/                 # 脚本工具
│   ├── collect_changdian.sh             # 定时采集脚本
│   ├── analyze_stock.py                 # 分析工具
│   ├── export_data.py                   # 导出工具
│   └── claude_api_client.py             # Claude API 客户端
├── tests/                   # 测试
│   ├── test_stock_analyzer.py           # 股票分析测试
│   └── test_news_collector.py           # 新闻采集测试
├── docs/                    # 文档
│   ├── ARCHITECTURE.md                  # 架构规范
│   ├── NEWS_COLLECTOR.md                # 新闻采集文档
│   └── HOT_SECTOR_COLLECTOR.md          # 热点板块文档
├── data/                    # 数据目录
│   ├── raw/                             # 原始行情数据
│   ├── news/                            # 新闻数据
│   ├── exports/                         # Excel 导出
│   └── analytics/                       # 分析结果
├── config/                  # 配置文件
└── requirements.txt         # 依赖列表
```

---

## 🧪 测试

运行所有测试：

```bash
pytest tests/ -v
```

测试覆盖：
- ✅ 移动平均线计算测试
- ✅ RSI 计算测试
- ✅ MACD 计算测试
- ✅ 布林带计算测试
- ✅ 价格趋势分析测试
- ✅ 成交量分析测试
- ✅ 技术指标信号测试
- ✅ 空数据处理测试
- ✅ 集成测试

---

## 🛠️ 技术栈

- **语言**: Python 3.11+
- **数据处理**: Pandas, NumPy
- **数据可视化**: Matplotlib
- **数据库**: PostgreSQL, SQLite
- **网络请求**: Requests, BeautifulSoup
- **任务调度**: Crontab
- **测试**: pytest
- **日志**: Loguru

---

## 📝 更新日志

### v1.0.0 (2024-02-11)
- ✅ 多数据源行情采集（东方财富、新浪财经）
- ✅ 股票新闻采集与情感分析
- ✅ 热点板块追踪
- ✅ 技术指标计算（RSI、MACD、布林带、MA）
- ✅ 数据可视化图表生成
- ✅ Excel 数据导出
- ✅ Claude API 客户端
- ✅ pytest 测试覆盖
- ✅ 架构规范文档

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的 Feature Branch (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到 Branch (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

---

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证开源。

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个 Star！**

</div>
