#!/usr/bin/env python3
"""
Stock News Collector
股票新闻采集模块
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

import akshare as ak
import pandas as pd
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_manager import get_db_manager, DatabaseManager


class NewsCollector:
    """股票新闻采集器"""

    # 新闻来源映射
    NEWS_SOURCES = {
        "sina": "新浪财经",
        "eastmoney": "东方财富",
        "10jqka": "同花顺",
        "cls": "财联社",
    }

    def __init__(self, config_path: str = "config"):
        self.config_path = Path(config_path)
        self.load_config()
        self.db_manager: Optional[DatabaseManager] = None

        # 如果配置了数据库，初始化数据库连接
        if self.settings.get("storage", {}).get("database"):
            self.init_database()

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path / "stocks.json", "r", encoding="utf-8") as f:
                self.stocks_config = json.load(f)
            with open(self.config_path / "settings.json", "r", encoding="utf-8") as f:
                self.settings = json.load(f)
            logger.info("新闻采集配置加载成功")
        except Exception as e:
            logger.error(f"新闻采集配置加载失败: {e}")
            raise

    def init_database(self):
        """初始化数据库连接"""
        try:
            self.db_manager = get_db_manager()
            logger.info("新闻采集数据库初始化成功")
        except Exception as e:
            logger.error(f"新闻采集数据库初始化失败: {e}")
            self.db_manager = None

    def _generate_news_id(self, title: str, url: str, pub_time: str) -> str:
        """
        生成新闻唯一ID

        使用标题、URL和发布时间生成稳定的哈希值作为唯一标识
        """
        content = f"{title}|{url}|{pub_time}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _safe_datetime(self, value: Any) -> Optional[datetime]:
        """
        安全转换为 datetime 类型

        支持多种格式:
        - pandas Timestamp
        - 字符串格式: "2024-01-15 10:30:00"
        - ISO 格式: "2024-01-15T10:30:00"
        """
        if value is None or pd.isna(value):
            return None

        try:
            # 已经是 datetime 类型
            if isinstance(value, datetime):
                return value

            # pandas Timestamp
            if isinstance(value, pd.Timestamp):
                return value.to_pydatetime()

            # 字符串解析
            str_value = str(value).strip()

            # 尝试多种格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(str_value, fmt)
                except ValueError:
                    continue

            # 使用 pandas 智能解析
            parsed = pd.to_datetime(str_value, errors="raise")
            return parsed.to_pydatetime()

        except Exception as e:
            logger.debug(f"时间转换失败: value={value}, error={e}")
            return None

    def _validate_news_data(self, df: pd.DataFrame) -> bool:
        """
        验证新闻数据完整性

        Args:
            df: 新闻数据 DataFrame

        Returns:
            数据是否有效
        """
        if df is None:
            logger.error("新闻数据验证失败: DataFrame 为 None")
            return False

        if df.empty:
            logger.warning("新闻数据验证警告: DataFrame 为空")
            return False

        # 检查必需字段（不同来源字段名不同）
        possible_title_cols = ["标题", "title", "news_title", "Title"]
        has_title = any(col in df.columns for col in possible_title_cols)

        if not has_title:
            logger.error(f"新闻数据验证失败: 缺少标题字段，可用字段: {df.columns.tolist()}")
            return False

        logger.debug(f"新闻数据验证通过: {len(df)} 条数据")
        return True

    def collect_individual_news(
        self, stock_code: str, days: int = 7, max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        采集个股新闻

        Args:
            stock_code: 股票代码 (如 "000001")
            days: 采集最近几天的新闻
            max_retries: 最大重试次数

        Returns:
            新闻数据 DataFrame
        """
        logger.info(f"开始采集股票 {stock_code} 的新闻...")

        task_name = f"individual_news_{stock_code}"
        start_time = datetime.now()
        last_error = None

        # 重试机制
        for attempt in range(max_retries):
            try:
                # 使用 akshare 获取个股新闻
                df = ak.stock_news_em(symbol=stock_code)

                # 验证数据
                if not self._validate_news_data(df):
                    raise ValueError("数据源返回无效新闻数据")

                # 筛选时间范围
                cutoff_date = datetime.now() - timedelta(days=days)

                # 根据数据源不同，时间字段名可能不同
                time_cols = ["发布时间", "pub_time", "ctime", "datetime", "时间"]
                time_col = None
                for col in time_cols:
                    if col in df.columns:
                        time_col = col
                        break

                if time_col:
                    # 转换时间并筛选
                    df["_parsed_time"] = df[time_col].apply(self._safe_datetime)
                    df = df[df["_parsed_time"] >= cutoff_date].copy()
                    df = df.drop(columns=["_parsed_time"])

                # 添加元数据
                df["_stock_code"] = stock_code
                df["_collected_at"] = datetime.now()
                df["_news_id"] = df.apply(
                    lambda row: self._generate_news_id(
                        str(row.get("标题", row.get("title", ""))),
                        str(row.get("链接", row.get("url", ""))),
                        str(row.get("发布时间", row.get("pub_time", ""))),
                    ),
                    axis=1,
                )

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"股票 {stock_code} 新闻采集成功: {len(df)} 条, 耗时: {elapsed:.2f}s")

                self.db_manager and self.db_manager.log_collection(
                    task_name, "success", f"采集成功: {len(df)} 条新闻"
                )

                return df

            except Exception as e:
                last_error = e

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"采集失败 (尝试 {attempt + 1}/{max_retries}): {e}, 等待 {wait_time}s 后重试..."
                    )
                    import time

                    time.sleep(wait_time)
                else:
                    logger.error(f"个股新闻采集失败: {e}, 股票代码: {stock_code}")

        self.db_manager and self.db_manager.log_collection(
            task_name, "error", f"重试 {max_retries} 次后失败: {last_error}"
        )
        return None

    def collect_market_news(
        self, news_type: str = "财经导读", max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        采集市场财经新闻

        Args:
            news_type: 新闻类型，可选: "财经导读", "上市公司", "国内经济", "国际经济", "全球股市", "商品期货"
            max_retries: 最大重试次数

        Returns:
            新闻数据 DataFrame
        """
        logger.info(f"开始采集市场新闻: {news_type}")

        task_name = f"market_news_{news_type}"
        start_time = datetime.now()
        last_error = None

        # 重试机制
        for attempt in range(max_retries):
            try:
                # 使用 akshare 获取财经新闻
                df = ak.stock_financial_report_sina()

                # 注意: akshare 的财经新闻接口可能会变化
                # 这里使用东方财富的新闻接口
                df = ak.stock_news_main_cx()

                # 验证数据
                if not self._validate_news_data(df):
                    raise ValueError("数据源返回无效新闻数据")

                # 添加元数据
                df["_news_type"] = news_type
                df["_collected_at"] = datetime.now()

                # 生成唯一ID
                df["_news_id"] = df.apply(
                    lambda row: self._generate_news_id(
                        str(row.get("标题", row.get("title", ""))),
                        str(row.get("链接", row.get("url", ""))),
                        str(row.get("发布时间", row.get("pub_time", ""))),
                    ),
                    axis=1,
                )

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"市场新闻采集成功: {len(df)} 条, 耗时: {elapsed:.2f}s")

                self.db_manager and self.db_manager.log_collection(
                    task_name, "success", f"采集成功: {len(df)} 条新闻"
                )

                return df

            except Exception as e:
                last_error = e

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"采集失败 (尝试 {attempt + 1}/{max_retries}): {e}, 等待 {wait_time}s 后重试..."
                    )
                    import time

                    time.sleep(wait_time)
                else:
                    logger.error(f"市场新闻采集失败: {e}")

        self.db_manager and self.db_manager.log_collection(
            task_name, "error", f"重试 {max_retries} 次后失败: {last_error}"
        )
        return None

    def collect_financial_news(
        self, num_pages: int = 5, max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        采集财经要闻

        Args:
            num_pages: 采集页数
            max_retries: 最大重试次数

        Returns:
            新闻数据 DataFrame
        """
        logger.info(f"开始采集财经要闻，页数: {num_pages}")

        task_name = "financial_news"
        start_time = datetime.now()
        last_error = None

        all_news = []

        for page in range(1, num_pages + 1):
            for attempt in range(max_retries):
                try:
                    # 使用 akshare 获取财经要闻
                    df = ak.stock_news_cx()

                    if df is not None and not df.empty:
                        all_news.append(df)
                        logger.info(f"第 {page} 页采集成功: {len(df)} 条")

                    # 避免请求过于频繁
                    import time

                    time.sleep(0.5)
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"第 {page} 页采集失败，重试中...")
                        time.sleep(wait_time)
                    else:
                        logger.warning(f"第 {page} 页采集最终失败: {e}")

        if not all_news:
            logger.error("财经要闻采集完全失败")
            self.db_manager and self.db_manager.log_collection(
                task_name, "error", "采集完全失败"
            )
            return None

        # 合并所有数据
        combined_df = pd.concat(all_news, ignore_index=True)

        # 去重
        combined_df = combined_df.drop_duplicates(subset=["标题"], keep="first")

        # 添加元数据
        combined_df["_collected_at"] = datetime.now()
        combined_df["_news_id"] = combined_df.apply(
            lambda row: self._generate_news_id(
                str(row.get("标题", row.get("title", ""))),
                str(row.get("链接", row.get("url", ""))),
                str(row.get("发布时间", row.get("pub_time", ""))),
            ),
            axis=1,
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"财经要闻采集完成: {len(combined_df)} 条, 耗时: {elapsed:.2f}s")

        self.db_manager and self.db_manager.log_collection(
            task_name, "success", f"采集成功: {len(combined_df)} 条新闻"
        )

        return combined_df

    def collect_all_stocks_news(
        self, days: int = 3, max_stocks: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量采集关注列表中所有股票的新闻

        Args:
            days: 采集最近几天的新闻
            max_stocks: 最多采集多少只股票（None 表示全部）

        Returns:
            股票代码 -> 新闻 DataFrame 的字典
        """
        logger.info("开始批量采集关注股票新闻...")

        stocks = self.stocks_config.get("stocks", [])
        if max_stocks:
            stocks = stocks[:max_stocks]

        results = {}
        total_start = datetime.now()

        for idx, stock in enumerate(stocks, 1):
            code = stock.get("code")
            name = stock.get("name")

            if not code:
                continue

            logger.info(f"[{idx}/{len(stocks)}] 采集 {name} ({code}) 的新闻...")

            df = self.collect_individual_news(code, days=days)
            if df is not None and not df.empty:
                results[code] = df

            # 避免请求过于频繁
            import time

            time.sleep(1)

        total_elapsed = (datetime.now() - total_start).total_seconds()
        total_news = sum(len(df) for df in results.values())

        logger.info(f"批量采集完成: {len(results)}/{len(stocks)} 只股票, 共 {total_news} 条新闻, 耗时: {total_elapsed:.2f}s")

        return results

    def save_news_to_database(self, df: pd.DataFrame, stock_code: Optional[str] = None) -> bool:
        """
        保存新闻数据到数据库

        Args:
            df: 新闻数据 DataFrame
            stock_code: 关联的股票代码（可选）

        Returns:
            是否保存成功
        """
        if not self.db_manager:
            logger.warning("数据库未配置，跳过保存")
            return False

        if df is None or df.empty:
            logger.warning("新闻数据为空，跳过保存")
            return False

        try:
            news_data = []

            for _, row in df.iterrows():
                # 提取字段（适配不同数据源）
                title = str(
                    row.get("标题", row.get("title", row.get("news_title", "")))
                ).strip()

                content = str(
                    row.get("内容", row.get("content", row.get("摘要", row.get("summary", ""))))
                ).strip()

                url = str(row.get("链接", row.get("url", row.get("news_url", "")))).strip()

                source = str(
                    row.get("来源", row.get("source", row.get("media_name", "未知")))
                ).strip()

                pub_time = self._safe_datetime(
                    row.get("发布时间", row.get("pub_time", row.get("ctime", None)))
                )

                news_id = row.get("_news_id")
                if not news_id:
                    news_id = self._generate_news_id(title, url, str(pub_time))

                # 关联的股票代码
                related_stock = stock_code or row.get("_stock_code")

                news_item = {
                    "news_id": news_id,
                    "stock_code": related_stock,
                    "title": title[:500] if title else "无标题",  # 限制长度
                    "content": content[:4000] if content else "",  # 限制长度
                    "url": url[:1000] if url else "",
                    "source": source[:100] if source else "未知",
                    "published_at": pub_time,
                }

                news_data.append(news_item)

            # 批量插入
            if news_data:
                success = self.db_manager.insert_stock_news_batch(news_data)
                if success:
                    logger.info(f"成功保存 {len(news_data)} 条新闻到数据库")
                return success

            return True

        except Exception as e:
            logger.error(f"保存新闻到数据库失败: {e}")
            return False

    def save_news_to_csv(self, df: pd.DataFrame, prefix: str = "news") -> Optional[Path]:
        """
        保存新闻数据到 CSV 文件

        Args:
            df: 新闻数据 DataFrame
            prefix: 文件名前缀

        Returns:
            保存的文件路径
        """
        if df is None or df.empty:
            logger.warning("新闻数据为空，跳过保存")
            return None

        try:
            storage_path = Path(self.settings["storage"]["path"])
            news_path = storage_path / "news"
            news_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.csv"
            filepath = news_path / filename

            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logger.info(f"新闻数据已保存到: {filepath}")

            return filepath

        except Exception as e:
            logger.error(f"保存新闻到 CSV 失败: {e}")
            return None

    def run(self):
        """运行新闻采集任务"""
        logger.info("=" * 50)
        logger.info("股票新闻采集任务开始")
        logger.info("=" * 50)

        try:
            # 1. 采集财经要闻
            financial_news = self.collect_financial_news(num_pages=3)
            if financial_news is not None:
                self.save_news_to_database(financial_news)
                self.save_news_to_csv(financial_news, prefix="financial_news")

            # 2. 采集关注股票的新闻
            stock_news_results = self.collect_all_stocks_news(days=3)
            for code, df in stock_news_results.items():
                self.save_news_to_database(df, stock_code=code)
                self.save_news_to_csv(df, prefix=f"news_{code}")

        finally:
            logger.info("新闻采集任务完成")

    def close(self):
        """关闭资源"""
        if self.db_manager:
            self.db_manager.close()
            logger.info("新闻采集器数据库连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    with NewsCollector() as collector:
        collector.run()
