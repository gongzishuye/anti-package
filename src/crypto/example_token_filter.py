#!/usr/bin/env python3
"""
Token筛选器使用示例
演示如何使用token_filter_multi_period.py进行Token筛选
"""

import os
import glob
from token_filter_multi_period import MultiPeriodTokenFilter, get_latest_excel_file

def main():
    """演示Token筛选器的各种使用方式"""
    
    print("="*80)
    print("Token筛选器使用示例")
    print("="*80)
    
    # 示例1：自动查找最新文件
    print("\n📁 示例1：自动查找最新文件")
    print("-" * 50)
    
    latest_file = get_latest_excel_file()
    if latest_file:
        print(f"自动找到的最新文件: {os.path.basename(latest_file)}")
        
        # 创建筛选器并执行筛选
        filter_tool = MultiPeriodTokenFilter(latest_file)
        results = filter_tool.filter_all_periods()
        
        # 打印摘要
        filter_tool.print_summary(results)
        
        # 保存结果
        output_file = filter_tool.save_results_to_excel(results)
        if output_file:
            print(f"\n筛选结果已保存: {os.path.basename(output_file)}")
    else:
        print("未找到任何Excel文件")
    
    print("\n" + "="*80)
    
    # 示例2：指定文件路径
    print("\n📂 示例2：指定文件路径")
    print("-" * 50)
    
    # 查找data目录下的所有Excel文件
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    excel_files = glob.glob(os.path.join(data_dir, "*_multi_period_*.xlsx"))
    
    if excel_files:
        # 选择第一个文件进行演示
        test_file = excel_files[0]
        print(f"使用指定文件: {os.path.basename(test_file)}")
        
        # 创建筛选器
        filter_tool = MultiPeriodTokenFilter(test_file)
        
        # 只筛选1日数据作为演示
        if '1日' in filter_tool.data_dict:
            print("\n筛选1日数据...")
            daily_results = filter_tool.filter_single_period(filter_tool.data_dict['1日'], '1日')
            
            print(f"\n1日筛选结果: 找到 {len(daily_results)} 个符合条件的Token")
            
            if daily_results:
                print("\n前5个Token:")
                for i, token in enumerate(daily_results[:5], 1):
                    symbol = token['symbol']
                    vol_growth = token['volume_growth_rate']
                    print(f"  {i}. {symbol} - 成交量增长: {vol_growth:.1f}%")
    else:
        print("data目录下没有找到Excel文件")
    
    print("\n" + "="*80)
    
    # 示例3：命令行使用说明
    print("\n💻 示例3：命令行使用方式")
    print("-" * 50)
    print("1. 自动模式（推荐）:")
    print("   python3 src/crypto/token_filter_multi_period.py --auto")
    print()
    print("2. 指定输入文件:")
    print("   python3 src/crypto/token_filter_multi_period.py --input /path/to/file.xlsx --auto")
    print()
    print("3. 交互模式:")
    print("   python3 src/crypto/token_filter_multi_period.py")
    print()
    print("4. 自定义输出文件名:")
    print("   python3 src/crypto/token_filter_multi_period.py --output my_results --auto")
    print()
    print("5. 查看帮助:")
    print("   python3 src/crypto/token_filter_multi_period.py --help")
    
    print("\n" + "="*80)
    print("✅ 示例完成")
    print("="*80)
    print("功能特点:")
    print("  - 支持自动查找最新文件")
    print("  - 支持指定输入文件路径")
    print("  - 支持自定义输出文件名")
    print("  - 支持自动模式和交互模式")
    print("  - 多周期数据筛选（1日、3日、周）")
    print("  - 智能筛选条件：成交量增长 + 技术形态")
    print("="*80)

if __name__ == "__main__":
    main()
