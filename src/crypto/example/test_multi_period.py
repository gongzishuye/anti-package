#!/usr/bin/env python3
"""
多周期K线数据获取测试版
快速测试功能（只获取前5个代币）
"""

from fetch_multi_period_data import fetch_all_periods_data, save_to_excel, print_data_summary

def main():
    """测试版主函数"""
    print("="*80)
    print("多周期K线数据获取 - 测试版")
    print("="*80)
    print()
    print("⚠ 这是测试版本，只获取前5个代币的数据")
    print()
    
    # 测试参数（只获取前5个）
    TOP_N = 5
    DAYS_1D = 16
    DAYS_3D = 30
    DAYS_WEEK = 180
    
    try:
        # 获取数据
        data_dict = fetch_all_periods_data(
            top_n=TOP_N,
            days_for_daily=DAYS_1D,
            days_for_3d=DAYS_3D,
            days_for_week=DAYS_WEEK
        )
        
        # 打印汇总
        print_data_summary(data_dict)
        
        # 保存到Excel
        excel_file = save_to_excel(data_dict, 'test_multi_period.xlsx')
        
        if excel_file:
            print()
            print("="*80)
            print("✓ 测试成功！")
            print("="*80)
            print()
            print("已生成测试文件: test_multi_period.xlsx")
            print()
            print("如需获取完整Top100数据，请运行:")
            print("  ./fetch_multi_period.sh")
            print("或")
            print("  python3 fetch_multi_period_data.py")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

