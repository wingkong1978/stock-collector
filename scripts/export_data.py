#!/usr/bin/env python3
"""
数据导出脚本
用法:
    python export_data.py                    # 导出所有数据
    python export_data.py --stock 600584     # 导出指定股票
    python export_data.py --type stock       # 只导出行情数据
    python export_data.py --type news        # 只导出新闻数据
    python export_data.py --list             # 查看已导出文件
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.data_exporter import main

if __name__ == "__main__":
    main()
