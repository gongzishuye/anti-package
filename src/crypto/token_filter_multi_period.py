#!/usr/bin/env python3
"""
多周期币安Token筛选器
从Excel文件的多个sheet中筛选符合条件的Token
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple
import os
import glob

class MultiPeriodTokenFilter:
    """多周期Token筛选器"""
    
    def __init__(self, excel_file_path: str):
        """
        初始化筛选器
        
        Args:
            excel_file_path: Excel数据文件路径
        """
        self.excel_file_path = excel_file_path
        self.data_dict = {}  # 存储各个周期的数据
        self.load_data()
    
    def load_data(self):
        """加载Excel文件的所有sheet"""
        try:
            # 读取Excel文件
            excel_file = pd.ExcelFile(self.excel_file_path)
            
            print("="*80)
            print(f"加载Excel文件: {self.excel_file_path}")
            print("="*80)
            print(f"发现 {len(excel_file.sheet_names)} 个sheet: {', '.join(excel_file.sheet_names)}")
            print()
            
            # 读取每个sheet
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(self.excel_file_path, sheet_name=sheet_name)
                
                # 转换时间戳列
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # 确保数值列为float类型
                numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                self.data_dict[sheet_name] = df
                
                print(f"✓ {sheet_name}:")
                print(f"  - 记录数: {len(df)}")
                print(f"  - 代币数: {df['symbol'].nunique()}")
                print(f"  - 时间范围: {df['timestamp'].min().date()} 至 {df['timestamp'].max().date()}")
            
            print()
            
        except Exception as e:
            print(f"✗ 加载数据失败: {e}")
            self.data_dict = {}
    
    def get_latest_dates(self, df: pd.DataFrame) -> Tuple[datetime, datetime, datetime]:
        """
        获取最新的三个日期
        
        Args:
            df: DataFrame数据
            
        Returns:
            (T, T-1, T-2) - 最新、次新、第三新日期
        """
        unique_dates = sorted(df['timestamp'].dt.date.unique(), reverse=True)
        
        if len(unique_dates) < 3:
            raise ValueError(f"数据不足，需要至少3个周期的数据，当前只有 {len(unique_dates)} 个周期")
        
        T = pd.to_datetime(unique_dates[0])  # 最新日期
        T_minus_1 = pd.to_datetime(unique_dates[1])  # 次新
        T_minus_2 = pd.to_datetime(unique_dates[2])  # 第三新
        
        return T, T_minus_1, T_minus_2
    
    def is_bullish_candle(self, row) -> bool:
        """判断是否为阳线（收盘价 > 开盘价）"""
        return row['close'] > row['open']
    
    def is_bearish_candle(self, row) -> bool:
        """判断是否为阴线（收盘价 < 开盘价）"""
        return row['close'] < row['open']
    
    def filter_single_period(self, df: pd.DataFrame, period_name: str) -> List[Dict]:
        """
        筛选单个周期的数据
        
        筛选条件:
        1. T-1的成交量大于T-2
        2. T-2是阴线（收盘价低于开盘价）
        3. T-1是阳线（开盘价低于收盘价）且T-1收盘价大于T-2的开盘价
        
        改进：针对每个币种使用其自己最新的3个周期，而不是全局日期
        
        Args:
            df: 单个周期的DataFrame
            period_name: 周期名称（如"1日K线"）
            
        Returns:
            符合条件的Token数据列表
        """
        print("="*80)
        print(f"筛选 {period_name}")
        print("="*80)
        
        try:
            # 获取全局日期信息（仅用于显示）
            unique_dates = sorted(df['timestamp'].dt.date.unique(), reverse=True)
            print(f"数据集包含日期: {unique_dates[0]} 至 {unique_dates[-1]} (共{len(unique_dates)}个)")
            print()
            
            qualified_tokens = []
            
            # 遍历所有Token
            all_symbols = sorted(df['symbol'].unique())
            print(f"开始分析 {len(all_symbols)} 个币种...")
            print()
            
            for symbol in all_symbols:
                # 获取该Token的所有数据，按时间排序
                symbol_data = df[df['symbol'] == symbol].sort_values('timestamp')
                
                # 检查是否有至少3个周期的数据
                if len(symbol_data) < 3:
                    continue
                
                # 取该Token最新的3个周期
                latest_3 = symbol_data.tail(3)
                t_minus_2_data_point = latest_3.iloc[0]
                t_minus_1_data_point = latest_3.iloc[1]
                t_data_point = latest_3.iloc[2]
                
                # 检查是否有足够的数据
                if pd.isna(t_minus_2_data_point['close']) or pd.isna(t_minus_1_data_point['close']):
                    continue
                
                # 应用筛选条件
                condition1 = t_minus_1_data_point['volume'] > t_minus_2_data_point['volume']  # T-1成交量 > T-2成交量
                condition2 = self.is_bearish_candle(t_minus_2_data_point)  # T-2是阴线
                condition3a = self.is_bullish_candle(t_minus_1_data_point)  # T-1是阳线
                condition3b = t_minus_1_data_point['close'] > t_minus_2_data_point['open']  # T-1收盘价 > T-2开盘价
                condition3 = condition3a and condition3b
                
                # 如果所有条件都满足
                if condition1 and condition2 and condition3:
                    # 计算指标
                    volume_growth_rate = ((t_minus_1_data_point['volume'] - t_minus_2_data_point['volume']) / 
                                        t_minus_2_data_point['volume'] * 100) if t_minus_2_data_point['volume'] > 0 else 0
                    
                    # 计算USDT成交量增长（如果有的话）
                    usdt_volume_growth = 0
                    if 'quote_asset_volume' in t_minus_1_data_point and 'quote_asset_volume' in t_minus_2_data_point:
                        if t_minus_2_data_point['quote_asset_volume'] > 0:
                            usdt_volume_growth = ((t_minus_1_data_point['quote_asset_volume'] - 
                                                 t_minus_2_data_point['quote_asset_volume']) / 
                                                t_minus_2_data_point['quote_asset_volume'] * 100)
                    
                    qualified_token = {
                        'symbol': symbol,
                        'period': period_name,
                        'T_minus_2': {
                            'date': t_minus_2_data_point['timestamp'],
                            'open': t_minus_2_data_point['open'],
                            'high': t_minus_2_data_point['high'],
                            'low': t_minus_2_data_point['low'],
                            'close': t_minus_2_data_point['close'],
                            'volume': t_minus_2_data_point['volume'],
                            'quote_asset_volume': t_minus_2_data_point.get('quote_asset_volume', 0),
                            'is_bearish': condition2
                        },
                        'T_minus_1': {
                            'date': t_minus_1_data_point['timestamp'],
                            'open': t_minus_1_data_point['open'],
                            'high': t_minus_1_data_point['high'],
                            'low': t_minus_1_data_point['low'],
                            'close': t_minus_1_data_point['close'],
                            'volume': t_minus_1_data_point['volume'],
                            'quote_asset_volume': t_minus_1_data_point.get('quote_asset_volume', 0),
                            'is_bullish': condition3a,
                            'close_above_t2_open': condition3b
                        },
                        'volume_growth_rate': volume_growth_rate,
                        'usdt_volume_growth_rate': usdt_volume_growth,
                        'conditions_met': {
                            'volume_increase': condition1,
                            't2_bearish': condition2,
                            't1_bullish_and_above': condition3
                        }
                    }
                    qualified_tokens.append(qualified_token)
                    
                    print(f"✓ {symbol}")
                    t2_date = pd.to_datetime(t_minus_2_data_point['timestamp']).date()
                    t1_date = pd.to_datetime(t_minus_1_data_point['timestamp']).date()
                    print(f"  T-2: {t2_date} 阴线 成交量:{t_minus_2_data_point['volume']:.2f}")
                    print(f"  T-1: {t1_date} 阳线 成交量:{t_minus_1_data_point['volume']:.2f}")
                    print(f"  成交量增长: {volume_growth_rate:.2f}%")
            
            print()
            print(f"筛选结果: {period_name} 共找到 {len(qualified_tokens)} 个符合条件的Token")
            print()
            
            return qualified_tokens
            
        except Exception as e:
            print(f"✗ 筛选过程出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def filter_all_periods(self) -> Dict[str, List[Dict]]:
        """
        筛选所有周期的数据
        
        Returns:
            包含所有周期筛选结果的字典
        """
        results = {}
        
        for sheet_name, df in self.data_dict.items():
            qualified_tokens = self.filter_single_period(df, sheet_name)
            results[sheet_name] = qualified_tokens
        
        return results
    
    def _extract_prefix_from_filename(self, input_filename: str = None) -> str:
        """
        从输入文件名中提取前缀
        
        Args:
            input_filename: 输入文件名
            
        Returns:
            提取的前缀，如果没有则返回空字符串
        """
        if not input_filename:
            return ""
        
        # 获取文件名（不含路径）
        filename = os.path.basename(input_filename)
        
        # 提取前缀的逻辑
        if filename.startswith('okx_'):
            return 'okx_'
        elif filename.startswith('binance_'):
            return 'binance_'
        elif filename.startswith('futures_'):
            return 'futures_'
        else:
            return ""
    
    def save_results_to_excel(self, results: Dict[str, List[Dict]], output_filename: str = None, input_filename: str = None) -> str:
        """
        将筛选结果保存到Excel文件（每个周期一个sheet）
        
        Args:
            results: 筛选结果字典
            output_filename: 输出文件名
            input_filename: 输入文件名，用于提取前缀
            
        Returns:
            保存的文件路径
        """
        if not results or all(len(tokens) == 0 for tokens in results.values()):
            print("没有符合条件的Token数据")
            return ""
        
        if output_filename is None:
            # 根据输入文件名生成输出文件名
            if input_filename:
                # 获取输入文件名（不含路径）
                input_basename = os.path.basename(input_filename)
                # 移除扩展名
                name_without_ext = os.path.splitext(input_basename)[0]
                # 添加qualified_前缀
                output_filename = f'qualified_{name_without_ext}.xlsx'
            else:
                # 如果没有输入文件名，使用默认格式
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f'qualified_tokens_multi_period_{timestamp}.xlsx'
        
        # 确保文件名以.xlsx结尾
        if not output_filename.endswith('.xlsx'):
            output_filename = output_filename.replace('.csv', '.xlsx')
        
        # 确保文件保存到data目录
        if not os.path.isabs(output_filename):
            # data目录在项目根目录
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
            data_dir = os.path.abspath(data_dir)
            os.makedirs(data_dir, exist_ok=True)
            output_filename = os.path.join(data_dir, output_filename)
        
        print("="*80)
        print("保存筛选结果到Excel...")
        print("="*80)
        
        try:
            with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
                for period_name, tokens in results.items():
                    if not tokens:
                        print(f"⚠ {period_name}: 无数据，跳过")
                        continue
                    
                    # 准备数据
                    rows = []
                    for token in tokens:
                        symbol = token['symbol']
                        t2 = token['T_minus_2']
                        t1 = token['T_minus_1']
                        
                        # 计算指标
                        price_change_t1 = ((t1['close'] - t1['open']) / t1['open'] * 100) if t1['open'] > 0 else 0
                        price_change_t2 = ((t2['close'] - t2['open']) / t2['open'] * 100) if t2['open'] > 0 else 0
                        
                        row = {
                            'symbol': symbol,
                            'T_minus_2_date': t2['date'].strftime('%Y-%m-%d'),
                            'T_minus_2_open': t2['open'],
                            'T_minus_2_high': t2['high'],
                            'T_minus_2_low': t2['low'],
                            'T_minus_2_close': t2['close'],
                            'T_minus_2_volume': t2['volume'],
                            'T_minus_2_quote_asset_volume': t2['quote_asset_volume'],
                            'T_minus_2_change_pct': price_change_t2,
                            'T_minus_1_date': t1['date'].strftime('%Y-%m-%d'),
                            'T_minus_1_open': t1['open'],
                            'T_minus_1_high': t1['high'],
                            'T_minus_1_low': t1['low'],
                            'T_minus_1_close': t1['close'],
                            'T_minus_1_volume': t1['volume'],
                            'T_minus_1_quote_asset_volume': t1['quote_asset_volume'],
                            'T_minus_1_change_pct': price_change_t1,
                            'volume_growth_rate_pct': token['volume_growth_rate'],
                            'usdt_volume_growth_rate_pct': token['usdt_volume_growth_rate'],
                        }
                        rows.append(row)
                    
                    # 按T-1的USDT成交量降序排序
                    df_output = pd.DataFrame(rows)
                    df_output = df_output.sort_values('T_minus_1_quote_asset_volume', ascending=False)
                    
                    # 保存到对应的sheet
                    sheet_name = period_name.replace('K线', '筛选结果')
                    df_output.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    print(f"✓ {sheet_name}: {len(rows)} 个Token")
            
            file_size = os.path.getsize(output_filename) / 1024
            print()
            print(f"✓ 筛选结果已保存到: {output_filename}")
            print(f"  文件大小: {file_size:.2f} KB")
            
            return output_filename
            
        except Exception as e:
            print(f"✗ 保存失败: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def save_results_to_csv(self, results: Dict[str, List[Dict]], prefix: str = None, input_filename: str = None) -> List[str]:
        """
        将筛选结果保存到多个CSV文件
        
        Args:
            results: 筛选结果字典
            prefix: 文件名前缀
            input_filename: 输入文件名，用于提取前缀
            
        Returns:
            保存的文件路径列表
        """
        if prefix is None:
            # 根据输入文件名生成前缀
            if input_filename:
                # 获取输入文件名（不含路径）
                input_basename = os.path.basename(input_filename)
                # 移除扩展名
                name_without_ext = os.path.splitext(input_basename)[0]
                # 添加qualified_前缀
                prefix = f'qualified_{name_without_ext}'
            else:
                # 如果没有输入文件名，使用默认格式
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                prefix = f'qualified_tokens_{timestamp}'
        
        saved_files = []
        
        # 确保data目录存在
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        data_dir = os.path.abspath(data_dir)
        os.makedirs(data_dir, exist_ok=True)
        
        print("="*80)
        print("保存筛选结果到CSV文件...")
        print("="*80)
        
        for period_name, tokens in results.items():
            if not tokens:
                print(f"⚠ {period_name}: 无数据，跳过")
                continue
            
            # 文件名
            safe_name = period_name.replace('K线', 'kline').replace('日', 'd').replace('周', 'week')
            filename = f"{prefix}_{safe_name}.csv"
            
            # 保存到data目录
            if not os.path.isabs(filename):
                filename = os.path.join(data_dir, filename)
            
            # 准备数据
            rows = []
            for token in tokens:
                symbol = token['symbol']
                t2 = token['T_minus_2']
                t1 = token['T_minus_1']
                
                price_change_t1 = ((t1['close'] - t1['open']) / t1['open'] * 100) if t1['open'] > 0 else 0
                price_change_t2 = ((t2['close'] - t2['open']) / t2['open'] * 100) if t2['open'] > 0 else 0
                
                row = {
                    'symbol': symbol,
                    'T_minus_2_date': t2['date'].strftime('%Y-%m-%d'),
                    'T_minus_2_open': t2['open'],
                    'T_minus_2_close': t2['close'],
                    'T_minus_2_volume': t2['volume'],
                    'T_minus_2_quote_asset_volume': t2['quote_asset_volume'],
                    'T_minus_2_change_pct': price_change_t2,
                    'T_minus_1_date': t1['date'].strftime('%Y-%m-%d'),
                    'T_minus_1_open': t1['open'],
                    'T_minus_1_close': t1['close'],
                    'T_minus_1_volume': t1['volume'],
                    'T_minus_1_quote_asset_volume': t1['quote_asset_volume'],
                    'T_minus_1_change_pct': price_change_t1,
                    'volume_growth_rate_pct': token['volume_growth_rate'],
                }
                rows.append(row)
            
            # 保存
            df_output = pd.DataFrame(rows)
            df_output = df_output.sort_values('T_minus_1_quote_asset_volume', ascending=False)
            df_output.to_csv(filename, index=False, encoding='utf-8-sig')
            
            file_size = os.path.getsize(filename) / 1024
            print(f"✓ {period_name}: {filename}")
            print(f"  {len(rows)} 个Token, {file_size:.2f} KB")
            
            saved_files.append(filename)
        
        print()
        print(f"✓ 共保存 {len(saved_files)} 个文件")
        
        return saved_files
    
    def print_summary(self, results: Dict[str, List[Dict]]):
        """打印所有周期的筛选结果摘要"""
        print()
        print("="*80)
        print("筛选结果总览")
        print("="*80)
        print()
        
        total_tokens = 0
        
        for period_name, tokens in results.items():
            print(f"【{period_name}】")
            if not tokens:
                print("  未找到符合条件的Token")
                print()
                continue
            
            print(f"  符合条件: {len(tokens)} 个Token")
            
            # 计算平均指标
            avg_volume_growth = sum(t['volume_growth_rate'] for t in tokens) / len(tokens)
            max_volume_growth = max(t['volume_growth_rate'] for t in tokens)
            
            print(f"  平均成交量增长: {avg_volume_growth:.1f}%")
            print(f"  最大成交量增长: {max_volume_growth:.1f}%")
            
            # 显示前5个Token
            print(f"  Top 5 Token:")
            for i, token in enumerate(sorted(tokens, 
                                            key=lambda x: x['T_minus_1']['quote_asset_volume'], 
                                            reverse=True)[:5], 1):
                symbol = token['symbol']
                vol_growth = token['volume_growth_rate']
                usdt_vol = token['T_minus_1']['quote_asset_volume']
                print(f"    {i}. {symbol:12s} - 成交量增长: {vol_growth:+6.1f}% | "
                      f"USDT成交量: {usdt_vol:,.0f}")
            
            print()
            total_tokens += len(tokens)
        
        print(f"总计: 所有周期共找到 {total_tokens} 个符合条件的Token")
        print("="*80)

def get_latest_excel_file():
    """获取最新的Excel文件（支持不同的交易所和topN）"""
    # data在上一层目录
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    data_dir = os.path.abspath(data_dir)
    
    # 匹配多种文件格式
    patterns = [
        "binance_top*_multi_period_*.xlsx",
        "binance_futures_top*_multi_period_*.xlsx", 
        "okx_top*_multi_period_*.xlsx",
        "okx_futures_top*_multi_period_*.xlsx",
        "*_top*_multi_period_*.xlsx",  # 通用模式
        "top*_multi_period_*.xlsx",    # 简化模式
        "futures_top*_multi_period_*.xlsx"  # 合约模式
    ]
    
    all_files = []
    for pattern in patterns:
        files = glob.glob(os.path.join(data_dir, pattern))
        all_files.extend(files)
    
    print(f"在 {data_dir} 中找到的Excel文件:")
    for f in sorted(all_files, key=os.path.getmtime, reverse=True):
        print(f"  - {os.path.basename(f)} ({datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M:%S')})")
    
    if not all_files:
        print("  未找到任何Excel文件")
        return None
    
    # 返回最新的文件
    latest_file = max(all_files, key=os.path.getmtime)
    print(f"选择最新文件: {os.path.basename(latest_file)}")
    return latest_file


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='多周期Token筛选器')
    parser.add_argument('--input', '-i', type=str, 
                        help='输入Excel文件路径（可选，不指定则自动查找最新文件）')
    parser.add_argument('--output', '-o', type=str,
                        help='输出文件名前缀（可选，默认自动生成）')
    parser.add_argument('--auto', action='store_true',
                        help='自动模式：不询问，直接保存为Excel（用于自动化脚本）')
    
    args = parser.parse_args()
    
    print("="*80)
    print("多周期Token筛选器")
    print("="*80)
    print()
    
    # 确定输入文件
    if args.input:
        # 使用指定的输入文件
        excel_file = args.input
        print(f"使用指定文件: {excel_file}")
    else:
        # 自动查找最新的Excel文件
        excel_file = get_latest_excel_file()
        if excel_file:
            print(f"自动找到最新文件: {excel_file}")
        else:
            print("✗ 未找到任何Excel文件")
            print()
            print("请使用 --input 参数指定文件路径，或确保data目录下有Excel文件")
            print("支持的文件格式: binance_top*_multi_period_*.xlsx, okx_*_top*_multi_period_*.xlsx")
            return
    
    # 检查文件是否存在
    if not excel_file or not os.path.exists(excel_file):
        print(f"✗ 文件不存在: {excel_file}")
        print()
        print("请确保Excel文件存在，或使用 --input 参数指定正确的文件路径")
        return
    
    try:
        # 创建筛选器
        filter_tool = MultiPeriodTokenFilter(excel_file)
        
        # 执行筛选
        results = filter_tool.filter_all_periods()
        
        # 打印摘要
        filter_tool.print_summary(results)
        
        # 保存结果
        if args.auto:
            # 自动模式：直接保存为Excel
            print("自动模式：保存为Excel文件")
            print()
            output_file = filter_tool.save_results_to_excel(results, output_filename=args.output, input_filename=excel_file)
            if output_file:
                print()
                print("💡 提示: 使用Excel打开文件，可以看到不同周期的筛选结果")
        else:
            # 交互模式：询问用户
            print("选择保存方式:")
            print("1. Excel文件（不同sheet） - 推荐")
            print("2. 多个CSV文件")
            print("3. 两种都保存")
            
            choice = input("\n请选择 (1/2/3，默认1): ").strip() or '1'
            print()
            
            if choice in ['1', '3']:
                output_file = filter_tool.save_results_to_excel(results, output_filename=args.output, input_filename=excel_file)
                if output_file:
                    print()
                    print("💡 提示: 使用Excel打开文件，可以看到不同周期的筛选结果")
            
            if choice in ['2', '3']:
                print()
                csv_files = filter_tool.save_results_to_csv(results, prefix=args.output, input_filename=excel_file)
        
        print()
        print("="*80)
        print("✓ 所有任务完成！")
        print("="*80)
        
    except Exception as e:
        print(f"✗ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

