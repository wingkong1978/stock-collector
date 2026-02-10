"""
PostgreSQL 数据库连接模块
"""
import os
import json
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import SimpleConnectionPool
from loguru import logger


class DatabaseManager:
    """PostgreSQL 数据库管理器（线程安全单例）"""
    
    # 类级别的锁和实例
    _instance: Optional['DatabaseManager'] = None
    _instance_lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, config_path: str = "config/settings.json") -> 'DatabaseManager':
        """线程安全的单例模式"""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config/settings.json"):
        """初始化（只执行一次）"""
        # 避免重复初始化
        if DatabaseManager._initialized:
            return
            
        with DatabaseManager._instance_lock:
            if DatabaseManager._initialized:
                return
                
            self.config = self._load_config(config_path)
            self.db_config = self.config.get("storage", {}).get("database", {})
            self.connection_pool: Optional[SimpleConnectionPool] = None
            self._init_pool()
            
            DatabaseManager._initialized = True
            logger.info("DatabaseManager 单例初始化完成")
        
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

        -- 股票新闻表
        CREATE TABLE IF NOT EXISTS stock_news (
            id SERIAL PRIMARY KEY,
            news_id VARCHAR(32) UNIQUE NOT NULL,
            stock_code VARCHAR(20),
            title VARCHAR(500) NOT NULL,
            content TEXT,
            url VARCHAR(1000),
            source VARCHAR(100),
            published_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_stock_prices_code ON stock_prices(stock_code);
        CREATE INDEX IF NOT EXISTS idx_stock_prices_time ON stock_prices(collected_at);

        -- 新闻表索引
        CREATE INDEX IF NOT EXISTS idx_stock_news_code ON stock_news(stock_code);
        CREATE INDEX IF NOT EXISTS idx_stock_news_time ON stock_news(published_at);
        CREATE INDEX IF NOT EXISTS idx_stock_news_id ON stock_news(news_id);

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

    def insert_stock_news(self, news_id: str, stock_code: Optional[str],
                          title: str, content: str, url: str,
                          source: str, published_at: Optional[datetime]) -> bool:
        """插入单条股票新闻"""
        sql = """
        INSERT INTO stock_news (news_id, stock_code, title, content, url, source, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (news_id) DO UPDATE SET
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            url = EXCLUDED.url,
            source = EXCLUDED.source,
            published_at = EXCLUDED.published_at,
            updated_at = CURRENT_TIMESTAMP
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, (news_id, stock_code, title, content, url, source, published_at))
                logger.debug(f"新闻插入/更新成功: {news_id}")
                return True
        except Exception as e:
            logger.error(f"插入新闻失败: {e}")
            return False

    def insert_stock_news_batch(self, data: List[Dict[str, Any]]) -> bool:
        """批量插入股票新闻"""
        sql = """
        INSERT INTO stock_news (news_id, stock_code, title, content, url, source, published_at)
        VALUES %s
        ON CONFLICT (news_id) DO UPDATE SET
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            url = EXCLUDED.url,
            source = EXCLUDED.source,
            published_at = EXCLUDED.published_at,
            updated_at = CURRENT_TIMESTAMP
        """
        try:
            with self.get_cursor() as cursor:
                values = [
                    (d["news_id"], d["stock_code"], d["title"],
                     d["content"], d["url"], d["source"], d["published_at"])
                    for d in data
                ]
                execute_values(cursor, sql, values)
                logger.info(f"批量插入/更新 {len(data)} 条新闻")
                return True
        except Exception as e:
            logger.error(f"批量插入新闻失败: {e}")
            return False

    def get_stock_news(self, stock_code: Optional[str] = None,
                       limit: int = 100,
                       days: Optional[int] = None) -> List[Dict]:
        """
        获取股票新闻

        Args:
            stock_code: 股票代码（None 表示获取所有新闻）
            limit: 返回条数限制
            days: 只返回最近几天的数据

        Returns:
            新闻数据列表
        """
        base_sql = """
        SELECT * FROM stock_news
        WHERE 1=1
        """
        params = []

        if stock_code:
            base_sql += " AND stock_code = %s"
            params.append(stock_code)

        if days:
            base_sql += " AND published_at >= NOW() - INTERVAL '%s days'"
            params.append(days)

        base_sql += " ORDER BY published_at DESC LIMIT %s"
        params.append(limit)

        try:
            with self.get_cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(base_sql, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"查询新闻失败: {e}")
            return []

    def get_news_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        获取新闻统计信息

        Args:
            days: 统计最近几天的数据

        Returns:
            统计信息字典
        """
        sql = """
        SELECT
            COUNT(*) as total_count,
            COUNT(DISTINCT stock_code) as stock_count,
            COUNT(DISTINCT source) as source_count
        FROM stock_news
        WHERE created_at >= NOW() - INTERVAL '%s days'
        """
        try:
            with self.get_cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, (days,))
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"获取新闻统计失败: {e}")
            return {}
    
    def close(self):
        """关闭连接池并重置单例状态"""
        with DatabaseManager._instance_lock:
            if self.connection_pool:
                try:
                    self.connection_pool.closeall()
                    logger.info("数据库连接池已关闭")
                except Exception as e:
                    logger.error(f"关闭连接池失败: {e}")
            
            # 重置单例状态，允许重新创建实例
            DatabaseManager._instance = None
            DatabaseManager._initialized = False
            db_manager = None


# 模块级别的单例实例
_db_manager: Optional[DatabaseManager] = None
_db_manager_lock = threading.Lock()


def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器实例（线程安全单例）
    
    Returns:
        DatabaseManager 实例
    """
    global _db_manager
    if _db_manager is None:
        with _db_manager_lock:
            if _db_manager is None:
                _db_manager = DatabaseManager()
    return _db_manager


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
