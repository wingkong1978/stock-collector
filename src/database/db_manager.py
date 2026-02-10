"""
PostgreSQL 数据库连接模块
"""
import os
import json
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import SimpleConnectionPool
from loguru import logger


class DatabaseManager:
    """PostgreSQL 数据库管理器"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        self.config = self._load_config(config_path)
        self.db_config = self.config.get("storage", {}).get("database", {})
        self.connection_pool: Optional[SimpleConnectionPool] = None
        self._init_pool()
        
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}
    
    def _init_pool(self):
        """初始化连接池"""
        try:
            password = self.db_config.get("password", "")
            # 支持环境变量
            if password.startswith("${") and password.endswith("}"):
                env_var = password[2:-1]
                password = os.getenv(env_var, "")
            
            self.connection_pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.db_config.get("host", "localhost"),
                port=self.db_config.get("port", 5432),
                dbname=self.db_config.get("dbname", "stockdb"),
                user=self.db_config.get("user", "stockuser"),
                password=password,
                sslmode=self.db_config.get("sslmode", "prefer")
            )
            logger.info("数据库连接池初始化成功")
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """获取游标（上下文管理器）"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def init_tables(self):
        """初始化数据库表结构"""
        create_tables_sql = """
        -- 股票基本信息表
        CREATE TABLE IF NOT EXISTS stocks (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            market VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(code, market)
        );
        
        -- 股票实时数据表
        CREATE TABLE IF NOT EXISTS stock_prices (
            id SERIAL PRIMARY KEY,
            stock_code VARCHAR(20) NOT NULL,
            price DECIMAL(10, 2),
            change_percent DECIMAL(5, 2),
            volume BIGINT,
            turnover DECIMAL(15, 2),
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_stock_prices_code ON stock_prices(stock_code);
        CREATE INDEX IF NOT EXISTS idx_stock_prices_time ON stock_prices(collected_at);
        
        -- 数据采集日志表
        CREATE TABLE IF NOT EXISTS collection_logs (
            id SERIAL PRIMARY KEY,
            task_name VARCHAR(50),
            status VARCHAR(20),
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        with self.get_cursor() as cursor:
            cursor.execute(create_tables_sql)
            logger.info("数据库表初始化完成")
    
    def insert_stock(self, code: str, name: str, market: str) -> bool:
        """插入股票基本信息"""
        sql = """
        INSERT INTO stocks (code, name, market)
        VALUES (%s, %s, %s)
        ON CONFLICT (code, market) DO UPDATE SET
            name = EXCLUDED.name
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (code, name, market))
                logger.info(f"股票 {code} 插入/更新成功")
                return True
        except Exception as e:
            logger.error(f"插入股票失败: {e}")
            return False
    
    def insert_stock_price(self, stock_code: str, price: float, 
                          change_percent: float, volume: int, turnover: float) -> bool:
        """插入股票价格数据"""
        sql = """
        INSERT INTO stock_prices (stock_code, price, change_percent, volume, turnover)
        VALUES (%s, %s, %s, %s, %s)
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (stock_code, price, change_percent, volume, turnover))
                return True
        except Exception as e:
            logger.error(f"插入价格数据失败: {e}")
            return False
    
    def insert_stock_prices_batch(self, data: List[Dict[str, Any]]) -> bool:
        """批量插入股票价格数据"""
        sql = """
        INSERT INTO stock_prices (stock_code, price, change_percent, volume, turnover)
        VALUES %s
        """
        try:
            with self.get_cursor() as cursor:
                values = [
                    (d["stock_code"], d["price"], d["change_percent"], 
                     d["volume"], d["turnover"])
                    for d in data
                ]
                execute_values(cursor, sql, values)
                logger.info(f"批量插入 {len(data)} 条价格数据")
                return True
        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            return False
    
    def get_latest_prices(self, stock_code: Optional[str] = None, 
                         limit: int = 100) -> List[Dict]:
        """获取最新价格数据"""
        if stock_code:
            sql = """
            SELECT * FROM stock_prices
            WHERE stock_code = %s
            ORDER BY collected_at DESC
            LIMIT %s
            """
            params = (stock_code, limit)
        else:
            sql = """
            SELECT * FROM stock_prices
            ORDER BY collected_at DESC
            LIMIT %s
            """
            params = (limit,)
        
        try:
            with self.get_cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"查询数据失败: {e}")
            return []
    
    def log_collection(self, task_name: str, status: str, message: str = ""):
        """记录采集日志"""
        sql = """
        INSERT INTO collection_logs (task_name, status, message)
        VALUES (%s, %s, %s)
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (task_name, status, message))
        except Exception as e:
            logger.error(f"记录日志失败: {e}")
    
    def close(self):
        """关闭连接池"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("数据库连接池已关闭")


# 单例模式
db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（单例）"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


if __name__ == "__main__":
    # 测试数据库连接
    db = DatabaseManager()
    db.init_tables()
    
    # 测试插入数据
    db.insert_stock("000001", "平安银行", "sz")
    db.insert_stock_price("000001", 12.50, 1.25, 1000000, 12500000.00)
    
    # 查询数据
    prices = db.get_latest_prices(limit=10)
    print(f"查询到 {len(prices)} 条记录")
    
    db.close()
