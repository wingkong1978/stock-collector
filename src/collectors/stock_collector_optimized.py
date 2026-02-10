#!/usr/bin/env python3
"""
Stock Data Collector - Optimized Version
定时采集股票数据（优化版）
"""

import json
import os
import sys
import signal
import atexit
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal, InvalidOperation
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import akshare as ak
import pandas as pd
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_manager import get_db_manager, DatabaseManager

# 配置日志 - 更详细的格式
logger.remove()
logger.add(
    "logs/stock_collector.log",
    rotation="10MB",
    retention="30 days",
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/stock_collector_error.log",
    rotation="10MB",
    retention="30 days",
    level="ERROR",
    format="<red>{time:YYYY-MM-DD HH:mm:ss}</red> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    import time
                    time.sleep(delay * (attempt + 1))  # 指数退避
        return wrapper
    return decorator


def timing_decorator(func):
    """性能计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = datetime.now()
        try:
            result = func(*args, **kwargs)
            elapsed = (datetime.now() - start).total_seconds()
            logger.info(f"{func.__name__} 完成，耗时: {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            logger.error(f"{func.__name__} 失败，耗时: {elapsed:.2f}s, 错误: {e}")
            raise
    return wrapper


class StockCollector:
    """股票数据采集器（优化版）"""
    
    # 类级别的线程锁，防止并发问题
    _instance_lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """单例模式，确保只有一个采集器实例"""
        if not hasattr(cls, '_instance'):
            with cls._instance_lock:
                if not hasattr(cls, '_instance'):
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config"):
        # 避免重复初始化
        if StockCollector._initialized:
            return
            
        with StockCollector._instance_lock:
            if StockCollector._initialized:
                return
                
            self.config_path = Path(config_path)
            self._shutdown_event = threading.Event()
            self._executor: Optional[ThreadPoolExecutor] = None
            
            # 加载配置
            self._load_config()
            self._setup_storage()
            
            # 数据库管理器
            self.db_manager: Optional[DatabaseManager] = None
            if self.settings.get("storage", {}).get("database"):
                self._init_database()
            
            # 注册退出处理
            atexit.register(self.close)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            StockCollector._initialized = True
            logger.info("StockCollector 初始化完成")
    
    def _signal_handler(self, signum, frame):
        """信号处理 - 优雅关闭"""
        logger.info(f"收到信号 {signum}，开始优雅关闭...")
        self._shutdown_event.set()
        self.close()
        sys.exit(0)
    
    def _load_config(self) -> None:
        """加载配置文件（带验证）"""
        try:
            stocks_path = self.config_path / "stocks.json"
            settings_path = self.config_path / "settings.json"
            
            if not stocks_path.exists():
                raise FileNotFoundError(f"股票配置文件不存在: {stocks_path}")
            if not settings_path.exists():
                raise FileNotFoundError(f"设置配置文件不存在: {settings_path}")
            
            with open(stocks_path, "r", encoding="utf-8") as f:
                self.stocks_config = json.load(f)
            with open(settings_path, "r", encoding="utf-8") as f:
                self.settings = json.load(f)
            
            # 验证配置
            self._validate_config()
            logger.info("配置加载成功")
            
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise
    
    def _validate_config(self) -> None:
        """验证配置完整性"""
        required_settings = ["collection", "storage"]
        for key in required_settings:
            if key not in self.settings:
                raise ValueError(f"配置文件缺少必要字段: {key}")
        
        if "stocks" not in self.stocks_config:
            logger.warning("未配置关注的股票列表")
    
    def _setup_storage(self) -> None:
        """设置存储目录"""
        storage_path = Path(self.settings["storage"]["path"])
        self.raw_path = storage_path / "raw"
        self.processed_path = storage_path / "processed"

        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录按日期组织
        today = datetime.now().strftime("%Y%m%d")
        self.daily_raw_path = self.raw_path / today
        self.daily_processed_path = self.processed_path / today
        self.daily_raw_path.mkdir(exist_ok=True)
        self.daily_processed_path.mkdir(exist_ok=True)

    def _init_database(self) -> None:
        """初始化数据库连接"""
        try:
            self.db_manager = get_db_manager()
            self.db_manager.init_tables()
            logger.info("数据库初始化成功")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}，将使用文件存储作为备用")
            self.db_manager = None
    
    @retry_on_error(max_retries=3, delay=1.0)
    @timing_decorator
    def sync_stock_basic_info(self) -> Tuple[int, int]:
        """
        同步股票基本信息到数据库
        返回: (成功数, 总数)
        """
        if not self.db_manager:
            return 0, 0

        stocks = self.stocks_config.get("stocks", [])
        if not stocks:
            logger.warning("没有配置股票列表")
            return 0, 0

        logger.info(f"开始同步 {len(stocks)} 只股票的基本信息...")
        success_count = 0

        for stock in stocks:
            if self._shutdown_event.is_set():
                logger.info("收到关闭信号，停止同步")
                break
                
            code = stock.get("code")
            name = stock.get("name")
            market = stock.get("market")

            if not all([code, name, market]):
                logger.warning(f"股票信息不完整: {stock}")
                continue
                
            try:
                if self.db_manager.insert_stock(code, name, market):
                    success_count += 1
            except Exception as e:
                logger.error(f"同步股票 {code} 失败: {e}")

        logger.info(f"股票基本信息同步完成: {success_count}/{len(stocks)}")
        return success_count, len(stocks)

    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """安全转换为 Decimal 类型"""
        try:
            if pd.isna(value) or value == "-" or value == "":
                return None
            return Decimal(str(value).replace(",", ""))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """安全转换为 int 类型"""
        try:
            if pd.isna(value) or value == "-" or value == "":
                return None
            return int(float(str(value).replace(",", "")))
        except (ValueError, TypeError):
            return None

    def _prepare_price_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """准备价格数据用于批量插入（优化版）"""
        if df.empty:
            return []
            
        price_data = []
        
        # 字段映射
        field_mapping = {
            "代码": "stock_code",
            "最新价": "price",
            "涨跌幅": "change_percent",
            "成交量": "volume",
            "成交额": "turnover"
        }

        # 使用向量化操作提高效率
        for ak_col, db_col in field_mapping.items():
            if ak_col not in df.columns:
                logger.warning(f"数据源缺少字段: {ak_col}")
                continue

        for _, row in df.iterrows():
            if self._shutdown_event.is_set():
                break
                
            data = {}
            for ak_col, db_col in field_mapping.items():
                if ak_col not in row:
                    continue
                    
                value = row[ak_col]
                if db_col in ("price", "change_percent", "turnover"):
                    data[db_col] = self._safe_decimal(value)
                elif db_col == "volume":
                    data[db_col] = self._safe_int(value)
                else:
                    data[db_col] = str(value).strip() if pd.notna(value) else None

            # 验证必要字段
            if data.get("stock_code") and data.get("price") is not None:
                price_data.append(data)

        return price_data
    
    @retry_on_error(max_retries=3, delay=2.0)
    @timing_decorator
    def collect_realtime_data(self) -> Optional[pd.DataFrame]:
        """采集实时行情数据（优化版）"""
        if self._shutdown_event.is_set():
            logger.info("收到关闭信号，跳过采集")
            return None
            
        logger.info("开始采集实时数据...")
        task_name = "realtime_data_collection"

        try:
            # 获取A股实时行情
            df = ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                raise ValueError("akshare 返回空数据")

            # 筛选关注的股票
            stock_codes = [s["code"] for s in self.stocks_config.get("stocks", [])]
            if not stock_codes:
                logger.warning("未配置关注的股票")
                return None
                
            filtered_df = df[df["代码"].isin(stock_codes)].copy()

            if filtered_df.empty:
                logger.warning(f"未找到匹配的股票数据: {stock_codes}")
                self.db_manager and self.db_manager.log_collection(task_name, "warning", "未找到匹配的股票数据")
                return None

            # 保存CSV文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"realtime_{timestamp}.csv"
            filepath = self.daily_raw_path / filename
            filtered_df.to_csv(filepath, index=False, encoding="utf-8-sig")

            # 保存到数据库
            if self.db_manager:
                price_data = self._prepare_price_data(filtered_df)
                if price_data:
                    if self.db_manager.insert_stock_prices_batch(price_data):
                        logger.info(f"成功保存 {len(price_data)} 条价格数据到数据库")
                    else:
                        logger.error("批量插入数据库失败")

            logger.info(f"实时数据已保存: {filepath}")
            self.db_manager and self.db_manager.log_collection(
                task_name, "success", f"采集成功: {len(filtered_df)} 条记录"
            )

            return filtered_df

        except Exception as e:
            logger.error(f"数据采集失败: {e}")
            self.db_manager and self.db_manager.log_collection(task_name, "error", str(e))
            return None
    
    @timing_decorator
    def collect_index_data(self) -> Optional[pd.DataFrame]:
        """采集指数数据（优化版，使用线程池）"""
        if self._shutdown_event.is_set():
            return None
            
        logger.info("开始采集指数数据...")
        task_name = "index_data_collection"
        
        indexes = self.stocks_config.get("indexs", [])
        if not indexes:
            logger.info("未配置指数列表")
            return None

        all_data = []
        errors = []

        def fetch_index(index: Dict) -> Optional[pd.DataFrame]:
            """获取单个指数数据"""
            if self._shutdown_event.is_set():
                return None
                
            symbol = index.get("code")
            name = index.get("name")
            if not symbol:
                return None

            try:
                df = ak.index_zh_a_hist(symbol=symbol, period="daily")
                if not df.empty:
                    df["指数名称"] = name
                    df["指数代码"] = symbol
                    logger.info(f"采集 {name} 数据成功: {len(df)} 条")
                    return df
            except Exception as e:
                errors.append(f"{name}: {e}")
                logger.warning(f"采集指数 {name} 失败: {e}")
            return None

        # 使用线程池并发采集
        max_workers = min(len(indexes), 4)  # 最多4个线程
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_index, idx): idx for idx in indexes}
            
            for future in as_completed(futures):
                if self._shutdown_event.is_set():
                    break
                result = future.result()
                if result is not None:
                    all_data.append(result)

        if not all_data:
            logger.warning("未采集到任何指数数据")
            self.db_manager and self.db_manager.log_collection(task_name, "warning", "未采集到指数数据")
            return None

        # 合并数据
        combined_df = pd.concat(all_data, ignore_index=True)

        # 保存CSV文件
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"index_{timestamp}.csv"
        filepath = self.daily_raw_path / filename
        combined_df.to_csv(filepath, index=False, encoding="utf-8-sig")

        logger.info(f"指数数据已保存: {filepath}")
        self.db_manager and self.db_manager.log_collection(
            task_name, "success", f"采集成功: {len(combined_df)} 条记录"
        )

        return combined_df
    
    def is_market_hours(self) -> bool:
        """检查是否在股市交易时间"""
        now = datetime.now().time()
        # 上午 9:30-11:30，下午 13:00-15:00
        morning_start = dt_time(9, 30)
        morning_end = dt_time(11, 30)
        afternoon_start = dt_time(13, 0)
        afternoon_end = dt_time(15, 0)
        
        return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)
    
    def run(self) -> None:
        """运行采集任务（优化版）"""
        if self._shutdown_event.is_set():
            return
            
        logger.info("=" * 60)
        logger.info("股票数据采集任务开始")
        logger.info(f"交易时间检查: {'是' if self.is_market_hours() else '否'}")
        logger.info("=" * 60)

        try:
            # 同步股票基本信息
            if self.db_manager:
                self.sync_stock_basic_info()

            # 采集实时数据
            self.collect_realtime_data()

            # 采集指数数据（收盘后或每天一次）
            current_hour = datetime.now().hour
            if current_hour >= 15:
                self.collect_index_data()

        except Exception as e:
            logger.exception(f"采集任务异常: {e}")
        finally:
            logger.info("采集任务完成")

    def close(self) -> None:
        """关闭资源（线程安全）"""
        if not StockCollector._initialized:
            return
            
        with StockCollector._instance_lock:
            if StockCollector._initialized:
                logger.info("正在关闭资源...")
                
                if self._executor:
                    self._executor.shutdown(wait=True)
                    
                if self.db_manager:
                    try:
                        self.db_manager.close()
                        logger.info("数据库连接已关闭")
                    except Exception as e:
                        logger.error(f"关闭数据库连接失败: {e}")
                
                StockCollector._initialized = False
                logger.info("资源关闭完成")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    try:
        with StockCollector() as collector:
            collector.run()
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.exception(f"程序异常退出: {e}")
        sys.exit(1)
