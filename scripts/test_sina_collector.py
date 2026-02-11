#!/usr/bin/env python3
"""
Stock Data Test Collector (Sina Finance)
使用新浪财经数据源的测试采集器
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
import pandas as pd
from datetime import datetime
from loguru import logger

logger.add(sys.stderr, level="INFO")


def fetch_sina_index_data(symbol="sh000001", days=10):
    """
    从新浪财经获取指数数据
    
    Args:
        symbol: 指数代码 (sh000001=上证指数, sz399001=深证成指)
        days: 获取天数
    
    Returns:
        DataFrame with index data
    """
    url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    params = {
        'symbol': symbol,
        'scale': 240,  # 240分钟 = 日线
        'ma': 5,
        'datalen': days,
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://finance.sina.com.cn/',
    }
    
    try:
        logger.info(f"正在获取 {symbol} 的数据...")
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            logger.error(f"请求失败: HTTP {resp.status_code}")
            return None
        
        data = resp.json()
        if not data:
            logger.warning("返回数据为空")
            return None
        
        # 转换为DataFrame
        df = pd.DataFrame(data)
        df['symbol'] = symbol
        df['collected_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 重命名列
        df = df.rename(columns={
            'day': 'date',
            'open': 'open_price',
            'high': 'high_price',
            'low': 'low_price',
            'close': 'close_price',
            'volume': 'volume',
        })
        
        # 计算涨跌幅
        df['open_price'] = pd.to_numeric(df['open_price'])
        df['close_price'] = pd.to_numeric(df['close_price'])
        df['change_pct'] = ((df['close_price'] - df['open_price']) / df['open_price'] * 100).round(2)
        
        logger.info(f"成功获取 {len(df)} 条数据")
        return df
        
    except Exception as e:
        logger.error(f"获取数据失败: {e}")
        return None


def fetch_multiple_indices():
    """获取多个主要指数数据"""
    indices = {
        'sh000001': '上证指数',
        'sz399001': '深证成指',
        'sz399006': '创业板指',
        'sh000016': '上证50',
        'sh000300': '沪深300',
    }
    
    results = {}
    for symbol, name in indices.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"采集: {name} ({symbol})")
        logger.info('='*50)
        
        df = fetch_sina_index_data(symbol, days=5)
        if df is not None and not df.empty:
            results[name] = df
            # 显示最新数据
            latest = df.iloc[-1]
            logger.info(f"最新数据 ({latest['date']}):")
            logger.info(f"  开盘: {latest['open_price']}")
            logger.info(f"  收盘: {latest['close_price']}")
            logger.info(f"  最高: {latest['high_price']}")
            logger.info(f"  最低: {latest['low_price']}")
            logger.info(f"  涨跌: {latest['change_pct']}%")
            logger.info(f"  成交量: {int(latest['volume']):,}")
    
    return results


def save_to_csv(data_dict, output_dir="data/test"):
    """保存数据到CSV"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for name, df in data_dict.items():
        filename = f"{name}_{timestamp}.csv"
        filepath = output_path / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"数据已保存: {filepath}")


def main():
    logger.info("="*60)
    logger.info("新浪财经数据采集测试")
    logger.info("="*60)
    
    # 获取多个指数数据
    results = fetch_multiple_indices()
    
    if results:
        logger.info("\n" + "="*60)
        logger.info("采集完成！")
        logger.info(f"成功采集 {len(results)} 个指数的数据")
        logger.info("="*60)
        
        # 保存到CSV
        save_to_csv(results)
        
        # 汇总
        logger.info("\n📊 数据汇总:")
        logger.info("-"*60)
        for name, df in results.items():
            latest = df.iloc[-1]
            change_emoji = "📈" if latest['change_pct'] > 0 else "📉" if latest['change_pct'] < 0 else "➡️"
            logger.info(f"{change_emoji} {name:8s}: {latest['close_price']:>8.2f} ({latest['change_pct']:+.2f}%)")
        
        return True
    else:
        logger.error("采集失败，未获取到任何数据")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
