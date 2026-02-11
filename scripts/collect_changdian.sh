#!/bin/bash
# Changdian Technology (600584) Collection Script
# 长电科技数据采集脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="${PROJECT_DIR}/venv"
STOCK_CODE="600584"
STOCK_NAME="长电科技"

# 记录日志
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ========================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始采集 ${STOCK_NAME}(${STOCK_CODE}) 数据"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ========================================"

# 激活虚拟环境
if [ -f "${VENV_PATH}/bin/activate" ]; then
    source "${VENV_PATH}/bin/activate"
fi

cd "$PROJECT_DIR"

# 设置 Python 路径
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📊 采集股票实时数据..."
python3 -c "
import sys
sys.path.insert(0, 'src')
from collectors.stock_collector import StockCollector
import akshare as ak
from datetime import datetime

try:
    # 获取实时行情
    df = ak.stock_zh_a_spot_em()
    stock_data = df[df['代码'] == '${STOCK_CODE}']
    
    if not stock_data.empty:
        row = stock_data.iloc[0]
        print(f\"✅ ${STOCK_NAME}(${STOCK_CODE}) 实时数据:\")
        print(f\"   最新价: {row['最新价']}\")
        print(f\"   涨跌幅: {row['涨跌幅']}%\")
        print(f\"   成交量: {row['成交量']}\")
        print(f\"   成交额: {row['成交额']}\")
        
        # 保存到CSV
        import pandas as pd
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f\"data/raw/${STOCK_CODE}_${timestamp}.csv\"
        stock_data.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f\"   数据已保存: {output_file}\")
    else:
        print(f\"⚠️ 未找到 ${STOCK_CODE} 的实时数据\")
except Exception as e:
    print(f\"❌ 采集实时数据失败: {e}\")
"

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📰 采集股票新闻..."
python3 scripts/collect_news.py --code ${STOCK_CODE} --days 1

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 采集完成"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ========================================"

# 汇总信息
NEWEST_NEWS=$(ls -t data/news/news_${STOCK_CODE}_*.csv 2>/dev/null | head -1)
NEWEST_DATA=$(ls -t data/raw/${STOCK_CODE}_*.csv 2>/dev/null | head -1)

echo ""
echo "📁 数据文件:"
[ -n "$NEWEST_DATA" ] && echo "   行情数据: $NEWEST_DATA" || echo "   行情数据: 未采集"
[ -n "$NEWEST_NEWS" ] && echo "   新闻数据: $NEWEST_NEWS" || echo "   新闻数据: 未采集"

echo ""
echo "💡 提示: 可使用以下命令查看最新数据"
echo "   tail -20 logs/changdian_cron.log"
