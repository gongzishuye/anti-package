#!/usr/bin/env python3
"""
Polygon.io API 使用示例集合
展示各种常见用例和高级功能
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher


def example_basic_usage():
    """示例 1: 基本用法"""
    print("="*80)
    print("示例 1: 基本用法 - 获取最近交易日数据")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        df = fetcher.get_latest_market_summary()
        
        if not df.empty:
            print(f"\n✓ 获取到 {len(df)} 只股票数据")
            print(f"\n前 5 条记录:")
            print(df[['symbol', 'open', 'high', 'low', 'close', 'volume']].head())
        
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_specific_date():
    """示例 2: 获取指定日期数据"""
    print("\n" + "="*80)
    print("示例 2: 获取指定日期数据")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        
        # 获取一周前的数据
        target_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        df = fetcher.get_daily_market_summary(target_date)
        
        if not df.empty:
            print(f"\n✓ {target_date} 数据: {len(df)} 只股票")
            
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_top_gainers():
    """示例 3: 找出涨幅最大的股票"""
    print("\n" + "="*80)
    print("示例 3: 涨幅排行榜")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        df = fetcher.get_latest_market_summary()
        
        if not df.empty:
            # 计算涨跌幅
            df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
            
            # 涨幅前 10 名
            gainers = df.nlargest(10, 'change_pct')
            
            print("\n涨幅前 10 名:")
            print(gainers[['symbol', 'open', 'close', 'volume', 'change_pct']].to_string(index=False))
            
            # 跌幅前 10 名
            losers = df.nsmallest(10, 'change_pct')
            
            print("\n跌幅前 10 名:")
            print(losers[['symbol', 'open', 'close', 'volume', 'change_pct']].to_string(index=False))
            
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_volume_analysis():
    """示例 4: 成交量分析"""
    print("\n" + "="*80)
    print("示例 4: 成交量分析")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        df = fetcher.get_latest_market_summary()
        
        if not df.empty:
            # 成交量统计
            print("\n成交量统计:")
            print(f"  总成交量: {df['volume'].sum():,.0f}")
            print(f"  平均成交量: {df['volume'].mean():,.0f}")
            print(f"  中位成交量: {df['volume'].median():,.0f}")
            print(f"  最大成交量: {df['volume'].max():,.0f}")
            
            # 成交量前 20 名
            top_volume = df.nlargest(20, 'volume')
            
            print("\n成交量前 20 名:")
            print(top_volume[['symbol', 'close', 'volume']].to_string(index=False))
            
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_price_range_analysis():
    """示例 5: 价格区间分析"""
    print("\n" + "="*80)
    print("示例 5: 价格区间分析")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        df = fetcher.get_latest_market_summary()
        
        if not df.empty:
            # 定义价格区间
            bins = [0, 10, 50, 100, 500, float('inf')]
            labels = ['$0-10', '$10-50', '$50-100', '$100-500', '$500+']
            
            df['price_range'] = pd.cut(df['close'], bins=bins, labels=labels)
            
            # 统计各价格区间
            price_dist = df['price_range'].value_counts().sort_index()
            
            print("\n价格区间分布:")
            for range_label, count in price_dist.items():
                pct = (count / len(df)) * 100
                print(f"  {range_label:10s}: {count:6d} ({pct:5.1f}%)")
            
            # 各区间平均涨幅
            df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
            avg_change = df.groupby('price_range')['change_pct'].mean()
            
            print("\n各价格区间平均涨跌幅:")
            for range_label, avg in avg_change.items():
                print(f"  {range_label:10s}: {avg:+6.2f}%")
            
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_stock_screening():
    """示例 6: 股票筛选"""
    print("\n" + "="*80)
    print("示例 6: 股票筛选策略")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        df = fetcher.get_latest_market_summary()
        
        if not df.empty:
            # 计算指标
            df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
            df['range_pct'] = ((df['high'] - df['low']) / df['low']) * 100
            
            # 筛选条件
            selected = df[
                (df['close'] >= 10) &                # 价格 >= $10
                (df['close'] <= 100) &               # 价格 <= $100
                (df['volume'] >= 1000000) &          # 成交量 >= 100万
                (df['change_pct'] >= 3) &            # 涨幅 >= 3%
                (df['change_pct'] <= 15) &           # 涨幅 <= 15%
                (df['range_pct'] >= 5)               # 波动 >= 5%
            ].sort_values('volume', ascending=False)
            
            print(f"\n筛选条件:")
            print(f"  - 价格: $10 - $100")
            print(f"  - 成交量: >= 100万")
            print(f"  - 涨幅: 3% - 15%")
            print(f"  - 波动: >= 5%")
            
            print(f"\n✓ 符合条件的股票: {len(selected)} 只")
            
            if len(selected) > 0:
                print("\n筛选结果（前 20 名）:")
                print(selected[['symbol', 'close', 'volume', 'change_pct', 'range_pct']].head(20).to_string(index=False))
                
                # 保存结果
                os.makedirs('data/screened', exist_ok=True)
                filename = f'data/screened/selected_{datetime.now().strftime("%Y%m%d")}.csv'
                selected.to_csv(filename, index=False)
                print(f"\n✓ 结果已保存: {filename}")
            
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_multi_day_analysis():
    """示例 7: 多日数据分析"""
    print("\n" + "="*80)
    print("示例 7: 多日数据趋势分析")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        
        # 获取最近 5 个交易日数据
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        print(f"\n获取 {start_date} 至 {end_date} 的数据...")
        df = fetcher.get_multi_day_summary(start_date, end_date)
        
        if not df.empty:
            # 按日期统计
            daily_stats = df.groupby('date').agg({
                'symbol': 'count',
                'volume': 'sum',
                'close': 'mean'
            }).rename(columns={
                'symbol': 'stock_count',
                'volume': 'total_volume',
                'close': 'avg_price'
            })
            
            print("\n每日市场统计:")
            print(daily_stats.to_string())
            
            # 找出连续上涨的股票
            df_sorted = df.sort_values(['symbol', 'date'])
            df_sorted['prev_close'] = df_sorted.groupby('symbol')['close'].shift(1)
            df_sorted['is_up'] = df_sorted['close'] > df_sorted['prev_close']
            
            # 统计每只股票的上涨天数
            up_days = df_sorted.groupby('symbol')['is_up'].sum()
            continuous_gainers = up_days[up_days == up_days.max()]
            
            print(f"\n连续上涨天数最多的股票（{up_days.max():.0f} 天）:")
            for symbol in continuous_gainers.index[:10]:
                stock_data = df[df['symbol'] == symbol].sort_values('date')
                print(f"  {symbol}: {stock_data[['date', 'close']].to_dict('records')}")
            
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_save_data():
    """示例 8: 数据保存"""
    print("\n" + "="*80)
    print("示例 8: 数据保存到文件")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        df = fetcher.get_latest_market_summary()
        
        if not df.empty:
            # 保存到 CSV
            fetcher.save_to_csv(df, data_dir='data/polygon')
            
            # 保存到 Excel
            fetcher.save_to_excel(df, data_dir='data/polygon')
            
            print("\n✓ 数据已保存到 data/polygon/ 目录")
            
    except Exception as e:
        print(f"✗ 错误: {e}")


def example_advanced_filtering():
    """示例 9: 高级筛选"""
    print("\n" + "="*80)
    print("示例 9: 高级筛选 - VWAP 分析")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        df = fetcher.get_latest_market_summary()
        
        if not df.empty and 'vwap' in df.columns:
            # 计算收盘价相对于 VWAP 的偏离
            df['vwap_deviation'] = ((df['close'] - df['vwap']) / df['vwap']) * 100
            
            # 找出偏离 VWAP 较大的股票（可能的交易机会）
            high_deviation = df[
                (df['volume'] >= df['volume'].median()) &
                (abs(df['vwap_deviation']) >= 2)
            ].sort_values('vwap_deviation', ascending=False)
            
            print("\n收盘价高于 VWAP 超过 2% 的股票:")
            above_vwap = high_deviation[high_deviation['vwap_deviation'] > 0].head(10)
            if len(above_vwap) > 0:
                print(above_vwap[['symbol', 'close', 'vwap', 'volume', 'vwap_deviation']].to_string(index=False))
            
            print("\n收盘价低于 VWAP 超过 2% 的股票:")
            below_vwap = high_deviation[high_deviation['vwap_deviation'] < 0].tail(10)
            if len(below_vwap) > 0:
                print(below_vwap[['symbol', 'close', 'vwap', 'volume', 'vwap_deviation']].to_string(index=False))
            
    except Exception as e:
        print(f"✗ 错误: {e}")


def main():
    """运行所有示例"""
    print("\n" + "🚀"*40)
    print("Polygon.io API 使用示例集合")
    print("🚀"*40)
    
    examples = [
        ("基本用法", example_basic_usage),
        ("指定日期", example_specific_date),
        ("涨跌排行", example_top_gainers),
        ("成交量分析", example_volume_analysis),
        ("价格区间", example_price_range_analysis),
        ("股票筛选", example_stock_screening),
        ("多日分析", example_multi_day_analysis),
        ("数据保存", example_save_data),
        ("高级筛选", example_advanced_filtering),
    ]
    
    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\n请选择要运行的示例（输入数字，或按 Enter 运行全部）:")
    choice = input("> ").strip()
    
    if choice.isdigit() and 1 <= int(choice) <= len(examples):
        # 运行选定的示例
        _, func = examples[int(choice) - 1]
        func()
    else:
        # 运行所有示例
        for name, func in examples:
            func()
    
    print("\n" + "🎉"*40)
    print("示例运行完成！")
    print("🎉"*40)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()






