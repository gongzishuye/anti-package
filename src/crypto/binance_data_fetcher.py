#!/usr/bin/env python3
"""
币安前100代币日线数据获取工具
使用币安官方SDK获取交易量前100的代币日线K线数据
"""

import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from binance.client import Client
from binance.exceptions import BinanceAPIException
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
import logging
import requests

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class BinanceDataFetcher:
    """币安数据获取器"""
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, 
                 testnet: bool = False, market_type: str = 'spot'):
        """
        初始化币安客户端
        
        Args:
            api_key: 币安API密钥（可选，如果不提供则使用公开API）
            secret_key: 币安API密钥密码（可选）
            testnet: 是否使用测试网
            market_type: 市场类型，'spot'为现货，'futures'为合约，默认为现货
        """
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.secret_key = secret_key or os.getenv('BINANCE_SECRET_KEY')
        self.testnet = testnet or os.getenv('BINANCE_TESTNET', 'False').lower() == 'true'
        self.market_type = market_type.lower()  # 现货或合约
        
        # 初始化币安客户端
        if self.api_key and self.secret_key:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.secret_key,
                testnet=self.testnet
            )
        else:
            # 使用公开API（无需密钥）
            self.client = Client(testnet=self.testnet)
        
        # 根据市场类型设置基础URL
        if self.market_type == 'futures':
            self.base_url = 'https://fapi.binance.com'
        else:
            self.base_url = 'https://api.binance.com'
    
    def get_all_tokens(self, quote_asset: str = 'USDT') -> List[str]:
        """
        获取所有USDT交易对（支持现货和合约）
        
        Args:
            quote_asset: 计价货币，默认为USDT
            
        Returns:
            所有交易对列表
        """
        try:
            if self.market_type == 'futures':
                # 获取合约交易所信息
                exchange_info = self.client.futures_exchange_info()
            else:
                # 获取现货交易所信息
                exchange_info = self.client.get_exchange_info()
            
            # 过滤指定计价货币的交易对
            all_pairs = []
            for symbol_info in exchange_info['symbols']:
                if symbol_info['quoteAsset'] == quote_asset and symbol_info['status'] == 'TRADING':
                    all_pairs.append(symbol_info['symbol'])
            
            market_type_name = "合约" if self.market_type == 'futures' else "现货"
            logger.info(f"获取到 {len(all_pairs)} 个{market_type_name} {quote_asset} 交易对")
            return all_pairs
            
        except BinanceAPIException as e:
            market_type_name = "合约" if self.market_type == 'futures' else "现货"
            logger.error(f"获取{market_type_name}代币列表失败: {e}")
            return []
    
    def get_top_n_tokens(self, quote_asset: str = 'USDT', top_n: int = 100) -> List[str]:
        """
        获取交易量前N的代币对（支持现货和合约）
        
        Args:
            quote_asset: 计价货币，默认为USDT
            top_n: 获取前N个代币对
            
        Returns:
            前N个代币对列表
        """
        try:
            if self.market_type == 'futures':
                # 获取合约24小时价格统计
                ticker_24hr = self.client.futures_ticker()
            else:
                # 获取现货24小时价格统计
                ticker_24hr = self.client.get_ticker()
            
            # 过滤指定计价货币的交易对
            filtered_pairs = []
            for ticker in ticker_24hr:
                if ticker['symbol'].endswith(quote_asset):
                    # 确保交易对是活跃的
                    if float(ticker['quoteVolume']) > 0:
                        filtered_pairs.append({
                            'symbol': ticker['symbol'],
                            'volume': float(ticker['quoteVolume']),
                            'count': int(ticker['count'])
                        })
            
            # 按交易量排序，取前N个
            filtered_pairs.sort(key=lambda x: x['volume'], reverse=True)
            top_n_tokens = filtered_pairs[:top_n]
            
            market_type_name = "合约" if self.market_type == 'futures' else "现货"
            logger.info(f"获取到 {len(top_n_tokens)} 个{market_type_name} {quote_asset} 交易对")
            return [pair['symbol'] for pair in top_n_tokens]
            
        except BinanceAPIException as e:
            market_type_name = "合约" if self.market_type == 'futures' else "现货"
            logger.error(f"获取{market_type_name}代币列表失败: {e}")
            return []
    
    def get_futures_only_tokens(self, quote_asset: str = 'USDT') -> List[str]:
        """
        获取仅上线合约但未上线现货的USDT交易对
        
        Args:
            quote_asset: 计价货币，默认为USDT
            
        Returns:
            仅上线合约的交易对列表
        """
        try:
            # 创建临时现货获取器
            spot_fetcher = BinanceDataFetcher(market_type='spot')
            # 创建临时合约获取器
            futures_fetcher = BinanceDataFetcher(market_type='futures')
            
            logger.info(f"获取现货 {quote_asset} 交易对列表...")
            spot_tokens = set(spot_fetcher.get_all_tokens(quote_asset))
            
            logger.info(f"获取合约 {quote_asset} 交易对列表...")
            futures_tokens = set(futures_fetcher.get_all_tokens(quote_asset))
            
            # 计算差集：只在上合约中的交易对
            futures_only = list(futures_tokens - spot_tokens)
            futures_only.sort()
            
            logger.info(f"发现 {len(futures_only)} 个仅上线合约的交易对")
            logger.info(f"现货总数: {len(spot_tokens)}, 合约总数: {len(futures_tokens)}")
            
            return futures_only
            
        except Exception as e:
            logger.error(f"获取仅合约交易对失败: {e}")
            return []
    
    def get_all_futures_funding_rates(self) -> List[Dict]:
        """
        获取所有合约交易对的资金费率信息
        
        Returns:
            包含资金费率信息的列表，每项包含：
            - symbol: 交易对
            - markPrice: 标记价格
            - indexPrice: 指数价格
            - lastFundingRate: 最近资金费率
            - nextFundingTime: 下次资金费率结算时间（毫秒）
            - time: 当前数据时间
        """
        if self.market_type != 'futures':
            logger.warning("资金费率查询仅支持合约市场")
            return []
        
        try:
            url = f"{self.base_url}/fapi/v1/premiumIndex"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict):
                data = [data]
            
            funding_data = []
            for item in data:
                symbol = item.get('symbol')
                if not symbol:
                    continue
                try:
                    funding_data.append({
                        'symbol': symbol,
                        'markPrice': float(item.get('markPrice', 0) or 0),
                        'indexPrice': float(item.get('indexPrice', 0) or 0),
                        'lastFundingRate': float(item.get('lastFundingRate', 0) or 0),
                        'nextFundingTime': item.get('nextFundingTime'),
                        'time': item.get('time')
                    })
                except (TypeError, ValueError):
                    logger.debug(f"解析资金费率数据失败: {item}")
                    continue
            
            logger.info(f"获取到 {len(funding_data)} 个合约交易对的资金费率信息")
            return funding_data
        
        except Exception as e:
            logger.error(f"获取资金费率信息失败: {e}")
            return []
    
    def get_funding_rate_adjustments(self) -> Dict[str, Dict]:
        """
        获取资金费率调整信息（仅返回被特殊调整的交易对）
        
        Returns:
            {symbol: {adjustedFundingRateCap, adjustedFundingRateFloor, fundingIntervalHours, disclaimer}}
        """
        if self.market_type != 'futures':
            logger.warning("资金费率调整信息仅支持合约市场")
            return {}
        
        try:
            url = f"{self.base_url}/fapi/v1/fundingInfo"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                return {}
            
            adjustments = {}
            for item in data:
                symbol = item.get('symbol')
                if not symbol:
                    continue
                adjustments[symbol] = {
                    'adjustedFundingRateCap': float(item.get('adjustedFundingRateCap', 0) or 0),
                    'adjustedFundingRateFloor': float(item.get('adjustedFundingRateFloor', 0) or 0),
                    'fundingIntervalHours': item.get('fundingIntervalHours'),
                    'disclaimer': item.get('disclaimer', False)
                }
            
            logger.info(f"获取到 {len(adjustments)} 个资金费率调整信息")
            return adjustments
        
        except Exception as e:
            logger.error(f"获取资金费率调整信息失败: {e}")
            return {}
    
    def get_klines(self, symbol: str, days: int = 16, interval: str = '1d') -> pd.DataFrame:
        """
        获取指定代币的K线数据（支持现货和合约，支持多种时间周期）
        
        注意：币安的日K线默认时间范围是北京时间早上8:00开始到次日7:59:59结束
        也就是说，收盘时间是北京时间早上8点，符合中国用户习惯
        
        Args:
            symbol: 交易对符号
            days: 应该是希望获取的k线数量
            interval: K线间隔，支持：
                     '1m', '3m', '5m', '15m', '30m' - 分钟线
                     '1h', '2h', '4h', '6h', '8h', '12h' - 小时线
                     '1d' - 日线（默认）
                     '3d' - 3日线
                     '1w' - 周线
                     '1M' - 月线
            
        Returns:
            K线数据DataFrame
        """
        # K线间隔映射
        interval_map = {
            '1m': Client.KLINE_INTERVAL_1MINUTE,
            '3m': Client.KLINE_INTERVAL_3MINUTE,
            '5m': Client.KLINE_INTERVAL_5MINUTE,
            '15m': Client.KLINE_INTERVAL_15MINUTE,
            '30m': Client.KLINE_INTERVAL_30MINUTE,
            '1h': Client.KLINE_INTERVAL_1HOUR,
            '2h': Client.KLINE_INTERVAL_2HOUR,
            '4h': Client.KLINE_INTERVAL_4HOUR,
            '6h': Client.KLINE_INTERVAL_6HOUR,
            '8h': Client.KLINE_INTERVAL_8HOUR,
            '12h': Client.KLINE_INTERVAL_12HOUR,
            '1d': Client.KLINE_INTERVAL_1DAY,
            '3d': Client.KLINE_INTERVAL_3DAY,
            '1w': Client.KLINE_INTERVAL_1WEEK,
            '1M': Client.KLINE_INTERVAL_1MONTH,
        }
        
        if interval not in interval_map:
            logger.error(f"不支持的K线间隔: {interval}")
            logger.error(f"支持的间隔: {', '.join(interval_map.keys())}")
            return pd.DataFrame()

        if interval == '1d':
            actual_days = days + 1
            aggregate_days = None
        elif interval == '2d':
            # 2日K线直接通过API获取，不进行本地聚合
            actual_days = days * 2 + 1  # 2日K线需要更多历史数据
            aggregate_days = None
        elif interval == '3d':
            actual_days = days * 3 + 1  # 3日K线需要更多历史数据
            aggregate_days = None
        elif interval == '5d':
            # 5日K线直接通过API获取，不进行本地聚合
            actual_days = days * 5 + 1  # 5日K线需要更多历史数据
            aggregate_days = None
        elif interval == '1w':
            actual_days = days * 7 + 1  # 周K线需要更多历史数据
            aggregate_days = None
        else:
            actual_days = days
            aggregate_days = None
        
        try:
            # 计算开始时间
            end_time = datetime.now()
            start_time = end_time - timedelta(days=actual_days)
            
            # 根据市场类型获取K线数据
            if self.market_type == 'futures':
                # 获取合约K线数据
                klines = self.client.futures_historical_klines(
                    symbol=symbol,
                    interval=interval_map[interval],
                    start_str=start_time.strftime('%d %b %Y %H:%M:%S'),
                    end_str=end_time.strftime('%d %b %Y %H:%M:%S'),
                    limit=min(300, days)
                )
            else:
                # 获取现货K线数据
                klines = self.client.get_historical_klines(
                    symbol=symbol,
                    interval=interval_map[interval],
                    start_str=start_time.strftime('%d %b %Y %H:%M:%S'),
                    end_str=end_time.strftime('%d %b %Y %H:%M:%S'),
                    limit=min(300, days)
                )
            logger.info(f"{self.market_type} {symbol} {interval} klines: {len(klines)}")
            
            if not klines:
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 数据类型转换
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume',
                             'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 添加交易对信息
            df['symbol'] = symbol
            
            # 重新排列列的顺序
            df = df[['symbol', 'timestamp', 'close_time', 'open', 'high', 'low', 'close', 
                    'volume', 'quote_asset_volume', 'number_of_trades']]
            
            return df
            
        except BinanceAPIException as e:
            market_type_name = "合约" if self.market_type == 'futures' else "现货"
            logger.error(f"获取{market_type_name} {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_klines_utf8(self, symbol: str, days: int = 16, interval: str = '1d') -> pd.DataFrame:
        """
        获取指定代币的现货K线数据（使用UTC+8时区，支持多种时间周期）
        
        注意：此方法使用timeZone=8参数，K线间隔将按照UTC+8时区（北京时间）解释
        当interval='1d'时，获取的是UTC+8时区0点到第二天0点的数据
        
        Args:
            symbol: 交易对符号
            days: 应该是希望获取的k线数量
            interval: K线间隔，支持：
                     '1m', '3m', '5m', '15m', '30m' - 分钟线
                     '1h', '2h', '4h', '6h', '8h', '12h' - 小时线
                     '1d' - 日线（默认），获取UTC+8时区0点到第二天0点的数据
                     '3d' - 3日线
                     '1w' - 周线
                     '1M' - 月线
            
        Returns:
            K线数据DataFrame
        """
        # K线间隔映射（直接使用字符串格式，因为REST API需要字符串）
        interval_map = {
            '1m': '1m',
            '3m': '3m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '2h': '2h',
            '4h': '4h',
            '6h': '6h',
            '8h': '8h',
            '12h': '12h',
            '1d': '1d',
            '3d': '3d',
            '1w': '1w',
            '1M': '1M',
        }
        
        if interval not in interval_map:
            logger.error(f"不支持的K线间隔: {interval}")
            logger.error(f"支持的间隔: {', '.join(interval_map.keys())}")
            return pd.DataFrame()

        if interval == '1d':
            actual_days = days + 1
        elif interval == '2d':
            actual_days = days * 2 + 1
        elif interval == '3d':
            actual_days = days * 3 + 1
        elif interval == '5d':
            actual_days = days * 5 + 1
        elif interval == '1w':
            actual_days = days * 7 + 1
        else:
            actual_days = days
        
        try:
            # UTC+8时区偏移
            utc8_offset = timezone(timedelta(hours=8))
            
            if interval == '1d':
                # 对于日线，使用UTC+8时区的0点作为边界
                # 获取当前UTC+8时区的日期0点
                now_utc8 = datetime.now(utc8_offset)
                # 今天的0点（UTC+8）
                today_utc8_0 = now_utc8.replace(hour=0, minute=0, second=0, microsecond=0)
                # 结束时间：使用当前时间（UTC+8），这样可以包含今天正在进行的K线
                # 如果使用明天的0点，可能无法获取今天还在进行中的K线
                end_time_utc8 = now_utc8
                # 开始时间：N天前的0点（UTC+8）
                start_time_utc8 = today_utc8_0 - timedelta(days=actual_days - 1)
                
                # 转换为UTC时间戳（毫秒）
                start_timestamp = int(start_time_utc8.astimezone(timezone.utc).timestamp() * 1000)
                end_timestamp = int(end_time_utc8.astimezone(timezone.utc).timestamp() * 1000)
            else:
                # 对于其他时间周期，使用当前时间
                end_time = datetime.now()
                start_time = end_time - timedelta(days=actual_days)
                start_timestamp = int(start_time.timestamp() * 1000)
                end_timestamp = int(end_time.timestamp() * 1000)
            
            # 使用现货API
            url = f"https://api.binance.com/api/v3/klines"
            
            # 构建请求参数
            # limit需要设置为days+1，因为可能包含今天正在进行的K线
            params = {
                'symbol': symbol,
                'interval': interval_map[interval],
                'startTime': start_timestamp,
                'endTime': end_timestamp,
                'timeZone': '8',  # UTC+8时区（北京时间）
                'limit': min(1000, days + 1)  # 币安API最大支持1000条，+1确保包含今天的数据
            }
            
            # 发送请求
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            logger.info(f"现货 {symbol} {interval} klines (UTC+8): {len(klines)}")
            
            if not klines:
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 数据类型转换
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume',
                             'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 添加交易对信息
            df['symbol'] = symbol
            
            # 重新排列列的顺序
            df = df[['symbol', 'timestamp', 'close_time', 'open', 'high', 'low', 'close', 
                    'volume', 'quote_asset_volume', 'number_of_trades']]
            
            return df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取现货 {symbol} 数据失败 (UTC+8): {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取现货 {symbol} 数据时发生未知错误 (UTC+8): {e}")
            return pd.DataFrame()
    
    def get_daily_klines(self, symbol: str, days: int = 16) -> pd.DataFrame:
        """
        获取指定代币的日线K线数据（向后兼容的方法）
        
        Args:
            symbol: 交易对符号
            days: 获取最近多少天的数据
            
        Returns:
            K线数据DataFrame
        """
        return self.get_klines(symbol, days, interval='1d')
    
    def get_open_interest(self, symbol: str) -> Dict:
        """
        获取指定合约的实时持仓量
        
        Args:
            symbol: 合约代码（如 BTCUSDT）
            
        Returns:
            包含持仓量信息的字典：
            {
                'symbol': 合约代码,
                'openInterest': 持仓量（BTC数量）,
                'time': 时间戳（毫秒）
            }
        """
        if self.market_type != 'futures':
            logger.error(f"持仓量查询仅支持合约市场，当前市场类型: {self.market_type}")
            return {}
        
        try:
            url = f"{self.base_url}/fapi/v1/openInterest"
            params = {"symbol": symbol}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"获取 {symbol} 持仓量成功: {data.get('openInterest')} BTC")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 {symbol} 持仓量失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"获取 {symbol} 持仓量时发生未知错误: {e}")
            return {}
    
    def get_open_interest_hist(self, symbol: str, period: str = '5m', limit: int = 30) -> pd.DataFrame:
        """
        获取历史持仓量数据
        
        Args:
            symbol: 合约代码（如 BTCUSDT）
            period: 时间周期，支持：5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d
            limit: 返回数量，默认30，最大500
            
        Returns:
            历史持仓量数据DataFrame，包含：
            - symbol: 合约代码
            - sumOpenInterest: 总持仓量（BTC数量）
            - sumOpenInterestValue: 持仓量价值（USDT）
            - CMCCirculatingSupply: CoinMarketCap流通量
            - timestamp: 时间戳
        """
        if self.market_type != 'futures':
            logger.error(f"持仓量查询仅支持合约市场，当前市场类型: {self.market_type}")
            return pd.DataFrame()
        
        # 验证时间周期
        valid_periods = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
        if period not in valid_periods:
            logger.error(f"不支持的时间周期: {period}，支持的周期: {', '.join(valid_periods)}")
            return pd.DataFrame()
        
        # 限制返回数量
        limit = min(max(1, limit), 500)
        
        try:
            url = "https://fapi.binance.com/futures/data/openInterestHist"
            params = {
                "symbol": symbol,
                "period": period,
                "limit": limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"未获取到 {symbol} 的历史持仓量数据")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 数据类型转换
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            numeric_columns = ['sumOpenInterest', 'sumOpenInterestValue', 'CMCCirculatingSupply']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"获取 {symbol} 历史持仓量成功: {len(df)} 条记录")
            return df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 {symbol} 历史持仓量失败: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取 {symbol} 历史持仓量时发生未知错误: {e}")
            return pd.DataFrame()
    
    def get_today_kline(self, symbol: str, interval: str = '1d', include_history: bool = False) -> pd.DataFrame:
        """
        获取指定代币的当天K线数据
        
        注意：币安的日K线是UTC时间00:00开盘，23:59:59收盘
        如果在交易日进行中调用，返回的是实时更新的K线数据
        
        Args:
            symbol: 交易对符号（如：BTCUSDT）
            interval: K线间隔（如：'1d', '4h', '1h'等）
            include_history: 是否包含前一根已完成的K线，默认False只返回当天的
            
        Returns:
            K线数据DataFrame，包含当天的K线（可能是进行中的）
        """
        # 获取最近2-3根K线，确保包含当天的
        days_to_fetch = 3 if include_history else 2
        df = self.get_klines(symbol, days=days_to_fetch, interval=interval)
        
        if df.empty:
            return df
        
        if include_history:
            # 返回最近的几根K线
            return df
        else:
            # 只返回当天正在进行的K线（收盘时间在未来的）
            now = pd.Timestamp.now()
            current_df = df[df['close_time'] > now]
            
            # 如果没有找到进行中的K线，返回最新的一根（可能刚好收盘）
            if current_df.empty:
                return df.tail(1)
            
            return current_df
    
    def aggregate_to_n_days(self, df: pd.DataFrame, n_days: int) -> pd.DataFrame:
        """
        将K线数据聚合为N日K线
        用于创建2日、5日等币安不直接支持的周期
        
        Args:
            df: 原始K线DataFrame
            n_days: 聚合周期（天数）
            
        Returns:
            聚合后的DataFrame
        """
        if df.empty:
            return df
        
        # 确保按时间排序
        df = df.sort_values('timestamp').copy()
        
        # 设置时间索引
        df_indexed = df.set_index('timestamp')
        
        # 聚合规则
        agg_rules = {
            'open': 'first',      # 开盘价取第一个
            'high': 'max',        # 最高价取最大值
            'low': 'min',         # 最低价取最小值
            'close': 'last',      # 收盘价取最后一个
            'volume': 'sum',      # 成交量求和
            'quote_asset_volume': 'sum',  # USDT成交量求和
            'number_of_trades': 'sum',    # 交易次数求和
        }
        
        # 只聚合存在的列
        agg_rules = {k: v for k, v in agg_rules.items() if k in df_indexed.columns}
        
        # 按N日重采样
        result = df_indexed.resample(f'{n_days}D').agg(agg_rules)
        
        # 移除空行
        result = result.dropna(subset=['close'])
        
        # 重置索引
        result.reset_index(inplace=True)
        
        # 保留symbol列
        if 'symbol' in df.columns:
            result['symbol'] = df['symbol'].iloc[0]
        
        return result
    
    def fetch_top_n_daily_data(self, days: int = 16, delay: float = 0.1, top_n: int = 100, interval: str = '1d', aggregate_days: int = None) -> pd.DataFrame:
        """
        获取前N个代币的K线数据（支持现货和合约）
        
        注意：币安日K线默认是北京时间早上8点收盘（每天8:00-次日7:59:59）
        
        Args:
            days: 获取最近多少天的数据
            delay: 请求间隔（秒），避免触发API限制
            top_n: 获取前N个代币
            interval: K线间隔，支持 '1d', '3d', '1w', '1M', '4h' 等
            aggregate_days: 聚合天数（可选）
                          例如设为2可创建2日线，设为5可创建5日线
                          仅在interval='1d'时有效
            
        Returns:
            包含所有代币数据的DataFrame
        """
        # 获取前N个代币
        top_n_symbols = self.get_top_n_tokens(top_n=top_n)
        
        if not top_n_symbols:
            logger.error("无法获取代币列表")
            return pd.DataFrame()
        
        all_data = []
        total = len(top_n_symbols)
        
        market_type_name = "合约" if self.market_type == 'futures' else "现货"
        interval_name = f"{aggregate_days}日" if aggregate_days else interval
        logger.info(f"开始获取 {total} 个{market_type_name}代币的 {days} 天 {interval_name} K线数据...")
        
        for i, symbol in enumerate(top_n_symbols, 1):
            logger.info(f"正在获取 {i}/{total}: {symbol}")
            
            df = self.get_klines(symbol, days, interval)
            
            # 如果需要聚合
            if not df.empty and aggregate_days and interval == '1d':
                df = self.aggregate_to_n_days(df, aggregate_days)
            
            if not df.empty:
                all_data.append(df)
                logger.info(f"  ✓ 获取到 {len(df)} 条记录")
            else:
                logger.info(f"  ✗ 获取失败")
            
            # 添加延迟避免API限制
            if delay > 0 and i < total:
                time.sleep(delay)
        
        if all_data:
            # 合并所有数据
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"\n总计s获取到 {len(combined_df)} 条{market_type_name}K线记录")
            return combined_df
        else:
            logger.info(f"没有获取到任何{market_type_name}数据")
            return pd.DataFrame()
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        保存数据到CSV文件（支持现货和合约数据）
        
        Args:
            df: 要保存的DataFrame
            filename: 文件名，如果不提供则自动生成
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            market_type_prefix = "futures" if self.market_type == 'futures' else "spot"
            filename = f'binance_{market_type_prefix}_top_n_daily_{timestamp}.csv'
        
        # 确保文件路径是绝对路径
        if not os.path.isabs(filename):
            filename = os.path.join(os.getcwd(), filename)
        
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        market_type_name = "合约" if self.market_type == 'futures' else "现货"
        logger.info(f"{market_type_name}数据已保存到: {filename}")
        return filename

def main():
    """主函数 - 演示现货和合约数据获取"""
    import argparse
    
    parser = argparse.ArgumentParser(description='币安数据获取工具（支持现货和合约）')
    parser.add_argument('--market-type', choices=['spot', 'futures'], default='spot',
                        help='市场类型：spot(现货) 或 futures(合约)，默认为现货')
    parser.add_argument('--top-n', type=int, default=10,
                        help='获取前N个代币，默认为10')
    parser.add_argument('--days', type=int, default=16,
                        help='获取最近多少天的数据，默认为16天')
    
    args = parser.parse_args()
    
    market_type_name = "合约" if args.market_type == 'futures' else "现货"
    print(f"币安{market_type_name}数据获取工具")
    print("=" * 50)
    
    # 创建数据获取器
    fetcher = BinanceDataFetcher(market_type=args.market_type)
    
    # 获取数据
    df = fetcher.fetch_top_n_daily_data(days=args.days, delay=0.2, top_n=args.top_n)
    
    if not df.empty:
        # 显示数据统计信息
        print(f"\n数据统计:")
        print(f"市场类型: {market_type_name}")
        print(f"总记录数: {len(df)}")
        print(f"代币数量: {df['symbol'].nunique()}")
        print(f"日期范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}")
        
        # 保存数据
        filename = fetcher.save_to_csv(df)
        
        # 显示前几条数据
        print(f"\n前5条数据预览:")
        print(df.head())
        
        print(f"\n数据已成功保存到: {filename}")
        
        # 显示支持的代币列表
        print(f"\n获取到的{market_type_name}代币列表:")
        unique_symbols = df['symbol'].unique()
        for i, symbol in enumerate(unique_symbols, 1):
            print(f"{i:2d}. {symbol}")
    else:
        print(f"没有获取到{market_type_name}数据，请检查网络连接和API配置")
    
    # 如果是合约市场，演示持仓量查询功能
    if args.market_type == 'futures':
        print("\n" + "=" * 50)
        print("持仓量查询示例")
        print("=" * 50)
        
        # 查询BTCUSDT实时持仓量
        print("\n1. 查询BTCUSDT实时持仓量:")
        oi_data = fetcher.get_open_interest('BTCUSDT')
        if oi_data:
            print(f"  合约: {oi_data['symbol']}")
            print(f"  持仓量: {oi_data['openInterest']} BTC")
            print(f"  时间: {datetime.fromtimestamp(oi_data['time']/1000)}")
        
        # 查询BTCUSDT历史持仓量
        print("\n2. 查询BTCUSDT历史持仓量 (最近5条5分钟数据):")
        oi_hist_df = fetcher.get_open_interest_hist('BTCUSDT', period='5m', limit=5)
        if not oi_hist_df.empty:
            print(oi_hist_df[['timestamp', 'sumOpenInterest', 'sumOpenInterestValue']])
            print(f"\n  说明: sumOpenInterest为持仓量(BTC)，sumOpenInterestValue为持仓量价值(USDT)")
        
        # 查询仅上线合约的交易对
        print("\n" + "=" * 50)
        print("合约独有交易对示例")
        print("=" * 50)
        futures_only = fetcher.get_futures_only_tokens()
        if futures_only:
            print(f"\n发现 {len(futures_only)} 个仅上线合约的交易对")
            print("\n前20个:")
            for i, symbol in enumerate(futures_only[:20], 1):
                print(f"  {i:2d}. {symbol}")
            if len(futures_only) > 20:
                print(f"  ... 还有 {len(futures_only) - 20} 个")

if __name__ == "__main__":
    main()
