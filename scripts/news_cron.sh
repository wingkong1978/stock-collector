#!/bin/bash
# Stock News Collection Script
# 股票新闻定时采集脚本
#
# 建议添加到 crontab:
# */30 9-15 * * 1-5 /source_code/stock-collector/scripts/news_cron.sh >> /source_code/stock-collector/logs/news_cron.log 2>&1
# 0 8 * * 1-5 /source_code/stock-collector/scripts/news_cron.sh --morning >> /source_code/stock-collector/logs/news_cron.log 2>&1
# 0 18 * * 1-5 /source_code/stock-collector/scripts/news_cron.sh --evening >> /source_code/stock-collector/logs/news_cron.log 2>&1

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="${PROJECT_DIR}/venv"

# 激活虚拟环境
if [ -f "${VENV_PATH}/bin/activate" ]; then
    source "${VENV_PATH}/bin/activate"
fi

cd "$PROJECT_DIR"

# 解析参数
MODE="${1:-normal}"

# 设置 Python 路径
export PYTHONPATH="${PROJECT_DIR}:${PYTHONPATH}"

case "$MODE" in
    --morning)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行早间新闻采集..."
        python scripts/collect_news.py --financial --pages 5
        ;;
    --evening)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行晚间完整新闻采集..."
        python scripts/collect_news.py --days 7
        ;;
    --financial)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行财经要闻采集..."
        python scripts/collect_news.py --financial --pages 3
        ;;
    --stocks)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行股票新闻采集..."
        python scripts/collect_news.py --stocks --days 3
        ;;
    *)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行常规新闻采集..."
        python scripts/collect_news.py --financial --pages 2
        ;;
esac

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 新闻采集完成"
