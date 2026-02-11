#!/usr/bin/env python3
"""
Multi-Source Stock Data Collector
多数据源股票行情采集器

当主数据源(东方财富)失败时，自动切换到备选数据源(新浪财经)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import time
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any
from decimal import Decimal

import akshare as ak
import pandas as pd
from loguru import logger


class MultiSourceStockCollector:
    """多数据源股票采集器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://finance.sina.com.cn/',
        }
        
    def fetch_from_eastmoney(self, stock_codes: List[str]) -> Optional[pd.DataFrame]:
        """
        从东方财富获取实时行情
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            DataFrame with stock data
        """
        try:
            logger.info("尝试从东方财富获取数据...")
            df = ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                raise ValueError("东方财富返回空数据")
            
            # 筛选指定股票
            filtered_df = df[df["代码"].isin(stock_codes)].copy()
            
            if filtered_df.empty:
                logger.warning(f"东方财富未找到股票: {stock_codes}")
                return None
            
            logger.info(f"东方财富数据获取成功: {len(filtered_df)} 条")
            return filtered_df
            
        except Exception as e:
            logger.warning(f"东方财富获取失败: {e}")
            return None
    
    def fetch_from_sina(self, stock_codes: List[str]) -> Optional[pd.DataFrame]:
        """
        从新浪财经获取实时行情
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            DataFrame with stock data
        """
        try:
            logger.info("尝试从新浪财经获取数据...")
            
            # 转换股票代码格式
            sina_codes = []
            for code in stock_codes:
                if code.startswith('6'):
                    sina_codes.append(f"sh{code}")
                else:
                    sina_codes.append(f"sz{code}")
            
            # 构建URL
            codes_str = ','.join(sina_codes)
            url = f"https://hq.sinajs.cn/list={codes_str}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                raise ValueError(f"新浪财经返回错误: {response.status_code}")
            
            # 解析数据
            data = []
            lines = response.text.strip().split('\n')
            
            for line in lines:
                if not line or '=' not in line:
                    continue
                
                # 解析每一行数据
                # 格式: var hq_str_sh600584="长电科技,41.280,41.350,41.280,41.550,41.080,41.280,41.310..."
                try:
                    code_part, data_part = line.split('=')
                    code = code_part.split('_')[-1].replace('sh', '').replace('sz', '')
                    
                    if not data_part or data_part == '"";':
                        continue
                    
                    values = data_part.strip('"').split(',')
                    
                    if len(values) < 33:
                        continue
                    
                    # 构建数据字典
                    row = {
                        '代码': code,
                        '名称': values[0],
                        '最新价': float(values[3]),  # 当前价
                        '涨跌幅': round((float(values[3]) - float(values[2])) / float(values[2]) * 100, 2),
                        '成交量': int(values[8]) // 100,  # 手
                        '成交额': float(values[9]),
                        '开盘价': float(values[1]),
                        '最高价': float(values[4]),
                        '最低价': float(values[5]),
                        '昨收': float(values[2]),
                        '买一价': float(values[11]),
                        '卖一价': float(values[21]),
                    }
                    data.append(row)
                    
                except Exception as e:
                    logger.debug(f"解析行数据失败: {e}")
                    continue
            
            if not data:
                raise ValueError("新浪财经返回数据为空")
            
            df = pd.DataFrame(data)
            logger.info(f"新浪财经数据获取成功: {len(df)} 条")
            return df
            
        except Exception as e:
            logger.warning(f"新浪财经获取失败: {e}")
            return None
    
    def fetch_stock_data(self, stock_codes: List[str]) -> Optional[pd.DataFrame]:
        """
        获取股票数据(多数据源自动切换)
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            DataFrame with stock data
        """
        if not stock_codes:
            logger.warning("未提供股票代码")
            return None
        
        logger.info(f"开始采集 {len(stock_codes)} 只股票的数据...")
        
        # 尝试数据源1: 东方财富
        df = self.fetch_from_eastmoney(stock_codes)
        if df is not None and not df.empty:
            df['_source'] = 'eastmoney'
            return df
        
        # 等待后尝试数据源2: 新浪财经
        time.sleep(1)
        df = self.fetch_from_sina(stock_codes)
        if df is not None and not df.empty:
            df['_source'] = 'sina'
            return df
        
        logger.error("所有数据源均失败")
        return None
    
    def save_to_csv(self, df: pd.DataFrame, output_dir: str = "data/raw") -> Path:
        """保存数据到CSV"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source = df['_source'].iloc[0] if '_source' in df.columns else 'unknown'
        filename = f"stocks_{source}_{timestamp}.csv"
        filepath = output_path / filename
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"数据已保存: {filepath}")
        return filepath
    
    def collect_changdian(self) -> Optional[pd.DataFrame]:
        """采集长电科技数据"""
        stock_code = "600584"
        stock_name = "长电科技"
        
        logger.info(f"开始采集 {stock_name}({stock_code})...")
        
        df = self.fetch_stock_data([stock_code])
        
        if df is not None and not df.empty:
            # 显示数据
            row = df.iloc[0]
            source = row.get('_source', 'unknown')
            
            logger.info(f"✅ {stock_name}({stock_code}) 数据获取成功 [来源: {source}]")
            logger.info(f"   最新价: {row.get('最新价')}")
            logger.info(f"   涨跌幅: {row.get('涨跌幅')}%")
            logger.info(f"   成交量: {row.get('成交量')}")
            
            # 保存
            self.save_to_csv(df)
            return df
        else:
            logger.error(f"❌ {stock_name}({stock_code}) 数据获取失败")
            return None


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("多数据源股票采集器")
    logger.info("=" * 60)
    
    collector = MultiSourceStockCollector()
    
    # 采集长电科技
    df = collector.collect_changdian()
    
    if df is not None:
        logger.info("\n✅ 采集完成!")
        return True
    else:
        logger.error("\n❌ 采集失败!")
        return False


if __name__ == "__main__":
    import pandas as pd
    from pathlib import Path
    
    success = main()
    sys.exit(0 if success else 1)
