#!/usr/bin/env python3
"""
OKX数据获取器 - 兼容BN数据格式
获取OKX交易所的K线数据，输出格式与BinanceDataFetcher保持一致
"""

import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import pytz

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OKXDataFetcher:
    """OKX数据获取器 - 兼容BN数据格式，支持现货和合约"""
    
    def __init__(self, market_type: str = 'spot'):
        """
        初始化OKX数据获取器
        
        Args:
            market_type: 市场类型，'spot' 或 'futures'
        """
        self.market_type = market_type
        self.base_url = "https://www.okx.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 周期映射 - UTC+0开盘价的K线（默认）
        self.interval_map_utc0 = {
            '1d': '1Dutc',    # UTC+0开盘价K线
            '2d': '2Dutc',    # UTC+0开盘价K线
            '3d': '3Dutc',    # UTC+0开盘价K线
            '5d': '5Dutc',    # UTC+0开盘价K线
            '1w': '1Wutc'     # UTC+0开盘价K线
        }
        # 周期映射 - UTC+8开盘价的K线
        self.interval_map_utc8 = {
            '1d': '1D',       # UTC+8开盘价K线
            '2d': '2D',       # UTC+8开盘价K线
            '3d': '3D',       # UTC+8开盘价K线
            '5d': '5D',       # UTC+8开盘价K线（如果API支持）
            '1w': '1W'        # UTC+8开盘价K线
        }
    
    def get_top_n_tokens(self, quote_asset: str = 'USDT', top_n: int = 100) -> List[str]:
        """
        获取交易量前N的代币对
        
        Args:
            quote_asset: 计价货币，默认USDT
            top_n: 返回数量
            
        Returns:
            代币对列表
        """
        try:
            url = f"{self.base_url}/api/v5/market/tickers"
            
            # 根据市场类型设置instType
            if self.market_type == 'futures':
                params = {
                    'instType': 'SWAP'  # OKX的永续合约类型
                }
            else:
                params = {
                    'instType': 'SPOT'
                }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] != '0':
                raise Exception(f"API返回错误: {data['msg']}")
            
            tickers = []
            for item in data['data']:
                inst_id = item['instId']
                # 根据市场类型判断是否匹配
                if self.market_type == 'futures':
                    # 合约格式: BTC-USDT-SWAP
                    if inst_id.endswith(f'-{quote_asset}-SWAP'):
                        # 对于合约，volCcy24h是基础货币数量，需要乘以价格得到USDT计价交易量
                        vol_ccy = float(item['volCcy24h'])
                        high_24h = float(item.get('high24h', 0))
                        low_24h = float(item.get('low24h', 0))
                        # 使用24h最高价和最低价的平均值作为平均价格
                        avg_price = (high_24h + low_24h) / 2 if (high_24h > 0 and low_24h > 0) else 0
                        quote_volume = vol_ccy * avg_price if avg_price > 0 else 0
                        
                        tickers.append({
                            'symbol': inst_id,
                            'quote_volume': quote_volume
                        })
                else:
                    # 现货格式: BTC-USDT
                    # 对于现货，volCcy24h已经是计价货币（USDT）的交易量
                    if inst_id.endswith(f'-{quote_asset}'):
                        tickers.append({
                            'symbol': inst_id,
                            'quote_volume': float(item['volCcy24h'])
                        })
            
            # 按交易量排序
            tickers.sort(key=lambda x: x['quote_volume'], reverse=True)
            top_symbols = [item['symbol'] for item in tickers[:top_n]]
            
            market_name = "合约" if self.market_type == 'futures' else "现货"
            logger.info(f"获取到前{len(top_symbols)}个{quote_asset}{market_name}交易对")
            return top_symbols
            
        except Exception as e:
            logger.error(f"获取交易对失败: {e}")
            return []
    
    def get_klines(self, symbol: str, days: int = 16, interval: str = '1d', expected_count: int = None, is_prescreening: bool = False, use_utc0: bool = True) -> pd.DataFrame:
        """
        获取K线数据 - 输出格式与BN保持一致
        
        Args:
            symbol: 交易对符号
            days: 获取天数
            interval: K线周期 (1d, 3d, 1w)
            expected_count: 期望的K线数量
            is_prescreening: 是否为预筛选阶段
            use_utc0: 是否使用UTC+0开盘价K线，True为UTC+0，False为UTC+8，默认True
            
        Returns:
            K线数据DataFrame，格式与BN一致
        """
        try:
            # 根据参数选择周期映射
            if use_utc0:
                interval_map = self.interval_map_utc0
                utc_type = "UTC+0"
            else:
                interval_map = self.interval_map_utc8
                utc_type = "UTC+8"
            
            # 映射周期
            okx_interval = interval_map.get(interval, '1D' if not use_utc0 else '1Dutc')
            
            # 计算时间范围 - 使用UTC时区
            utc_tz = pytz.UTC
            end_time = datetime.now(utc_tz)
            start_time = end_time - timedelta(days=days)
            
            # 转换为毫秒时间戳（OKX API要求）
            after_timestamp = int(start_time.timestamp() * 1000)
            before_timestamp = int(end_time.timestamp() * 1000)
            
            # 调试信息：显示时间范围
            logger.info(f"获取{symbol} {interval} K线数据 ({utc_type}开盘价) - 时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            url = f"{self.base_url}/api/v5/market/candles"
            # 计算期望的K线数量
            if expected_count is not None:
                # 如果指定了期望数量，直接使用
                expected_limit = expected_count
            else:
                # 根据周期类型和天数计算
                if interval == '1d':
                    expected_limit = days
                elif interval == '2d':
                    expected_limit = days // 2
                elif interval == '3d':
                    expected_limit = days // 3
                elif interval == '5d':
                    expected_limit = days // 5
                elif interval == '1w':
                    expected_limit = days // 7
                else:
                    expected_limit = days
            
            # 只在非预筛选阶段输出调试信息
            if not is_prescreening:
                logger.info(f"expected_limit: {expected_limit}")
                logger.info(f"days: {days}")
            params = {
                'instId': symbol,
                'bar': okx_interval,
                'limit': min(300, expected_limit)  # 使用期望的K线数量
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] != '0':
                logger.warning(f"获取{symbol} K线数据失败: {data['msg']}")
                return pd.DataFrame()
            
            if not data['data']:
                return pd.DataFrame()
            
            klines = []
            for item in reversed(data['data']):  # OKX返回的是倒序，需要反转
                # OKX返回格式: [timestamp, open, high, low, close, volume, volCcy, volCcyQuote, confirm]
                original_timestamp = pd.to_datetime(int(item[0]), unit='ms', utc=True)
                
                # 调整K线时间：从16:00调整为下一天的00:00（适用于所有周期）
                # OKX的16:00 UTC K线代表UTC+8的00:00开始的那一天，所以应该调整为下一天的00:00 UTC
                if original_timestamp.hour == 16:
                    # 16:00 UTC的K线调整为下一天的00:00 UTC
                    adjusted_timestamp = original_timestamp.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                else:
                    # 其他时间的K线保持原样
                    adjusted_timestamp = original_timestamp
                
                timestamp = adjusted_timestamp
                
                klines.append({
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'close_time': timestamp + timedelta(days=1) - timedelta(seconds=1),  # 模拟BN的close_time
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5]),
                    'quote_asset_volume': float(item[6]),  # volCcy
                    'number_of_trades': 0,  # OKX不提供交易次数，设为0
                    'taker_buy_base_asset_volume': 0,  # OKX不提供，设为0
                    'taker_buy_quote_asset_volume': 0   # OKX不提供，设为0
                })
            
            df = pd.DataFrame(klines)
            
            # 调试信息：显示获取到的数据时间范围
            if not df.empty:
                min_time = df['timestamp'].min()
                max_time = df['timestamp'].max()
                logger.info(f"获取到{symbol} {interval} K线数据 {len(df)} 条 - 时间范围: {min_time.strftime('%Y-%m-%d %H:%M:%S UTC')} 到 {max_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # 重新排列列的顺序，与BN保持一致
            if not df.empty:
                df = df[['symbol', 'timestamp', 'close_time', 'open', 'high', 'low', 'close', 
                        'volume', 'quote_asset_volume', 'number_of_trades']]
            
            return df
            
        except Exception as e:
            logger.error(f"获取{symbol} K线数据失败: {e}")
            return pd.DataFrame()
    
    def aggregate_to_n_days(self, df: pd.DataFrame, n_days: int) -> pd.DataFrame:
        """
        将1日K线聚合成N日K线 - 与BN逻辑保持一致
        
        Args:
            df: 1日K线DataFrame
            n_days: 聚合天数
            
        Returns:
            聚合后的DataFrame
        """
        if df.empty:
            return df
        
        # 按n_days分组聚合
        df_sorted = df.sort_values('timestamp')
        df_sorted['group'] = df_sorted.index // n_days
        
        aggregated = []
        for group_id, group_data in df_sorted.groupby('group'):
            if len(group_data) < n_days:
                continue
                
            agg_data = {
                'symbol': group_data.iloc[0]['symbol'],
                'timestamp': group_data.iloc[-1]['timestamp'],  # 使用最后一根K线的时间
                'close_time': group_data.iloc[-1]['close_time'],  # 使用最后一根K线的收盘时间
                'open': group_data.iloc[0]['open'],
                'high': group_data['high'].max(),
                'low': group_data['low'].min(),
                'close': group_data.iloc[-1]['close'],
                'volume': group_data['volume'].sum(),
                'quote_asset_volume': group_data['quote_asset_volume'].sum(),
                'number_of_trades': group_data['number_of_trades'].sum()
            }
            aggregated.append(agg_data)
        
        return pd.DataFrame(aggregated)
    
    def fetch_top_n_daily_data(self, days: int = 16, delay: float = 0.1, 
                              top_n: int = 100, interval: str = '1d', 
                              aggregate_days: int = None) -> pd.DataFrame:
        """
        获取前N个交易对的K线数据 - 与BN接口保持一致
        
        Args:
            days: 获取天数
            delay: 请求间隔
            top_n: 前N个交易对
            interval: K线周期 (1d, 3d, 1w)
            aggregate_days: 聚合天数（如果指定，会将1日K线聚合成指定天数）
            
        Returns:
            合并后的K线数据DataFrame
        """
        market_name = "合约" if self.market_type == 'futures' else "现货"
        logger.info(f"开始获取OKX Top{top_n}{market_name}交易对的{interval}K线数据...")
        
        # 获取前N个交易对
        symbols = self.get_top_n_tokens('USDT', top_n)
        if not symbols:
            logger.error("无法获取交易对列表")
            return pd.DataFrame()
        
        all_data = []
        total = len(symbols)
        
        # 根据周期确定获取天数和聚合参数
        if interval == '1d':
            actual_days = days
            aggregate_days = None
        elif interval == '2d':
            # 2日K线直接通过API获取，不进行本地聚合
            actual_days = days * 2  # 2日K线需要更多历史数据
            aggregate_days = None
        elif interval == '3d':
            actual_days = days * 3  # 3日K线需要更多历史数据
            aggregate_days = None
        elif interval == '5d':
            # 5日K线直接通过API获取，不进行本地聚合
            actual_days = days * 5  # 5日K线需要更多历史数据
            aggregate_days = None
        elif interval == '1w':
            actual_days = days * 7  # 周K线需要更多历史数据
            aggregate_days = None
        else:
            actual_days = days
            aggregate_days = None
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"获取 {symbol} 数据 ({i}/{total})")
                
                # 获取K线数据
                if aggregate_days:
                    # 对于需要聚合的周期（2日、5日），先获取1日K线数据
                    df = self.get_klines(symbol, actual_days, '1d', expected_count=days, is_prescreening=(days >= 200))
                    if not df.empty:
                        df = self.aggregate_to_n_days(df, aggregate_days)
                        logger.info(f"{symbol}: 聚合为{aggregate_days}日K线，共{len(df)}条")
                        all_data.append(df)
                else:
                    # 对于原生支持的周期（1日、3日、周），直接获取
                    # 如果days >= 200，说明是预筛选阶段，不限制数量
                    if days >= 200:
                        # 预筛选阶段：也限制为指定的K线数量
                        df = self.get_klines(symbol, actual_days, interval, expected_count=days, is_prescreening=True)
                    else:
                        # 正常阶段：限制为指定的K线数量
                        df = self.get_klines(symbol, actual_days, interval, expected_count=days)
                    if not df.empty:
                        logger.info(f"{symbol}: 获取{len(df)}条K线")
                        all_data.append(df)
                
                # 延迟避免请求过快
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"获取{symbol}数据失败: {e}")
                continue
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"成功获取 {len(result)} 条K线数据，涵盖 {result['symbol'].nunique()} 个交易对")
            return result
        else:
            logger.error("未获取到任何K线数据")
            return pd.DataFrame()
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        保存数据到CSV文件 - 与BN接口保持一致
        
        Args:
            df: 要保存的DataFrame
            filename: 文件名，如果不提供则自动生成
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now(pytz.UTC).strftime('%Y%m%d_%H%M%S')
            market_type_prefix = "futures_" if self.market_type == 'futures' else ""
            filename = f'okx_{market_type_prefix}top_n_daily_{timestamp}.csv'
        
        # 确保文件路径是绝对路径
        if not os.path.isabs(filename):
            filename = os.path.join(os.getcwd(), filename)
        
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"数据已保存到: {filename}")
        return filename


def main():
    """测试函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OKX数据获取器测试')
    parser.add_argument('--market-type', choices=['spot', 'futures'], default='spot', 
                       help='市场类型：spot(现货) 或 futures(合约)')
    parser.add_argument('--top-n', type=int, default=10, help='获取前N个代币')
    parser.add_argument('--days', type=int, default=5, help='获取天数')
    args = parser.parse_args()
    
    # 创建数据获取器
    fetcher = OKXDataFetcher(market_type=args.market_type)
    market_name = "合约" if args.market_type == 'futures' else "现货"
    
    print("="*80)
    print(f"OKX{market_name}数据获取器测试")
    print("="*80)
    
    # 测试获取交易对
    print(f"1. 获取{market_name}交易对信息...")
    symbols = fetcher.get_top_n_tokens('USDT', args.top_n)
    print(f"前{args.top_n}个{market_name}交易对: {symbols}")
    print()
    
    # 测试获取K线数据
    print("2. 获取K线数据...")
    if symbols:
        test_symbol = symbols[0]
        df_klines = fetcher.get_klines(test_symbol, args.days, '1d')
        if not df_klines.empty:
            print(f"{test_symbol} 最近{args.days}日K线:")
            print(df_klines[['timestamp', 'open', 'high', 'low', 'close', 'volume']])
        print()
    
    # 测试批量获取
    print("3. 批量获取数据...")
    df_all = fetcher.fetch_top_n_daily_data(days=args.days, top_n=3, interval='1d')
    if not df_all.empty:
        print(f"获取到 {len(df_all)} 条记录，涵盖 {df_all['symbol'].nunique()} 个交易对")
        print("数据格式:")
        print(df_all.columns.tolist())
    print()
    
    print("="*80)
    print(f"OKX{market_name}数据获取测试完成")
    print("="*80)
    
    # 演示同时获取现货和合约数据
    print("\n" + "="*80)
    print("演示：同时获取现货和合约数据")
    print("="*80)
    
    # 现货数据
    print("获取现货数据...")
    spot_fetcher = OKXDataFetcher(market_type='spot')
    spot_symbols = spot_fetcher.get_top_n_tokens('USDT', 5)
    print(f"现货前5个交易对: {spot_symbols}")
    
    # 合约数据
    print("获取合约数据...")
    futures_fetcher = OKXDataFetcher(market_type='futures')
    futures_symbols = futures_fetcher.get_top_n_tokens('USDT', 5)
    print(f"合约前5个交易对: {futures_symbols}")
    
    print("="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    main()
