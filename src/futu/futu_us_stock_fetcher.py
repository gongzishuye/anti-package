#!/usr/bin/env python3
"""
富途API美股数据获取工具
使用富途OpenAPI获取美股所有股票的信息数据
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from futu import *
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class FutuUSStockFetcher:
    """富途美股数据获取器"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 11111):
        """
        初始化富途API客户端
        
        Args:
            host: FutuOpenD服务器地址（默认本地）
            port: FutuOpenD服务器端口（默认11111）
        """
        self.host = host or os.getenv('FUTU_HOST', '127.0.0.1')
        self.port = int(port or os.getenv('FUTU_PORT', '11111'))
        self.quote_ctx = None
        
    def connect(self):
        """连接到FutuOpenD"""
        try:
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
            print(f"✓ 成功连接到FutuOpenD ({self.host}:{self.port})")
            return True
        except Exception as e:
            print(f"✗ 连接FutuOpenD失败: {e}")
            print("\n请确保:")
            print("1. 已安装FutuOpenD客户端")
            print("2. FutuOpenD客户端正在运行")
            print("3. 端口号正确（默认11111）")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.quote_ctx:
            self.quote_ctx.close()
            print("✓ 已断开FutuOpenD连接")
    
    def get_all_us_stocks(self) -> pd.DataFrame:
        """
        获取所有美股股票列表
        
        Returns:
            包含所有美股股票信息的DataFrame
        """
        if not self.quote_ctx:
            if not self.connect():
                return pd.DataFrame()
        
        print("\n正在获取美股股票列表...")
        all_stocks = []
        
        try:
            # 获取美股主板股票
            ret, data = self.quote_ctx.get_stock_basicinfo(Market.US, SecurityType.STOCK)
            if ret == RET_OK:
                print(f"✓ 获取到美股主板股票: {len(data)} 只")
                all_stocks.append(data)
            else:
                print(f"✗ 获取美股主板股票失败: {data}")
            
            # 稍微延迟避免请求过快
            time.sleep(0.5)
            
            # 获取美股ETF
            ret, data = self.quote_ctx.get_stock_basicinfo(Market.US, SecurityType.ETF)
            if ret == RET_OK:
                print(f"✓ 获取到美股ETF: {len(data)} 只")
                all_stocks.append(data)
            else:
                print(f"✗ 获取美股ETF失败: {data}")
            
            time.sleep(0.5)
            
            # 获取美股权证（可选）
            ret, data = self.quote_ctx.get_stock_basicinfo(Market.US, SecurityType.WARRANT)
            if ret == RET_OK:
                print(f"✓ 获取到美股权证: {len(data)} 只")
                all_stocks.append(data)
            else:
                print(f"✗ 获取美股权证失败: {data}")
            
            # 合并所有数据
            if all_stocks:
                df = pd.concat(all_stocks, ignore_index=True)
                print(f"\n✓ 总共获取到 {len(df)} 只美股证券")
                return df
            else:
                print("✗ 未获取到任何股票数据")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"✗ 获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_snapshot(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取股票快照数据（实时行情）
        
        Args:
            stock_codes: 股票代码列表（如 ['US.AAPL', 'US.TSLA']）
            
        Returns:
            包含股票快照信息的DataFrame
        """
        if not self.quote_ctx:
            if not self.connect():
                return pd.DataFrame()
        
        all_snapshots = []
        batch_size = 200  # 富途API每次最多请求200只股票
        
        print(f"\n正在获取 {len(stock_codes)} 只股票的实时行情...")
        
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            try:
                ret, data = self.quote_ctx.get_market_snapshot(batch)
                if ret == RET_OK:
                    all_snapshots.append(data)
                    print(f"✓ 已获取 {i + len(batch)}/{len(stock_codes)} 只股票行情")
                else:
                    print(f"✗ 获取行情失败 (批次 {i//batch_size + 1}): {data}")
                
                # 避免请求过快
                time.sleep(0.3)
                
            except Exception as e:
                print(f"✗ 获取行情异常 (批次 {i//batch_size + 1}): {e}")
                continue
        
        if all_snapshots:
            df = pd.concat(all_snapshots, ignore_index=True)
            print(f"\n✓ 成功获取 {len(df)} 只股票的实时行情")
            return df
        else:
            return pd.DataFrame()
    
    def get_stock_kline(self, stock_code: str, start_date: str, end_date: str, 
                       ktype: KLType = KLType.K_DAY) -> pd.DataFrame:
        """
        获取股票K线数据
        
        Args:
            stock_code: 股票代码（如 'US.AAPL'）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            ktype: K线类型（日线、周线等）
            
        Returns:
            包含K线数据的DataFrame
        """
        if not self.quote_ctx:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            ret, data, page_req_key = self.quote_ctx.request_history_kline(
                stock_code, 
                start=start_date, 
                end=end_date,
                ktype=ktype,
                max_count=1000
            )
            
            if ret == RET_OK:
                return data
            else:
                print(f"✗ 获取K线失败 ({stock_code}): {data}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"✗ 获取K线异常 ({stock_code}): {e}")
            return pd.DataFrame()
    
    def fetch_all_us_stocks_with_quotes(self) -> pd.DataFrame:
        """
        获取所有美股股票及其实时行情
        
        Returns:
            包含股票基本信息和实时行情的完整DataFrame
        """
        # 1. 获取股票列表
        stocks_df = self.get_all_us_stocks()
        if stocks_df.empty:
            return pd.DataFrame()
        
        # 2. 获取实时行情
        stock_codes = stocks_df['code'].tolist()
        quotes_df = self.get_stock_snapshot(stock_codes)
        
        if quotes_df.empty:
            print("\n⚠ 未获取到实时行情，仅返回股票基本信息")
            return stocks_df
        
        # 3. 合并数据
        try:
            merged_df = pd.merge(
                stocks_df, 
                quotes_df, 
                on='code', 
                how='left',
                suffixes=('', '_quote')
            )
            print(f"\n✓ 成功合并数据，共 {len(merged_df)} 条记录")
            return merged_df
        except Exception as e:
            print(f"✗ 合并数据失败: {e}")
            return stocks_df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = None):
        """
        保存数据到CSV文件
        
        Args:
            df: 要保存的DataFrame
            filename: 文件名（可选，默认自动生成）
        """
        if df.empty:
            print("✗ 数据为空，无法保存")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'us_stocks_{timestamp}.csv'
        
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n✓ 数据已保存到: {filename}")
            print(f"  文件大小: {os.path.getsize(filename) / 1024:.2f} KB")
            print(f"  股票数量: {len(df)}")
        except Exception as e:
            print(f"✗ 保存文件失败: {e}")


def print_sample_data(df: pd.DataFrame, n: int = 10):
    """打印样本数据"""
    if df.empty:
        return
    
    print("\n" + "="*80)
    print(f"样本数据（前{n}条）:")
    print("="*80)
    
    # 选择关键列显示
    display_columns = []
    all_columns = df.columns.tolist()
    
    # 优先显示的列
    priority_cols = ['code', 'name', 'stock_type', 'last_price', 'change_rate', 
                    'volume', 'turnover', 'market_val', 'pe_ratio', 'listing_date']
    
    for col in priority_cols:
        if col in all_columns:
            display_columns.append(col)
    
    # 如果没有找到优先列，显示前10列
    if not display_columns:
        display_columns = all_columns[:10]
    
    print(df[display_columns].head(n).to_string())
    print("="*80)


def main():
    """主函数"""
    print("="*80)
    print("富途API - 美股数据获取工具")
    print("="*80)
    
    # 创建数据获取器
    fetcher = FutuUSStockFetcher()
    
    try:
        # 连接到FutuOpenD
        if not fetcher.connect():
            return
        
        # 获取所有美股数据
        print("\n开始获取美股数据...")
        df = fetcher.fetch_all_us_stocks_with_quotes()
        
        if not df.empty:
            # 显示样本数据
            print_sample_data(df)
            
            # 显示数据统计
            print("\n数据统计:")
            print(f"  总股票数: {len(df)}")
            if 'stock_type' in df.columns:
                print(f"\n  按类型统计:")
                type_counts = df['stock_type'].value_counts()
                for stock_type, count in type_counts.items():
                    print(f"    {stock_type}: {count}")
            
            # 保存到CSV
            fetcher.save_to_csv(df)
            
            print("\n" + "="*80)
            print("✓ 所有任务完成！")
            print("="*80)
        else:
            print("\n✗ 未获取到任何数据")
            
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 断开连接
        fetcher.disconnect()


if __name__ == "__main__":
    main()

