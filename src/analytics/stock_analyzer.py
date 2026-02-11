#!/usr/bin/env python3
"""
Stock Data Analyzer
股票数据分析模块
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
import json


class StockAnalyzer:
    """股票数据分析器"""
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.raw_path = self.data_path / "raw"
        self.news_path = self.data_path / "news"
        self.analytics_path = self.data_path / "analytics"
        self.analytics_path.mkdir(parents=True, exist_ok=True)
        
    def load_stock_data(self, stock_code: str, days: int = 30) -> pd.DataFrame:
        """加载股票历史数据"""
        files = list(self.raw_path.glob(f"stocks_*_{stock_code}_*.csv"))
        if not files:
            files = list(self.raw_path.glob("stocks_*.csv"))
        
        if not files:
            logger.warning("未找到股票数据文件")
            return pd.DataFrame()
        
        # 按时间排序
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        all_data = []
        for file in files[:days]:
            try:
                df = pd.read_csv(file)
                # 过滤指定股票
                if '代码' in df.columns:
                    df = df[df['代码'].astype(str) == str(stock_code)]
                if not df.empty:
                    # 从文件名提取时间
                    timestamp = datetime.fromtimestamp(file.stat().st_mtime)
                    df['采集时间'] = timestamp
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"读取文件失败 {file}: {e}")
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        combined = pd.concat(all_data, ignore_index=True)
        # 按时间排序
        if '采集时间' in combined.columns:
            combined = combined.sort_values('采集时间')
        return combined
    
    def calculate_ma(self, df: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
        """计算移动平均线"""
        if df.empty or '最新价' not in df.columns:
            return df
        
        for period in periods:
            df[f'MA{period}'] = df['最新价'].rolling(window=period, min_periods=1).mean()
        
        return df
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算RSI指标"""
        if df.empty or '最新价' not in df.columns:
            return df
        
        delta = df['最新价'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df
    
    def calculate_macd(self, df: pd.DataFrame, 
                      fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """计算MACD指标"""
        if df.empty or '最新价' not in df.columns:
            return df
        
        ema_fast = df['最新价'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['最新价'].ewm(span=slow, adjust=False).mean()
        
        df['MACD'] = ema_fast - ema_slow
        df['MACD_Signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        return df
    
    def calculate_bollinger(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        """计算布林带"""
        if df.empty or '最新价' not in df.columns:
            return df
        
        df['BOLL_MID'] = df['最新价'].rolling(window=period, min_periods=1).mean()
        rolling_std = df['最新价'].rolling(window=period, min_periods=1).std()
        df['BOLL_UPPER'] = df['BOLL_MID'] + (rolling_std * std_dev)
        df['BOLL_LOWER'] = df['BOLL_MID'] - (rolling_std * std_dev)
        
        return df
    
    def analyze_price_trend(self, df: pd.DataFrame) -> Dict:
        """分析价格趋势"""
        if df.empty or '最新价' not in df.columns:
            return {}
        
        prices = df['最新价']
        
        analysis = {
            'current_price': float(prices.iloc[-1]),
            'price_change': float(prices.iloc[-1] - prices.iloc[0]),
            'price_change_pct': float((prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0] * 100),
            'highest': float(prices.max()),
            'lowest': float(prices.min()),
            'avg_price': float(prices.mean()),
            'volatility': float(prices.std()),
            'trend_direction': 'up' if prices.iloc[-1] > prices.iloc[0] else 'down'
        }
        
        # 移动平均线趋势
        if 'MA5' in df.columns and 'MA20' in df.columns:
            analysis['ma5_above_ma20'] = bool(df['MA5'].iloc[-1] > df['MA20'].iloc[-1])
            if len(df) > 1:
                analysis['golden_cross'] = bool((df['MA5'].iloc[-1] > df['MA20'].iloc[-1]) and \
                                       (df['MA5'].iloc[-2] <= df['MA20'].iloc[-2]))
            else:
                analysis['golden_cross'] = False
        
        return analysis
    
    def analyze_volume(self, df: pd.DataFrame) -> Dict:
        """分析成交量"""
        if df.empty or '成交量' not in df.columns:
            return {}
        
        volumes = df['成交量']
        
        analysis = {
            'avg_volume': float(volumes.mean()),
            'max_volume': float(volumes.max()),
            'min_volume': float(volumes.min()),
            'current_volume': float(volumes.iloc[-1]),
            'volume_trend': 'increasing' if volumes.iloc[-1] > volumes.mean() else 'decreasing',
            'volume_ratio': float(volumes.iloc[-1] / volumes.mean()) if volumes.mean() > 0 else 0
        }
        
        return analysis
    
    def get_technical_signals(self, df: pd.DataFrame) -> Dict:
        """获取技术分析信号"""
        signals = {}
        
        # RSI 信号
        if 'RSI' in df.columns and not df['RSI'].isna().all():
            rsi = df['RSI'].iloc[-1]
            if rsi > 70:
                signals['rsi_signal'] = 'overbought'
            elif rsi < 30:
                signals['rsi_signal'] = 'oversold'
            else:
                signals['rsi_signal'] = 'neutral'
            signals['rsi_value'] = float(rsi)
        
        # MACD 信号
        if 'MACD' in df.columns and 'MACD_Signal' in df.columns:
            macd = df['MACD'].iloc[-1]
            macd_signal = df['MACD_Signal'].iloc[-1]
            macd_hist = df['MACD_Histogram'].iloc[-1]
            
            if macd > macd_signal and macd_hist > 0:
                signals['macd_signal'] = 'bullish'
            elif macd < macd_signal and macd_hist < 0:
                signals['macd_signal'] = 'bearish'
            else:
                signals['macd_signal'] = 'neutral'
            signals['macd_value'] = float(macd)
        
        # 布林带信号
        if 'BOLL_UPPER' in df.columns and 'BOLL_LOWER' in df.columns:
            price = df['最新价'].iloc[-1]
            upper = df['BOLL_UPPER'].iloc[-1]
            lower = df['BOLL_LOWER'].iloc[-1]
            
            if price >= upper:
                signals['boll_signal'] = 'overbought'
            elif price <= lower:
                signals['boll_signal'] = 'oversold'
            else:
                signals['boll_signal'] = 'neutral'
            signals['boll_position'] = float((price - lower) / (upper - lower) * 100)
        
        return signals
    
    def generate_report(self, stock_code: str) -> Dict:
        """生成完整分析报告"""
        logger.info(f"开始分析股票 {stock_code}...")
        
        # 加载数据
        df = self.load_stock_data(stock_code)
        
        if df.empty:
            logger.error(f"未找到股票 {stock_code} 的数据")
            return {}
        
        # 计算指标
        df = self.calculate_ma(df)
        df = self.calculate_rsi(df)
        df = self.calculate_macd(df)
        df = self.calculate_bollinger(df)
        
        # 生成分析
        report = {
            'stock_code': stock_code,
            'analysis_time': datetime.now().isoformat(),
            'data_points': len(df),
            'price_analysis': self.analyze_price_trend(df),
            'volume_analysis': self.analyze_volume(df),
            'technical_signals': self.get_technical_signals(df),
            'recommendation': self._generate_recommendation(df)
        }
        
        # 保存报告
        self._save_report(stock_code, report)
        
        return report
    
    def _generate_recommendation(self, df: pd.DataFrame) -> str:
        """生成投资建议"""
        signals = self.get_technical_signals(df)
        
        bullish_count = 0
        bearish_count = 0
        
        if signals.get('rsi_signal') == 'oversold':
            bullish_count += 1
        elif signals.get('rsi_signal') == 'overbought':
            bearish_count += 1
        
        if signals.get('macd_signal') == 'bullish':
            bullish_count += 1
        elif signals.get('macd_signal') == 'bearish':
            bearish_count += 1
        
        if signals.get('boll_signal') == 'oversold':
            bullish_count += 1
        elif signals.get('boll_signal') == 'overbought':
            bearish_count += 1
        
        if bullish_count > bearish_count:
            return '看涨'
        elif bearish_count > bullish_count:
            return '看跌'
        else:
            return '中性'
    
    def _save_report(self, stock_code: str, report: Dict):
        """保存分析报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{stock_code}_{timestamp}.json"
        filepath = self.analytics_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析报告已保存: {filepath}")
    
    def list_analysis_reports(self, stock_code: Optional[str] = None) -> List[Path]:
        """列出分析报告"""
        if stock_code:
            pattern = f"analysis_{stock_code}_*.json"
        else:
            pattern = "analysis_*.json"
        
        files = list(self.analytics_path.glob(pattern))
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files


if __name__ == "__main__":
    # 测试
    analyzer = StockAnalyzer()
    report = analyzer.generate_report("600584")
    print(json.dumps(report, ensure_ascii=False, indent=2))
