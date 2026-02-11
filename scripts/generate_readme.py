#!/usr/bin/env python3
"""
使用 Claude API 生成项目 README
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from claude_api_client import ClaudeAPIClient


def generate_readme():
    """生成 README"""
    
    client = ClaudeAPIClient()
    
    # 项目详细信息
    project_info = """
项目名称: stock-collector
GitHub: https://github.com/wingkong1978/stock-collector

【核心功能模块】
1. 多源数据采集 (src/collectors/multi_source_collector.py)
   - 支持东方财富、新浪财经双数据源
   - 自动切换机制（主源失败切备用源）
   - 实时股票行情采集

2. 新闻采集 (src/collectors/news_collector.py)
   - 个股新闻采集
   - 财经要闻采集
   - 热点板块新闻追踪
   - 新闻去重（MD5哈希）

3. 热点板块采集 (src/collectors/hot_sector_collector.py)
   - 概念板块涨幅排行
   - 行业板块涨幅排行
   - 板块相关新闻采集

4. 数据导出 (src/collectors/data_exporter.py)
   - 支持 Excel (.xlsx) 格式
   - 股票行情数据导出
   - 新闻数据导出
   - 自动统计信息生成

5. 技术分析 (src/analytics/stock_analyzer.py)
   - RSI 指标计算
   - MACD 指标计算
   - 布林带 (Bollinger Bands)
   - 移动平均线 (MA5/10/20/60)
   - 价格趋势分析
   - 成交量分析

6. 情感分析 (src/analytics/sentiment_analyzer.py)
   - 新闻情感分类（正面/负面/中性）
   - 关键词提取
   - 情感分布统计

7. 数据可视化 (src/analytics/chart_generator.py)
   - 价格趋势图（含布林带）
   - 技术指标图（RSI、MACD）
   - 情感分析饼图

8. 定时任务
   - 系统 crontab 定时采集
   - 工作日 8:30-17:00 每30分钟采集
   - 支持长电科技(600584)等股票自动监控

【技术栈】
- Python 3.11
- PostgreSQL (数据存储)
- Pandas, NumPy (数据处理)
- Matplotlib (可视化)
- Requests, BeautifulSoup (网络爬虫)
- Loguru (日志)
- pytest (测试)

【项目结构】
stock-collector/
├── src/
│   ├── collectors/      # 数据采集模块
│   ├── analytics/       # 数据分析模块
│   ├── database/        # 数据库模块
│   └── storage/         # 存储模块
├── scripts/             # 脚本工具
│   ├── collect_changdian.sh
│   ├── analyze_stock.py
│   ├── export_data.py
│   └── claude_api_client.py
├── tests/               # 测试
├── docs/                # 文档
├── data/                # 数据目录
└── config/              # 配置文件

【使用示例】
# 股票分析
python scripts/analyze_stock.py --code 600584 --all --chart

# 数据导出
python scripts/export_data.py --stock 600584

# 运行测试
pytest tests/test_stock_analyzer.py -v

【安装】
pip install -r requirements.txt

【定时任务配置】
0,30 8-17 * * 1-5 cd /source_code/stock-collector && bash scripts/collect_changdian.sh
"""

    prompt = f"""请根据以下项目信息，生成一份专业的 README.md 文档。

{project_info}

要求：
1. 使用标准 Markdown 格式，适合 GitHub 展示
2. 包含项目徽章（Python、License MIT等）
3. 在顶部添加清晰的项目标题和简介
4. 使用勾选框列出所有实际功能（不要添加未实现的功能）
5. 包含快速开始指南（安装、配置、使用）
6. 包含常用命令示例
7. 使用 emoji 增加可读性
8. 底部添加许可证信息（MIT）

请直接输出完整的 README.md 内容，不要包含任何说明文字。"""

    print("🤖 Claude 正在生成 README...")
    result = client.send_message(prompt, max_tokens=8000)
    
    return result


if __name__ == "__main__":
    readme_content = generate_readme()
    
    # 保存到文件
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("\n" + "="*60)
    print("✅ README 已更新: README.md")
    print("="*60)
    print("\n预览 (前1500字符):")
    print(readme_content[:1500])
    print("...\n[完整内容请查看 README.md]")
