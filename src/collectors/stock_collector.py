#!/usr/bin/env python3
"""
Stock Data Collector
定时采集股票数据
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from decimal import Decimal, InvalidOperation

import akshare as ak
import pandas as pd
from loguru import logger

from database.db_manager import get_db_manager, DatabaseManager

# 配置日志
logger.add(
    "logs/stock_collector.log",
    rotation="10MB",
    retention="30 days",
    level="INFO"
)


class StockCollector:
    def __init__(self, config_path: str = "config"):
        self.config_path = Path(config_path)
        self.load_config()
        self.setup_storage()
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
            logger.info("配置加载成功")
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise
    
    def setup_storage(self):
        """设置存储目录"""
        storage_path = Path(self.settings["storage"]["path"])
        self.raw_path = storage_path / "raw"
        self.processed_path = storage_path / "processed"

        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)

    def init_database(self):
        """初始化数据库连接"""
        try:
            self.db_manager = get_db_manager()
            self.db_manager.init_tables()
            logger.info("数据库初始化成功")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            # 不中断程序，仍可使用文件存储
            self.db_manager = None

    def sync_stock_basic_info(self):
        """同步股票基本信息到数据库"""
        if not self.db_manager:
            return False

        logger.info("开始同步股票基本信息...")
        success_count = 0
        total_count = len(self.stocks_config.get("stocks", []))

        for stock in self.stocks_config.get("stocks", []):
            code = stock.get("code")
            name = stock.get("name")
            market = stock.get("market")

            if code and name and market:
                if self.db_manager.insert_stock(code, name, market):
                    success_count += 1

        logger.info(f"股票基本信息同步完成: {success_count}/{total_count}")
        return success_count > 0

    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """安全转换为 Decimal 类型"""
        try:
            if pd.isna(value):
                return None
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """安全转换为 int 类型"""
        try:
            if pd.isna(value):
                return None
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None

    def _prepare_price_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """准备价格数据用于批量插入"""
        price_data = []

        # 字段映射: akshare列名 -> 数据库字段名
        field_mapping = {
            "代码": "stock_code",
            "最新价": "price",
            "涨跌幅": "change_percent",
            "成交量": "volume",
            "成交额": "turnover"
        }

        for _, row in df.iterrows():
            data = {}
            for ak_col, db_col in field_mapping.items():
                if ak_col not in row:
                    continue

                if db_col in ("price", "change_percent", "turnover"):
                    data[db_col] = self._safe_decimal(row[ak_col])
                elif db_col == "volume":
                    data[db_col] = self._safe_int(row[ak_col])
                else:
                    data[db_col] = str(row[ak_col]).strip()

            # 只包含有效数据
            if all(key in data and data[key] is not None for key in ["stock_code", "price"]):
                price_data.append(data)

        return price_data
        
    def collect_realtime_data(self):
        """采集实时行情数据"""
        logger.info("开始采集实时数据...")

        task_name = "realtime_data_collection"
        start_time = datetime.now()

        try:
            # 获取A股实时行情
            df = ak.stock_zh_a_spot_em()

            # 筛选关注的股票
            stock_codes = [s["code"] for s in self.stocks_config["stocks"]]
            filtered_df = df[df["代码"].isin(stock_codes)]

            if filtered_df.empty:
                logger.warning("未找到匹配的股票数据")
                self.db_manager and self.db_manager.log_collection(task_name, "warning", "未找到匹配的股票数据")
                return None

            # 保存CSV文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"realtime_{timestamp}.csv"
            filepath = self.raw_path / filename
            filtered_df.to_csv(filepath, index=False, encoding="utf-8-sig")

            # 保存到数据库（批量插入）
            if self.db_manager:
                price_data = self._prepare_price_data(filtered_df)
                if price_data:
                    # 先同步股票基本信息
                    self.sync_stock_basic_info()

                    # 批量插入价格数据
                    if self.db_manager.insert_stock_prices_batch(price_data):
                        logger.info(f"成功保存 {len(price_data)} 条价格数据到数据库")

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"实时数据已保存: {filepath}, 耗时: {elapsed:.2f}s")
            self.db_manager and self.db_manager.log_collection(task_name, "success", f"采集成功: {len(filtered_df)} 条记录")

            return filtered_df

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"数据采集失败: {e}, 耗时: {elapsed:.2f}s")
            self.db_manager and self.db_manager.log_collection(task_name, "error", str(e))
            return None
    
    def collect_index_data(self):
        """采集指数数据"""
        logger.info("开始采集指数数据...")

        task_name = "index_data_collection"
        start_time = datetime.now()

        try:
            # 获取配置的指数列表
            indexes = self.stocks_config.get("indexs", [])
            all_data = []

            for index in indexes:
                symbol = index.get("code")
                name = index.get("name")
                if not symbol:
                    continue

                try:
                    # 获取指数历史数据
                    df = ak.index_zh_a_hist(symbol=symbol, period="daily")

                    if not df.empty:
                        # 添加指数名称
                        df["指数名称"] = name
                        all_data.append(df)
                        logger.info(f"采集 {name} 数据成功: {len(df)} 条")
                except Exception as e:
                    logger.warning(f"采集指数 {name} 失败: {e}")
                    continue

            if not all_data:
                logger.warning("未采集到任何指数数据")
                self.db_manager and self.db_manager.log_collection(task_name, "warning", "未采集到指数数据")
                return None

            # 合并所有指数数据
            combined_df = pd.concat(all_data, ignore_index=True)

            # 保存CSV文件
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"index_{timestamp}.csv"
            filepath = self.raw_path / filename
            combined_df.to_csv(filepath, index=False, encoding="utf-8-sig")

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"指数数据已保存: {filepath}, 耗时: {elapsed:.2f}s")
            self.db_manager and self.db_manager.log_collection(task_name, "success", f"采集成功: {len(combined_df)} 条记录")

            return combined_df

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"指数数据采集失败: {e}, 耗时: {elapsed:.2f}s")
            self.db_manager and self.db_manager.log_collection(task_name, "error", str(e))
            return None
    
    def run(self):
        """运行采集任务"""
        logger.info("=" * 50)
        logger.info("股票数据采集任务开始")
        logger.info("=" * 50)

        try:
            # 同步股票基本信息
            if self.db_manager:
                self.sync_stock_basic_info()

            # 采集实时数据
            self.collect_realtime_data()

            # 采集指数数据（每天收盘后采集一次）
            current_hour = datetime.now().hour
            if current_hour >= 15 or current_hour < 9:  # 收盘后或开盘前
                self.collect_index_data()

        finally:
            logger.info("采集任务完成")

    def close(self):
        """关闭资源"""
        if self.db_manager:
            self.db_manager.close()
            logger.info("数据库连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

if __name__ == "__main__":
    with StockCollector() as collector:
        collector.run()
