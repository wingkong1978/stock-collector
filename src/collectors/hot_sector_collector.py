#!/usr/bin/env python3
"""
Hot Sector News Collector
热点板块及新闻采集模块
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import akshare as ak
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_manager import get_db_manager, DatabaseManager


class HotSectorCollector:
    """热点板块及新闻采集器"""

    def __init__(self, config_path: str = "config"):
        self.config_path = Path(config_path)
        self.load_config()
        self.db_manager: Optional[DatabaseManager] = None

        if self.settings.get("storage", {}).get("database"):
            self.init_database()

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path / "stocks.json", "r", encoding="utf-8") as f:
                self.stocks_config = json.load(f)
            with open(self.config_path / "settings.json", "r", encoding="utf-8") as f:
                self.settings = json.load(f)
            logger.info("热点板块配置加载成功")
        except Exception as e:
            logger.error(f"热点板块配置加载失败: {e}")
            raise

    def init_database(self):
        """初始化数据库连接"""
        try:
            self.db_manager = get_db_manager()
            logger.info("热点板块采集数据库初始化成功")
        except Exception as e:
            logger.error(f"热点板块采集数据库初始化失败: {e}")
            self.db_manager = None

    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为 float"""
        try:
            if value is None or pd.isna(value):
                return None
            str_value = str(value).strip().replace(",", "")
            if str_value in ["", "-"]:
                return None
            return float(str_value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """安全转换为 int"""
        try:
            if value is None or pd.isna(value):
                return None
            str_value = str(value).strip().replace(",", "")
            if str_value in ["", "-"]:
                return None
            return int(float(str_value))
        except (ValueError, TypeError):
            return None

    def collect_concept_sectors(
        self, top_n: int = 20, max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        采集概念板块涨幅排行

        Args:
            top_n: 采集前N个板块
            max_retries: 最大重试次数

        Returns:
            概念板块数据 DataFrame
        """
        logger.info(f"开始采集概念板块数据，前 {top_n} 名...")

        task_name = "concept_sectors"
        start_time = datetime.now()

        for attempt in range(max_retries):
            try:
                # 获取概念板块列表（包含涨跌幅）
                df = ak.stock_board_concept_name_em()

                if df is None or df.empty:
                    raise ValueError("获取概念板块数据失败")

                # 按涨跌幅排序
                df = df.sort_values(by="涨跌幅", ascending=False)

                # 只取前N个
                df = df.head(top_n).copy()

                # 添加元数据
                df["_collected_at"] = datetime.now()
                df["_sector_type"] = "concept"

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"概念板块采集成功: {len(df)} 条, 耗时: {elapsed:.2f}s")

                self.db_manager and self.db_manager.log_collection(
                    task_name, "success", f"采集成功: {len(df)} 个板块"
                )

                return df

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"采集失败，{wait_time}s 后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"概念板块采集失败: {e}")

        self.db_manager and self.db_manager.log_collection(task_name, "error", str(e))
        return None

    def collect_industry_sectors(
        self, top_n: int = 20, max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        采集行业板块涨幅排行

        Args:
            top_n: 采集前N个板块
            max_retries: 最大重试次数

        Returns:
            行业板块数据 DataFrame
        """
        logger.info(f"开始采集行业板块数据，前 {top_n} 名...")

        task_name = "industry_sectors"
        start_time = datetime.now()

        for attempt in range(max_retries):
            try:
                # 获取行业板块列表
                df = ak.stock_board_industry_name_em()

                if df is None or df.empty:
                    raise ValueError("获取行业板块数据失败")

                # 按涨跌幅排序
                df = df.sort_values(by="涨跌幅", ascending=False)

                # 只取前N个
                df = df.head(top_n).copy()

                # 添加元数据
                df["_collected_at"] = datetime.now()
                df["_sector_type"] = "industry"

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"行业板块采集成功: {len(df)} 条, 耗时: {elapsed:.2f}s")

                self.db_manager and self.db_manager.log_collection(
                    task_name, "success", f"采集成功: {len(df)} 个板块"
                )

                return df

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"采集失败，{wait_time}s 后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"行业板块采集失败: {e}")

        self.db_manager and self.db_manager.log_collection(task_name, "error", str(e))
        return None

    def collect_hot_sectors_combined(
        self, top_n: int = 20
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        采集热点板块（概念+行业）

        Args:
            top_n: 每个类别采集前N个

        Returns:
            包含概念和行业板块数据的字典
        """
        logger.info("开始采集热点板块数据...")

        results = {
            "concept": None,
            "industry": None,
        }

        # 采集概念板块
        try:
            results["concept"] = self.collect_concept_sectors(top_n=top_n)
        except Exception as e:
            logger.error(f"概念板块采集异常: {e}")

        time.sleep(1)  # 避免请求过于频繁

        # 采集行业板块
        try:
            results["industry"] = self.collect_industry_sectors(top_n=top_n)
        except Exception as e:
            logger.error(f"行业板块采集异常: {e}")

        total_count = sum(
            len(df) for df in results.values() if df is not None
        )
        logger.info(f"热点板块采集完成，共 {total_count} 个板块")

        return results

    def collect_sector_news(
        self, sector_name: str, sector_type: str = "concept", max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        采集板块相关新闻

        Args:
            sector_name: 板块名称
            sector_type: 板块类型（concept/industry）
            max_retries: 最大重试次数

        Returns:
            新闻数据 DataFrame
        """
        logger.info(f"开始采集 [{sector_name}] 板块相关新闻...")

        task_name = f"sector_news_{sector_name}"
        start_time = datetime.now()

        for attempt in range(max_retries):
            try:
                # 获取板块成分股
                if sector_type == "concept":
                    df = ak.stock_board_concept_cons_em(symbol=sector_name)
                else:
                    df = ak.stock_board_industry_cons_em(symbol=sector_name)

                if df is None or df.empty:
                    logger.warning(f"[{sector_name}] 板块无成分股数据")
                    return None

                # 获取成分股代码列表
                stock_codes = df["代码"].tolist() if "代码" in df.columns else []

                if not stock_codes:
                    logger.warning(f"[{sector_name}] 板块无法获取成分股代码")
                    return None

                # 采集前5只成分股的新闻
                all_news = []
                for code in stock_codes[:5]:
                    try:
                        news_df = ak.stock_news_em(symbol=code)
                        if news_df is not None and not news_df.empty:
                            news_df["_related_stock"] = code
                            news_df["_related_sector"] = sector_name
                            all_news.append(news_df)
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"获取股票 {code} 新闻失败: {e}")
                        continue

                if not all_news:
                    logger.warning(f"[{sector_name}] 板块未采集到相关新闻")
                    return None

                # 合并所有新闻
                combined_df = pd.concat(all_news, ignore_index=True)

                # 去重
                combined_df = combined_df.drop_duplicates(
                    subset=["标题"] if "标题" in combined_df.columns else ["title"],
                    keep="first",
                )

                # 添加元数据
                combined_df["_collected_at"] = datetime.now()
                combined_df["_sector_type"] = sector_type

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"[{sector_name}] 板块新闻采集成功: {len(combined_df)} 条, 耗时: {elapsed:.2f}s"
                )

                return combined_df

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"采集失败，{wait_time}s 后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[{sector_name}] 板块新闻采集失败: {e}")

        return None

    def collect_hot_sectors_with_news(
        self, top_n: int = 10
    ) -> Dict[str, Any]:
        """
        采集热点板块及其相关新闻

        Args:
            top_n: 采集前N个热门板块

        Returns:
            包含板块数据和新闻的字典
        """
        logger.info("开始采集热点板块及新闻...")

        results = {
            "sectors": {},
            "news": {},
        }

        # 先采集热点板块
        sectors_data = self.collect_hot_sectors_combined(top_n=top_n)

        # 为每个热点板块采集新闻
        for sector_type, df in sectors_data.items():
            if df is None or df.empty:
                continue

            results["sectors"][sector_type] = df

            for _, row in df.iterrows():
                sector_name = row.get("板块名称", "")
                if not sector_name:
                    continue

                logger.info(f"采集 [{sector_name}] 相关新闻...")
                news_df = self.collect_sector_news(sector_name, sector_type)

                if news_df is not None and not news_df.empty:
                    results["news"][sector_name] = news_df

                time.sleep(1)  # 避免请求过于频繁

        total_sectors = sum(
            len(df) for df in results["sectors"].values() if df is not None
        )
        total_news = sum(
            len(df) for df in results["news"].values() if df is not None
        )

        logger.info(
            f"热点板块及新闻采集完成: {total_sectors} 个板块, {total_news} 条新闻"
        )

        return results

    def save_sectors_to_csv(
        self, df: pd.DataFrame, sector_type: str = "concept"
    ) -> Optional[Path]:
        """
        保存板块数据到 CSV

        Args:
            df: 板块数据 DataFrame
            sector_type: 板块类型

        Returns:
            保存的文件路径
        """
        if df is None or df.empty:
            logger.warning("板块数据为空，跳过保存")
            return None

        try:
            storage_path = Path(self.settings["storage"]["path"])
            sectors_path = storage_path / "sectors"
            sectors_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{sector_type}_sectors_{timestamp}.csv"
            filepath = sectors_path / filename

            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logger.info(f"板块数据已保存到: {filepath}")

            return filepath

        except Exception as e:
            logger.error(f"保存板块数据失败: {e}")
            return None

    def save_sector_news_to_csv(
        self, sector_name: str, df: pd.DataFrame
    ) -> Optional[Path]:
        """
        保存板块新闻到 CSV

        Args:
            sector_name: 板块名称
            df: 新闻数据 DataFrame

        Returns:
            保存的文件路径
        """
        if df is None or df.empty:
            logger.warning("板块新闻数据为空，跳过保存")
            return None

        try:
            storage_path = Path(self.settings["storage"]["path"])
            news_path = storage_path / "sector_news"
            news_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in sector_name if c.isalnum() or c in "_-")
            filename = f"sector_{safe_name}_{timestamp}.csv"
            filepath = news_path / filename

            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logger.info(f"[{sector_name}] 板块新闻已保存到: {filepath}")

            return filepath

        except Exception as e:
            logger.error(f"保存板块新闻失败: {e}")
            return None

    def get_hot_sectors_summary(
        self, sectors_data: Dict[str, Optional[pd.DataFrame]]
    ) -> str:
        """
        生成热点板块摘要

        Args:
            sectors_data: 板块数据字典

        Returns:
            摘要文本
        """
        lines = ["\n📊 热点板块汇总", "=" * 50]

        for sector_type, df in sectors_data.items():
            if df is None or df.empty:
                continue

            type_name = "概念板块" if sector_type == "concept" else "行业板块"
            lines.append(f"\n🔥 {type_name} Top {len(df)}")
            lines.append("-" * 40)

            for idx, row in df.iterrows():
                rank = row.get("排名", idx + 1)
                name = row.get("板块名称", "N/A")
                change = row.get("涨跌幅", 0)
                leader = row.get("领涨股票", "N/A")
                leader_change = row.get("领涨股票-涨跌幅", 0)

                lines.append(
                    f"{rank:2d}. {name:8s} | 涨幅: {change:+.2f}% | 领涨: {leader} ({leader_change:+.2f}%)"
                )

        return "\n".join(lines)

    def run(self, include_news: bool = True):
        """
        运行热点板块采集任务

        Args:
            include_news: 是否同时采集板块相关新闻
        """
        logger.info("=" * 60)
        logger.info("热点板块采集任务开始")
        logger.info("=" * 60)

        try:
            if include_news:
                # 采集板块及新闻
                results = self.collect_hot_sectors_with_news(top_n=10)

                # 保存板块数据
                for sector_type, df in results["sectors"].items():
                    self.save_sectors_to_csv(df, sector_type)

                # 保存板块新闻
                for sector_name, df in results["news"].items():
                    self.save_sector_news_to_csv(sector_name, df)

                # 输出摘要
                summary = self.get_hot_sectors_summary(results["sectors"])
                logger.info(summary)
            else:
                # 仅采集板块数据
                results = self.collect_hot_sectors_combined(top_n=20)

                for sector_type, df in results.items():
                    self.save_sectors_to_csv(df, sector_type)

                # 输出摘要
                summary = self.get_hot_sectors_summary(results)
                logger.info(summary)

        finally:
            logger.info("=" * 60)
            logger.info("热点板块采集任务完成")
            logger.info("=" * 60)

    def close(self):
        """关闭资源"""
        if self.db_manager:
            self.db_manager.close()
            logger.info("热点板块采集器数据库连接已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="热点板块采集工具")
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

    args = parser.parse_args()

    with HotSectorCollector() as collector:
        if args.concept_only:
            df = collector.collect_concept_sectors(top_n=args.top)
            if df is not None:
                collector.save_sectors_to_csv(df, "concept")
                print(collector.get_hot_sectors_summary({"concept": df}))
        elif args.industry_only:
            df = collector.collect_industry_sectors(top_n=args.top)
            if df is not None:
                collector.save_sectors_to_csv(df, "industry")
                print(collector.get_hot_sectors_summary({"industry": df}))
        else:
            collector.run(include_news=not args.no_news)
