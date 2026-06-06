#!/usr/bin/env python3
"""
币安数据获取器使用示例 - 现货vs合约数据对比
"""

from binance_data_fetcher import BinanceDataFetcher
import pandas as pd

def compare_spot_vs_futures():
    """对比现货和合约数据的差异"""
    
    print("="*80)
    print("币安现货 vs 合约数据对比示例")
    print("="*80)
    
    # 创建现货数据获取器
    spot_fetcher = BinanceDataFetcher(market_type='spot')
    
    # 创建合约数据获取器
    futures_fetcher = BinanceDataFetcher(market_type='futures')
    
    print("\n1. 获取Top5现货交易对:")
    spot_symbols = spot_fetcher.get_top_n_tokens(top_n=5)
    print(f"现货Top5: {spot_symbols}")
    
    print("\n2. 获取Top5合约交易对:")
    futures_symbols = futures_fetcher.get_top_n_tokens(top_n=5)
    print(f"合约Top5: {futures_symbols}")
    
    print("\n3. 对比分析:")
    print(f"现货独有: {set(spot_symbols) - set(futures_symbols)}")
    print(f"合约独有: {set(futures_symbols) - set(spot_symbols)}")
    print(f"共同交易对: {set(spot_symbols) & set(futures_symbols)}")
    
    # 获取BTCUSDT的现货和合约数据对比
    common_symbols = set(spot_symbols) & set(futures_symbols)
    if common_symbols:
        test_symbol = list(common_symbols)[0]
        print(f"\n4. {test_symbol} 现货vs合约K线数据对比:")
        
        # 获取现货数据
        spot_data = spot_fetcher.get_klines(test_symbol, days=3, interval='1d')
        # 获取合约数据
        futures_data = futures_fetcher.get_klines(test_symbol, days=3, interval='1d')
        
        if not spot_data.empty and not futures_data.empty:
            print(f"\n现货数据 ({len(spot_data)}条):")
            print(spot_data[['timestamp', 'close', 'volume', 'quote_asset_volume']].head())
            
            print(f"\n合约数据 ({len(futures_data)}条):")
            print(futures_data[['timestamp', 'close', 'volume', 'quote_asset_volume']].head())
            
            # 计算价格差异
            spot_close = spot_data['close'].iloc[-1]
            futures_close = futures_data['close'].iloc[-1]
            price_diff = futures_close - spot_close
            price_diff_pct = (price_diff / spot_close) * 100
            
            print(f"\n价格对比 (最新收盘价):")
            print(f"现货价格: ${spot_close:.4f}")
            print(f"合约价格: ${futures_close:.4f}")
            print(f"价差: ${price_diff:.4f} ({price_diff_pct:+.4f}%)")
            
            # 计算成交量对比
            spot_volume = spot_data['quote_asset_volume'].sum()
            futures_volume = futures_data['quote_asset_volume'].sum()
            
            print(f"\n成交量对比 (3日总和):")
            print(f"现货USDT成交量: ${spot_volume:,.0f}")
            print(f"合约USDT成交量: ${futures_volume:,.0f}")
            print(f"合约/现货成交量比: {futures_volume/spot_volume:.2f}x")

def demo_market_type_usage():
    """演示不同市场类型的使用方法"""
    
    print("\n" + "="*80)
    print("市场类型使用示例")
    print("="*80)
    
    # 示例1: 默认现货
    print("\n示例1: 默认现货数据")
    fetcher1 = BinanceDataFetcher()  # 默认为现货
    symbols1 = fetcher1.get_top_n_tokens(top_n=3)
    print(f"默认(现货)Top3: {symbols1}")
    
    # 示例2: 明确指定现货
    print("\n示例2: 明确指定现货数据")
    fetcher2 = BinanceDataFetcher(market_type='spot')
    symbols2 = fetcher2.get_top_n_tokens(top_n=3)
    print(f"现货Top3: {symbols2}")
    
    # 示例3: 合约数据
    print("\n示例3: 合约数据")
    fetcher3 = BinanceDataFetcher(market_type='futures')
    symbols3 = fetcher3.get_top_n_tokens(top_n=3)
    print(f"合约Top3: {symbols3}")
    
    # 示例4: 批量获取数据
    print("\n示例4: 批量获取不同市场数据")
    markets = ['spot', 'futures']
    
    for market in markets:
        fetcher = BinanceDataFetcher(market_type=market)
        data = fetcher.fetch_top_n_daily_data(days=2, top_n=2, delay=0.1)
        
        if not data.empty:
            market_name = "合约" if market == 'futures' else "现货"
            print(f"\n{market_name}数据统计:")
            print(f"  交易对数量: {data['symbol'].nunique()}")
            print(f"  总记录数: {len(data)}")
            print(f"  交易对列表: {data['symbol'].unique().tolist()}")
            
            # 保存数据
            filename = fetcher.save_to_csv(data)
            print(f"  数据已保存到: {filename}")

if __name__ == "__main__":
    try:
        # 运行对比分析
        compare_spot_vs_futures()
        
        # 运行使用示例
        demo_market_type_usage()
        
        print("\n" + "="*80)
        print("示例运行完成！")
        print("="*80)
        
    except Exception as e:
        print(f"运行示例时出错: {e}")
        import traceback
        traceback.print_exc()
