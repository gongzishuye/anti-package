#!/usr/bin/env python3
"""
富途API使用示例
展示各种常见的使用场景
"""

from futu_us_stock_fetcher import FutuUSStockFetcher
from futu import KLType
import pandas as pd


def example_1_get_all_stocks():
    """示例1: 获取所有美股股票列表"""
    print("\n" + "="*80)
    print("示例1: 获取所有美股股票列表")
    print("="*80)
    
    fetcher = FutuUSStockFetcher()
    fetcher.connect()
    
    # 获取所有股票
    df = fetcher.get_all_us_stocks()
    
    print(f"\n总共有 {len(df)} 只美股证券")
    print("\n前10条数据:")
    print(df.head(10))
    
    fetcher.disconnect()
    return df


def example_2_get_specific_stocks_quotes():
    """示例2: 获取指定股票的实时行情"""
    print("\n" + "="*80)
    print("示例2: 获取指定股票的实时行情")
    print("="*80)
    
    fetcher = FutuUSStockFetcher()
    fetcher.connect()
    
    # 科技股龙头
    tech_stocks = ['US.AAPL', 'US.MSFT', 'US.GOOGL', 'US.AMZN', 'US.TSLA', 
                   'US.META', 'US.NVDA', 'US.NFLX']
    
    print(f"\n获取科技股行情: {', '.join(tech_stocks)}")
    quotes_df = fetcher.get_stock_snapshot(tech_stocks)
    
    if not quotes_df.empty:
        # 显示关键信息
        display_cols = ['code', 'name', 'last_price', 'change_rate', 'volume', 
                       'turnover', 'market_val', 'pe_ratio']
        available_cols = [col for col in display_cols if col in quotes_df.columns]
        
        print("\n实时行情:")
        print(quotes_df[available_cols].to_string())
    
    fetcher.disconnect()
    return quotes_df


def example_3_get_kline_data():
    """示例3: 获取历史K线数据"""
    print("\n" + "="*80)
    print("示例3: 获取历史K线数据")
    print("="*80)
    
    fetcher = FutuUSStockFetcher()
    fetcher.connect()
    
    # 获取苹果股票最近30天的日K线
    stock_code = 'US.AAPL'
    print(f"\n获取 {stock_code} 最近30天的K线数据...")
    
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    kline_df = fetcher.get_stock_kline(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        ktype=KLType.K_DAY
    )
    
    if not kline_df.empty:
        print(f"\n获取到 {len(kline_df)} 条K线数据")
        print("\n最近5天:")
        print(kline_df.tail())
        
        # 计算简单统计
        if 'close' in kline_df.columns:
            print(f"\n价格统计:")
            print(f"  最高: ${kline_df['high'].max():.2f}")
            print(f"  最低: ${kline_df['low'].min():.2f}")
            print(f"  平均: ${kline_df['close'].mean():.2f}")
    
    fetcher.disconnect()
    return kline_df


def example_4_filter_and_analyze():
    """示例4: 筛选和分析股票"""
    print("\n" + "="*80)
    print("示例4: 筛选和分析股票")
    print("="*80)
    
    fetcher = FutuUSStockFetcher()
    fetcher.connect()
    
    # 获取所有股票及行情
    df = fetcher.fetch_all_us_stocks_with_quotes()
    
    if df.empty:
        print("未获取到数据")
        fetcher.disconnect()
        return
    
    print(f"\n总共 {len(df)} 只股票")
    
    # 筛选条件示例
    # 1. 只看主板股票（非ETF、权证）
    if 'stock_type' in df.columns:
        stocks_only = df[df['stock_type'] == 'STOCK']
        print(f"主板股票: {len(stocks_only)} 只")
        df = stocks_only
    
    # 2. 有涨跌幅数据的
    if 'change_rate' in df.columns:
        df_with_price = df[df['change_rate'].notna()]
        print(f"有行情数据: {len(df_with_price)} 只")
        
        # 3. 涨幅超过5%的
        gainers = df_with_price[df_with_price['change_rate'] > 5.0]
        print(f"\n今日涨幅>5%的股票: {len(gainers)} 只")
        
        if not gainers.empty:
            # 按涨幅排序
            gainers_sorted = gainers.sort_values('change_rate', ascending=False)
            
            # 显示前10名
            display_cols = ['code', 'name', 'last_price', 'change_rate', 'volume']
            available_cols = [col for col in display_cols if col in gainers_sorted.columns]
            
            print("\n涨幅前10名:")
            print(gainers_sorted[available_cols].head(10).to_string())
        
        # 4. 跌幅超过5%的
        losers = df_with_price[df_with_price['change_rate'] < -5.0]
        print(f"\n今日跌幅>5%的股票: {len(losers)} 只")
        
        if not losers.empty:
            losers_sorted = losers.sort_values('change_rate', ascending=True)
            
            display_cols = ['code', 'name', 'last_price', 'change_rate', 'volume']
            available_cols = [col for col in display_cols if col in losers_sorted.columns]
            
            print("\n跌幅前10名:")
            print(losers_sorted[available_cols].head(10).to_string())
    
    fetcher.disconnect()
    return df


def example_5_save_different_formats():
    """示例5: 保存不同格式的数据"""
    print("\n" + "="*80)
    print("示例5: 保存不同格式的数据")
    print("="*80)
    
    fetcher = FutuUSStockFetcher()
    fetcher.connect()
    
    # 获取数据
    df = fetcher.get_all_us_stocks()
    
    if not df.empty:
        # 1. 保存完整数据
        fetcher.save_to_csv(df, 'us_stocks_full.csv')
        
        # 2. 只保存主板股票
        if 'stock_type' in df.columns:
            stocks_only = df[df['stock_type'] == 'STOCK']
            fetcher.save_to_csv(stocks_only, 'us_stocks_main_board.csv')
            print(f"✓ 主板股票已保存: {len(stocks_only)} 只")
        
        # 3. 只保存ETF
        if 'stock_type' in df.columns:
            etf_only = df[df['stock_type'] == 'ETF']
            fetcher.save_to_csv(etf_only, 'us_etf.csv')
            print(f"✓ ETF已保存: {len(etf_only)} 只")
        
        # 4. 保存特定列
        if 'code' in df.columns and 'name' in df.columns:
            simple_df = df[['code', 'name', 'stock_type', 'listing_date']]
            fetcher.save_to_csv(simple_df, 'us_stocks_simple.csv')
            print(f"✓ 简化数据已保存: {len(simple_df)} 只")
    
    fetcher.disconnect()


def main():
    """运行所有示例"""
    print("="*80)
    print("富途API使用示例集")
    print("="*80)
    print("\n请选择要运行的示例:")
    print("1. 获取所有美股股票列表")
    print("2. 获取指定股票的实时行情")
    print("3. 获取历史K线数据")
    print("4. 筛选和分析股票")
    print("5. 保存不同格式的数据")
    print("6. 运行所有示例")
    print("0. 退出")
    
    try:
        choice = input("\n请输入选项 (0-6): ").strip()
        
        if choice == '1':
            example_1_get_all_stocks()
        elif choice == '2':
            example_2_get_specific_stocks_quotes()
        elif choice == '3':
            example_3_get_kline_data()
        elif choice == '4':
            example_4_filter_and_analyze()
        elif choice == '5':
            example_5_save_different_formats()
        elif choice == '6':
            example_1_get_all_stocks()
            example_2_get_specific_stocks_quotes()
            example_3_get_kline_data()
            example_4_filter_and_analyze()
            example_5_save_different_formats()
        elif choice == '0':
            print("\n退出程序")
            return
        else:
            print("\n无效的选项")
            return
        
        print("\n" + "="*80)
        print("示例运行完成！")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

