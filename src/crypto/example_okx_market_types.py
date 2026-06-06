#!/usr/bin/env python3
"""
OKX数据获取器市场类型示例
演示如何使用OKXDataFetcher获取现货和合约数据
"""

from okx_data_fetcher import OKXDataFetcher
import pandas as pd
from datetime import datetime

def main():
    """演示OKX数据获取器的现货和合约功能"""
    
    print("="*80)
    print("OKX数据获取器 - 现货&合约功能演示")
    print("="*80)
    
    # 1. 现货数据获取
    print("\n📈 获取现货数据...")
    spot_fetcher = OKXDataFetcher(market_type='spot')
    
    # 获取前10个现货交易对
    spot_symbols = spot_fetcher.get_top_n_tokens('USDT', 10)
    print(f"现货前10个交易对: {spot_symbols[:5]}...")  # 显示前5个
    
    # 获取现货K线数据
    if spot_symbols:
        spot_df = spot_fetcher.fetch_top_n_daily_data(
            days=5, 
            top_n=3, 
            interval='1d'
        )
        print(f"现货K线数据: {len(spot_df)} 条记录，涵盖 {spot_df['symbol'].nunique()} 个交易对")
    
    # 2. 合约数据获取
    print("\n📊 获取合约数据...")
    futures_fetcher = OKXDataFetcher(market_type='futures')
    
    # 获取前10个合约交易对
    futures_symbols = futures_fetcher.get_top_n_tokens('USDT', 10)
    print(f"合约前10个交易对: {futures_symbols[:5]}...")  # 显示前5个
    
    # 获取合约K线数据
    if futures_symbols:
        futures_df = futures_fetcher.fetch_top_n_daily_data(
            days=5, 
            top_n=3, 
            interval='1d'
        )
        print(f"合约K线数据: {len(futures_df)} 条记录，涵盖 {futures_df['symbol'].nunique()} 个交易对")
    
    # 3. 数据对比
    print("\n🔍 数据对比分析...")
    if not spot_df.empty and not futures_df.empty:
        print(f"现货数据列: {spot_df.columns.tolist()}")
        print(f"合约数据列: {futures_df.columns.tolist()}")
        print(f"数据格式一致性: {list(spot_df.columns) == list(futures_df.columns)}")
        
        # 显示最新的价格数据
        print("\n最新价格对比:")
        for symbol in spot_df['symbol'].unique()[:3]:
            spot_latest = spot_df[spot_df['symbol'] == symbol].iloc[-1]
            print(f"现货 {symbol}: ${spot_latest['close']:.4f}")
        
        for symbol in futures_df['symbol'].unique()[:3]:
            futures_latest = futures_df[futures_df['symbol'] == symbol].iloc[-1]
            print(f"合约 {symbol}: ${futures_latest['close']:.4f}")
    
    # 4. 保存数据示例
    print("\n💾 保存数据示例...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if not spot_df.empty:
        spot_filename = f'okx_spot_top3_daily_{timestamp}.csv'
        spot_fetcher.save_to_csv(spot_df, spot_filename)
        print(f"现货数据已保存: {spot_filename}")
    
    if not futures_df.empty:
        futures_filename = f'okx_futures_top3_daily_{timestamp}.csv'
        futures_fetcher.save_to_csv(futures_df, futures_filename)
        print(f"合约数据已保存: {futures_filename}")
    
    print("\n" + "="*80)
    print("✅ OKX数据获取器演示完成")
    print("="*80)
    print("功能特点:")
    print("  - 支持现货和合约数据获取")
    print("  - 统一的API接口，与BinanceDataFetcher兼容")
    print("  - 自动文件名前缀区分（现货/合约）")
    print("  - 完整的数据格式兼容性")
    print("="*80)

if __name__ == "__main__":
    main()
