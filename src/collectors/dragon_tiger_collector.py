import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
import sys
import os

# 配置 loguru
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")
logger.add("./logs/stock_collector_{time:YYYY-MM-DD}.log", rotation="10 MB", retention="7 days")

class DragonTigerCollector:
    """
    龙虎榜数据采集器
    数据来源：东方财富网
    """
    
    def __init__(self):
        # 东方财富 API 基础 URL
        self.base_url = "http://datacenter-web.eastmoney.com/api/data/v1/get"
        
        # 请求头，模拟浏览器访问
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "http://data.eastmoney.com/stock/lhb.html"
        }
        
        # 创建必要的文件夹
        if not os.path.exists("./data"):
            os.makedirs("./data")
        if not os.path.exists("./logs"):
            os.makedirs("./logs")

    def _get_request(self, params: Dict) -> Optional[Dict]:
        """内部方法：发送 HTTP GET 请求并处理错误"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
                response.raise_for_status()
                result = response.json()
                
                if "result" not in result:
                    logger.warning(f"API返回无数据: {params}")
                    return None
                    
                return result
            except requests.exceptions.RequestException as e:
                logger.error(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return None
            except Exception as e:
                logger.error(f"解析JSON失败: {e}")
                return None

    def collect_daily(self, date_str: Optional[str] = None) -> pd.DataFrame:
        """
        采集指定日期的龙虎榜数据
        :param date_str: 日期字符串，格式 YYYYMMDD，默认为当日
        :return: 包含当日龙虎榜数据的 DataFrame
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        
        logger.info(f"开始采集 {date_str} 的龙虎榜数据...")

        # 构造获取每日概览的参数
        # 接口类型: 1. 个股 2. 营业部等。这里使用个股数据接口。
        # filter: 筛选条件
        # sortColumns: 排序字段
        # sortTypes: 排序方式
        # pageSize: 每页数量
        # pageNumber: 页码
        # reportName: RPT_DAILYBILLBOARD_DETAILS
        params = {
            "sortColumns": "SECURITY_CODE,TRADE_DATE",
            "sortTypes": "1,1",
            "pageSize": "500", # 单日数据一般不会超过500条
            "pageNumber": "1",
            "reportName": "RPT_DAILYBILLBOARD_DETAILS",
            "columns": "ALL",
            "filter": f'(TRADE_DATE="{date_str}")'
        }

        data = self._get_request(params)
        
        if not data or not data.get("result", {}).get("data"):
            logger.warning(f"日期 {date_str} 未找到数据。")
            return pd.DataFrame()

        raw_list = data["result"]["data"]
        
        # 数据清洗与字段重命名
        df = pd.DataFrame(raw_list)
        
        # 字段映射字典 (东方财富原始字段 -> 友好字段)
        column_mapping = {
            "SECURITY_CODE": "stock_code",          # 股票代码
            "SECURITY_NAME_ABBR": "stock_name",     # 股票名称
            "TRADE_DATE": "date",                   # 上榜日期
            "BILLBOARD_REASON_NAME": "reason",      # 上榜原因
            "EXPLANATION": "explanation",           # 备注
            "CLOSE_PRICE": "close_price",           # 收盘价
            "PCT_CHANGE": "pct_change",             # 涨跌幅
            "TURNOVERRATE": "turnover_rate",        # 换手率
            "NET_BUY_AMT": "net_buy",               # 净买入额
            "BUY_AMT": "total_buy",                 # 总买入额
            "SELL_AMT": "total_sell",               # 总卖出额
            "BILLBOARD_TYPE": "type",               # 类型 (如龙虎榜、大宗等)
            "MARKET": "market"                      # 市场
        }
        
        # 选择并重命名列
        df = df.rename(columns=column_mapping)
        
        # 数据类型转换 (金额单位通常是元，转为万元或保留)
        money_cols = ["net_buy", "total_buy", "total_sell"]
        for col in money_cols:
            if col in df.columns:
                df[col] = df[col].astype(float) / 10000  # 转换为万元

        # 格式化日期
        df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d")
        
        logger.success(f"采集完成，共获取 {len(df)} 条记录。")
        return df

    def get_detail_brokers(self, stock_code: str, date_str: str) -> Dict:
        """
        获取单个股票在特定日期的买卖前五营业部明细
        由于接口限制，这里使用解析详情页的方式或特定API
        为了效率，我们调用另一个API接口: RPT_ORG_BILLBOARD_DET
        """
        params = {
            "sortColumns": "SECURITY_CODE,TRADE_DATE",
            "sortTypes": "1,1",
            "pageSize": "20",
            "pageNumber": "1",
            "reportName": "RPT_ORG_BILLBOARD_DET",
            "columns": "ALL",
            "filter": f'(TRADE_DATE="{date_str}")(SECURITY_CODE="{stock_code}")'
        }
        
        data = self._get_request(params)
        
        buy_details = []
        sell_details = []
        
        if data and data.get("result", {}).get("data"):
            items = data["result"]["data"]
            for item in items:
                exch_name = item.get("OPERATEORG_NAME", "未知营业部")
                # 金额单位转换：元 -> 万元
                amount = float(item.get("BUY_AMT", 0) if item.get("BUY_AMT") else 0) / 10000
                if amount > 0:
                    buy_details.append({"broker": exch_name, "amount": amount})
                
                amount_sell = float(item.get("SELL_AMT", 0) if item.get("SELL_AMT") else 0) / 10000
                if amount_sell > 0:
                    sell_details.append({"broker": exch_name, "amount": amount_sell})

        return {
            "buy_top5": sorted(buy_details, key=lambda x: x['amount'], reverse=True)[:5],
            "sell_top5": sorted(sell_details, key=lambda x: x['amount'], reverse=True)[:5]
        }

    def collect_history(self, start_date: str, end_date: str, enrich_details: bool = False) -> pd.DataFrame:
        """
        采集历史龙虎榜数据
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :param enrich_details: 是否填充营业部明细 (较慢)
        :return: DataFrame
        """
        logger.info(f"开始采集历史数据: {start_date} 至 {end_date}")
        
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        
        all_data = []
        current_dt = start_dt
        
        # 跳过周末的逻辑由API自己处理，或者我们可以手动加
        # 这里简单的遍历每一天
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y%m%d")
            
            # 只尝试周一到周五
            if current_dt.weekday() < 5:
                df_day = self.collect_daily(date_str)
                if not df_day.empty:
                    if enrich_details:
                        logger.info(f"正在获取 {date_str} 的营业部明细...")
                        # 这里使用 apply 稍慢，但对于采集器来说可接受
                        # 如果追求极致速度，需要将详情查询改为异步
                        details_list = []
                        for _, row in df_day.iterrows():
                            detail = self.get_detail_brokers(row['stock_code'], date_str)
                            details_list.append(detail)
                            time.sleep(0.1) # 避免请求过快
                        
                        # 将字典列展开
                        df_day['buy_brokers'] = [d['buy_top5'] for d in details_list]
                        df_day['sell_brokers'] = [d['sell_top5'] for d in details_list]
                    
                    all_data.append(df_day)
            
            current_dt += timedelta(days=1)
            
        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"历史数据采集完成，总计 {len(result_df)} 条记录。")
            return result_df
        else:
            return pd.DataFrame()

    def query_by_stock(self, stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        按股票代码查询龙虎榜历史
        """
        if start_date is None:
            # 默认查询最近一年
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
            
        logger.info(f"查询股票 {stock_code} 从 {start_date} 到 {end_date} 的记录")
        
        params = {
            "sortColumns": "TRADE_DATE,SECURITY_CODE",
            "sortTypes": "-1,1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_DAILYBILLBOARD_DETAILS",
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{stock_code}")(TRADE_DATE>="{start_date}")(TRADE_DATE<="{end_date}")'
        }
        
        data = self._get_request(params)
        if not data or not data.get("result", {}).get("data"):
            logger.warning(f"未找到股票 {stock_code} 的记录。")
            return pd.DataFrame()
            
        df = pd.DataFrame(data["result"]["data"])
        
        # 字段重命名 (复用之前的映射逻辑)
        column_mapping = {
            "SECURITY_CODE": "stock_code",
            "SECURITY_NAME_ABBR": "stock_name",
            "TRADE_DATE": "date",
            "BILLBOARD_REASON_NAME": "reason",
            "NET_BUY_AMT": "net_buy",
            "BUY_AMT": "total_buy",
            "SELL_AMT": "total_sell"
        }
        df = df.rename(columns=column_mapping)
        
        # 处理金额
        for col in ["net_buy", "total_buy", "total_sell"]:
            if col in df.columns:
                df[col] = df[col].astype(float) / 10000
        
        df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d")
        
        return df

    def analyze_broker(self, df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        统计营业部偏好 (需要 DataFrame 包含 enriched 的营业部明细)
        或者基于 collect_history 的数据 (如果未包含明细，此方法需要修改为调用明细API)
        
        注意：如果传入的 df 是 collect_history(enrich_details=True) 的结果，
        则可以直接解析 'buy_brokers' 列。否则需要重新请求。
        """
        
        logger.info("开始分析营业部偏好...")
        
        broker_stats = []
        
        # 检查是否有明细数据
        if 'buy_brokers' not in df.columns:
            logger.warning("输入数据缺少 'buy_brokers' 列，尝试重新获取明细... (这会很慢)")
            # 这里为了简化，如果用户传入的是简单数据，建议在 collect_history 时开启 enrich_details
            # 或者我们可以仅基于已有的数据进行分析，但已有的数据没有营业部名称。
            # 因此，此处我们假设用户使用了 collect_history(..., enrich_details=True)
            pass
            
        for _, row in df.iterrows():
            date = row['date']
            code = row['stock_code']
            name = row['stock_name']
            
            # 获取买入营业部列表
            buyers = row.get('buy_brokers', [])
            if isinstance(buyers, list):
                for b in buyers:
                    broker_stats.append({
                        "broker": b['broker'],
                        "stock_code": code,
                        "stock_name": name,
                        "amount": b['amount'],
                        "date": date
                    })
        
        if not broker_stats:
            logger.warning("没有找到营业部明细数据进行分析。")
            return pd.DataFrame()

        stats_df = pd.DataFrame(broker_stats)
        
        # 统计每个营业部买入总金额
        broker_rank = stats_df.groupby(['broker', 'stock_code', 'stock_name'])['amount'].sum().reset_index()
        
        # 找出每个营业部买入最多的股票
        # 按营业部分组，取买入金额最大的几只股票
        result = []
        for broker, group in broker_rank.groupby('broker'):
            total_bought = group['amount'].sum()
            # 取该营业部买入金额最大的前3只股票
            top_stocks = group.sort_values('amount', ascending=False).head(3)
            
            stock_list = ", ".join([f"{row['stock_name']}({row['stock_code']})" for _, row in top_stocks.iterrows()])
            
            result.append({
                "broker": broker,
                "total_buy_amount": total_bought,
                "hit_count": len(group),
                "favorite_stocks": stock_list
            })
            
        result_df = pd.DataFrame(result).sort_values('total_buy_amount', ascending=False).head(top_n)
        
        logger.info("营业部偏好分析完成。")
        return result_df

    def to_csv(self, df: pd.DataFrame, filename: str = None):
        """保存数据到 CSV"""
        if df.empty:
            logger.warning("DataFrame 为空，不保存文件。")
            return

        if filename is None:
            filename = f"./data/stock_lhb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        df.to_csv(filename, index=False, encoding="utf_8_sig")
        logger.success(f"数据已保存至: {filename}")

if __name__ == "__main__":
    # 实例化采集器
    collector = DragonTigerCollector()

    print("=" * 50)
    print("1. 采集当日数据")
    print("=" * 50)
    daily_df = collector.collect_daily()
    if not daily_df.empty:
        print(daily_df.head())
        collector.to_csv(daily_df, "./data/daily_lhb.csv")

    print("\n" + "=" * 50)
    print("2. 采集历史数据 (示例：最近3天)")
    print("=" * 50)
    # 计算日期范围
    end_d = datetime.now()
    start_d = end_d - timedelta(days=5)
    
    # 开启 enrich_details=True 以便分析营业部 (会慢一些)
    history_df = collector.collect_history(
        start_date=start_d.strftime("%Y%m%d"), 
        end_date=end_d.strftime("%Y%m%d"),
        enrich_details=False # 为了演示速度，设为False；分析时设为True
    )
    
    if not history_df.empty:
        print(f"历史数据条数: {len(history_df)}")
        print(history_df[['date', 'stock_code', 'stock_name', 'reason', 'net_buy']].head())
        collector.to_csv(history_df, "./data/history_lhb.csv")

    print("\n" + "=" * 50)
    print("3. 按股票查询 (示例：东方财富 600519)")
    print("=" * 50)
    # 查询最近一个月的记录，假设有数据
    query_start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    query_end = datetime.now().strftime("%Y%m%d")
    
    stock_df = collector.query_by_stock("600519", query_start, query_end)
    if not stock_df.empty:
        print(stock_df[['date', 'reason', 'net_buy']])
    else:
        print("该时间段内未查询到上榜记录。")

    print("\n" + "=" * 50)
    print("4. 统计营业部偏好 (需要 enrich_details=True 的数据)")
    print("=" * 50)
    # 重新采集一小段时间带明细的数据用于演示分析
    demo_start = (datetime.now() - timedelta(days=2)).strftime("%Y%m%d")
    demo_df = collector.collect_history(demo_start, query_end, enrich_details=True)
    
    if not demo_df.empty:
        analysis_df = collector.analyze_broker(demo_df)
        print(analysis_df)