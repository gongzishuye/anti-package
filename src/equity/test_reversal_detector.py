#!/usr/bin/env python3
"""
反包检测器测试脚本
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.equity.us_stock_reversal_detector import USStockReversalDetector


def test_reversal_detection():
    """测试反包检测功能"""
    print("="*80)
    print("美股反包检测器测试")
    print("="*80)
    
    try:
        # 创建检测器
        print("\n1. 初始化反包检测器...")
        detector = USStockReversalDetector()
        
        print(f"   ✓ 数据目录: {detector.data_dir}")
        print(f"   ✓ 历史文件: {detector.history_file}")
        
        # 运行反包检测
        print("\n2. 运行反包检测...")
        results = detector.run_reversal_detection()
        
        # 显示结果
        if not results.empty:
            print(f"\n3. 检测结果:")
            print(f"   ✓ 符合条件股票: {len(results)} 只")
            
            # 显示详细数据
            print("\n   前 5 名详情:")
            display_cols = [
                'symbol', 
                'open_t2', 'close_t2', 't2_change_pct', 'volume_t2',
                'open_t1', 'close_t1', 't1_change_pct', 'volume_t1',
                'volume_increase_pct', 'reversal_strength'
            ]
            
            available_cols = [col for col in display_cols if col in results.columns]
            print(results[available_cols].head().to_string(index=False))
            
            print(f"\n   结果已保存到:")
            print(f"   {detector.data_dir / 'us_stock_reversal_results.xlsx'}")
        else:
            print("\n3. 未找到符合反包条件的股票")
        
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


def test_date_calculation():
    """测试日期计算功能"""
    print("\n" + "="*80)
    print("测试日期计算")
    print("="*80)
    
    try:
        detector = USStockReversalDetector()
        
        today = detector.get_trading_date(0)
        t1 = detector.get_trading_date(1)
        t2 = detector.get_trading_date(2)
        
        print(f"\n今天 (T):   {today}")
        print(f"昨天 (T-1): {t1}")
        print(f"前天 (T-2): {t2}")
        
        print("\n✓ 日期计算正常")
        
    except Exception as e:
        print(f"✗ 日期计算失败: {e}")


def test_data_management():
    """测试数据管理功能"""
    print("\n" + "="*80)
    print("测试数据管理")
    print("="*80)
    
    try:
        detector = USStockReversalDetector()
        
        # 检查现有 sheets
        existing_sheets = detector.get_existing_sheets()
        print(f"\n已有的数据 sheets: {len(existing_sheets)}")
        if existing_sheets:
            print(f"日期: {', '.join(existing_sheets[-5:])}")  # 显示最近5个
        
        # 测试数据获取
        print("\n测试获取最近 2 个交易日的数据...")
        t1 = detector.get_trading_date(1)
        t2 = detector.get_trading_date(2)
        
        data_dict = detector.ensure_data_available([t2, t1])
        
        for date, df in data_dict.items():
            print(f"  {date}: {len(df)} 条记录")
        
        print("\n✓ 数据管理测试完成")
        
    except Exception as e:
        print(f"✗ 数据管理测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行所有测试
    test_date_calculation()
    test_data_management()
    test_reversal_detection()

