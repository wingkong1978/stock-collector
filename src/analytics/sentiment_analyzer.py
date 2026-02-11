#!/usr/bin/env python3
"""
News Sentiment Analyzer
新闻情感分析模块
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter
from loguru import logger
import json


class SentimentAnalyzer:
    """新闻情感分析器"""
    
    # 正面词汇词典
    POSITIVE_WORDS = [
        '上涨', '大涨', '暴涨', '飙升', '涨停', '突破', '利好', '强劲',
        '增长', '提升', '改善', '优化', '创新', '领先', '优势', '成功',
        '盈利', '增收', '扩张', '合作', '订单', '交付', '量产', '爬坡',
        '超预期', '看好', '推荐', '买入', '增持', '目标价', '上调',
        '反弹', '回暖', '复苏', '景气', '高增', '爆发', '拐点'
    ]
    
    # 负面词汇词典
    NEGATIVE_WORDS = [
        '下跌', '大跌', '暴跌', '跌停', '崩盘', '破位', '利空', '疲软',
        '下降', '下滑', '亏损', '减少', '裁员', '关闭', '退出', '失败',
        '暴雷', '违约', '诉讼', '调查', '处罚', '退市', '风险', '警示',
        '下调', '卖出', '减持', '看空', '回避', ' downgrade',
        '放缓', '收缩', '低迷', '寒冬', '承压', '拖累', '不及预期'
    ]
    
    # 中性行业词汇（过滤用）
    NEUTRAL_WORDS = [
        '股票', '股市', '证券', '市场', '板块', '行业', '概念',
        '涨幅', '跌幅', '成交额', '成交量', '换手率', '市盈率',
        '主力资金', '净流入', '净流出'
    ]
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.news_path = self.data_path / "news"
        self.analytics_path = self.data_path / "analytics"
        self.analytics_path.mkdir(parents=True, exist_ok=True)
    
    def load_news_data(self, stock_code: Optional[str] = None, days: int = 30) -> pd.DataFrame:
        """加载新闻数据"""
        if stock_code:
            pattern = f"news_{stock_code}_*.csv"
        else:
            pattern = "news_*.csv"
        
        files = list(self.news_path.glob(pattern))
        
        if not files:
            logger.warning("未找到新闻数据文件")
            return pd.DataFrame()
        
        # 按时间排序
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        all_data = []
        for file in files[:days * 2]:  # 读取更多文件
            try:
                df = pd.read_csv(file)
                all_data.append(df)
            except Exception as e:
                logger.warning(f"读取文件失败 {file}: {e}")
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        combined = pd.concat(all_data, ignore_index=True)
        
        # 去重
        if '新闻标题' in combined.columns:
            combined = combined.drop_duplicates(subset=['新闻标题'], keep='first')
        
        return combined
    
    def analyze_sentiment(self, text: str) -> Dict:
        """分析单条文本的情感"""
        if not text or pd.isna(text):
            return {'score': 0, 'label': 'neutral', 'confidence': 0}
        
        text = str(text)
        
        # 统计正负词汇
        positive_count = sum(1 for word in self.POSITIVE_WORDS if word in text)
        negative_count = sum(1 for word in self.NEGATIVE_WORDS if word in text)
        
        # 计算情感得分 (-1 到 1)
        total = positive_count + negative_count
        if total == 0:
            return {'score': 0, 'label': 'neutral', 'confidence': 0}
        
        score = (positive_count - negative_count) / total
        
        # 确定标签
        if score > 0.2:
            label = 'positive'
        elif score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'
        
        # 置信度
        confidence = min(total / 3, 1.0)
        
        return {
            'score': float(score),
            'label': label,
            'confidence': float(confidence),
            'positive_words': positive_count,
            'negative_words': negative_count
        }
    
    def analyze_news_sentiment(self, stock_code: Optional[str] = None) -> Dict:
        """分析新闻情感"""
        logger.info(f"开始分析新闻情感...")
        
        df = self.load_news_data(stock_code)
        
        if df.empty:
            logger.warning("没有新闻数据可供分析")
            return {}
        
        results = []
        
        # 分析每条新闻
        for idx, row in df.iterrows():
            content = ""
            if '新闻标题' in row and pd.notna(row['新闻标题']):
                content += str(row['新闻标题'])
            if '新闻内容' in row and pd.notna(row['新闻内容']):
                content += " " + str(row['新闻内容'])
            
            sentiment = self.analyze_sentiment(content)
            
            result = {
                'title': row.get('新闻标题', ''),
                'publish_time': row.get('发布时间', ''),
                'source': row.get('文章来源', ''),
                'sentiment': sentiment['label'],
                'score': sentiment['score'],
                'confidence': sentiment['confidence']
            }
            results.append(result)
        
        # 统计
        sentiments = [r['sentiment'] for r in results]
        sentiment_counts = Counter(sentiments)
        
        total = len(results)
        positive_pct = sentiment_counts.get('positive', 0) / total * 100
        negative_pct = sentiment_counts.get('negative', 0) / total * 100
        neutral_pct = sentiment_counts.get('neutral', 0) / total * 100
        
        # 计算平均情感得分
        avg_score = sum(r['score'] for r in results) / total if total > 0 else 0
        
        analysis = {
            'stock_code': stock_code,
            'analysis_time': datetime.now().isoformat(),
            'total_news': total,
            'sentiment_distribution': {
                'positive': {'count': sentiment_counts.get('positive', 0), 'percentage': round(positive_pct, 2)},
                'negative': {'count': sentiment_counts.get('negative', 0), 'percentage': round(negative_pct, 2)},
                'neutral': {'count': sentiment_counts.get('neutral', 0), 'percentage': round(neutral_pct, 2)}
            },
            'average_sentiment_score': round(avg_score, 4),
            'overall_sentiment': 'positive' if avg_score > 0.1 else ('negative' if avg_score < -0.1 else 'neutral'),
            'news_details': results[:20]  # 只保存前20条详情
        }
        
        # 保存分析结果
        self._save_sentiment_report(stock_code, analysis)
        
        return analysis
    
    def analyze_keywords(self, stock_code: Optional[str] = None, top_n: int = 20) -> Dict:
        """分析关键词"""
        df = self.load_news_data(stock_code)
        
        if df.empty:
            return {}
        
        # 提取所有文本
        all_text = ""
        for idx, row in df.iterrows():
            if '新闻标题' in row and pd.notna(row['新闻标题']):
                all_text += str(row['新闻标题']) + " "
            if '新闻内容' in row and pd.notna(row['新闻内容']):
                all_text += str(row['新闻内容']) + " "
        
        # 简单的分词（基于空格和标点）
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', all_text)
        
        # 过滤中性词和停用词
        filtered_words = [w for w in words if w not in self.NEUTRAL_WORDS and len(w) >= 2]
        
        # 统计词频
        word_counts = Counter(filtered_words)
        
        return {
            'top_keywords': word_counts.most_common(top_n),
            'total_words': len(words),
            'unique_words': len(word_counts)
        }
    
    def _save_sentiment_report(self, stock_code: Optional[str], report: Dict):
        """保存情感分析报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        code_suffix = f"_{stock_code}" if stock_code else ""
        filename = f"sentiment{code_suffix}_{timestamp}.json"
        filepath = self.analytics_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"情感分析报告已保存: {filepath}")
    
    def generate_sentiment_summary(self, stock_code: str) -> str:
        """生成情感分析摘要文本"""
        analysis = self.analyze_news_sentiment(stock_code)
        keywords = self.analyze_keywords(stock_code, top_n=10)
        
        if not analysis:
            return "暂无新闻数据"
        
        summary = f"""
📊 {stock_code} 新闻情感分析

📰 新闻数量: {analysis['total_news']} 条

📈 情感分布:
   正面: {analysis['sentiment_distribution']['positive']['count']} 条 ({analysis['sentiment_distribution']['positive']['percentage']}%)
   负面: {analysis['sentiment_distribution']['negative']['count']} 条 ({analysis['sentiment_distribution']['negative']['percentage']}%)
   中性: {analysis['sentiment_distribution']['neutral']['count']} 条 ({analysis['sentiment_distribution']['neutral']['percentage']}%)

🎯 整体情感: {analysis['overall_sentiment']}
📊 平均得分: {analysis['average_sentiment_score']:.4f}
"""
        
        if keywords.get('top_keywords'):
            summary += "\n🔥 热门关键词:\n"
            for word, count in keywords['top_keywords'][:5]:
                summary += f"   - {word}: {count}次\n"
        
        return summary


if __name__ == "__main__":
    # 测试
    analyzer = SentimentAnalyzer()
    
    # 情感分析
    sentiment = analyzer.analyze_news_sentiment("600584")
    print(json.dumps(sentiment, ensure_ascii=False, indent=2))
    
    # 关键词分析
    keywords = analyzer.analyze_keywords("600584")
    print("\n关键词:", keywords)
    
    # 摘要
    summary = analyzer.generate_sentiment_summary("600584")
    print("\n" + summary)
