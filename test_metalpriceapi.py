#!/usr/bin/env python3
"""
MetalPriceAPI 数据获取器测试脚本
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from src.metal.metalpriceapi_fetcher import MetalPriceAPIFetcher
import pandas as pd

# 设置pandas显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


def test_single_ohlc():
    """测试获取单个日期的OHLC数据"""
    print("\n" + "="*80)
    print("测试1: 获取单个日期的OHLC数据")
    print("="*80)
    
    fetcher = MetalPriceAPIFetcher()
    
    # 测试获取今天的黄金数据
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n获取 XAU/USD {today} 的OHLC数据...")
    
    ohlc = fetcher.get_ohlc('XAU', 'USD', today)
    
    if ohlc:
        print(f"\n✓ 成功获取数据:")
        print(f"  商品: {ohlc['base']}/{ohlc['quote']}")
        print(f"  时间戳: {ohlc['timestamp']}")
        rate = ohlc['rate']
        print(f"  开盘价: ${rate['open']:.2f}")
        print(f"  最高价: ${rate['high']:.2f}")
        print(f"  最低价: ${rate['low']:.2f}")
        print(f"  收盘价: ${rate['close']:.2f}")
    else:
        print("✗ 获取数据失败")


def test_multiple_days():
    """测试获取多天的OHLC数据"""
    print("\n" + "="*80)
    print("测试2: 获取多天的OHLC数据")
    print("="*80)
    
    fetcher = MetalPriceAPIFetcher()
    
    # 获取最近5天的黄金数据
    print("\n获取 XAU/USD 最近5天的OHLC数据...")
    
    df = fetcher.get_klines('XAU', 'USD', days=5)
    
    if not df.empty:
        print(f"\n✓ 成功获取 {len(df)} 条数据")
        print(f"\n数据预览:")
        print(df[['symbol', 'timestamp', 'open', 'high', 'low', 'close']].to_string(index=False))
        
        print(f"\n数据统计:")
        print(f"  记录数: {len(df)}")
        print(f"  日期范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
        print(f"  最新收盘价: ${df['close'].iloc[-1]:.2f}")
        print(f"  最高价: ${df['high'].max():.2f}")
        print(f"  最低价: ${df['low'].min():.2f}")
    else:
        print("✗ 获取数据失败")


def test_date_range():
    """测试使用日期范围获取数据"""
    print("\n" + "="*80)
    print("测试3: 使用日期范围获取数据")
    print("="*80)
    
    fetcher = MetalPriceAPIFetcher()
    
    # 获取指定日期范围的数据
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d')
    
    print(f"\n获取 XAU/USD {start_date} 至 {end_date} 的OHLC数据...")
    
    df = fetcher.get_klines('XAU', 'USD', start_date=start_date, end_date=end_date)
    
    if not df.empty:
        print(f"\n✓ 成功获取 {len(df)} 条数据")
        print(f"\n数据预览:")
        print(df[['symbol', 'timestamp', 'open', 'high', 'low', 'close']].to_string(index=False))
    else:
        print("✗ 获取数据失败")


def test_multiple_metals():
    """测试批量获取多个贵金属数据"""
    print("\n" + "="*80)
    print("测试4: 批量获取多个贵金属数据")
    print("="*80)
    
    fetcher = MetalPriceAPIFetcher()
    
    # 获取黄金和白银的数据
    metals = ['XAU', 'XAG']
    print(f"\n批量获取 {', '.join(metals)} 的OHLC数据...")
    
    results = fetcher.get_multiple_metals(metals, currency='USD', days=5)
    
    for metal, df in results.items():
        if not df.empty:
            print(f"\n{metal}/USD 数据:")
            print(f"  记录数: {len(df)}")
            print(f"  最新收盘价: ${df['close'].iloc[-1]:.2f}")
            print(f"  最高价: ${df['high'].max():.2f}")
            print(f"  最低价: ${df['low'].min():.2f}")


def test_silver():
    """测试获取白银数据"""
    print("\n" + "="*80)
    print("测试5: 获取白银(XAG)数据")
    print("="*80)
    
    fetcher = MetalPriceAPIFetcher()
    
    print("\n获取 XAG/USD 最近5天的OHLC数据...")
    
    df = fetcher.get_klines('XAG', 'USD', days=5)
    
    if not df.empty:
        print(f"\n✓ 成功获取 {len(df)} 条数据")
        print(f"\n数据预览:")
        print(df[['symbol', 'timestamp', 'open', 'high', 'low', 'close']].to_string(index=False))
    else:
        print("✗ 获取数据失败")


def main():
    """主函数"""
    print("="*80)
    print("MetalPriceAPI 数据获取器测试")
    print("="*80)
    
    try:
        # 测试1: 单个日期
        test_single_ohlc()
        
        # 测试2: 多天数据
        test_multiple_days()
        
        # 测试3: 日期范围
        test_date_range()
        
        # 测试4: 多个贵金属
        test_multiple_metals()
        
        # 测试5: 白银
        test_silver()
        
        print("\n" + "="*80)
        print("测试完成")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
