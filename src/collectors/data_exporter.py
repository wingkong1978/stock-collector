#!/usr/bin/env python3
"""
Data Export Module
数据导出模块 - 支持 Excel 格式
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger


class DataExporter:
    """数据导出器"""
    
    def __init__(self, config_path: str = "config"):
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
        self.news_path = storage_path / "news"
        self.export_path = storage_path / "exports"
        
        self.export_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"导出目录: {self.export_path}")
    
    def find_latest_files(self, pattern: str, directory: Path) -> List[Path]:
        """查找最新的文件"""
        files = list(directory.glob(pattern))
        if not files:
            return []
        # 按修改时间排序，返回最新的
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files
    
    def export_stock_data(self, stock_code: Optional[str] = None, 
                         output_file: Optional[str] = None) -> Optional[Path]:
        """
        导出股票行情数据到 Excel
        
        Args:
            stock_code: 股票代码，None 则导出所有
            output_file: 输出文件名
            
        Returns:
            导出的文件路径
        """
        try:
            # 查找股票数据文件
            pattern = "stocks_*.csv"
            
            files = self.find_latest_files(pattern, self.raw_path)
            
            if not files:
                logger.warning(f"未找到股票数据文件")
                return None
            
            # 读取所有数据
            all_data = []
            for file in files[:10]:  # 最多读取最近10个文件
                try:
                    df = pd.read_csv(file)
                    df['_source_file'] = file.name
                    all_data.append(df)
                except Exception as e:
                    logger.warning(f"读取文件失败 {file}: {e}")
                    continue
            
            if not all_data:
                logger.error("没有可导出的数据")
                return None
            
            # 合并数据
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # 生成文件名
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stock_suffix = f"_{stock_code}" if stock_code else ""
                output_file = f"stock_data{stock_suffix}_{timestamp}.xlsx"
            
            output_path = self.export_path / output_file
            
            # 导出到 Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                combined_df.to_excel(writer, sheet_name='股票行情', index=False)
                
                # 添加统计信息
                stats = {
                    '指标': ['数据条数', '股票数量', '开始时间', '结束时间', '数据来源'],
                    '数值': [
                        len(combined_df),
                        combined_df['代码'].nunique() if '代码' in combined_df.columns else 0,
                        combined_df['collected_at'].min() if 'collected_at' in combined_df.columns else 'N/A',
                        combined_df['collected_at'].max() if 'collected_at' in combined_df.columns else 'N/A',
                        ', '.join(combined_df['_source'].unique()) if '_source' in combined_df.columns else 'N/A'
                    ]
                }
                stats_df = pd.DataFrame(stats)
                stats_df.to_excel(writer, sheet_name='统计信息', index=False)
            
            logger.info(f"股票数据已导出: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"导出股票数据失败: {e}")
            return None
    
    def export_news_data(self, stock_code: Optional[str] = None,
                        output_file: Optional[str] = None) -> Optional[Path]:
        """
        导出新闻数据到 Excel
        
        Args:
            stock_code: 股票代码，None 则导出所有
            output_file: 输出文件名
            
        Returns:
            导出的文件路径
        """
        try:
            # 查找新闻数据文件
            if stock_code:
                pattern = f"news_{stock_code}_*.csv"
            else:
                pattern = "news_*.csv"
            
            files = self.find_latest_files(pattern, self.news_path)
            
            if not files:
                logger.warning(f"未找到新闻数据文件")
                return None
            
            # 读取所有数据
            all_data = []
            for file in files[:20]:  # 最多读取最近20个文件
                try:
                    df = pd.read_csv(file)
                    df['_source_file'] = file.name
                    all_data.append(df)
                except Exception as e:
                    logger.warning(f"读取文件失败 {file}: {e}")
                    continue
            
            if not all_data:
                logger.error("没有可导出的数据")
                return None
            
            # 合并数据并去重
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # 根据新闻标题去重
            if '新闻标题' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['新闻标题'], keep='first')
            
            # 生成文件名
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stock_suffix = f"_{stock_code}" if stock_code else ""
                output_file = f"news_data{stock_suffix}_{timestamp}.xlsx"
            
            output_path = self.export_path / output_file
            
            # 导出到 Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 主要新闻数据
                combined_df.to_excel(writer, sheet_name='新闻数据', index=False)
                
                # 统计信息
                stats = {
                    '指标': ['新闻条数', '涉及股票', '来源数量', '时间范围'],
                    '数值': [
                        len(combined_df),
                        combined_df['_stock_code'].nunique() if '_stock_code' in combined_df.columns else 0,
                        combined_df['文章来源'].nunique() if '文章来源' in combined_df.columns else 0,
                        f"{combined_df['发布时间'].min()} ~ {combined_df['发布时间'].max()}" 
                        if '发布时间' in combined_df.columns else 'N/A'
                    ]
                }
                stats_df = pd.DataFrame(stats)
                stats_df.to_excel(writer, sheet_name='统计信息', index=False)
                
                # 来源统计
                if '文章来源' in combined_df.columns:
                    source_stats = combined_df['文章来源'].value_counts().reset_index()
                    source_stats.columns = ['来源', '数量']
                    source_stats.to_excel(writer, sheet_name='来源统计', index=False)
            
            logger.info(f"新闻数据已导出: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"导出新闻数据失败: {e}")
            return None
    
    def export_all(self, stock_code: Optional[str] = None) -> Dict[str, Optional[Path]]:
        """
        导出所有数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            导出的文件路径字典
        """
        logger.info("开始导出所有数据...")
        
        results = {
            'stock_data': self.export_stock_data(stock_code),
            'news_data': self.export_news_data(stock_code)
        }
        
        # 汇总信息
        success_count = sum(1 for v in results.values() if v is not None)
        logger.info(f"导出完成: {success_count}/2 成功")
        
        return results
    
    def list_exports(self) -> List[Path]:
        """列出所有导出文件"""
        files = list(self.export_path.glob("*.xlsx"))
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据导出工具")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--type", type=str, choices=['stock', 'news', 'all'], 
                       default='all', help="导出类型")
    parser.add_argument("--output", type=str, help="输出文件名")
    parser.add_argument("--list", action="store_true", help="列出所有导出文件")
    
    args = parser.parse_args()
    
    exporter = DataExporter()
    
    if args.list:
        exports = exporter.list_exports()
        print(f"\n📁 导出文件列表 ({len(exports)} 个):")
        for i, file in enumerate(exports[:10], 1):
            size = file.stat().st_size / 1024
            print(f"  {i}. {file.name} ({size:.1f} KB)")
        return
    
    if args.type == 'stock':
        result = exporter.export_stock_data(args.stock, args.output)
        if result:
            print(f"\n✅ 股票数据已导出: {result}")
        else:
            print("\n❌ 导出失败")
    
    elif args.type == 'news':
        result = exporter.export_news_data(args.stock, args.output)
        if result:
            print(f"\n✅ 新闻数据已导出: {result}")
        else:
            print("\n❌ 导出失败")
    
    else:  # all
        results = exporter.export_all(args.stock)
        print("\n📊 导出结果:")
        for key, path in results.items():
            if path:
                print(f"  ✅ {key}: {path}")
            else:
                print(f"  ❌ {key}: 导出失败")


if __name__ == "__main__":
    main()
