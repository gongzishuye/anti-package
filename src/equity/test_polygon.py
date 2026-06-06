#!/usr/bin/env python3
"""
Polygon.io API 测试脚本
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher


def test_daily_market_summary():
    """测试每日市场摘要 API"""
    print("="*80)
    print("测试 Polygon.io 每日市场摘要 API")
    print("="*80)
    
    try:
        # 创建获取器
        fetcher = PolygonUSStockFetcher()
        
        # 获取最近的交易日数据
        print("\n1. 获取最近一个交易日的数据...")
        df = fetcher.get_latest_market_summary(days_back=1)
        
        if not df.empty:
            print(f"✓ 成功获取 {len(df)} 只股票数据")
            fetcher.print_summary(df, top_n=5)
            
            # 保存数据
            fetcher.save_to_csv(df, data_dir='data/polygon')
            fetcher.save_to_excel(df, data_dir='data/polygon')
        else:
            print("✗ 未获取到数据")
        
        # 测试指定日期
        print("\n2. 测试指定日期...")
        test_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        df2 = fetcher.get_daily_market_summary(test_date)
        
        if not df2.empty:
            print(f"✓ {test_date} 数据获取成功，共 {len(df2)} 条记录")
        
        print("\n" + "="*80)
        print("✓ 测试完成！")
        print("="*80)
        
    except ValueError as e:
        print(f"\n✗ 配置错误: {e}")
        print("\n请先设置 Polygon.io API 密钥:")
        print("1. 在项目根目录创建 .env 文件")
        print("2. 添加以下内容:")
        print("   POLYGON_KEY=your-api-key-here")
        print("\n获取 API 密钥: https://polygon.io/dashboard/api-keys")
    
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_multi_day_summary():
    """测试多日数据获取"""
    print("\n" + "="*80)
    print("测试多日数据获取")
    print("="*80)
    
    try:
        fetcher = PolygonUSStockFetcher()
        
        # 获取最近 5 个交易日的数据
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        print(f"\n获取 {start_date} 至 {end_date} 的数据...")
        df = fetcher.get_multi_day_summary(start_date, end_date)
        
        if not df.empty:
            print(f"✓ 成功获取 {len(df)} 条记录")
            print(f"  日期范围: {df['date'].unique()}")
            
            # 按日期分组统计
            daily_stats = df.groupby('date').agg({
                'symbol': 'count',
                'volume': 'sum'
            }).rename(columns={'symbol': 'stock_count', 'volume': 'total_volume'})
            
            print("\n每日统计:")
            print(daily_stats.to_string())
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")


if __name__ == "__main__":
    # 测试每日市场摘要
    test_daily_market_summary()
    
    # 测试多日数据（可选，注释掉以节省 API 配额）
    # test_multi_day_summary()


