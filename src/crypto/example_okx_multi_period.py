#!/usr/bin/env python3
"""
OKX多周期数据获取示例
演示如何使用okx_fetch_multi_period_data.py获取现货和合约数据
"""

from okx_fetch_multi_period_data import fetch_all_periods_data, save_to_excel, print_data_summary
import os

def main():
    """演示OKX多周期数据获取功能"""
    
    print("="*80)
    print("OKX多周期数据获取示例")
    print("="*80)
    
    # 示例1：获取现货数据
    print("\n📈 示例1：获取现货数据")
    print("-" * 50)
    
    spot_data = fetch_all_periods_data(
        top_n=5,
        days_for_daily=5,
        days_for_3d=5, 
        days_for_week=5,
        market_type='spot'
    )
    
    print_data_summary(spot_data)
    
    # 保存现货数据
    if any(not df.empty for df in spot_data.values()):
        spot_file = save_to_excel(spot_data, top_n=5, market_type='spot')
        print(f"现货数据已保存: {os.path.basename(spot_file)}")
    
    print("\n" + "="*80)
    
    # 示例2：获取合约数据
    print("\n📊 示例2：获取合约数据")
    print("-" * 50)
    
    futures_data = fetch_all_periods_data(
        top_n=5,
        days_for_daily=5,
        days_for_3d=5,
        days_for_week=5, 
        market_type='futures'
    )
    
    print_data_summary(futures_data)
    
    # 保存合约数据
    if any(not df.empty for df in futures_data.values()):
        futures_file = save_to_excel(futures_data, top_n=5, market_type='futures')
        print(f"合约数据已保存: {os.path.basename(futures_file)}")
    
    print("\n" + "="*80)
    print("✅ 示例完成")
    print("="*80)
    print("功能特点:")
    print("  - 支持现货和合约数据获取")
    print("  - 多周期数据（1日、3日、周K线）")
    print("  - 自动文件命名区分市场类型")
    print("  - 与Binance格式完全兼容")
    print("="*80)

if __name__ == "__main__":
    main()
