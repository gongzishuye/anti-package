#!/usr/bin/env python3
"""
K线数据获取使用示例
展示如何获取不同周期的K线数据
"""

from binance_data_fetcher import BinanceDataFetcher

def example_1d_kline():
    """示例1: 获取1日K线（默认）"""
    print("\n" + "="*70)
    print("示例1: 获取1日K线")
    print("="*70)
    
    fetcher = BinanceDataFetcher()
    
    # 获取单个币种的1日K线
    df = fetcher.get_klines('BTCUSDT', days=30, interval='1d')
    
    if not df.empty:
        print(f"✓ 获取到 {len(df)} 根1日K线")
        print("\n最近5根K线:")
        print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())


def example_3d_kline():
    """示例2: 获取3日K线（币安原生支持）"""
    print("\n" + "="*70)
    print("示例2: 获取3日K线（币安原生支持）")
    print("="*70)
    
    fetcher = BinanceDataFetcher()
    
    # 获取3日K线
    df = fetcher.get_klines('BTCUSDT', days=90, interval='3d')
    
    if not df.empty:
        print(f"✓ 获取到 {len(df)} 根3日K线")
        print("\n最近5根K线:")
        print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())


def example_2d_aggregated():
    """示例3: 创建2日K线（通过聚合）"""
    print("\n" + "="*70)
    print("示例3: 创建2日K线（通过聚合1日K线）")
    print("="*70)
    
    fetcher = BinanceDataFetcher()
    
    # 先获取1日K线
    df_1d = fetcher.get_klines('BTCUSDT', days=30, interval='1d')
    print(f"✓ 获取到 {len(df_1d)} 根1日K线")
    
    # 聚合为2日K线
    df_2d = fetcher.aggregate_to_n_days(df_1d, n_days=2)
    print(f"✓ 聚合为 {len(df_2d)} 根2日K线")
    
    print("\n2日K线数据:")
    print(df_2d[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())


def example_5d_aggregated():
    """示例4: 创建5日K线（通过聚合）"""
    print("\n" + "="*70)
    print("示例4: 创建5日K线（通过聚合1日K线）")
    print("="*70)
    
    fetcher = BinanceDataFetcher()
    
    # 先获取1日K线
    df_1d = fetcher.get_klines('BTCUSDT', days=60, interval='1d')
    print(f"✓ 获取到 {len(df_1d)} 根1日K线")
    
    # 聚合为5日K线
    df_5d = fetcher.aggregate_to_n_days(df_1d, n_days=5)
    print(f"✓ 聚合为 {len(df_5d)} 根5日K线")
    
    print("\n5日K线数据:")
    print(df_5d[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())


def example_week_kline():
    """示例5: 获取周K线"""
    print("\n" + "="*70)
    print("示例5: 获取周K线")
    print("="*70)
    
    fetcher = BinanceDataFetcher()
    
    # 获取周K线
    df = fetcher.get_klines('BTCUSDT', days=180, interval='1w')
    
    if not df.empty:
        print(f"✓ 获取到 {len(df)} 根周K线")
        print("\n最近5根周K线:")
        print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())


def example_4h_kline():
    """示例6: 获取4小时K线"""
    print("\n" + "="*70)
    print("示例6: 获取4小时K线")
    print("="*70)
    
    fetcher = BinanceDataFetcher()
    
    # 获取4小时K线
    df = fetcher.get_klines('BTCUSDT', days=30, interval='4h')
    
    if not df.empty:
        print(f"✓ 获取到 {len(df)} 根4小时K线")
        print("\n最近5根K线:")
        print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())


def example_top100_with_2d():
    """示例7: 获取前100代币的2日K线"""
    print("\n" + "="*70)
    print("示例7: 获取前100代币的2日K线（使用聚合功能）")
    print("="*70)
    
    fetcher = BinanceDataFetcher()
    
    # 获取前10个代币的2日K线（为了快速演示，这里只获取前10个）
    df = fetcher.fetch_top_n_daily_data(
        days=16,
        delay=0.2,
        top_n=10,           # 演示用，实际可设为100
        interval='1d',      # 使用1日K线
        aggregate_days=2    # 聚合为2日K线
    )
    
    if not df.empty:
        print(f"\n✓ 总共获取到 {len(df)} 根2日K线")
        print(f"✓ 涵盖 {df['symbol'].nunique()} 个代币")
        
        # 保存数据
        filename = fetcher.save_to_csv(df, 'top10_2day_klines.csv')
        print(f"✓ 数据已保存: {filename}")


def example_top100_with_3d():
    """示例8: 获取前100代币的3日K线"""
    print("\n" + "="*70)
    print("示例8: 获取前100代币的3日K线（币安原生支持）")
    print("="*70)
    
    fetcher = BinanceDataFetcher()
    
    # 获取前10个代币的3日K线
    df = fetcher.fetch_top_n_daily_data(
        days=30,
        delay=0.2,
        top_n=10,      # 演示用
        interval='3d'  # 直接使用3日K线
    )
    
    if not df.empty:
        print(f"\n✓ 总共获取到 {len(df)} 根3日K线")
        print(f"✓ 涵盖 {df['symbol'].nunique()} 个代币")
        
        # 保存数据
        filename = fetcher.save_to_csv(df, 'top10_3day_klines.csv')
        print(f"✓ 数据已保存: {filename}")


def main():
    """主函数"""
    print("="*70)
    print("K线数据获取示例")
    print("="*70)
    print("\n请选择示例:")
    print("1. 获取1日K线")
    print("2. 获取3日K线（币安原生支持）")
    print("3. 创建2日K线（通过聚合）")
    print("4. 创建5日K线（通过聚合）")
    print("5. 获取周K线")
    print("6. 获取4小时K线")
    print("7. 获取前100代币的2日K线（演示版：前10个）")
    print("8. 获取前100代币的3日K线（演示版：前10个）")
    print("9. 查看所有支持的K线类型")
    print("0. 退出")
    
    try:
        choice = input("\n请输入选项 (0-9): ").strip()
        
        if choice == '1':
            example_1d_kline()
        elif choice == '2':
            example_3d_kline()
        elif choice == '3':
            example_2d_aggregated()
        elif choice == '4':
            example_5d_aggregated()
        elif choice == '5':
            example_week_kline()
        elif choice == '6':
            example_4h_kline()
        elif choice == '7':
            example_top100_with_2d()
        elif choice == '8':
            example_top100_with_3d()
        elif choice == '9':
            print("\n" + "="*70)
            print("币安支持的K线间隔类型")
            print("="*70)
            print("\n【分钟级别】")
            print("  1m, 3m, 5m, 15m, 30m")
            print("\n【小时级别】")
            print("  1h, 2h, 4h, 6h, 8h, 12h")
            print("\n【日/周/月级别】")
            print("  1d  - 1日（日K）")
            print("  3d  - 3日 ⭐")
            print("  1w  - 1周（周K）")
            print("  1M  - 1月（月K）")
            print("\n【通过聚合实现】")
            print("  2日、5日等任意天数 - 使用 aggregate_to_n_days() 方法")
            print("="*70)
        elif choice == '0':
            print("\n退出")
            return
        else:
            print("\n无效选项")
            
        print("\n" + "="*70)
        print("示例完成！")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

