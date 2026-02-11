#!/bin/bash
# 发送采集结果通知

STOCK_CODE="600584"
STOCK_NAME="长电科技"

# 获取最新的新闻文件
NEWEST_NEWS=$(ls -t /source_code/stock-collector/data/news/news_${STOCK_CODE}_*.csv 2>/dev/null | head -1)

if [ -n "$NEWEST_NEWS" ]; then
    # 读取新闻数量
    NEWS_COUNT=$(wc -l < "$NEWEST_NEWS")
    NEWS_COUNT=$((NEWS_COUNT - 1))  # 减去标题行
    
    # 获取最新一条新闻标题
    LATEST_TITLE=$(tail -1 "$NEWEST_NEWS" | cut -d',' -f2)
    
    MESSAGE="📊 ${STOCK_NAME}(${STOCK_CODE}) 数据采集完成

⏰ 时间: $(date '+%Y-%m-%d %H:%M')
📰 新闻: ${NEWS_COUNT} 条
📝 最新: ${LATEST_TITLE}

💡 查看详细数据:
cd /source_code/stock-collector
cat data/news/news_${STOCK_CODE}_*.csv"

    # 发送消息
    openclaw message send --channel qqbot --to "2BD16CBAEBC9CA5832255C79A03BB518" --message "$MESSAGE"
fi
