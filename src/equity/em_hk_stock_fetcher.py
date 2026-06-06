#!/usr/bin/env python3
"""
EM 港股数据获取工具
使用本地接口获取港股市场数据
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


class EMHKStockFetcher:
    """EM 港股数据获取器"""
    
    def __init__(self, api_url: str = None):
        """
        初始化 EM API 客户端
        
        Args:
            api_url: API 地址，默认 http://127.0.0.1:8080/api/public/stock_hk_spot_em
        """
        self.api_url = api_url or "http://127.0.0.1:8080/api/public/stock_hk_spot_em"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        
        logger.info("✓ EM 港股数据获取器初始化成功")
        logger.info(f"  API 地址: {self.api_url}")
    
    def get_latest_market_data(self) -> pd.DataFrame:
        """
        获取最新的港股市场数据
        
        Returns:
            包含所有港股数据的 DataFrame
        """
        logger.info("正在获取最新的港股市场数据...")
        
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
                
                # 重命名列（映射到标准字段名）
                column_mapping = {
                    '代码': 'code',              # 股票代码
                    '名称': 'name',              # 股票名称
                    '最新价': 'close',           # 收盘价（最新价）
                    '今开': 'open',              # 开盘价
                    '最高': 'high',              # 最高价
                    '最低': 'low',               # 最低价
                    '昨收': 'previous_close',    # 昨收价
                    '涨跌额': 'change',          # 涨跌额
                    '涨跌幅': 'change_pct',      # 涨跌幅
                    '成交量': 'volume',          # 成交量
                    '成交额': 'turnover',         # 成交额
                }
                
                # 只重命名存在的列
                rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
                df = df.rename(columns=rename_dict)
                
                # 港股代码直接使用，不需要解析（如 "02546"）
                # 确保symbol是字符串类型，保留前导0
                if 'code' in df.columns:
                    df['symbol'] = df['code'].astype(str).str.strip()
                
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
        注意：此接口返回的是最新数据，date 参数主要用于兼容性
        
        Args:
            date: 日期字符串 YYYY-MM-DD（此接口忽略此参数，返回最新数据）
            
        Returns:
            包含所有港股数据的 DataFrame
        """
        logger.info(f"正在获取 {date} 的港股市场数据...")
        logger.warning("注意：此接口返回最新数据，date 参数仅用于兼容性")
        
        df = self.get_latest_market_data()
        
        if not df.empty:
            # 更新日期字段
            df['date'] = date
        
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
    print("EM 港股数据获取工具 - 测试")
    print("="*80)
    
    try:
        # 创建数据获取器
        fetcher = EMHKStockFetcher()
        
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

