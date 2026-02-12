#!/bin/bash
# 股票新闻采集并发送到QQ
# 定时任务脚本

cd /source_code/stock-collector

# 设置日志文件
LOG_FILE="/tmp/news_collect_$(date +%Y%m%d_%H%M%S).log"
NEWS_OUTPUT="/tmp/latest_news.txt"

echo "开始执行新闻采集 - $(date)" >> "$LOG_FILE"

# 执行新闻采集（财经要闻）
python3 scripts/collect_news.py --financial --days 1 2>&1 | tee -a "$LOG_FILE"

# 检查是否有新闻数据文件生成
LATEST_NEWS=$(find data/news -name "*.csv" -type f -mmin -5 2>/dev/null | head -1)

if [ -n "$LATEST_NEWS" ]; then
    # 提取新闻标题（前10条）
    echo "📰 今日财经新闻 ($(date '+%Y-%m-%d'))" > "$NEWS_OUTPUT"
    echo "" >> "$NEWS_OUTPUT"
    
    # 读取CSV并提取标题（跳过header，取前10行）
    tail -n +2 "$LATEST_NEWS" | head -10 | while IFS=',' read -r title url time source; do
        echo "• $title" >> "$NEWS_OUTPUT"
    done
    
    echo "" >> "$NEWS_OUTPUT"
    echo "数据来源: 财联社/新浪财经" >> "$NEWS_OUTPUT"
    echo "采集时间: $(date '+%H:%M:%S')" >> "$NEWS_OUTPUT"
    
    # 输出发送内容
    cat "$NEWS_OUTPUT"
    echo "✅ 新闻采集完成，已生成报告"
else
    echo "⚠️ 未能获取新闻数据文件"
    echo "请检查 /source_code/stock-collector/data/news/ 目录"
fi

echo "执行完成 - $(date)" >> "$LOG_FILE"
