#!/bin/bash
# Stock Collector Daily Script
# 定时采集脚本

cd "$(dirname "$0")/.."

# 激活虚拟环境（如果有）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 运行采集程序
python src/collectors/stock_collector.py >> logs/cron.log 2>&1

# 记录执行时间
echo "[$(date)] Collection completed" >> logs/cron.log
