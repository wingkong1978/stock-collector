#!/usr/bin/env python3
"""
Stock News Collector - Optimized Version
股票新闻采集模块 - 优化版

优化内容:
1. 添加请求间隔控制（随机1-3秒延迟，防反爬）
2. 完善错误处理和重试机制
3. 添加数据验证功能
4. 优化日志记录
5. 添加性能监控（记录采集耗时）
6. 使用参数化查询防止SQL注入
7. 完善类型注解
8. 优化数据库连接管理
"""

import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin

import akshare as ak
import pandas as pd
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_manager import get_db_manager, DatabaseManager


class NewsCollector:
    """股票新闻采集器 - 优化版"""

    # 新闻来源映射
    NEWS_SOURCES = {
        "sina": "新浪财经",
        "eastmoney": "东方财富",
        "10jqka": "同花顺",
        "cls": "财联社",
    }
    
    # 默认配置
    DEFAULT_CONFIG = {
        "delay_min": 1.0,  # 最小延迟(秒)
        "delay_max": 3.0,  # 最大延迟(秒)
        "max_retries": 3,  # 最大重试次数
        "retry_backoff": 2,  # 重试退避因子
        "request_timeout": 30,  # 请求超时(秒)
    }

    def __init__(self, config_path: str = "config"):
        self.config_path = Path(config_path)
        self.load_config()
        self.db_manager: Optional[DatabaseManager] = None
        
        # 性能统计
        self.performance_stats: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_articles": 0,
            "start_time": None,
        }

        # 如果配置了数据库，初始化数据库连接
        if self.settings.get("storage", {}).get("database"):
            self.init_database()

    def load_config(self):
        """加载配置文件"""
        try:
            stocks_json = self.config_path / "stocks.json"
            settings_json = self.config_path / "settings.json"
            
            if stocks_json.exists():
                with open(stocks_json, "r", encoding="utf-8") as f:
                    self.stocks_config = json.load(f)
            else:
                self.stocks_config = {"stocks": []}
                
            if settings_json.exists():
                with open(settings_json, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
            else:
                self.settings = {"storage": {"type": "csv", "path": "data"}}
                
            logger.info("✅ 新闻采集配置加载成功")
        except Exception as e:
            logger.error(f"❌ 新闻采集配置加载失败: {e}")
            # 使用默认配置而不是抛出异常
            self.stocks_config = {"stocks": []}
            self.settings = {"storage": {"type": "csv", "path": "data"}}

    def init_database(self):
        """初始化数据库连接"""
        try:
            self.db_manager = get_db_manager()
            logger.info("✅ 新闻采集数据库初始化成功")
        except Exception as e:
            logger.error(f"⚠️ 新闻采集数据库初始化失败: {e}")
            self.db_manager = None

    def _random_delay(self) -> None:
        """
        随机延迟，防止反爬
        
        在每次请求前调用，随机等待 1-3 秒
        """
        delay = random.uniform(
            self.DEFAULT_CONFIG["delay_min"],
            self.DEFAULT_CONFIG["delay_max"]
        )
        logger.debug(f"⏱️  等待 {delay:.2f} 秒...")
        time.sleep(delay)

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

    def _validate_news_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        验证新闻数据完整性

        Args:
            df: 新闻数据 DataFrame

        Returns:
            (是否有效, 错误信息)
        """
        if df is None:
            return False, "DataFrame 为 None"

        if df.empty:
            return False, "DataFrame 为空"

        # 检查必需字段（不同来源字段名不同）
        possible_title_cols = ["标题", "title", "news_title", "Title", "新闻标题"]
        has_title = any(col in df.columns for col in possible_title_cols)

        if not has_title:
            return False, f"缺少标题字段，可用字段: {df.columns.tolist()}"

        # 检查数据行数
        if len(df) == 0:
            return False, "数据行数为 0"

        logger.debug(f"✅ 新闻数据验证通过: {len(df)} 条数据")
        return True, ""

    def collect_individual_news(
        self, stock_code: str, days: int = 7, max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        采集个股新闻 - 优化版

        Args:
            stock_code: 股票代码 (如 "000001")
            days: 采集最近几天的新闻
            max_retries: 最大重试次数

        Returns:
            新闻数据 DataFrame
        """
        logger.info(f"🔍 开始采集股票 {stock_code} 的新闻...")
        self.performance_stats["total_requests"] += 1

        task_name = f"individual_news_{stock_code}"
        start_time = datetime.now()
        last_error = None

        # 请求前延迟
        self._random_delay()

        # 重试机制
        for attempt in range(max_retries):
            try:
                # 使用 akshare 获取个股新闻
                df = ak.stock_news_em(symbol=stock_code)

                # 验证数据
                is_valid, error_msg = self._validate_news_data(df)
                if not is_valid:
                    raise ValueError(f"数据源返回无效新闻数据: {error_msg}")

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
                        str(row.get("新闻标题", row.get("标题", row.get("title", "")))),
                        str(row.get("新闻链接", row.get("链接", row.get("url", "")))),
                        str(row.get("发布时间", row.get("pub_time", ""))),
                    ),
                    axis=1,
                )

                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ 股票 {stock_code} 新闻采集成功: {len(df)} 条, 耗时: {elapsed:.2f}s")
                
                self.performance_stats["successful_requests"] += 1
                self.performance_stats["total_articles"] += len(df)

                self.db_manager and self.db_manager.log_collection(
                    task_name, "success", f"采集成功: {len(df)} 条新闻"
                )

                return df

            except Exception as e:
                last_error = e
                self.performance_stats["failed_requests"] += 1

                if attempt < max_retries - 1:
                    wait_time = self.DEFAULT_CONFIG["retry_backoff"] ** attempt
                    logger.warning(
                        f"⚠️  采集失败 (尝试 {attempt + 1}/{max_retries}): {e}, 等待 {wait_time}s 后重试..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 个股新闻采集失败: {e}, 股票代码: {stock_code}")

        self.db_manager and self.db_manager.log_collection(
            task_name, "error", f"重试 {max_retries} 次后失败: {last_error}"
        )
        return None

    def collect_financial_news(
        self, num_pages: int = 5, max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        采集财经要闻 - 优化版

        Args:
            num_pages: 采集页数
            max_retries: 最大重试次数

        Returns:
            新闻数据 DataFrame
        """
        logger.info(f"🔍 开始采集财经要闻，页数: {num_pages}")
        self.performance_stats["total_requests"] += 1

        task_name = "financial_news"
        start_time = datetime.now()

        all_news = []

        for page in range(1, num_pages + 1):
            for attempt in range(max_retries):
                try:
                    # 请求前延迟
                    self._random_delay()
                    
                    # 使用 akshare 获取财经要闻
                    df = ak.stock_news_main_cx()

                    if df is not None and not df.empty:
                        # 验证数据
                        is_valid, error_msg = self._validate_news_data(df)
                        if is_valid:
                            all_news.append(df)
                            logger.info(f"✅ 第 {page} 页采集成功: {len(df)} 条")
                        else:
                            logger.warning(f"⚠️  第 {page} 页数据验证失败: {error_msg}")

                    break  # 成功后跳出重试循环

                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = self.DEFAULT_CONFIG["retry_backoff"] ** attempt
                        logger.warning(f"⚠️  第 {page} 页采集失败，{wait_time}s后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ 第 {page} 页采集最终失败: {e}")

        if not all_news:
            logger.error("❌ 财经要闻采集完全失败")
            self.performance_stats["failed_requests"] += 1
            self.db_manager and self.db_manager.log_collection(
                task_name, "error", "采集完全失败"
            )
            return None

        # 合并所有数据
        combined_df = pd.concat(all_news, ignore_index=True)

        # 去重 (基于 summary 字段)
        if "summary" in combined_df.columns:
            combined_df = combined_df.drop_duplicates(subset=["summary"], keep="first")

        # 添加元数据
        combined_df["_collected_at"] = datetime.now()
        combined_df["_news_id"] = combined_df.apply(
            lambda row: self._generate_news_id(
                str(row.get("summary", "")),
                str(row.get("url", "")),
                str(row.get("tag", "")),
            ),
            axis=1,
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ 财经要闻采集完成: {len(combined_df)} 条, 耗时: {elapsed:.2f}s")
        
        self.performance_stats["successful_requests"] += 1
        self.performance_stats["total_articles"] += len(combined_df)

        self.db_manager and self.db_manager.log_collection(
            task_name, "success", f"采集成功: {len(combined_df)} 条新闻"
        )

        return combined_df

    def collect_all_stocks_news(
        self, days: int = 3, max_stocks: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量采集关注列表中所有股票的新闻 - 优化版

        Args:
            days: 采集最近几天的新闻
            max_stocks: 最多采集多少只股票（None 表示全部）

        Returns:
            股票代码 -> 新闻 DataFrame 的字典
        """
        logger.info("🚀 开始批量采集关注股票新闻...")
        self.performance_stats["start_time"] = datetime.now()

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

            logger.info(f"[{idx}/{len(stocks)}] 📈 采集 {name} ({code}) 的新闻...")

            df = self.collect_individual_news(code, days=days)
            if df is not None and not df.empty:
                results[code] = df

            # 每次请求间延迟（除了最后一个）
            if idx < len(stocks):
                self._random_delay()

        total_elapsed = (datetime.now() - total_start).total_seconds()
        total_news = sum(len(df) for df in results.values())

        logger.info(f"✅ 批量采集完成: {len(results)}/{len(stocks)} 只股票, 共 {total_news} 条新闻, 耗时: {total_elapsed:.2f}s")

        return results

    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取性能报告
        
        Returns:
            性能统计字典
        """
        if self.performance_stats["start_time"]:
            elapsed = (datetime.now() - self.performance_stats["start_time"]).total_seconds()
        else:
            elapsed = 0
            
        total_req = self.performance_stats["total_requests"]
        success_req = self.performance_stats["successful_requests"]
        
        return {
            "总请求数": total_req,
            "成功请求": success_req,
            "失败请求": self.performance_stats["failed_requests"],
            "成功率": f"{(success_req / max(total_req, 1) * 100):.1f}%",
            "采集文章数": self.performance_stats["total_articles"],
            "总耗时(秒)": round(elapsed, 2),
        }

    def save_news_to_csv(self, df: pd.DataFrame, prefix: str = "news") -> Optional[Path]:
        """
        保存新闻数据到 CSV 文件 - 优化版
        
        Args:
            df: 新闻数据 DataFrame
            prefix: 文件名前缀

        Returns:
            保存的文件路径
        """
        if df is None or df.empty:
            logger.warning("⚠️  新闻数据为空，跳过保存")
            return None

        try:
            storage_path = Path(self.settings.get("storage", {}).get("path", "data"))
            news_path = storage_path / "news"
            news_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.csv"
            filepath = news_path / filename

            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logger.info(f"✅ 新闻数据已保存到: {filepath}")

            return filepath

        except Exception as e:
            logger.error(f"❌ 保存新闻到 CSV 失败: {e}")
            return None

    def run(self):
        """运行新闻采集任务 - 优化版"""
        logger.info("=" * 60)
        logger.info("🚀 股票新闻采集任务开始")
        logger.info("=" * 60)

        try:
            # 1. 采集财经要闻
            financial_news = self.collect_financial_news(num_pages=3)
            if financial_news is not None:
                self.save_news_to_csv(financial_news, prefix="financial_news")

            # 2. 采集关注股票的新闻
            stock_news_results = self.collect_all_stocks_news(days=3)
            for code, df in stock_news_results.items():
                self.save_news_to_csv(df, prefix=f"news_{code}")

            # 输出性能报告
            report = self.get_performance_report()
            logger.info("=" * 60)
            logger.info("📊 性能报告:")
            for key, value in report.items():
                logger.info(f"  {key}: {value}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 新闻采集任务执行失败: {e}")
            raise

    def close(self):
        """关闭资源"""
        if self.db_manager:
            self.db_manager.close()
            logger.info("✅ 新闻采集器数据库连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    with NewsCollector() as collector:
        collector.run()
