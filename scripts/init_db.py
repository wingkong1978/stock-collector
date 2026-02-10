#!/usr/bin/env python3
"""
数据库初始化脚本
"""
import sys
sys.path.insert(0, "/source_code/stock-collector/src")

from database.db_manager import DatabaseManager

def main():
    print("正在初始化 PostgreSQL 数据库...")
    
    try:
        # 创建数据库管理器
        db = DatabaseManager("config/settings.json")
        
        # 初始化表结构
        db.init_tables()
        
        print("✅ 数据库初始化成功！")
        print("\n已创建以下表：")
        print("  - stocks: 股票基本信息表")
        print("  - stock_prices: 股票价格数据表")
        print("  - collection_logs: 采集日志表")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("\n请检查：")
        print("  1. PostgreSQL 服务是否运行")
        print("  2. config/settings.json 中的数据库配置是否正确")
        print("  3. 数据库用户是否有创建表的权限")
        sys.exit(1)

if __name__ == "__main__":
    main()
