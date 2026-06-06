#!/usr/bin/env python3
"""
MetalPriceAPI 贵金属数据获取器
用于获取贵金属（XAU、XAG等）的OHLC数据

API文档: https://metalpriceapi.com/documentation
"""

import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class MetalPriceAPIFetcher:
    """MetalPriceAPI 贵金属数据获取器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化MetalPriceAPI数据获取器
        
        Args:
            api_key: API密钥（可选，如果不提供则使用默认密钥）
        """
        self.api_key = api_key or 'c587300bc520e01c70f2c0ae5d6a0b77'
        self.base_url = 'https://api.metalpriceapi.com/v1'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_ohlc(self, base: str, currency: str = 'USD', date: str = None, 
                 max_retries: int = 3, retry_delay: int = 1) -> Optional[Dict]:
        """
        获取单个日期的OHLC数据
        
        Args:
            base: 贵金属代码，如 'XAU'（黄金）、'XAG'（白银）
            currency: 计价货币，默认为 'USD'
            date: 日期字符串，格式 'YYYY-MM-DD'，默认为今天
            max_retries: 最大重试次数，默认3次
            retry_delay: 重试延迟（秒），默认1秒
        
        Returns:
            包含OHLC数据的字典，格式：
            {
                'base': 'XAU',
                'quote': 'USD',
                'timestamp': 1738108799,
                'rate': {
                    'open': 2741.97,
                    'high': 2764.96,
                    'low': 2735.11,
                    'close': 2742.22
                }
            }
            如果失败则返回None
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 验证日期格式
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            logger.error(f"日期格式错误: {date}，应为 'YYYY-MM-DD' 格式")
            return None
        
        url = f"{self.base_url}/ohlc"
        params = {
            'api_key': self.api_key,
            'base': base,
            'currency': currency,
            'date': date
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"获取 {base}/{currency} {date} 的OHLC数据 (尝试 {attempt}/{max_retries})...")
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # 检查API返回的success字段
                if not data.get('success', False):
                    error_info = data.get('error', {})
                    error_msg = error_info.get('message', '未知错误')
                    error_code = error_info.get('statusCode', 'N/A')
                    
                    # 如果是免费计划的5天限制错误，给出提示
                    if error_code == 211:
                        logger.warning(f"⚠️  免费计划限制: {error_msg}")
                        logger.warning(f"   查询日期 {date} 超过5天，需要付费计划")
                    else:
                        logger.error(f"✗ API返回错误: {error_msg} (状态码: {error_code})")
                    
                    return None
                
                logger.info(f"✓ 成功获取 {base}/{currency} {date} 的OHLC数据")
                return data
                
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    wait_time = retry_delay * attempt
                    logger.warning(f"⚠️  请求超时 (尝试 {attempt}/{max_retries})，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"✗ 请求超时，达到最大重试次数")
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    wait_time = retry_delay * attempt
                    logger.warning(f"⚠️  网络错误 (尝试 {attempt}/{max_retries}): {e}")
                    logger.warning(f"   等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"✗ 网络错误: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"✗ 获取OHLC数据时发生未知错误: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        return None
    
    def get_klines(self, base: str, currency: str = 'USD', days: int = 5, 
                   start_date: Optional[str] = None, end_date: Optional[str] = None,
                   max_retries: int = 3, retry_delay: int = 1) -> pd.DataFrame:
        """
        获取多天的OHLC数据，返回标准DataFrame格式
        
        Args:
            base: 贵金属代码，如 'XAU'（黄金）、'XAG'（白银）
            currency: 计价货币，默认为 'USD'
            days: 获取天数（从今天往前），默认5天（免费计划限制）
            start_date: 可选，开始日期（'YYYY-MM-DD'），如果提供则忽略days参数
            end_date: 可选，结束日期（'YYYY-MM-DD'），默认为今天
            max_retries: 最大重试次数，默认3次
            retry_delay: 重试延迟（秒），默认1秒
        
        Returns:
            pandas DataFrame，格式与现有数据获取器保持一致：
            - symbol: 商品代码（如 'XAU/USD'）
            - timestamp: 日期时间（datetime类型）
            - close_time: 收盘时间（datetime类型，设为当天23:59:59）
            - open, high, low, close: OHLC价格
            - volume: 设为0（API不提供）
            - quote_asset_volume: 设为0（API不提供）
            - number_of_trades: 设为0（API不提供）
        """
        # 确定日期范围
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if start_date is None:
            # 使用days参数计算开始日期
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=days - 1)
            start_date = start_dt.strftime('%Y-%m-%d')
        
        # 验证日期格式
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError as e:
            logger.error(f"日期格式错误: {e}")
            return pd.DataFrame()
        
        if start_dt > end_dt:
            logger.error(f"开始日期 {start_date} 不能晚于结束日期 {end_date}")
            return pd.DataFrame()
        
        logger.info(f"获取 {base}/{currency} 的OHLC数据: {start_date} 至 {end_date}")
        
        # 生成日期列表
        date_list = []
        current_dt = start_dt
        while current_dt <= end_dt:
            date_list.append(current_dt.strftime('%Y-%m-%d'))
            current_dt += timedelta(days=1)
        
        logger.info(f"共需获取 {len(date_list)} 天的数据")
        
        # 获取每天的OHLC数据
        klines = []
        failed_dates = []
        
        for idx, date in enumerate(date_list, 1):
            logger.info(f"正在获取第 {idx}/{len(date_list)} 天: {date}")
            
            ohlc_data = self.get_ohlc(base, currency, date, max_retries, retry_delay)
            
            if ohlc_data is None:
                failed_dates.append(date)
                logger.warning(f"⚠️  跳过日期 {date}（获取失败）")
                continue
            
            rate = ohlc_data.get('rate', {})
            timestamp = ohlc_data.get('timestamp', 0)
            
            # 将时间戳转换为datetime
            if timestamp:
                dt = datetime.fromtimestamp(timestamp)
            else:
                # 如果没有时间戳，使用日期字符串
                dt = datetime.strptime(date, '%Y-%m-%d')
            
            # 创建K线数据
            kline = {
                'symbol': f'{base}/{currency}',
                'timestamp': dt.replace(hour=0, minute=0, second=0, microsecond=0),
                'close_time': dt.replace(hour=23, minute=59, second=59, microsecond=0),
                'open': float(rate.get('open', 0)),
                'high': float(rate.get('high', 0)),
                'low': float(rate.get('low', 0)),
                'close': float(rate.get('close', 0)),
                'volume': 0,  # API不提供成交量
                'quote_asset_volume': 0,  # API不提供计价货币成交量
                'number_of_trades': 0  # API不提供交易次数
            }
            
            klines.append(kline)
            
            # 避免请求过快，添加小延迟
            if idx < len(date_list):
                time.sleep(0.1)
        
        if not klines:
            logger.warning(f"✗ 未能获取到任何数据")
            if failed_dates:
                logger.warning(f"   失败的日期: {', '.join(failed_dates)}")
            return pd.DataFrame()
        
        # 转换为DataFrame
        df = pd.DataFrame(klines)
        
        # 按时间排序
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 确保数据类型正确
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                          'quote_asset_volume', 'number_of_trades']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        logger.info(f"✓ 成功获取 {len(df)} 条数据")
        if failed_dates:
            logger.warning(f"   失败的日期 ({len(failed_dates)} 天): {', '.join(failed_dates)}")
        
        # 显示数据摘要
        if len(df) > 0:
            logger.info(f"   日期范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
            logger.info(f"   最新收盘价: ${df['close'].iloc[-1]:.2f}")
            logger.info(f"   最高价: ${df['high'].max():.2f}")
            logger.info(f"   最低价: ${df['low'].min():.2f}")
        
        return df
    
    def get_multiple_metals(self, bases: List[str], currency: str = 'USD', 
                           days: int = 5, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        批量获取多个贵金属的OHLC数据
        
        Args:
            bases: 贵金属代码列表，如 ['XAU', 'XAG']
            currency: 计价货币，默认为 'USD'
            days: 获取天数，默认5天
            start_date: 可选，开始日期
            end_date: 可选，结束日期
        
        Returns:
            字典，键为贵金属代码，值为对应的DataFrame
        """
        results = {}
        
        for base in bases:
            logger.info(f"\n{'='*80}")
            logger.info(f"获取 {base}/{currency} 数据")
            logger.info('='*80)
            
            df = self.get_klines(base, currency, days, start_date, end_date)
            if not df.empty:
                results[base] = df
            else:
                logger.warning(f"✗ {base}/{currency} 数据获取失败")
        
        return results
