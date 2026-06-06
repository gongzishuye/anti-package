#!/usr/bin/env python3
"""
美股数据获取器
基于富途API获取美股市场数据，支持股票列表、实时行情、历史数据等
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time
import logging
from dotenv import load_dotenv

# 尝试导入富途API
try:
    from futu import *
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    print("⚠️ 富途API未安装，请运行: pip install futu-api")

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class USStockFetcher:
    """美股数据获取器"""
    
    def __init__(self, host: str = None, port: int = None):
        """
        初始化美股数据获取器
        
        Args:
            host: FutuOpenD服务器地址
            port: FutuOpenD服务器端口
        """
        if not FUTU_AVAILABLE:
            raise ImportError("富途API未安装，请先安装: pip install futu-api")
        
        self.host = host or os.getenv('FUTU_HOST', '127.0.0.1')
        self.port = int(port or os.getenv('FUTU_PORT', '11111'))
        self.quote_ctx = None
        self.trade_ctx = None
        self.is_connected = False
        
        logger.info(f"初始化美股数据获取器: {self.host}:{self.port}")
    
    def connect(self) -> bool:
        """连接到FutuOpenD"""
        try:
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            
            # 测试连接
            ret, data = self.quote_ctx.get_global_state()
            if ret == RET_OK:
                self.is_connected = True
                logger.info(f"✓ 成功连接到FutuOpenD ({self.host}:{self.port})")
                return True
            else:
                logger.error(f"✗ 连接测试失败: {data}")
                return False
                
        except Exception as e:
            logger.error(f"✗ 连接FutuOpenD失败: {e}")
            self._print_connection_help()
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.quote_ctx:
            self.quote_ctx.close()
            self.is_connected = False
            logger.info("✓ 已断开FutuOpenD连接")
        
        if self.trade_ctx:
            self.trade_ctx.close()
            self.trade_ctx = None
    
    def _print_connection_help(self):
        """打印连接帮助信息"""
        print("\n" + "="*60)
        print("连接失败帮助:")
        print("="*60)
        print("请确保:")
        print("1. 已安装FutuOpenD客户端")
        print("2. FutuOpenD客户端正在运行")
        print("3. 端口号正确（默认11111）")
        print("4. 已登录富途账户")
        print("5. 开通了美股交易权限")
        print("\n下载地址: https://www.futunn.com/download")
        print("="*60)
    
    def get_all_us_stocks(self, include_etf: bool = True, include_warrant: bool = False) -> pd.DataFrame:
        """
        获取所有美股股票列表
        
        Args:
            include_etf: 是否包含ETF
            include_warrant: 是否包含权证
            
        Returns:
            包含所有美股股票信息的DataFrame
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        
        all_stocks = []
        
        try:
            # 获取美股主板股票
            logger.info("正在获取美股主板股票...")
            ret, data = self.quote_ctx.get_stock_basicinfo(Market.US, SecurityType.STOCK)
            if ret == RET_OK:
                logger.info(f"✓ 获取到美股主板股票: {len(data)} 只")
                all_stocks.append(data)
            else:
                logger.error(f"✗ 获取美股主板股票失败: {data}")
            
            if include_etf:
                time.sleep(0.5)
                logger.info("正在获取美股ETF...")
                ret, data = self.quote_ctx.get_stock_basicinfo(Market.US, SecurityType.ETF)
                if ret == RET_OK:
                    logger.info(f"✓ 获取到美股ETF: {len(data)} 只")
                    all_stocks.append(data)
                else:
                    logger.error(f"✗ 获取美股ETF失败: {data}")
            
            if include_warrant:
                time.sleep(0.5)
                logger.info("正在获取美股权证...")
                ret, data = self.quote_ctx.get_stock_basicinfo(Market.US, SecurityType.WARRANT)
                if ret == RET_OK:
                    logger.info(f"✓ 获取到美股权证: {len(data)} 只")
                    all_stocks.append(data)
                else:
                    logger.error(f"✗ 获取美股权证失败: {data}")
            
            # 合并所有数据
            if all_stocks:
                df = pd.concat(all_stocks, ignore_index=True)
                logger.info(f"✓ 总共获取到 {len(df)} 只美股证券")
                return self._clean_stock_data(df)
            else:
                logger.error("✗ 未获取到任何股票数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"✗ 获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_snapshot(self, stock_codes: List[str], batch_size: int = 200) -> pd.DataFrame:
        """
        获取股票快照数据（实时行情）
        
        Args:
            stock_codes: 股票代码列表
            batch_size: 批次大小
            
        Returns:
            包含股票快照信息的DataFrame
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        
        if not stock_codes:
            logger.warning("股票代码列表为空")
            return pd.DataFrame()
        
        all_snapshots = []
        
        logger.info(f"正在获取 {len(stock_codes)} 只股票的实时行情...")
        
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            try:
                ret, data = self.quote_ctx.get_market_snapshot(batch)
                if ret == RET_OK:
                    all_snapshots.append(data)
                    logger.info(f"✓ 已获取 {i + len(batch)}/{len(stock_codes)} 只股票行情")
                else:
                    logger.error(f"✗ 获取行情失败 (批次 {i//batch_size + 1}): {data}")
                
                # 避免请求过快
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"✗ 获取行情异常 (批次 {i//batch_size + 1}): {e}")
                continue
        
        if all_snapshots:
            df = pd.concat(all_snapshots, ignore_index=True)
            logger.info(f"✓ 成功获取 {len(df)} 只股票的实时行情")
            return df
        else:
            logger.error("✗ 未获取到任何行情数据")
            return pd.DataFrame()
    
    def get_stock_kline(self, stock_code: str, start_date: str, end_date: str, 
                       ktype: KLType = KLType.K_DAY, max_count: int = 1000) -> pd.DataFrame:
        """
        获取股票K线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            ktype: K线类型
            max_count: 最大数量
            
        Returns:
            包含K线数据的DataFrame
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        
        try:
            ret, data, page_req_key = self.quote_ctx.request_history_kline(
                stock_code, 
                start=start_date, 
                end=end_date,
                ktype=ktype,
                max_count=max_count
            )
            
            if ret == RET_OK:
                logger.info(f"✓ 获取 {stock_code} K线数据: {len(data)} 条")
                return data
            else:
                logger.error(f"✗ 获取K线失败 ({stock_code}): {data}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"✗ 获取K线异常 ({stock_code}): {e}")
            return pd.DataFrame()
    
    def get_market_overview(self) -> Dict:
        """
        获取美股市场概览
        
        Returns:
            包含市场概览信息的字典
        """
        if not self._ensure_connected():
            return {}
        
        try:
            # 获取主要指数
            indices = ['US.SPX', 'US.NDX', 'US.DJI']
            ret, data = self.quote_ctx.get_market_snapshot(indices)
            
            overview = {}
            if ret == RET_OK:
                for _, row in data.iterrows():
                    overview[row['code']] = {
                        'name': row.get('name', ''),
                        'last_price': row.get('last_price', 0),
                        'change_rate': row.get('change_rate', 0),
                        'volume': row.get('volume', 0),
                        'turnover': row.get('turnover', 0)
                    }
            
            return overview
            
        except Exception as e:
            logger.error(f"✗ 获取市场概览失败: {e}")
            return {}
    
    def search_stocks(self, keyword: str, limit: int = 50) -> pd.DataFrame:
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            搜索结果DataFrame
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        
        try:
            ret, data = self.quote_ctx.get_stock_basicinfo(
                Market.US, 
                SecurityType.STOCK,
                keyword=keyword
            )
            
            if ret == RET_OK:
                if len(data) > limit:
                    data = data.head(limit)
                logger.info(f"✓ 搜索到 {len(data)} 只股票")
                return self._clean_stock_data(data)
            else:
                logger.error(f"✗ 搜索股票失败: {data}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"✗ 搜索股票异常: {e}")
            return pd.DataFrame()
    
    def get_top_gainers_losers(self, market_type: str = 'US', limit: int = 20) -> Dict:
        """
        获取涨跌幅排行榜
        
        Args:
            market_type: 市场类型
            limit: 返回数量
            
        Returns:
            包含涨跌排行榜的字典
        """
        if not self._ensure_connected():
            return {}
        
        try:
            # 获取所有股票的快照数据
            all_stocks = self.get_all_us_stocks(include_etf=True, include_warrant=False)
            if all_stocks.empty:
                return {}
            
            stock_codes = all_stocks['code'].tolist()
            snapshots = self.get_stock_snapshot(stock_codes[:500])  # 限制数量避免超时
            
            if snapshots.empty:
                return {}
            
            # 过滤有效数据
            valid_data = snapshots[
                (snapshots['last_price'] > 0) & 
                (snapshots['volume'] > 0) &
                (snapshots['change_rate'].notna())
            ].copy()
            
            if valid_data.empty:
                return {}
            
            # 排序
            gainers = valid_data.nlargest(limit, 'change_rate')
            losers = valid_data.nsmallest(limit, 'change_rate')
            
            return {
                'gainers': gainers.to_dict('records'),
                'losers': losers.to_dict('records'),
                'total_stocks': len(valid_data)
            }
            
        except Exception as e:
            logger.error(f"✗ 获取涨跌排行榜失败: {e}")
            return {}
    
    def fetch_all_us_data(self, include_quotes: bool = True, save_to_file: bool = True) -> pd.DataFrame:
        """
        获取所有美股数据（完整版）
        
        Args:
            include_quotes: 是否包含实时行情
            save_to_file: 是否保存到文件
            
        Returns:
            完整的美股数据DataFrame
        """
        logger.info("开始获取所有美股数据...")
        
        # 1. 获取股票列表
        stocks_df = self.get_all_us_stocks(include_etf=True, include_warrant=False)
        if stocks_df.empty:
            logger.error("未获取到股票列表")
            return pd.DataFrame()
        
        # 2. 获取实时行情（可选）
        if include_quotes:
            stock_codes = stocks_df['code'].tolist()
            quotes_df = self.get_stock_snapshot(stock_codes)
            
            if not quotes_df.empty:
                # 合并数据
                try:
                    merged_df = pd.merge(
                        stocks_df, 
                        quotes_df, 
                        on='code', 
                        how='left',
                        suffixes=('', '_quote')
                    )
                    logger.info(f"✓ 成功合并数据，共 {len(merged_df)} 条记录")
                    final_df = merged_df
                except Exception as e:
                    logger.error(f"合并数据失败: {e}")
                    final_df = stocks_df
            else:
                logger.warning("未获取到实时行情，仅返回股票基本信息")
                final_df = stocks_df
        else:
            final_df = stocks_df
        
        # 3. 保存到文件
        if save_to_file:
            self.save_to_csv(final_df)
        
        return final_df
    
    def _ensure_connected(self) -> bool:
        """确保已连接"""
        if not self.is_connected:
            return self.connect()
        return True
    
    def _clean_stock_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理股票数据"""
        if df.empty:
            return df
        
        # 重命名列
        column_mapping = {
            'code': 'symbol',
            'name': 'name',
            'stock_type': 'stock_type',
            'listing_date': 'listing_date',
            'lot_size': 'lot_size',
            'stock_id': 'stock_id'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 添加数据时间戳
        df['data_timestamp'] = datetime.now()
        
        return df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None, data_dir: str = 'data'):
        """
        保存数据到CSV文件
        
        Args:
            df: 要保存的DataFrame
            filename: 文件名
            data_dir: 数据目录
        """
        if df.empty:
            logger.warning("数据为空，无法保存")
            return
        
        # 创建数据目录
        os.makedirs(data_dir, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'us_stocks_all_{timestamp}.csv'
        
        filepath = os.path.join(data_dir, filename)
        
        try:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
            logger.info(f"✓ 数据已保存到: {filepath}")
            logger.info(f"  文件大小: {file_size:.2f} MB")
            logger.info(f"  股票数量: {len(df)}")
        except Exception as e:
            logger.error(f"✗ 保存文件失败: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


def main():
    """主函数 - 测试用"""
    print("="*80)
    print("美股数据获取器测试")
    print("="*80)
    
    with USStockFetcher() as fetcher:
        # 测试连接
        if not fetcher.is_connected:
            print("连接失败，退出")
            return
        
        # 获取市场概览
        print("\n获取市场概览...")
        overview = fetcher.get_market_overview()
        if overview:
            print("主要指数:")
            for code, info in overview.items():
                print(f"  {code}: {info['last_price']} ({info['change_rate']:+.2f}%)")
        
        # 搜索股票示例
        print("\n搜索苹果公司股票...")
        apple_stocks = fetcher.search_stocks("AAPL", limit=5)
        if not apple_stocks.empty:
            print(apple_stocks[['symbol', 'name', 'stock_type']].to_string())
        
        # 获取涨跌排行榜
        print("\n获取涨跌排行榜...")
        rankings = fetcher.get_top_gainers_losers(limit=5)
        if rankings:
            print("涨幅榜:")
            for stock in rankings['gainers'][:3]:
                print(f"  {stock['code']}: {stock['change_rate']:+.2f}%")
            
            print("跌幅榜:")
            for stock in rankings['losers'][:3]:
                print(f"  {stock['code']}: {stock['change_rate']:+.2f}%")


if __name__ == "__main__":
    main()
