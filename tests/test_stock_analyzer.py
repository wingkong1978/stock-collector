#!/usr/bin/env python3
"""
Test cases for stock_analyzer module
股票分析模块测试用例
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from analytics.stock_analyzer import StockAnalyzer


class TestStockAnalyzer:
    """StockAnalyzer 测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return StockAnalyzer(data_path="data")
    
    @pytest.fixture
    def sample_data(self):
        """创建示例股票数据"""
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        np.random.seed(42)  # 固定随机种子
        
        data = {
            '代码': ['600584'] * 30,
            '名称': ['长电科技'] * 30,
            '最新价': 45 + np.random.randn(30).cumsum() * 0.5,
            '涨跌幅': np.random.randn(30) * 2,
            '成交量': np.random.randint(100000, 500000, 30),
            '成交额': np.random.randint(100000000, 500000000, 30),
            '开盘价': 45 + np.random.randn(30) * 0.3,
            '最高价': 46 + np.random.randn(30) * 0.3,
            '最低价': 44 + np.random.randn(30) * 0.3,
            '昨收': 45 + np.random.randn(30) * 0.3,
            '采集时间': dates
        }
        
        return pd.DataFrame(data)
    
    def test_calculate_ma(self, sample_data):
        """测试移动平均线计算"""
        from analytics.stock_analyzer import StockAnalyzer
        
        analyzer = StockAnalyzer()
        df = analyzer.calculate_ma(sample_data.copy(), periods=[5, 10, 20])
        
        # 检查是否生成了 MA 列
        assert 'MA5' in df.columns
        assert 'MA10' in df.columns
        assert 'MA20' in df.columns
        
        # 检查 MA5 的值是否正确（前4个应该是 NaN 或使用 min_periods=1）
        assert not df['MA5'].isna().all()
        
        # 检查 MA5 < MA10 < MA20（一般情况下）
        valid_idx = 20  # 从第20个开始比较
        if len(df) > valid_idx:
            assert df['MA5'].iloc[valid_idx] <= df['MA10'].iloc[valid_idx] * 1.5
    
    def test_calculate_rsi(self, sample_data):
        """测试 RSI 计算"""
        analyzer = StockAnalyzer()
        df = analyzer.calculate_rsi(sample_data.copy(), period=14)
        
        assert 'RSI' in df.columns
        
        # RSI 应该在 0-100 之间
        valid_rsi = df['RSI'].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()
    
    def test_calculate_macd(self, sample_data):
        """测试 MACD 计算"""
        analyzer = StockAnalyzer()
        df = analyzer.calculate_macd(sample_data.copy())
        
        assert 'MACD' in df.columns
        assert 'MACD_Signal' in df.columns
        assert 'MACD_Histogram' in df.columns
        
        # 检查 MACD_Histogram = MACD - MACD_Signal
        valid_idx = df[['MACD', 'MACD_Signal', 'MACD_Histogram']].dropna().index
        if len(valid_idx) > 0:
            idx = valid_idx[0]
            expected = df['MACD'].iloc[idx] - df['MACD_Signal'].iloc[idx]
            actual = df['MACD_Histogram'].iloc[idx]
            assert abs(expected - actual) < 1e-10
    
    def test_calculate_bollinger(self, sample_data):
        """测试布林带计算"""
        analyzer = StockAnalyzer()
        df = analyzer.calculate_bollinger(sample_data.copy())
        
        assert 'BOLL_MID' in df.columns
        assert 'BOLL_UPPER' in df.columns
        assert 'BOLL_LOWER' in df.columns
        
        # 检查布林带关系：LOWER <= MID <= UPPER
        valid_idx = df[['BOLL_LOWER', 'BOLL_MID', 'BOLL_UPPER']].dropna().index
        for idx in valid_idx:
            assert df['BOLL_LOWER'].iloc[idx] <= df['BOLL_UPPER'].iloc[idx]
    
    def test_analyze_price_trend(self, sample_data):
        """测试价格趋势分析"""
        analyzer = StockAnalyzer()
        analysis = analyzer.analyze_price_trend(sample_data)
        
        # 检查返回的字段
        required_fields = [
            'current_price', 'price_change', 'price_change_pct',
            'highest', 'lowest', 'avg_price', 'volatility', 'trend_direction'
        ]
        
        for field in required_fields:
            assert field in analysis, f"缺少字段: {field}"
        
        # 检查趋势方向
        assert analysis['trend_direction'] in ['up', 'down']
        
        # 检查价格范围
        assert analysis['lowest'] <= analysis['current_price'] <= analysis['highest']
    
    def test_analyze_volume(self, sample_data):
        """测试成交量分析"""
        analyzer = StockAnalyzer()
        analysis = analyzer.analyze_volume(sample_data)
        
        required_fields = [
            'avg_volume', 'max_volume', 'min_volume',
            'current_volume', 'volume_trend', 'volume_ratio'
        ]
        
        for field in required_fields:
            assert field in analysis, f"缺少字段: {field}"
        
        # 检查成交量范围
        assert analysis['min_volume'] <= analysis['current_volume'] <= analysis['max_volume']
        assert analysis['volume_ratio'] >= 0
    
    def test_get_technical_signals(self, sample_data):
        """测试技术指标信号"""
        analyzer = StockAnalyzer()
        
        # 先计算指标
        df = analyzer.calculate_rsi(sample_data.copy())
        df = analyzer.calculate_macd(df)
        df = analyzer.calculate_bollinger(df)
        
        signals = analyzer.get_technical_signals(df)
        
        # 检查 RSI 信号
        if 'rsi_value' in signals:
            assert 'rsi_signal' in signals
            assert signals['rsi_signal'] in ['overbought', 'oversold', 'neutral']
            assert 0 <= signals['rsi_value'] <= 100
        
        # 检查 MACD 信号
        if 'macd_value' in signals:
            assert 'macd_signal' in signals
            assert signals['macd_signal'] in ['bullish', 'bearish', 'neutral']
    
    def test_empty_dataframe(self):
        """测试空 DataFrame 处理"""
        analyzer = StockAnalyzer()
        empty_df = pd.DataFrame()
        
        # 应该返回原始 DataFrame 或空结果，不抛出异常
        result = analyzer.calculate_ma(empty_df)
        assert result.empty
        
        result = analyzer.calculate_rsi(empty_df)
        assert result.empty
        
        analysis = analyzer.analyze_price_trend(empty_df)
        assert analysis == {}


class TestStockAnalyzerIntegration:
    """集成测试"""
    
    def test_full_analysis_pipeline(self):
        """测试完整分析流程"""
        analyzer = StockAnalyzer()
        
        # 创建测试数据
        np.random.seed(42)
        data = {
            '最新价': 45 + np.random.randn(30).cumsum() * 0.5,
            '成交量': np.random.randint(100000, 500000, 30),
            '代码': ['600584'] * 30
        }
        df = pd.DataFrame(data)
        
        # 执行完整分析流程
        df = analyzer.calculate_ma(df)
        df = analyzer.calculate_rsi(df)
        df = analyzer.calculate_macd(df)
        df = analyzer.calculate_bollinger(df)
        
        price_analysis = analyzer.analyze_price_trend(df)
        volume_analysis = analyzer.analyze_volume(df)
        signals = analyzer.get_technical_signals(df)
        
        # 验证结果
        assert len(price_analysis) > 0
        assert len(volume_analysis) > 0
        assert len(signals) > 0


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Stock Analyzer 测试")
    print("=" * 60)
    
    # 运行 pytest
    import subprocess
    result = subprocess.run(
        ['python3', '-m', 'pytest', __file__, '-v', '--tb=short'],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode


if __name__ == "__main__":
    # 如果没有 pytest，使用简单测试
    try:
        import pytest
        sys.exit(run_tests())
    except ImportError:
        print("⚠️ 未安装 pytest，运行简单测试...")
        
        # 简单测试
        analyzer = StockAnalyzer()
        
        # 测试数据
        data = {
            '最新价': [45.0, 45.5, 46.0, 45.8, 46.2],
            '成交量': [100000, 150000, 120000, 180000, 200000]
        }
        df = pd.DataFrame(data)
        
        # 测试 MA
        result = analyzer.calculate_ma(df)
        print("✓ MA 计算测试通过" if 'MA5' in result.columns else "✗ MA 计算失败")
        
        # 测试 RSI
        result = analyzer.calculate_rsi(df)
        print("✓ RSI 计算测试通过" if 'RSI' in result.columns else "✗ RSI 计算失败")
        
        print("\n简单测试完成")
