#!/usr/bin/env python3
"""
Polygon.io API 美股数据获取工具
使用 Polygon.io 的 REST API 获取美股市场数据
"""

import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PolygonUSStockFetcher:
    """Polygon.io 美股数据获取器"""
    
    def __init__(self, api_key: str = None):
        """
        初始化 Polygon.io API 客户端
        
        Args:
            api_key: Polygon.io API 密钥
        """
        # 支持 POLYGON_KEY 和 POLYGON_API_KEY 两种环境变量名
        self.api_key = api_key or os.getenv('POLYGON_KEY') or os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("未找到 Polygon.io API 密钥，请设置 POLYGON_KEY 或 POLYGON_API_KEY 环境变量")
        
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}'
        })
        
        logger.info("✓ Polygon.io API 客户端初始化成功")
    
    def get_daily_market_summary(self, date: str, adjusted: bool = True, include_otc: bool = False) -> pd.DataFrame:
        """
        获取指定日期的所有美股日线数据（OHLC）
        
        API 文档: https://polygon.io/docs/rest/stocks/aggregates/daily-market-summary
        
        Args:
            date: 日期，格式: YYYY-MM-DD
            adjusted: 是否调整拆股，默认 True
            include_otc: 是否包含 OTC 证券，默认 False
            
        Returns:
            包含所有美股 OHLC 数据的 DataFrame
        """
        logger.info(f"正在获取 {date} 的美股市场摘要数据...")
        
        # 构建 API 端点
        endpoint = f"/v2/aggs/grouped/locale/us/market/stocks/{date}"
        url = f"{self.base_url}{endpoint}"
        
        # 查询参数
        params = {
            'adjusted': str(adjusted).lower(),
            'include_otc': str(include_otc).lower()
        }
        
        try:
            # 发送请求
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            
            # 检查状态
            if data.get('status') != 'OK':
                logger.error(f"✗ API 返回状态异常: {data.get('status')}")
                return pd.DataFrame()
            
            # 获取结果
            results = data.get('results', [])
            if not results:
                logger.warning(f"✗ {date} 没有数据（可能是非交易日）")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            df = pd.DataFrame(results)
            
            # 重命名列（Polygon.io 使用简写）
            column_mapping = {
                'T': 'symbol',      # 股票代码
                'o': 'open',        # 开盘价
                'h': 'high',        # 最高价
                'l': 'low',         # 最低价
                'c': 'close',       # 收盘价
                'v': 'volume',      # 成交量
                'vw': 'vwap',       # 成交量加权平均价
                'n': 'transactions',  # 交易次数
                't': 'timestamp',   # 时间戳（毫秒）
                'otc': 'is_otc'     # 是否 OTC
            }
            df = df.rename(columns=column_mapping)
            
            # 转换时间戳
            if 'timestamp' in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 添加数据日期
            df['date'] = date
            df['data_fetched_at'] = datetime.now()
            
            logger.info(f"✓ 成功获取 {len(df)} 只股票的数据")
            logger.info(f"  查询数量: {data.get('queryCount', 'N/A')}")
            logger.info(f"  结果数量: {data.get('resultsCount', 'N/A')}")
            logger.info(f"  是否调整: {data.get('adjusted', 'N/A')}")
            
            return df
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"✗ HTTP 错误: {e}")
            if response.status_code == 401:
                logger.error("  认证失败，请检查 API 密钥")
            elif response.status_code == 403:
                logger.error("  权限不足，请检查您的 Polygon.io 订阅计划")
            elif response.status_code == 429:
                logger.error("  请求频率超限，请稍后重试")
            return pd.DataFrame()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ 请求失败: {e}")
            return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"✗ 发生错误: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_multi_day_summary(self, start_date: str, end_date: str, 
                             adjusted: bool = True, include_otc: bool = False) -> pd.DataFrame:
        """
        获取多日市场摘要数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjusted: 是否调整拆股
            include_otc: 是否包含 OTC 证券
            
        Returns:
            包含多日数据的 DataFrame
        """
        logger.info(f"正在获取 {start_date} 至 {end_date} 的市场数据...")
        
        # 生成日期列表
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        date_list = []
        
        current = start
        while current <= end:
            # 跳过周末
            if current.weekday() < 5:  # 0-4 是周一到周五
                date_list.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        
        logger.info(f"需要获取 {len(date_list)} 个交易日的数据")
        
        # 获取每日数据
        all_data = []
        for date in date_list:
            df = self.get_daily_market_summary(date, adjusted, include_otc)
            if not df.empty:
                all_data.append(df)
            
            # 避免请求过快（免费账户有限制）
            time.sleep(0.5)
        
        # 合并数据
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"✓ 成功获取共 {len(combined_df)} 条数据")
            return combined_df
        else:
            logger.warning("✗ 未获取到任何数据")
            return pd.DataFrame()
    
    def get_latest_market_summary(self, days_back: int = 1, 
                                  adjusted: bool = True, 
                                  include_otc: bool = False) -> pd.DataFrame:
        """
        获取最近的市场摘要数据
        
        Args:
            days_back: 向前追溯天数
            adjusted: 是否调整拆股
            include_otc: 是否包含 OTC 证券
            
        Returns:
            最近的市场数据 DataFrame
        """
        # 计算日期（跳过周末）
        today = datetime.now()
        target_date = today
        
        # 如果今天是周末，往回找最近的交易日
        while target_date.weekday() >= 5:
            target_date -= timedelta(days=1)
        
        # 再往前推 days_back 天
        for _ in range(days_back):
            target_date -= timedelta(days=1)
            while target_date.weekday() >= 5:
                target_date -= timedelta(days=1)
        
        date_str = target_date.strftime('%Y-%m-%d')
        return self.get_daily_market_summary(date_str, adjusted, include_otc)
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None, data_dir: str = 'data'):
        """
        保存数据到 CSV 文件
        
        Args:
            df: 要保存的 DataFrame
            filename: 文件名（可选）
            data_dir: 数据目录
        """
        if df.empty:
            logger.warning("✗ 数据为空，无法保存")
            return
        
        # 创建数据目录
        os.makedirs(data_dir, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'polygon_us_stocks_{timestamp}.csv'
        
        filepath = os.path.join(data_dir, filename)
        
        try:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
            logger.info(f"✓ 数据已保存到: {filepath}")
            logger.info(f"  文件大小: {file_size:.2f} MB")
            logger.info(f"  记录数量: {len(df)}")
        except Exception as e:
            logger.error(f"✗ 保存文件失败: {e}")
    
    def save_to_excel(self, df: pd.DataFrame, filename: str = None, data_dir: str = 'data'):
        """
        保存数据到 Excel 文件
        
        Args:
            df: 要保存的 DataFrame
            filename: 文件名（可选）
            data_dir: 数据目录
        """
        if df.empty:
            logger.warning("✗ 数据为空，无法保存")
            return
        
        # 创建数据目录
        os.makedirs(data_dir, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'polygon_us_stocks_{timestamp}.xlsx'
        
        filepath = os.path.join(data_dir, filename)
        
        try:
            df.to_excel(filepath, index=False, engine='openpyxl')
            file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
            logger.info(f"✓ 数据已保存到: {filepath}")
            logger.info(f"  文件大小: {file_size:.2f} MB")
            logger.info(f"  记录数量: {len(df)}")
        except Exception as e:
            logger.error(f"✗ 保存文件失败: {e}")
    
    def print_summary(self, df: pd.DataFrame, top_n: int = 10):
        """
        打印数据摘要
        
        Args:
            df: 数据 DataFrame
            top_n: 显示前 N 条记录
        """
        if df.empty:
            logger.warning("数据为空")
            return
        
        print("\n" + "="*80)
        print("数据摘要")
        print("="*80)
        
        print(f"\n总记录数: {len(df)}")
        
        if 'date' in df.columns:
            dates = df['date'].unique()
            print(f"日期范围: {', '.join(dates)}")
        
        if 'volume' in df.columns:
            total_volume = df['volume'].sum()
            print(f"总成交量: {total_volume:,.0f}")
        
        # 显示涨幅最大的股票
        if 'close' in df.columns and 'open' in df.columns:
            df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
            
            print("\n涨幅前 5 名:")
            top_gainers = df.nlargest(5, 'change_pct')[['symbol', 'open', 'close', 'volume', 'change_pct']]
            print(top_gainers.to_string(index=False))
            
            print("\n跌幅前 5 名:")
            top_losers = df.nsmallest(5, 'change_pct')[['symbol', 'open', 'close', 'volume', 'change_pct']]
            print(top_losers.to_string(index=False))
        
        # 显示成交量最大的股票
        if 'volume' in df.columns:
            print("\n成交量前 10 名:")
            top_volume = df.nlargest(10, 'volume')[['symbol', 'close', 'volume', 'vwap'] if 'vwap' in df.columns else ['symbol', 'close', 'volume']]
            print(top_volume.to_string(index=False))
        
        # 显示样本数据
        print(f"\n样本数据（前 {top_n} 条）:")
        display_cols = ['symbol', 'open', 'high', 'low', 'close', 'volume']
        if 'vwap' in df.columns:
            display_cols.append('vwap')
        
        available_cols = [col for col in display_cols if col in df.columns]
        print(df[available_cols].head(top_n).to_string(index=False))
        
        print("="*80)
    
    def get_ticker_details(self, symbol: str) -> Dict:
        """
        获取股票详细信息（包括市值）
        
        API 文档: https://polygon.io/docs/stocks/get_v3_reference_tickers__ticker
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含股票详细信息的字典，包括 market_cap（市值）
        """
        endpoint = f"/v3/reference/tickers/{symbol}"
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and 'results' in data:
                result = data['results']
                return {
                    'symbol': result.get('ticker', symbol),
                    'name': result.get('name', ''),
                    'market_cap': result.get('market_cap', 0),
                    'weighted_shares_outstanding': result.get('weighted_shares_outstanding', 0),
                    'description': result.get('description', ''),
                    'list_date': result.get('list_date', ''),
                    'primary_exchange': result.get('primary_exchange', ''),
                    'type': result.get('type', ''),
                    'currency_name': result.get('currency_name', 'USD'),
                }
            else:
                logger.warning(f"未获取到 {symbol} 的详细信息")
                return {}
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"获取 {symbol} 详细信息失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"获取 {symbol} 详细信息时发生错误: {e}")
            return {}
    
    def get_multiple_ticker_details(self, symbols: List[str], delay: float = 0.2) -> pd.DataFrame:
        """
        批量获取多个股票的详细信息
        
        Args:
            symbols: 股票代码列表
            delay: 请求间隔（秒），默认0.2秒（避免超过免费套餐5次/分钟的限制）
            
        Returns:
            包含详细信息的 DataFrame
        """
        import time
        
        logger.info(f"正在获取 {len(symbols)} 只股票的详细信息...")
        
        details_list = []
        for i, symbol in enumerate(symbols, 1):
            details = self.get_ticker_details(symbol)
            if details:
                details_list.append(details)
            
            if i % 10 == 0:
                logger.info(f"  进度: {i}/{len(symbols)}")
            
            # 添加延迟避免超过API限制
            if i < len(symbols):
                time.sleep(delay)
        
        if details_list:
            df = pd.DataFrame(details_list)
            logger.info(f"✓ 成功获取 {len(df)} 只股票的详细信息")
            return df
        else:
            logger.warning("未获取到任何股票详细信息")
            return pd.DataFrame()


def main():
    """主函数 - 测试用"""
    print("="*80)
    print("Polygon.io API - 美股每日市场摘要获取工具")
    print("="*80)
    
    try:
        # 创建数据获取器
        fetcher = PolygonUSStockFetcher()
        
        # 计算最近的交易日
        today = datetime.now()
        target_date = today - timedelta(days=1)
        
        # 如果是周末，往回找最近的交易日
        while target_date.weekday() >= 5:
            target_date -= timedelta(days=1)
        
        date_str = target_date.strftime('%Y-%m-%d')
        
        print(f"\n正在获取 {date_str} 的美股市场数据...")
        
        # 获取每日市场摘要
        df = fetcher.get_daily_market_summary(date_str)
        
        if not df.empty:
            # 打印摘要
            fetcher.print_summary(df)
            
            # 保存到文件
            fetcher.save_to_csv(df)
            fetcher.save_to_excel(df)
            
            print("\n" + "="*80)
            print("✓ 所有任务完成！")
            print("="*80)
        else:
            print("\n✗ 未获取到数据")
            print("提示: 请检查日期是否为交易日，或检查 API 密钥权限")
    
    except ValueError as e:
        print(f"\n✗ 配置错误: {e}")
        print("\n请设置环境变量:")
        print("  export POLYGON_KEY='your-api-key-here'")
        print("\n或在项目根目录创建 .env 文件:")
        print("  POLYGON_KEY=your-api-key-here")
    
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


