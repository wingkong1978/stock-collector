#!/usr/bin/env python3
"""
Hot Sector Collection Script
热点板块采集脚本
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime

from loguru import logger

from collectors.hot_sector_collector import HotSectorCollector


def main():
    parser = argparse.ArgumentParser(description="热点板块及新闻采集脚本")
    parser.add_argument(
        "--top", type=int, default=20, help="采集前N个板块（默认: 20）"
    )
    parser.add_argument(
        "--no-news", action="store_true", help="不采集板块相关新闻"
    )
    parser.add_argument(
        "--concept-only", action="store_true", help="仅采集概念板块"
    )
    parser.add_argument(
        "--industry-only", action="store_true", help="仅采集行业板块"
    )
    parser.add_argument(
        "--sector", type=str, help="指定板块名称采集相关新闻"
    )
    parser.add_argument(
        "--sector-type", type=str, default="concept",
        choices=["concept", "industry"],
        help="板块类型（默认: concept）"
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("热点板块采集脚本启动")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    with HotSectorCollector() as collector:
        # 指定了板块名称，只采集该板块的新闻
        if args.sector:
            logger.info(f"采集 [{args.sector}] 板块相关新闻...")
            df = collector.collect_sector_news(
                sector_name=args.sector,
                sector_type=args.sector_type
            )
            if df is not None and not df.empty:
                collector.save_sector_news_to_csv(args.sector, df)
                logger.info(f"成功采集 [{args.sector}] 板块 {len(df)} 条新闻")
            else:
                logger.warning(f"未采集到 [{args.sector}] 板块的新闻")
            return

        # 仅采集概念板块
        if args.concept_only:
            logger.info("采集概念板块...")
            df = collector.collect_concept_sectors(top_n=args.top)
            if df is not None:
                collector.save_sectors_to_csv(df, "concept")
                summary = collector.get_hot_sectors_summary({"concept": df})
                logger.info(summary)
                print(summary)  # 同时输出到控制台
            return

        # 仅采集行业板块
        if args.industry_only:
            logger.info("采集行业板块...")
            df = collector.collect_industry_sectors(top_n=args.top)
            if df is not None:
                collector.save_sectors_to_csv(df, "industry")
                summary = collector.get_hot_sectors_summary({"industry": df})
                logger.info(summary)
                print(summary)  # 同时输出到控制台
            return

        # 默认：采集热点板块及新闻
        collector.run(include_news=not args.no_news)

    logger.info("=" * 60)
    logger.info("热点板块采集完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
