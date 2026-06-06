#!/usr/bin/env python3
"""
美股反包检测器演示脚本
展示如何使用反包检测器进行股票筛选
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.equity import USStockReversalDetector


def demo_basic_usage():
    """演示 1: 基本用法"""
    print("="*80)
    print("演示 1: 基本反包检测")
    print("="*80)
    
    # 创建检测器
    detector = USStockReversalDetector()
    
    # 运行检测
    results = detector.run_reversal_detection()
    
    if not results.empty:
        print(f"\n✓ 找到 {len(results)} 只符合反包条件的股票")
    else:
        print("\n未找到符合条件的股票")


def demo_custom_filtering():
    """演示 2: 自定义筛选"""
    print("\n" + "="*80)
    print("演示 2: 自定义筛选条件")
    print("="*80)
    
    detector = USStockReversalDetector()
    results = detector.run_reversal_detection()
    
    if results.empty:
        print("\n没有基础反包数据，跳过演示")
        return
    
    # 筛选条件 1: 价格在 10-100 美元之间
    price_filtered = results[
        (results['close_t1'] >= 10) &
        (results['close_t1'] <= 100)
    ]
    print(f"\n价格在 $10-$100 之间: {len(price_filtered)} 只")
    
    # 筛选条件 2: 成交量增幅超过 50%
    volume_filtered = results[
        results['volume_increase_pct'] >= 50
    ]
    print(f"成交量增幅 >= 50%: {len(volume_filtered)} 只")
    
    # 筛选条件 3: 综合条件
    quality_stocks = results[
        (results['close_t1'] >= 10) &
        (results['close_t1'] <= 100) &
        (results['volume_increase_pct'] >= 50) &
        (results['t1_change_pct'] >= 3)  # T-1 涨幅 >= 3%
    ]
    
    print(f"\n高质量反包股票（综合条件）: {len(quality_stocks)} 只")
    
    if not quality_stocks.empty:
        print("\n详细信息（前 5 只）:")
        for idx, row in quality_stocks.head(5).iterrows():
            print(f"\n{row['symbol']:6s} - 当前价格: ${row['close_t1']:.2f}")
            print(f"  T-2: ${row['open_t2']:.2f} → ${row['close_t2']:.2f} ({row['t2_change_pct']:+.2f}%)")
            print(f"  T-1: ${row['open_t1']:.2f} → ${row['close_t1']:.2f} ({row['t1_change_pct']:+.2f}%)")
            print(f"  成交量增幅: {row['volume_increase_pct']:+.1f}%")


def demo_manual_detection():
    """演示 3: 手动指定日期检测"""
    print("\n" + "="*80)
    print("演示 3: 手动指定日期检测")
    print("="*80)
    
    detector = USStockReversalDetector()
    
    # 获取日期
    t1_date = detector.get_trading_date(1)  # 昨天
    t2_date = detector.get_trading_date(2)  # 前天
    
    print(f"\n检测日期:")
    print(f"  T-2 (前天): {t2_date}")
    print(f"  T-1 (昨天): {t1_date}")
    
    # 确保数据可用
    print(f"\n获取数据...")
    data_dict = detector.ensure_data_available([t2_date, t1_date])
    
    if len(data_dict) == 2:
        # 手动检测
        print(f"\n执行反包检测...")
        results = detector.detect_reversal_pattern(
            df_t2=data_dict[t2_date],
            df_t1=data_dict[t1_date]
        )
        
        print(f"✓ 检测完成，找到 {len(results)} 只股票")
    else:
        print("✗ 数据不完整，无法检测")


def demo_data_management():
    """演示 4: 数据管理"""
    print("\n" + "="*80)
    print("演示 4: 数据管理")
    print("="*80)
    
    detector = USStockReversalDetector()
    
    # 查看已有的数据
    existing_sheets = detector.get_existing_sheets()
    
    print(f"\n历史数据文件: {detector.history_file}")
    print(f"已有数据 sheets: {len(existing_sheets)}")
    
    if existing_sheets:
        print(f"\n最近的 5 个日期:")
        for date in existing_sheets[-5:]:
            df = detector.load_daily_data(date)
            if df is not None:
                print(f"  {date}: {len(df)} 条记录")
    
    # 演示数据获取
    print(f"\n测试数据获取功能...")
    dates_to_check = [
        detector.get_trading_date(1),
        detector.get_trading_date(2),
    ]
    
    data_dict = detector.ensure_data_available(dates_to_check)
    
    print(f"\n数据获取结果:")
    for date, df in data_dict.items():
        print(f"  {date}: {len(df)} 条记录")


def demo_result_analysis():
    """演示 5: 结果分析"""
    print("\n" + "="*80)
    print("演示 5: 结果分析与统计")
    print("="*80)
    
    detector = USStockReversalDetector()
    results = detector.run_reversal_detection()
    
    if results.empty:
        print("\n没有检测结果，跳过演示")
        return
    
    # 统计信息
    print(f"\n统计信息:")
    print(f"  总数量: {len(results)}")
    print(f"  平均成交量增幅: {results['volume_increase_pct'].mean():.2f}%")
    print(f"  平均 T-1 涨幅: {results['t1_change_pct'].mean():.2f}%")
    print(f"  平均 T-2 跌幅: {results['t2_change_pct'].mean():.2f}%")
    print(f"  平均反包强度: ${results['reversal_strength'].mean():.2f}")
    
    # 价格分布
    print(f"\n价格分布:")
    price_ranges = [
        (0, 10, "$0-10"),
        (10, 50, "$10-50"),
        (50, 100, "$50-100"),
        (100, 500, "$100-500"),
        (500, float('inf'), "$500+")
    ]
    
    for min_price, max_price, label in price_ranges:
        count = len(results[(results['close_t1'] >= min_price) & (results['close_t1'] < max_price)])
        pct = (count / len(results)) * 100 if len(results) > 0 else 0
        print(f"  {label:10s}: {count:3d} ({pct:5.1f}%)")
    
    # 成交量增幅分布
    print(f"\n成交量增幅分布:")
    volume_ranges = [
        (0, 50, "0-50%"),
        (50, 100, "50-100%"),
        (100, 200, "100-200%"),
        (200, float('inf'), "200%+")
    ]
    
    for min_vol, max_vol, label in volume_ranges:
        count = len(results[(results['volume_increase_pct'] >= min_vol) & (results['volume_increase_pct'] < max_vol)])
        pct = (count / len(results)) * 100 if len(results) > 0 else 0
        print(f"  {label:10s}: {count:3d} ({pct:5.1f}%)")


def main():
    """主函数 - 运行所有演示"""
    print("\n" + "🚀"*40)
    print("美股反包检测器 - 完整演示")
    print("🚀"*40)
    
    try:
        # 运行所有演示
        demo_basic_usage()
        demo_custom_filtering()
        demo_manual_detection()
        demo_data_management()
        demo_result_analysis()
        
        print("\n" + "🎉"*40)
        print("所有演示完成！")
        print("🎉"*40)
        
        print("\n📚 更多信息:")
        print("  - 详细文档: src/equity/README_REVERSAL.md")
        print("  - 快速指南: 反包检测器使用说明.md")
        print("  - 完成总结: 反包检测器_完成总结.md")
        
    except ValueError as e:
        print(f"\n✗ 配置错误: {e}")
        print("\n请先设置 Polygon.io API 密钥:")
        print("1. 在项目根目录创建 .env 文件")
        print("2. 添加以下内容:")
        print("   POLYGON_KEY=your-api-key-here")
        print("\n获取 API 密钥: https://polygon.io/dashboard/api-keys")
    
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

