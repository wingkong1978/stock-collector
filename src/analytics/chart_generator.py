#!/usr/bin/env python3
"""
Visualization Module
数据可视化模块
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use('Agg')  # 无界面后端

import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import json

from analytics.stock_analyzer import StockAnalyzer
from analytics.sentiment_analyzer import SentimentAnalyzer


class ChartGenerator:
    """图表生成器"""
    
    def __init__(self, output_path: str = "data/analytics/charts"):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.analyzer = StockAnalyzer()
        self.sentiment = SentimentAnalyzer()
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    
    def generate_price_chart(self, stock_code: str) -> Optional[Path]:
        """生成价格趋势图"""
        try:
            df = self.analyzer.load_stock_data(stock_code, days=30)
            
            if df.empty or '最新价' not in df.columns:
                logger.warning(f"没有股票 {stock_code} 的数据")
                return None
            
            # 计算指标
            df = self.analyzer.calculate_ma(df, periods=[5, 10, 20])
            df = self.analyzer.calculate_bollinger(df)
            
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
            
            # 价格图
            x = range(len(df))
            ax1.plot(x, df['最新价'], label='Price', linewidth=1.5, color='#1f77b4')
            
            if 'MA5' in df.columns:
                ax1.plot(x, df['MA5'], label='MA5', linewidth=1, alpha=0.7, color='orange')
            if 'MA10' in df.columns:
                ax1.plot(x, df['MA10'], label='MA10', linewidth=1, alpha=0.7, color='green')
            if 'MA20' in df.columns:
                ax1.plot(x, df['MA20'], label='MA20', linewidth=1, alpha=0.7, color='red')
            
            # 布林带
            if 'BOLL_UPPER' in df.columns:
                ax1.fill_between(x, df['BOLL_UPPER'], df['BOLL_LOWER'], alpha=0.1, color='gray')
                ax1.plot(x, df['BOLL_UPPER'], '--', alpha=0.5, color='gray', label='Bollinger')
                ax1.plot(x, df['BOLL_LOWER'], '--', alpha=0.5, color='gray')
            
            ax1.set_title(f'{stock_code} Price Trend', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Price (CNY)')
            ax1.legend(loc='best')
            ax1.grid(True, alpha=0.3)
            
            # 成交量图
            if '成交量' in df.columns:
                colors = ['red' if df['最新价'].iloc[i] >= df['最新价'].iloc[i-1] else 'green' 
                         for i in range(1, len(df))]
                colors.insert(0, 'gray')
                ax2.bar(x, df['成交量'], color=colors, alpha=0.7)
                ax2.set_ylabel('Volume')
                ax2.set_xlabel('Time')
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"price_{stock_code}_{timestamp}.png"
            filepath = self.output_path / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"价格图表已生成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成价格图表失败: {e}")
            return None
    
    def generate_technical_chart(self, stock_code: str) -> Optional[Path]:
        """生成技术指标图"""
        try:
            df = self.analyzer.load_stock_data(stock_code, days=30)
            
            if df.empty:
                return None
            
            # 计算指标
            df = self.analyzer.calculate_rsi(df)
            df = self.analyzer.calculate_macd(df)
            
            fig, axes = plt.subplots(3, 1, figsize=(12, 10))
            
            x = range(len(df))
            
            # RSI
            if 'RSI' in df.columns:
                axes[0].plot(x, df['RSI'], color='purple', linewidth=1.5)
                axes[0].axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Overbought (70)')
                axes[0].axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Oversold (30)')
                axes[0].fill_between(x, 30, 70, alpha=0.1, color='gray')
                axes[0].set_title(f'{stock_code} RSI Indicator', fontsize=12, fontweight='bold')
                axes[0].set_ylabel('RSI')
                axes[0].set_ylim(0, 100)
                axes[0].legend()
                axes[0].grid(True, alpha=0.3)
            
            # MACD
            if 'MACD' in df.columns:
                axes[1].plot(x, df['MACD'], label='MACD', color='blue', linewidth=1.5)
                axes[1].plot(x, df['MACD_Signal'], label='Signal', color='red', linewidth=1.5)
                colors = ['green' if val > 0 else 'red' for val in df['MACD_Histogram']]
                axes[1].bar(x, df['MACD_Histogram'], color=colors, alpha=0.7, label='Histogram')
                axes[1].axhline(y=0, color='black', linestyle='-', alpha=0.3)
                axes[1].set_title('MACD Indicator', fontsize=12, fontweight='bold')
                axes[1].set_ylabel('MACD')
                axes[1].legend()
                axes[1].grid(True, alpha=0.3)
            
            # 涨跌幅
            if '涨跌幅' in df.columns:
                colors = ['red' if val > 0 else 'green' for val in df['涨跌幅']]
                axes[2].bar(x, df['涨跌幅'], color=colors, alpha=0.7)
                axes[2].axhline(y=0, color='black', linestyle='-', alpha=0.3)
                axes[2].set_title('Price Change %', fontsize=12, fontweight='bold')
                axes[2].set_ylabel('Change (%)')
                axes[2].set_xlabel('Time')
                axes[2].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"technical_{stock_code}_{timestamp}.png"
            filepath = self.output_path / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"技术指标图已生成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成技术指标图失败: {e}")
            return None
    
    def generate_sentiment_chart(self, stock_code: str) -> Optional[Path]:
        """生成情感分析图"""
        try:
            analysis = self.sentiment.analyze_news_sentiment(stock_code)
            
            if not analysis:
                return None
            
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            
            # 饼图 - 情感分布
            labels = ['Positive', 'Negative', 'Neutral']
            sizes = [
                analysis['sentiment_distribution']['positive']['count'],
                analysis['sentiment_distribution']['negative']['count'],
                analysis['sentiment_distribution']['neutral']['count']
            ]
            colors = ['#2ecc71', '#e74c3c', '#95a5a6']
            
            axes[0].pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
                       startangle=90, explode=(0.05, 0.05, 0))
            axes[0].set_title(f'{stock_code} News Sentiment Distribution', fontsize=12, fontweight='bold')
            
            # 条形图 - 数量
            axes[1].bar(labels, sizes, color=colors, alpha=0.8)
            axes[1].set_title('News Count by Sentiment', fontsize=12, fontweight='bold')
            axes[1].set_ylabel('Count')
            for i, v in enumerate(sizes):
                axes[1].text(i, v + max(sizes)*0.01, str(v), ha='center', fontweight='bold')
            axes[1].grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            
            # 保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sentiment_{stock_code}_{timestamp}.png"
            filepath = self.output_path / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"情感分析图已生成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成情感分析图失败: {e}")
            return None
    
    def generate_all_charts(self, stock_code: str) -> Dict[str, Optional[Path]]:
        """生成所有图表"""
        logger.info(f"开始为 {stock_code} 生成所有图表...")
        
        results = {
            'price_chart': self.generate_price_chart(stock_code),
            'technical_chart': self.generate_technical_chart(stock_code),
            'sentiment_chart': self.generate_sentiment_chart(stock_code)
        }
        
        success_count = sum(1 for v in results.values() if v is not None)
        logger.info(f"图表生成完成: {success_count}/3 成功")
        
        return results
    
    def list_charts(self, stock_code: Optional[str] = None) -> List[Path]:
        """列出所有图表"""
        if stock_code:
            pattern = f"*_{stock_code}_*.png"
        else:
            pattern = "*.png"
        
        files = list(self.output_path.glob(pattern))
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files


if __name__ == "__main__":
    # 测试
    generator = ChartGenerator()
    
    results = generator.generate_all_charts("600584")
    print("生成结果:")
    for name, path in results.items():
        if path:
            print(f"  ✅ {name}: {path}")
        else:
            print(f"  ❌ {name}: 失败")
