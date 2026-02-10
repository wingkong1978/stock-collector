#!/usr/bin/env python3
"""
Stock News Collection Script
股票新闻采集脚本

用法:
    python collect_news.py                    # 采集所有新闻
    python collect_news.py --financial        # 仅采集财经要闻
    python collect_news.py --stocks           # 仅采集关注股票新闻
    python collect_news.py --code 000001      # 采集指定股票新闻
    python collect_news.py --days 7           # 采集最近7天的新闻
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime

from loguru import logger

from collectors.news_collector import NewsCollector


def main():
    parser = argparse.ArgumentParser(description="股票新闻采集脚本")
    parser.add_argument(
        "--financial",
        action="store_true",
        help="仅采集财经要闻"
    )
    parser.add_argument(
        "--stocks",
        action="store_true",
        help="仅采集关注股票新闻"
    )
    parser.add_argument(
        "--code",
        type=str,
        help="指定股票代码（如: 000001）"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=3,
        help="采集最近几天的新闻（默认: 3）"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="财经要闻采集页数（默认: 3）"
    )
    parser.add_argument(
        "--max-stocks",
        type=int,
        help="最多采集多少只股票（默认: 全部）"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="不保存到数据库，仅保存到CSV"
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("股票新闻采集脚本启动")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    with NewsCollector() as collector:
        # 指定了股票代码
        if args.code:
            logger.info(f"采集股票 {args.code} 的新闻...")
            df = collector.collect_individual_news(args.code, days=args.days)
            if df is not None and not df.empty:
                if not args.no_db:
                    collector.save_news_to_database(df, stock_code=args.code)
                collector.save_news_to_csv(df, prefix=f"news_{args.code}")
                logger.info(f"成功采集 {len(df)} 条新闻")
            else:
                logger.warning(f"未采集到股票 {args.code} 的新闻")
            return

        # 仅采集财经要闻
        if args.financial:
            logger.info("采集财经要闻...")
            df = collector.collect_financial_news(num_pages=args.pages)
            if df is not None and not df.empty:
                if not args.no_db:
                    collector.save_news_to_database(df)
                collector.save_news_to_csv(df, prefix="financial_news")
                logger.info(f"成功采集 {len(df)} 条财经要闻")
            return

        # 仅采集股票新闻
        if args.stocks:
            logger.info("采集关注股票新闻...")
            results = collector.collect_all_stocks_news(
                days=args.days,
                max_stocks=args.max_stocks
            )
            total = 0
            for code, df in results.items():
                if df is not None and not df.empty:
                    if not args.no_db:
                        collector.save_news_to_database(df, stock_code=code)
                    collector.save_news_to_csv(df, prefix=f"news_{code}")
                    total += len(df)
            logger.info(f"成功采集 {len(results)} 只股票，共 {total} 条新闻")
            return

        # 默认：采集所有类型的新闻
        collector.run()

    logger.info("=" * 60)
    logger.info("新闻采集完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
