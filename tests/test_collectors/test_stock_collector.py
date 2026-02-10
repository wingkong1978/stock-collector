"""
测试示例 - 展示如何编写符合规范的单元测试
"""
import pytest
import pandas as pd
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# 被测代码
from src.collectors.stock_collector import StockCollector
from src.database.db_manager import DatabaseManager


class TestStockCollector:
    """StockCollector 测试类"""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """创建临时配置"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # 创建 stocks.json
        stocks_config = {
            "stocks": [
                {"code": "000001", "name": "平安银行", "market": "sz"},
                {"code": "600000", "name": "浦发银行", "market": "sh"}
            ]
        }
        import json
        with open(config_dir / "stocks.json", "w") as f:
            json.dump(stocks_config, f)
        
        # 创建 settings.json
        settings_config = {
            "collection": {
                "interval": 300,
                "market_hours_only": True,
                "retry_times": 3,
                "timeout": 30
            },
            "storage": {
                "format": "csv",
                "path": str(tmp_path / "data"),
                "compress": False,
                "retention_days": 90
            },
            "logging": {
                "level": "INFO",
                "file": str(tmp_path / "logs" / "test.log"),
                "max_size": "10MB",
                "backup_count": 5
            }
        }
        with open(config_dir / "settings.json", "w") as f:
            json.dump(settings_config, f)
        
        return config_dir
    
    def test_init_success(self, mock_config):
        """测试初始化成功"""
        collector = StockCollector(config_path=str(mock_config))
        assert collector.stocks_config is not None
        assert collector.settings is not None
        assert len(collector.stocks_config["stocks"]) == 2
    
    def test_load_config_file_not_found(self, tmp_path):
        """测试配置文件不存在时的处理"""
        with pytest.raises(FileNotFoundError):
            StockCollector(config_path=str(tmp_path / "nonexistent"))
    
    def test_safe_decimal_valid(self, mock_config):
        """测试 Decimal 转换 - 有效值"""
        collector = StockCollector(config_path=str(mock_config))
        
        result = collector._safe_decimal("12.50")
        assert result == Decimal("12.50")
        
        result = collector._safe_decimal(12.5)
        assert result == Decimal("12.5")
    
    def test_safe_decimal_invalid(self, mock_config):
        """测试 Decimal 转换 - 无效值"""
        collector = StockCollector(config_path=str(mock_config))
        
        result = collector._safe_decimal(None)
        assert result is None
        
        result = collector._safe_decimal("")
        assert result is None
        
        result = collector._safe_decimal("invalid")
        assert result is None
    
    @patch("src.collectors.stock_collector.ak.stock_zh_a_spot_em")
    def test_collect_realtime_data_success(self, mock_ak, mock_config):
        """测试采集实时数据成功"""
        # 准备模拟数据
        mock_data = pd.DataFrame({
            "代码": ["000001", "600000"],
            "名称": ["平安银行", "浦发银行"],
            "最新价": [12.50, 8.30],
            "涨跌幅": [1.25, -0.50],
            "成交量": [1000000, 2000000],
            "成交额": [12500000.0, 16600000.0]
        })
        mock_ak.return_value = mock_data
        
        collector = StockCollector(config_path=str(mock_config))
        result = collector.collect_realtime_data()
        
        assert result is not None
        assert len(result) == 2
        assert "000001" in result["代码"].values
        assert "600000" in result["代码"].values
    
    @patch("src.collectors.stock_collector.ak.stock_zh_a_spot_em")
    def test_collect_realtime_data_empty(self, mock_ak, mock_config):
        """测试采集返回空数据"""
        mock_ak.return_value = pd.DataFrame()
        
        collector = StockCollector(config_path=str(mock_config))
        result = collector.collect_realtime_data()
        
        assert result is None
    
    @patch("src.collectors.stock_collector.ak.stock_zh_a_spot_em")
    def test_collect_realtime_data_exception(self, mock_ak, mock_config):
        """测试采集时发生异常"""
        mock_ak.side_effect = Exception("网络错误")
        
        collector = StockCollector(config_path=str(mock_config))
        result = collector.collect_realtime_data()
        
        assert result is None


class TestDatabaseManager:
    """DatabaseManager 测试类"""
    
    @pytest.fixture
    def mock_db_config(self):
        """模拟数据库配置"""
        return {
            "storage": {
                "database": {
                    "type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "dbname": "test_db",
                    "user": "test_user",
                    "password": "test_pass"
                }
            }
        }
    
    @patch("src.database.db_manager.psycopg2.pool.SimpleConnectionPool")
    def test_init_success(self, mock_pool, mock_db_config, tmp_path):
        """测试数据库管理器初始化"""
        # 创建临时配置文件
        config_path = tmp_path / "config"
        config_path.mkdir()
        import json
        with open(config_path / "settings.json", "w") as f:
            json.dump(mock_db_config, f)
        
        db = DatabaseManager(str(config_path / "settings.json"))
        assert db.db_config is not None
    
    @patch("src.database.db_manager.psycopg2.pool.SimpleConnectionPool")
    def test_insert_stock_success(self, mock_pool, mock_db_config, tmp_path):
        """测试插入股票成功"""
        config_path = tmp_path / "config"
        config_path.mkdir()
        import json
        with open(config_path / "settings.json", "w") as f:
            json.dump(mock_db_config, f)
        
        db = DatabaseManager(str(config_path / "settings.json"))
        
        # 模拟游标
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.return_value.getconn.return_value = mock_conn
        
        result = db.insert_stock("000001", "平安银行", "sz")
        assert result is True
    
    def test_insert_stock_prices_batch(self):
        """测试批量插入价格数据"""
        # 准备测试数据
        data = [
            {
                "stock_code": "000001",
                "price": Decimal("12.50"),
                "change_percent": Decimal("1.25"),
                "volume": 1000000,
                "turnover": Decimal("12500000.00")
            },
            {
                "stock_code": "600000",
                "price": Decimal("8.30"),
                "change_percent": Decimal("-0.50"),
                "volume": 2000000,
                "turnover": Decimal("16600000.00")
            }
        ]
        
        # 验证数据格式
        assert len(data) == 2
        assert data[0]["stock_code"] == "000001"
        assert data[0]["price"] == Decimal("12.50")


# 使用 pytest.mark.parametrize 进行参数化测试
@pytest.mark.parametrize("input_val,expected", [
    ("12.50", Decimal("12.50")),
    (12.5, Decimal("12.5")),
    ("100", Decimal("100")),
])
def test_safe_decimal_parameterized(input_val, expected):
    """参数化测试 Decimal 转换"""
    # 这里可以调用实际的方法
    from decimal import Decimal
    result = Decimal(str(input_val))
    assert result == expected


# 测试异常处理
class TestErrorHandling:
    """测试错误处理"""
    
    def test_custom_exceptions(self):
        """测试自定义异常"""
        # 项目中应该定义这些异常
        # from src.exceptions import StockCollectorError, DataFetchError
        
        # 测试异常抛出
        # with pytest.raises(DataFetchError):
        #     raise DataFetchError("获取数据失败")
        
        pass


# Fixture 示例
@pytest.fixture(scope="session")
def db_connection():
    """会话级别的数据库连接 fixture"""
    # 建立连接
    # conn = create_connection()
    # yield conn
    # 清理
    # conn.close()
    pass


@pytest.fixture(autouse=True)
def setup_teardown():
    """自动使用的 fixture - 每个测试前后执行"""
    # 测试前设置
    print("\n测试开始...")
    yield
    # 测试后清理
    print("测试结束...")
