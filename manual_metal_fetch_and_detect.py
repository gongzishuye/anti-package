#!/usr/bin/env python3
"""
手动获取贵金属数据并执行反包检测
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from src.metal.metal_reversal_detector import MetalReversalDetector
import pandas as pd

def get_trading_date(days_back=0):
    """获取交易日日期（跳过周末）"""
    target_date = datetime.now()
    
    # 如果今天是周末，往回找最近的交易日
    while target_date.weekday() >= 5:
        target_date -= timedelta(days=1)
    
    # 再往前推 days_back 个交易日
    for _ in range(days_back):
        target_date -= timedelta(days=1)
        while target_date.weekday() >= 5:
            target_date -= timedelta(days=1)
    
    return target_date.strftime('%Y-%m-%d')


def main():
    print("="*80)
    print("手动获取贵金属数据并执行反包检测")
    print("="*80)
    
    # 创建检测器
    detector = MetalReversalDetector()
    
    # 获取T-1和T-2的日期
    t1_date = get_trading_date(1)  # 昨天
    t2_date = get_trading_date(2)  # 前天
    
    print(f"\n目标日期:")
    print(f"  T-1 (昨天): {t1_date}")
    print(f"  T-2 (前天): {t2_date}")
    
    # 确保数据可用
    print(f"\n检查并获取数据...")
    data_dict = detector.ensure_data_available([t2_date, t1_date])
    
    # 检查数据是否获取成功
    if t2_date not in data_dict:
        print(f"✗ T-2 ({t2_date}) 数据获取失败")
        return
    if t1_date not in data_dict:
        print(f"✗ T-1 ({t1_date}) 数据获取失败")
        return
    
    print(f"\n✓ 数据获取成功:")
    print(f"  T-2 ({t2_date}): {len(data_dict[t2_date])} 条记录")
    print(f"  T-1 ({t1_date}): {len(data_dict[t1_date])} 条记录")
    
    # 显示数据内容
    print(f"\nT-2 数据:")
    print(data_dict[t2_date][['symbol', 'open', 'high', 'low', 'close']].to_string(index=False))
    
    print(f"\nT-1 数据:")
    print(data_dict[t1_date][['symbol', 'open', 'high', 'low', 'close']].to_string(index=False))
    
    # 执行反包检测
    print(f"\n开始执行反包检测...")
    results = detector.run_reversal_detection()
    
    if not results.empty:
        print(f"\n✓ 反包检测完成，找到 {len(results)} 个符合条件的贵金属")
        print(f"\n反包结果:")
        print(results[['symbol', 'open_t2', 'close_t2', 'open_t1', 'close_t1', 
                      't2_change_pct', 't1_change_pct', 'price_change_increase_pct', 
                      'reversal_strength']].to_string(index=False))
    else:
        print(f"\n✓ 反包检测完成，未找到符合条件的贵金属")
    
    print("\n" + "="*80)
    print("任务完成")
    print("="*80)


if __name__ == "__main__":
    main()
