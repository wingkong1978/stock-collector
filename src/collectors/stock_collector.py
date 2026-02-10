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

import akshare as ak
import pandas as pd
from loguru import logger

# 配置日志
logger.add(
    "logs/stock_collector.log",
    rotation="10MB",
    retention="30 days",
    level="INFO"
)

class StockCollector:
    def __init__(self, config_path="config"):
        self.config_path = Path(config_path)
        self.load_config()
        self.setup_storage()
        
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
        
    def collect_realtime_data(self):
        """采集实时行情数据"""
        logger.info("开始采集实时数据...")
        
        try:
            # 获取A股实时行情
            df = ak.stock_zh_a_spot_em()
            
            # 筛选关注的股票
            stock_codes = [s["code"] for s in self.stocks_config["stocks"]]
            filtered_df = df[df["代码"].isin(stock_codes)]
            
            # 保存数据
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"realtime_{timestamp}.csv"
            filepath = self.raw_path / filename
            
            filtered_df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logger.info(f"实时数据已保存: {filepath}")
            
            return filtered_df
            
        except Exception as e:
            logger.error(f"数据采集失败: {e}")
            return None
    
    def collect_index_data(self):
        """采集指数数据"""
        logger.info("开始采集指数数据...")
        
        try:
            # 获取主要指数
            df = ak.index_zh_a_hist(symbol="000001", period="daily")
            
            # 保存数据
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"index_{timestamp}.csv"
            filepath = self.raw_path / filename
            
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logger.info(f"指数数据已保存: {filepath}")
            
            return df
            
        except Exception as e:
            logger.error(f"指数数据采集失败: {e}")
            return None
    
    def run(self):
        """运行采集任务"""
        logger.info("=" * 50)
        logger.info("股票数据采集任务开始")
        logger.info("=" * 50)
        
        # 采集实时数据
        self.collect_realtime_data()
        
        # 采集指数数据（每天只采一次）
        if datetime.now().hour == 15:  # 收盘后
            self.collect_index_data()
        
        logger.info("采集任务完成")

if __name__ == "__main__":
    collector = StockCollector()
    collector.run()
