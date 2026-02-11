#!/usr/bin/env python3
"""
股票数据分析脚本
用法:
    python analyze_stock.py --code 600584              # 分析指定股票
    python analyze_stock.py --code 600584 --chart      # 分析并生成图表
    python analyze_stock.py --code 600584 --sentiment  # 只分析新闻情感
    python analyze_stock.py --list                     # 列出分析报告
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
from analytics.stock_analyzer import StockAnalyzer
from analytics.sentiment_analyzer import SentimentAnalyzer
from analytics.chart_generator import ChartGenerator


def print_analysis_report(report: dict):
    """打印分析报告"""
    if not report:
        print("❌ 没有分析数据")
        return
    
    print("\n" + "="*60)
    print(f"📊 股票分析报告 - {report.get('stock_code', 'N/A')}")
    print("="*60)
    
    # 价格分析
    price = report.get('price_analysis', {})
    if price:
        print("\n📈 价格分析:")
        print(f"   当前价格: ¥{price.get('current_price', 'N/A')}")
        print(f"   涨跌: {price.get('price_change', 'N/A'):.2f} ({price.get('price_change_pct', 'N/A'):.2f}%)")
        print(f"   最高: ¥{price.get('highest', 'N/A')}")
        print(f"   最低: ¥{price.get('lowest', 'N/A')}")
        print(f"   平均: ¥{price.get('avg_price', 'N/A')}")
        print(f"   趋势: {'📈 上涨' if price.get('trend_direction') == 'up' else '📉 下跌'}")
    
    # 成交量分析
    volume = report.get('volume_analysis', {})
    if volume:
        print("\n📊 成交量分析:")
        print(f"   当前: {volume.get('current_volume', 'N/A'):,.0f}")
        print(f"   平均: {volume.get('avg_volume', 'N/A'):,.0f}")
        print(f"   量比: {volume.get('volume_ratio', 'N/A'):.2f}")
        print(f"   趋势: {'放量' if volume.get('volume_trend') == 'increasing' else '缩量'}")
    
    # 技术指标
    signals = report.get('technical_signals', {})
    if signals:
        print("\n📐 技术指标:")
        if 'rsi_value' in signals:
            rsi_signal = "超买" if signals.get('rsi_signal') == 'overbought' else \
                        ("超卖" if signals.get('rsi_signal') == 'oversold' else "正常")
            print(f"   RSI: {signals['rsi_value']:.2f} ({rsi_signal})")
        if 'macd_value' in signals:
            macd_signal = "看多" if signals.get('macd_signal') == 'bullish' else \
                         ("看空" if signals.get('macd_signal') == 'bearish' else "中性")
            print(f"   MACD: {macd_signal}")
        if 'boll_position' in signals:
            print(f"   布林带位置: {signals['boll_position']:.1f}%")
    
    # 建议
    recommendation = report.get('recommendation', 'N/A')
    print(f"\n🎯 投资建议: {recommendation}")
    print("="*60)


def print_sentiment_report(analysis: dict):
    """打印情感分析报告"""
    if not analysis:
        print("❌ 没有情感分析数据")
        return
    
    print("\n" + "="*60)
    print(f"📰 新闻情感分析 - {analysis.get('stock_code', 'N/A')}")
    print("="*60)
    
    print(f"\n📰 新闻数量: {analysis.get('total_news', 0)} 条")
    
    dist = analysis.get('sentiment_distribution', {})
    print("\n📊 情感分布:")
    print(f"   😊 正面: {dist.get('positive', {}).get('count', 0)} 条 ({dist.get('positive', {}).get('percentage', 0)}%)")
    print(f"   😞 负面: {dist.get('negative', {}).get('count', 0)} 条 ({dist.get('negative', {}).get('percentage', 0)}%)")
    print(f"   😐 中性: {dist.get('neutral', {}).get('count', 0)} 条 ({dist.get('neutral', {}).get('percentage', 0)}%)")
    
    sentiment = analysis.get('overall_sentiment', 'N/A')
    sentiment_emoji = "😊" if sentiment == 'positive' else ("😞" if sentiment == 'negative' else "😐")
    print(f"\n🎯 整体情感: {sentiment_emoji} {sentiment}")
    print(f"📊 平均得分: {analysis.get('average_sentiment_score', 0):.4f}")
    
    # 详情
    details = analysis.get('news_details', [])
    if details:
        print("\n📋 近期新闻情感:")
        for news in details[:5]:
            emoji = "😊" if news.get('sentiment') == 'positive' else \
                   ("😞" if news.get('sentiment') == 'negative' else "😐")
            print(f"   {emoji} {news.get('title', 'N/A')[:40]}...")
    
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="股票数据分析工具")
    parser.add_argument("--code", type=str, required=True, help="股票代码")
    parser.add_argument("--chart", action="store_true", help="生成图表")
    parser.add_argument("--sentiment", action="store_true", help="只分析新闻情感")
    parser.add_argument("--all", action="store_true", help="分析所有（价格+情感+图表）")
    parser.add_argument("--list", action="store_true", help="列出分析报告")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    
    args = parser.parse_args()
    
    if args.list:
        analyzer = StockAnalyzer()
        reports = analyzer.list_analysis_reports(args.code)
        print(f"\n📁 分析报告列表 ({len(reports)} 个):")
        for i, report in enumerate(reports[:10], 1):
            print(f"  {i}. {report.name}")
        return
    
    if args.sentiment:
        # 只分析情感
        sentiment_analyzer = SentimentAnalyzer()
        analysis = sentiment_analyzer.analyze_news_sentiment(args.code)
        
        if args.json:
            print(json.dumps(analysis, ensure_ascii=False, indent=2))
        else:
            print_sentiment_report(analysis)
    
    elif args.all:
        # 分析所有
        print(f"\n🔍 正在全面分析股票 {args.code}...")
        
        # 价格分析
        analyzer = StockAnalyzer()
        report = analyzer.generate_report(args.code)
        print_analysis_report(report)
        
        # 情感分析
        sentiment_analyzer = SentimentAnalyzer()
        sentiment = sentiment_analyzer.analyze_news_sentiment(args.code)
        print_sentiment_report(sentiment)
        
        # 生成图表
        if args.chart:
            print("\n📊 正在生成图表...")
            generator = ChartGenerator()
            results = generator.generate_all_charts(args.code)
            print("\n生成结果:")
            for name, path in results.items():
                if path:
                    print(f"  ✅ {name}: {path}")
                else:
                    print(f"  ❌ {name}: 失败")
    
    else:
        # 默认价格分析
        analyzer = StockAnalyzer()
        report = analyzer.generate_report(args.code)
        
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_analysis_report(report)
        
        # 可选生成图表
        if args.chart:
            print("\n📊 正在生成图表...")
            generator = ChartGenerator()
            results = generator.generate_all_charts(args.code)
            print("\n生成结果:")
            for name, path in results.items():
                if path:
                    print(f"  ✅ {name}: {path}")


if __name__ == "__main__":
    main()
