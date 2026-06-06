#!/usr/bin/env python3
"""
EM 美股数据获取工具
使用本地接口获取美股市场数据
"""

import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EMUSStockFetcher:
    """EM 美股数据获取器"""
    
    def __init__(self, api_url: str = None):
        """
        初始化 EM API 客户端
        
        Args:
            api_url: API 地址，默认 http://127.0.0.1:8080/api/public/stock_us_spot_em
        """
        self.api_url = api_url or "http://127.0.0.1:8080/api/public/stock_us_spot_em"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        
        logger.info("✓ EM 美股数据获取器初始化成功")
        logger.info(f"  API 地址: {self.api_url}")
    
    def _parse_symbol(self, code: str) -> str:
        """
        解析股票代码，去掉前缀
        
        Args:
            code: 原始代码，如 "105.LAZR" 或 "105.TSLA"
            
        Returns:
            标准股票代码，如 "LAZR" 或 "TSLA"
        """
        # 如果包含点号，取点号后的部分
        if '.' in code:
            return code.split('.')[-1]
        return code
    
    def get_latest_market_data(self) -> pd.DataFrame:
        """
        获取最新的美股市场数据
        
        Returns:
            包含所有美股数据的 DataFrame
        """
        logger.info("正在获取最新的美股市场数据...")
        
        # 重试配置：最多尝试2次，超时5分钟（300秒）
        max_retries = 2
        timeout = 300  # 5分钟
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"尝试 {attempt}/{max_retries}...")
                
                # 发送请求
                response = self.session.get(self.api_url, timeout=timeout)
                response.raise_for_status()
                
                # 解析响应
                data = response.json()
                
                if not isinstance(data, list):
                    logger.error(f"✗ API 返回格式异常，期望列表，实际: {type(data)}")
                    return pd.DataFrame()
                
                if not data:
                    logger.warning("✗ API 返回空数据")
                    return pd.DataFrame()
                
                # 转换为 DataFrame
                df = pd.DataFrame(data)
                
                # 解析股票代码
                if '代码' in df.columns:
                    df['symbol'] = df['代码'].apply(self._parse_symbol)
                
                # 重命名列（映射到标准字段名）
                column_mapping = {
                    '代码': 'code',              # 原始代码
                    '名称': 'name',              # 股票名称
                    '最新价': 'close',           # 收盘价（最新价）
                    '开盘价': 'open',            # 开盘价
                    '最高价': 'high',            # 最高价
                    '最低价': 'low',             # 最低价
                    '昨收价': 'previous_close', # 昨收价
                    '涨跌额': 'change',          # 涨跌额
                    '涨跌幅': 'change_pct',      # 涨跌幅
                    '成交量': 'volume',          # 成交量
                    '成交额': 'turnover',         # 成交额
                    '总市值': 'market_cap',       # 总市值
                    '市盈率': 'pe_ratio',         # 市盈率
                    '振幅': 'amplitude',         # 振幅
                    '换手率': 'turnover_rate',    # 换手率
                }
                
                # 只重命名存在的列
                rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
                df = df.rename(columns=rename_dict)
                
                # 确保有 symbol 列
                if 'symbol' not in df.columns and 'code' in df.columns:
                    df['symbol'] = df['code'].apply(self._parse_symbol)
                
                # 计算 vwap（成交量加权平均价）
                if 'turnover' in df.columns and 'volume' in df.columns:
                    # vwap = 成交额 / 成交量
                    df['vwap'] = df['turnover'] / df['volume'].replace(0, pd.NA)
                elif 'close' in df.columns:
                    # 如果没有成交额，使用收盘价作为近似值
                    df['vwap'] = df['close']
                
                # 添加数据日期（使用昨天的日期，因为接口返回的是最新数据）
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                df['date'] = yesterday
                df['data_fetched_at'] = datetime.now()
                
                logger.info(f"✓ 成功获取 {len(df)} 只股票的数据")
                
                return df
                
            except requests.exceptions.HTTPError as e:
                logger.error(f"✗ HTTP 错误 (尝试 {attempt}/{max_retries}): {e}")
                if response.status_code == 404:
                    logger.error("  API 端点不存在，请检查 URL")
                    return pd.DataFrame()  # 404错误不重试
                elif response.status_code == 500:
                    logger.error("  服务器内部错误")
                    if attempt < max_retries:
                        logger.info(f"等待后重试...")
                        import time
                        time.sleep(2)  # 等待2秒后重试
                        continue
                return pd.DataFrame()
            
            except requests.exceptions.RequestException as e:
                logger.error(f"✗ 请求失败 (尝试 {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    logger.info(f"等待后重试...")
                    import time
                    time.sleep(2)  # 等待2秒后重试
                    continue
                else:
                    logger.error("  请确保 API 服务正在运行")
                    return pd.DataFrame()
            
            except Exception as e:
                logger.error(f"✗ 发生错误 (尝试 {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    logger.info(f"等待后重试...")
                    import time
                    time.sleep(2)  # 等待2秒后重试
                    continue
                else:
                    import traceback
                    traceback.print_exc()
                    return pd.DataFrame()
        
        # 所有尝试都失败
        logger.error("✗ 所有尝试均失败")
        return pd.DataFrame()
    
    def get_daily_market_summary(self, date: str) -> pd.DataFrame:
        """
        获取指定日期的市场数据
        
        重要限制：此API接口只能获取昨天的数据（最新数据）
        如果请求的日期不是昨天，将返回空DataFrame
        
        Args:
            date: 日期字符串 YYYY-MM-DD
                  - 如果date是昨天：返回昨天的市场数据
                  - 如果date不是昨天：返回空DataFrame（无法获取历史数据）
            
        Returns:
            包含所有美股数据的 DataFrame（如果date是昨天），否则返回空DataFrame
        """
        # 计算昨天的日期
        from datetime import datetime, timedelta
        today = datetime.now()
        # 如果今天是周末，往回找最近的交易日
        while today.weekday() >= 5:
            today -= timedelta(days=1)
        yesterday = today - timedelta(days=1)
        while yesterday.weekday() >= 5:
            yesterday -= timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        # 检查请求的日期是否是昨天
        if date != yesterday_str:
            logger.warning(f"✗ API只能获取昨天({yesterday_str})的数据，无法获取 {date} 的数据")
            logger.warning(f"  请确保历史数据已保存到Excel文件中")
            return pd.DataFrame()
        
        logger.info(f"正在获取 {date} 的美股市场数据...")
        
        df = self.get_latest_market_data()
        
        if not df.empty:
            # 更新日期字段
            df['date'] = date
            logger.info(f"✓ 成功获取 {date} 的数据: {len(df)} 只股票")
        
        return df
    
    def print_summary(self, df: pd.DataFrame, top_n: int = 10):
        """
        打印数据摘要
        
        Args:
            df: 数据 DataFrame
            top_n: 显示前 N 条记录
        """
        if df.empty:
            print("数据为空")
            return
        
        print(f"\n数据摘要:")
        print(f"  总股票数: {len(df)}")
        print(f"\n前 {top_n} 只股票（按成交量排序）:")
        print("-" * 100)
        
        if 'volume' in df.columns:
            top_stocks = df.nlargest(top_n, 'volume')
        else:
            top_stocks = df.head(top_n)
        
        for idx, row in top_stocks.iterrows():
            symbol = row.get('symbol', row.get('code', 'N/A'))
            name = row.get('name', 'N/A')
            close = row.get('close', 0)
            volume = row.get('volume', 0)
            change_pct = row.get('change_pct', 0)
            
            print(f"{symbol:8s} | {name[:30]:30s} | 价格: ${close:8.2f} | 涨跌: {change_pct:+7.2f}% | 成交量: {volume:,.0f}")


def main():
    """主函数 - 测试用"""
    print("="*80)
    print("EM 美股数据获取工具 - 测试")
    print("="*80)
    
    try:
        # 创建数据获取器
        fetcher = EMUSStockFetcher()
        
        # 获取最新数据
        df = fetcher.get_latest_market_data()
        
        if not df.empty:
            # 打印摘要
            fetcher.print_summary(df)
            
            print("\n" + "="*80)
            print("✓ 数据获取成功！")
            print("="*80)
            
            # 显示列信息
            print(f"\n数据列: {list(df.columns)}")
            print(f"\n数据示例（前 3 条）:")
            print(df.head(3).to_string())
        else:
            print("\n✗ 未获取到数据")
            print("提示: 请检查 API 服务是否正在运行")
    
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

