#!/usr/bin/env python3
"""
获取不同周期的TopN OKX代币K线数据 - 兼容BN格式
将1日、3日、周K线数据保存到一个Excel文件的不同sheet中

数据保存位置: 项目根目录/data/
文件命名格式: okx_top{N}_multi_period_{timestamp}.xlsx
"""

import pandas as pd
from datetime import datetime
from okx_data_fetcher import OKXDataFetcher
import os
import glob


def fetch_all_periods_data(top_n: int = 100, days_for_daily: int = 16, days_for_2d: int = 20, days_for_3d: int = 30, days_for_5d: int = 25, days_for_week: int = 180, market_type: str = 'spot'):
    """
    获取不同周期的K线数据 - 支持OKX的2日和5日K线
    
    Args:
        top_n: 获取前N个代币
        days_for_daily: 1日K线获取天数
        days_for_2d: 2日K线获取天数
        days_for_3d: 3日K线获取天数
        days_for_5d: 5日K线获取天数
        days_for_week: 周K线获取天数
        market_type: 市场类型，'spot' 或 'futures'
        
    Returns:
        包含五个周期数据的字典
    """
    fetcher = OKXDataFetcher(market_type=market_type)
    results = {}
    
    market_name = "合约" if market_type == 'futures' else "现货"
    
    print("="*80)
    print(f"开始获取OKX Top {top_n} {market_name}代币的多周期K线数据")
    print("="*80)
    print()
    
    # 1. 获取1日K线数据
    print("【1/5】获取1日K线数据...")
    print("-"*80)
    df_1d = fetcher.fetch_top_n_daily_data(
        days=days_for_daily,
        delay=0.2,
        top_n=top_n,
        interval='1d'
    )
    results['1日'] = df_1d
    if not df_1d.empty:
        print(f"✓ 1日K线: {len(df_1d)} 条记录，{df_1d['symbol'].nunique()} 个代币")
    else:
        print("✗ 1日K线: 未获取到数据")
    print()
    
    # 2. 获取2日K线数据
    print("【2/5】获取2日K线数据...")
    print("-"*80)
    df_2d = fetcher.fetch_top_n_daily_data(
        days=days_for_2d,
        delay=0.2,
        top_n=top_n,
        interval='2d'
    )
    results['2日'] = df_2d
    if not df_2d.empty:
        print(f"✓ 2日K线: {len(df_2d)} 条记录，{df_2d['symbol'].nunique()} 个代币")
    else:
        print("✗ 2日K线: 未获取到数据")
    print()
    
    # 3. 获取3日K线数据
    print("【3/5】获取3日K线数据...")
    print("-"*80)
    df_3d = fetcher.fetch_top_n_daily_data(
        days=days_for_3d,
        delay=0.2,
        top_n=top_n,
        interval='3d'
    )
    results['3日'] = df_3d
    if not df_3d.empty:
        print(f"✓ 3日K线: {len(df_3d)} 条记录，{df_3d['symbol'].nunique()} 个代币")
    else:
        print("✗ 3日K线: 未获取到数据")
    print()
    
    # 4. 获取5日K线数据
    print("【4/5】获取5日K线数据...")
    print("-"*80)
    df_5d = fetcher.fetch_top_n_daily_data(
        days=days_for_5d,
        delay=0.2,
        top_n=top_n,
        interval='5d'
    )
    results['5日'] = df_5d
    if not df_5d.empty:
        print(f"✓ 5日K线: {len(df_5d)} 条记录，{df_5d['symbol'].nunique()} 个代币")
    else:
        print("✗ 5日K线: 未获取到数据")
    print()
    
    # 5. 获取周K线数据
    print("【5/5】获取周K线数据...")
    print("-"*80)
    df_week = fetcher.fetch_top_n_daily_data(
        days=days_for_week,
        delay=0.2,
        top_n=top_n,
        interval='1w'
    )
    results['周'] = df_week
    if not df_week.empty:
        print(f"✓ 周K线: {len(df_week)} 条记录，{df_week['symbol'].nunique()} 个代币")
    else:
        print("✗ 周K线: 未获取到数据")
    print()
    
    return results


def save_to_excel(data_dict: dict, filename: str = None, top_n: int = 100, market_type: str = 'spot'):
    """
    将多个DataFrame保存到Excel的不同sheet - 与BN格式保持一致
    
    Args:
        data_dict: 包含多个DataFrame的字典，key为sheet名称
        filename: 文件名（可选）
        top_n: 前N个代币数量，用于生成文件名
        market_type: 市场类型，'spot' 或 'futures'
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        market_prefix = "futures_" if market_type == 'futures' else ""
        filename = f'okx_{market_prefix}top{top_n}_multi_period_{timestamp}.xlsx'
    
    # 确保文件名以.xlsx结尾
    if not filename.endswith('.xlsx'):
        filename = filename.replace('.csv', '.xlsx')
    
    # 确保文件保存到data目录
    if not os.path.isabs(filename):
        # data目录在脚本的上一级目录
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        data_dir = os.path.abspath(data_dir)
        os.makedirs(data_dir, exist_ok=True)
        filename = os.path.join(data_dir, filename)
    
    print("="*80)
    print("保存数据到Excel文件...")
    print("="*80)
    
    try:
        # 使用ExcelWriter写入多个sheet
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, df in data_dict.items():
                if not df.empty:
                    # 处理时区信息：去掉时间戳列的时区信息
                    df_copy = df.copy()
                    
                    # 检查并处理时间戳列
                    timestamp_columns = ['timestamp', 'close_time', 'T_minus_2_date', 'T_minus_1_date']
                    for col in timestamp_columns:
                        if col in df_copy.columns:
                            # 如果列包含时区信息，去掉时区
                            if df_copy[col].dtype.name.startswith('datetime64'):
                                df_copy[col] = df_copy[col].dt.tz_localize(None)
                            elif hasattr(df_copy[col].iloc[0], 'tz') and df_copy[col].iloc[0].tz is not None:
                                df_copy[col] = df_copy[col].dt.tz_localize(None)
                    
                    # 保存到对应的sheet
                    df_copy.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"✓ Sheet '{sheet_name}': {len(df)} 行 x {len(df.columns)} 列")
                else:
                    print(f"⚠ Sheet '{sheet_name}': 数据为空，跳过")
        
        file_size = os.path.getsize(filename) / 1024
        print()
        print(f"✓ 数据已成功保存到: {filename}")
        print(f"  文件大小: {file_size:.2f} KB")
        print(f"  包含 {len([df for df in data_dict.values() if not df.empty])} 个sheet")
        
        return filename
        
    except Exception as e:
        print(f"✗ 保存失败: {e}")
        print()
        print("可能的原因:")
        print("1. 未安装openpyxl: pip install openpyxl")
        print("2. 文件被占用")
        print("3. 磁盘空间不足")
        return None


def save_to_multiple_csv(data_dict: dict, prefix: str = None, top_n: int = 100, market_type: str = 'spot'):
    """
    将多个DataFrame保存到独立的CSV文件（备用方案）
    
    Args:
        data_dict: 包含多个DataFrame的字典
        prefix: 文件名前缀
        top_n: 前N个代币数量，用于生成文件名
        market_type: 市场类型，'spot' 或 'futures'
    """
    if prefix is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        market_prefix = "futures_" if market_type == 'futures' else ""
        prefix = f'okx_{market_prefix}top{top_n}_{timestamp}'
    
    print("="*80)
    print("保存数据到多个CSV文件...")
    print("="*80)
    
    saved_files = []
    
    # 确保data目录存在
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    data_dir = os.path.abspath(data_dir)
    os.makedirs(data_dir, exist_ok=True)
    
    for name, df in data_dict.items():
        if not df.empty:
            # 文件名中的特殊字符替换
            safe_name = name.replace('K线', 'kline').replace('日', 'd').replace('周', 'week')
            filename = f"{prefix}_{safe_name}.csv"
            
            if not os.path.isabs(filename):
                filename = os.path.join(data_dir, filename)
            
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            file_size = os.path.getsize(filename) / 1024
            
            print(f"✓ {name}: {filename}")
            print(f"  {len(df)} 行 x {len(df.columns)} 列, {file_size:.2f} KB")
            
            saved_files.append(filename)
    
    print()
    print(f"✓ 共保存 {len(saved_files)} 个文件")
    return saved_files


def print_data_summary(data_dict: dict):
    """打印数据汇总信息"""
    print()
    print("="*80)
    print("数据汇总")
    print("="*80)
    print()
    
    for name, df in data_dict.items():
        if not df.empty:
            print(f"【{name}】")
            print(f"  总记录数: {len(df)}")
            print(f"  代币数量: {df['symbol'].nunique()}")
            
            if 'timestamp' in df.columns:
                print(f"  时间范围: {df['timestamp'].min().date()} 至 {df['timestamp'].max().date()}")
            
            # 显示前3个代币
            top_symbols = df['symbol'].unique()[:3]
            print(f"  代币示例: {', '.join(top_symbols)}...")
            print()


def main():
    """主函数"""
    import sys
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='OKX TopN代币多周期K线数据获取工具')
    parser.add_argument('-n', '--top-n', type=int, default=100, 
                        help='获取前N个代币（默认: 100）')
    parser.add_argument('--market-type', choices=['spot', 'futures'], default='spot',
                        help='市场类型：spot(现货) 或 futures(合约)（默认: spot）')
    parser.add_argument('--days-1d', type=int, default=16,
                        help='1日K线获取天数（默认: 16）')
    parser.add_argument('--days-3d', type=int, default=30,
                        help='3日K线获取天数（默认: 30）')
    parser.add_argument('--days-week', type=int, default=180,
                        help='周K线获取天数（默认: 180）')
    parser.add_argument('--auto', action='store_true',
                        help='自动模式：不询问，直接保存为Excel（用于自动化脚本）')
    
    args = parser.parse_args()
    
    market_name = "合约" if args.market_type == 'futures' else "现货"
    
    print("="*80)
    print(f"OKX Top{args.top_n} {market_name}代币多周期K线数据获取工具")
    print("="*80)
    print()
    print("将获取以下周期的K线数据:")
    print(f"  - 1日K线（最近{args.days_1d}天）")
    print(f"  - 3日K线（最近{args.days_3d}天）")
    print(f"  - 周K线（最近{args.days_week}天）")
    print()
    
    # 配置参数
    TOP_N = args.top_n
    MARKET_TYPE = args.market_type
    DAYS_1D = args.days_1d
    DAYS_3D = args.days_3d
    DAYS_WEEK = args.days_week
    
    try:
        # 1. 获取所有周期的数据
        data_dict = fetch_all_periods_data(
            top_n=TOP_N,
            days_for_daily=DAYS_1D,
            days_for_3d=DAYS_3D,
            days_for_week=DAYS_WEEK,
            market_type=MARKET_TYPE
        )
        
        # 2. 打印数据汇总
        print_data_summary(data_dict)
        
        # 3. 保存数据
        if args.auto:
            # 自动模式：直接保存为Excel
            choice = '1'
            print("自动模式：保存为Excel文件")
            print()
        else:
            # 交互模式：询问用户
            print("选择保存方式:")
            print("1. Excel文件（不同sheet） - 推荐")
            print("2. 多个CSV文件")
            print("3. 两种都保存")
            
            choice = input("\n请选择 (1/2/3，默认1): ").strip() or '1'
            print()
        
        if choice in ['1', '3']:
            # 检查是否安装了openpyxl
            try:
                import openpyxl
                excel_file = save_to_excel(data_dict, top_n=TOP_N, market_type=MARKET_TYPE)
                if excel_file:
                    print()
                    print("💡 提示: 使用Excel打开文件，可以看到3个sheet标签页")
            except ImportError:
                print("⚠ 未安装openpyxl，正在安装...")
                import subprocess
                subprocess.run(['pip', 'install', 'openpyxl'], check=False)
                print()
                print("请重新运行此脚本")
                return
        
        if choice in ['2', '3']:
            print()
            csv_files = save_to_multiple_csv(data_dict, top_n=TOP_N, market_type=MARKET_TYPE)
        
        print()
        print("="*80)
        print("✓ 所有任务完成！")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
