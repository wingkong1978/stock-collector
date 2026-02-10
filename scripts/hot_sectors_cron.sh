#!/bin/bash
# Hot Sector Collection Script
# 热点板块定时采集脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="${PROJECT_DIR}/venv"

# 激活虚拟环境
if [ -f "${VENV_PATH}/bin/activate" ]; then
    source "${VENV_PATH}/bin/activate"
fi

cd "$PROJECT_DIR"

# 设置 Python 路径
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH}"

MODE="${1:-normal}"

case "$MODE" in
    --concept)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行概念板块采集..."
        python scripts/collect_hot_sectors.py --concept-only --top 30
        ;;
    --industry)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行行业板块采集..."
        python scripts/collect_hot_sectors.py --industry-only --top 30
        ;;
    --with-news)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行热点板块及新闻采集..."
        python scripts/collect_hot_sectors.py --top 10
        ;;
    *)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行常规热点板块采集..."
        python scripts/collect_hot_sectors.py --top 20
        ;;
esac

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 热点板块采集完成"
