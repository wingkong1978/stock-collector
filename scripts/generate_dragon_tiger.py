#!/usr/bin/env python3
"""
使用 Claude API 生成龙虎榜采集器
"""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from claude_api_client import ClaudeAPIClient


def generate_dragon_tiger_collector():
    """生成龙虎榜采集器"""
    
    client = ClaudeAPIClient()
    
    prompt = '''请为 stock-collector 项目创建一个龙虎榜数据采集器。

项目路径: /source_code/stock-collector

龙虎榜数据来源: 东方财富网 https://data.eastmoney.com/stock/lhb.html

需要采集的字段:
1. 股票代码、股票名称
2. 上榜日期
3. 上榜原因（如：日涨幅偏离值达7%、日振幅值达15%等）
4. 买入金额、卖出金额
5. 净买入额
6. 买入营业部前五（名称、金额）
7. 卖出营业部前五（名称、金额）

功能要求:
1. 采集当日龙虎榜数据
2. 采集历史龙虎榜数据（支持日期范围）
3. 按股票代码查询龙虎榜历史
4. 统计营业部偏好（某个营业部喜欢买什么股票）
5. 保存到 CSV
6. 有完整的错误处理和日志记录（使用 loguru）

代码风格要求:
- 使用 pandas 处理数据
- 使用 requests 获取数据
- 类名：DragonTigerCollector
- 主要方法：collect_daily(), collect_history(), query_by_stock(), analyze_broker()

请生成完整的 Python 代码，确保可以直接运行。'''

    print('🤖 Claude 正在生成龙虎榜采集器...')
    result = client.send_message(prompt, max_tokens=8000)
    
    # 提取代码块
    code_match = re.search(r'```python\n(.*?)\n```', result, re.DOTALL)
    if code_match:
        code = code_match.group(1)
    else:
        # 如果没有代码块标记，使用全部内容
        code = result
    
    return code


if __name__ == '__main__':
    code = generate_dragon_tiger_collector()
    
    # 保存代码
    output_path = Path('/source_code/stock-collector/src/collectors/dragon_tiger_collector.py')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print('\n' + '='*60)
    print(f'✅ 龙虎榜采集器已生成: {output_path}')
    print('='*60)
    print('\n代码预览 (前80行):')
    lines = code.split('\n')
    for line in lines[:80]:
        print(line)
    if len(lines) > 80:
        print('...')
        print(f'[共 {len(lines)} 行，完整代码已保存]')
