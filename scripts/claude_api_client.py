#!/usr/bin/env python3
"""
Claude API 客户端
直接使用 Claude API 进行开发任务
"""

import os
import json
import requests
from pathlib import Path


class ClaudeAPIClient:
    """Claude API 客户端"""
    
    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_AUTH_TOKEN')
        self.base_url = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
        self.model = 'claude-sonnet-4-5'
        
        if not self.api_key:
            raise ValueError("未设置 ANTHROPIC_AUTH_TOKEN 环境变量")
    
    def send_message(self, prompt: str, max_tokens: int = 4000) -> str:
        """发送消息到 Claude API"""
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/v1/messages',
                headers=headers,
                json=data,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 提取文本内容
            if 'content' in result and len(result['content']) > 0:
                return result['content'][0]['text']
            else:
                return json.dumps(result, ensure_ascii=False, indent=2)
                
        except requests.exceptions.RequestException as e:
            return f"API 请求失败: {e}"
        except json.JSONDecodeError:
            return f"解析响应失败: {response.text}"
    
    def generate_readme_summary(self, project_path: str) -> str:
        """生成项目 README 摘要"""
        
        # 读取项目结构
        project = Path(project_path)
        
        # 收集文件信息
        files_info = []
        for file in project.rglob('*.py'):
            if '__pycache__' not in str(file):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 提取 docstring
                        docstring = content.split('"""')[1] if '"""' in content else ''
                        files_info.append({
                            'path': str(file.relative_to(project)),
                            'docstring': docstring[:200]  # 前200字符
                        })
                except:
                    pass
        
        # 构建提示
        prompt = f"""
请为 stock-collector 项目生成一个简洁的 README 介绍文档。

项目路径: {project_path}

当前功能模块:
1. 数据采集模块 (src/collectors/)
   - multi_source_collector.py: 多数据源行情采集（东方财富、新浪财经）
   - news_collector.py: 股票新闻采集
   - hot_sector_collector.py: 热点板块及新闻采集

2. 数据分析模块 (src/analytics/)
   - stock_analyzer.py: 股票技术分析（RSI、MACD、布林带、移动平均线）
   - sentiment_analyzer.py: 新闻情感分析
   - chart_generator.py: 数据可视化图表生成

3. 数据导出模块 (src/collectors/data_exporter.py)
   - 支持导出 Excel 格式
   - 行情数据和新闻数据导出

4. 数据库模块 (src/database/)
   - PostgreSQL 支持
   - 数据管理

5. 定时任务
   - 自动采集股票数据
   - 自动采集新闻数据

请生成一个适合放在 README 开头的项目介绍，包含:
- 项目名称和一句话简介
- 主要功能列表
- 技术栈
- 快速开始

输出格式为 Markdown。
"""
        
        return self.send_message(prompt)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Claude API 客户端')
    parser.add_argument('--prompt', type=str, help='直接输入提示词')
    parser.add_argument('--generate-readme', action='store_true', help='生成 README 摘要')
    parser.add_argument('--project', type=str, default='/source_code/stock-collector', 
                       help='项目路径')
    
    args = parser.parse_args()
    
    # 创建客户端
    try:
        client = ClaudeAPIClient()
    except ValueError as e:
        print(f"❌ 错误: {e}")
        print("请确保已设置 ANTHROPIC_AUTH_TOKEN 环境变量")
        return
    
    if args.generate_readme:
        print("🚀 正在生成 README 摘要...")
        result = client.generate_readme_summary(args.project)
        
        # 保存到文件
        output_file = Path(args.project) / 'README_GENERATED.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        
        print(f"\n✅ README 已生成: {output_file}")
        print("\n" + "="*60)
        print(result)
        print("="*60)
    
    elif args.prompt:
        print(f"🚀 发送提示: {args.prompt[:50]}...")
        result = client.send_message(args.prompt)
        print("\n" + "="*60)
        print(result)
        print("="*60)
    
    else:
        # 交互模式
        print("🤖 Claude API 客户端")
        print("输入 'exit' 退出\n")
        
        while True:
            prompt = input("你的问题: ").strip()
            
            if prompt.lower() in ['exit', 'quit', 'q']:
                print("再见!")
                break
            
            if not prompt:
                continue
            
            print("\n思考中...")
            result = client.send_message(prompt)
            print("\n" + result + "\n")


if __name__ == '__main__':
    main()
