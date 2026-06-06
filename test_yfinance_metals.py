#!/usr/bin/env python3
"""
使用yfinance获取金银铜的历史日K线数据测试文件

安装依赖：
    pip install yfinance pandas openpyxl

商品代码说明：
- 黄金：GC=F (COMEX黄金期货) 或 GLD (黄金ETF)
- 白银：SI=F (COMEX白银期货) 或 SLV (白银ETF)
- 铜：HG=F (COMEX铜期货)

使用方法：
    python test_yfinance_metals.py
"""

import sys
import os
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    print("错误: 未安装 yfinance")
    print("请运行: pip install yfinance")
    sys.exit(1)

import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

# 设置pandas显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


def get_metals_data(tickers: dict, start_date: str = None, end_date: str = None, period: str = "1y", 
                     max_retries: int = 3, retry_delay: int = 10, parallel: bool = False):
    """
    获取金银铜的历史日K线数据
    
    使用 yfinance.download() 批量下载（串行），或使用并行下载方式。
    参考: https://ranaroussi.github.io/yfinance/reference/api/yfinance.EquityQuery.html
    
    Args:
        tickers: 商品代码字典，格式: {'name': 'ticker'}
        start_date: 开始日期，格式: 'YYYY-MM-DD'
        end_date: 结束日期，格式: 'YYYY-MM-DD'
        period: 数据周期，可选: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
        max_retries: 最大重试次数，默认3次
        retry_delay: 重试延迟（秒），默认10秒
        parallel: 是否使用并行下载，默认False（串行）
    
    Returns:
        包含所有商品数据的字典
    """
    import time
    results = {}
    
    # 提取所有ticker代码
    ticker_list = list(tickers.values())
    ticker_names = {ticker: name for name, ticker in tickers.items()}
    
    print(f"\n{'='*80}")
    if parallel:
        print(f"使用并行下载方式获取数据（多线程）")
    else:
        print(f"使用批量下载方式获取数据（串行，推荐）")
    print(f"商品列表: {', '.join([f'{ticker_names[t]} ({t})' for t in ticker_list])}")
    print('='*80)
    
    # 如果使用并行下载
    if parallel:
        return get_metals_data_parallel(tickers, start_date, end_date, period, max_retries, retry_delay)
    
    # 使用 yfinance.download() 批量下载（串行）
    success = False
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n尝试 {attempt}/{max_retries}...")
            
            # 批量下载所有ticker的数据
            if start_date and end_date:
                print(f"下载日期范围: {start_date} 至 {end_date}")
                data = yf.download(
                    ticker_list,
                    start=start_date,
                    end=end_date,
                    group_by='ticker',
                    progress=False
                )
            else:
                print(f"下载周期: {period}")
                data = yf.download(
                    ticker_list,
                    period=period,
                    group_by='ticker',
                    progress=False
                )
            
            if data.empty:
                print(f"⚠️  数据为空，可能是速率限制或网络问题")
                if attempt < max_retries:
                    wait_time = retry_delay * attempt
                    print(f"   等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"✗ 达到最大重试次数，数据仍为空")
                    break
            
            print(f"✓ 批量下载成功")
            
            # 处理每个ticker的数据
            for ticker in ticker_list:
                name = ticker_names[ticker]
                print(f"\n处理 {name} ({ticker}) 的数据...")
                
                # 获取该ticker的数据
                if len(ticker_list) == 1:
                    # 单个ticker时，data直接是DataFrame
                    df = data.copy()
                else:
                    # 多个ticker时，data是MultiIndex DataFrame
                    if ticker in data.columns.levels[0]:
                        df = data[ticker].copy()
                    else:
                        print(f"⚠️  {name} ({ticker}) 数据不存在")
                        continue
                
                if df.empty:
                    print(f"⚠️  {name} 数据为空")
                    continue
                
                # 重置索引，将Date作为列
                df.reset_index(inplace=True)
                
                # 重命名列（yfinance.download返回的列名可能不同）
                column_mapping = {}
                if 'Date' in df.columns:
                    column_mapping['Date'] = 'date'
                elif 'Datetime' in df.columns:
                    column_mapping['Datetime'] = 'date'
                
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if col in df.columns:
                        column_mapping[col] = col.lower()
                
                df.rename(columns=column_mapping, inplace=True)
                
                # 确保有date列
                if 'date' not in df.columns and len(df) > 0:
                    df.reset_index(inplace=True)
                    if 'Date' in df.columns:
                        df.rename(columns={'Date': 'date'}, inplace=True)
                    elif df.index.name:
                        df.reset_index(inplace=True)
                        df.rename(columns={df.columns[0]: 'date'}, inplace=True)
                
                # 添加商品名称
                df['commodity'] = name
                df['ticker'] = ticker
                
                # 计算涨跌幅
                if 'close' in df.columns:
                    df['change_pct'] = df['close'].pct_change() * 100
                
                # 显示基本信息
                print(f"✓ 数据统计:")
                print(f"  记录数: {len(df)}")
                if 'date' in df.columns:
                    print(f"  日期范围: {df['date'].min()} 至 {df['date'].max()}")
                if 'close' in df.columns:
                    print(f"  最新收盘价: ${df['close'].iloc[-1]:.2f}")
                    print(f"  最高价: ${df['high'].max():.2f}")
                    print(f"  最低价: ${df['low'].min():.2f}")
                if 'volume' in df.columns:
                    print(f"  平均成交量: {df['volume'].mean():,.0f}")
                
                # 显示最新几条数据
                display_cols = ['date'] + [c for c in ['open', 'high', 'low', 'close', 'volume', 'change_pct'] if c in df.columns]
                print(f"\n最新5条数据:")
                print(df[display_cols].tail().to_string(index=False))
                
                results[name] = df
            
            success = True
            break  # 成功获取数据，跳出重试循环
            
        except yf.exceptions.YFRateLimitError as e:
            if attempt < max_retries:
                wait_time = retry_delay * attempt  # 递增等待时间
                print(f"⚠️  速率限制错误 (尝试 {attempt}/{max_retries})")
                print(f"   等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"✗ 批量下载失败: 达到最大重试次数")
                print(f"   错误: {e}")
                print(f"   建议: 请稍后再试，或减少请求频率")
                
        except Exception as e:
            if attempt < max_retries:
                wait_time = retry_delay * attempt
                print(f"⚠️  批量下载失败 (尝试 {attempt}/{max_retries}): {e}")
                print(f"   等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"✗ 批量下载失败: {e}")
                import traceback
                traceback.print_exc()
    
    if not success:
        print(f"✗ 批量下载失败，尝试逐个下载...")
        # 如果批量下载失败，回退到逐个下载方式
        return get_metals_data_individual(tickers, start_date, end_date, period, max_retries, retry_delay)
    
    return results


def get_metals_data_parallel(tickers: dict, start_date: str = None, end_date: str = None, 
                              period: str = "1y", max_retries: int = 3, retry_delay: int = 10):
    """
    并行获取商品数据（使用多线程）
    
    Args:
        tickers: 商品代码字典
        start_date: 开始日期
        end_date: 结束日期
        period: 数据周期
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    
    Returns:
        包含所有商品数据的字典
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    results = {}
    
    def download_single_ticker(name_ticker_tuple):
        """下载单个ticker的数据"""
        name, ticker = name_ticker_tuple
        print(f"[{name}] 开始下载...")
        
        for attempt in range(1, max_retries + 1):
            try:
                ticker_obj = yf.Ticker(ticker)
                
                if start_date and end_date:
                    df = ticker_obj.history(start=start_date, end=end_date)
                else:
                    df = ticker_obj.history(period=period)
                
                if df.empty:
                    print(f"[{name}] ⚠️  数据为空")
                    return name, None
                
                df.reset_index(inplace=True)
                df.rename(columns={
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                }, inplace=True)
                
                df['commodity'] = name
                df['ticker'] = ticker
                df['change_pct'] = df['close'].pct_change() * 100
                
                print(f"[{name}] ✓ 下载成功: {len(df)} 条记录")
                return name, df
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = retry_delay * attempt
                    print(f"[{name}] ⚠️  下载失败 (尝试 {attempt}/{max_retries}): {e}")
                    print(f"[{name}]    等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"[{name}] ✗ 下载失败: {e}")
                    return name, None
        
        return name, None
    
    # 使用线程池并行下载
    ticker_items = list(tickers.items())
    
    print(f"\n使用 {len(ticker_items)} 个线程并行下载...")
    
    with ThreadPoolExecutor(max_workers=len(ticker_items)) as executor:
        # 提交所有任务
        future_to_name = {
            executor.submit(download_single_ticker, item): item[0] 
            for item in ticker_items
        }
        
        # 收集结果
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result_name, df = future.result()
                if df is not None:
                    results[result_name] = df
            except Exception as e:
                print(f"[{name}] ✗ 获取结果失败: {e}")
    
    return results


def get_metals_data_individual(tickers: dict, start_date: str = None, end_date: str = None, 
                                period: str = "1y", max_retries: int = 3, retry_delay: int = 10):
    """
    逐个获取商品数据（串行，备用方法）
    """
    import time
    results = {}
    
    for idx, (name, ticker) in enumerate(tickers.items()):
        print(f"\n{'='*80}")
        print(f"正在获取 {name} ({ticker}) 的数据... ({idx+1}/{len(tickers)})")
        print('='*80)
        
        # 在请求之间添加延迟
        if idx > 0:
            print(f"等待 {retry_delay} 秒以避免速率限制...")
            time.sleep(retry_delay)
        
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                ticker_obj = yf.Ticker(ticker)
                
                if start_date and end_date:
                    df = ticker_obj.history(start=start_date, end=end_date)
                else:
                    df = ticker_obj.history(period=period)
                
                if df.empty:
                    print(f"⚠️  {name} 数据为空")
                    break
                
                df.reset_index(inplace=True)
                df.rename(columns={
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                }, inplace=True)
                
                df['commodity'] = name
                df['ticker'] = ticker
                df['change_pct'] = df['close'].pct_change() * 100
                
                print(f"✓ 获取成功: {len(df)} 条记录")
                results[name] = df
                success = True
                break
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = retry_delay * attempt
                    print(f"⚠️  获取失败 (尝试 {attempt}/{max_retries}): {e}")
                    print(f"   等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"✗ 获取 {name} 数据失败: {e}")
        
        if not success:
            print(f"✗ 跳过 {name}，继续获取下一个商品...")
    
    return results


def save_to_excel(data_dict: dict, output_file: str = "metals_data.xlsx"):
    """
    将数据保存到Excel文件
    
    Args:
        data_dict: 数据字典
        output_file: 输出文件名
    """
    if not data_dict:
        print("没有数据可保存")
        return
    
    print(f"\n{'='*80}")
    print(f"保存数据到Excel文件...")
    print('='*80)
    
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for name, df in data_dict.items():
                # 确保日期列为字符串格式
                df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                df.to_excel(writer, sheet_name=name, index=False)
                print(f"✓ {name} 数据已保存到 sheet: {name}")
        
        file_size = os.path.getsize(output_file) / 1024 / 1024  # MB
        print(f"\n✓ 所有数据已保存到: {output_file}")
        print(f"  文件大小: {file_size:.2f} MB")
        print(f"  Sheet数量: {len(data_dict)}")
        
    except Exception as e:
        print(f"✗ 保存失败: {e}")
        import traceback
        traceback.print_exc()


def compare_metals(data_dict: dict):
    """
    对比金银铜的价格走势
    
    Args:
        data_dict: 数据字典
    """
    if len(data_dict) < 2:
        print("数据不足，无法对比")
        return
    
    print(f"\n{'='*80}")
    print("金银铜价格对比分析")
    print('='*80)
    
    # 合并数据
    combined_data = []
    for name, df in data_dict.items():
        df_copy = df[['date', 'close']].copy()
        df_copy.rename(columns={'close': name}, inplace=True)
        df_copy.set_index('date', inplace=True)
        combined_data.append(df_copy)
    
    # 合并所有数据
    merged = pd.concat(combined_data, axis=1)
    merged = merged.sort_index()
    
    # 计算相关性
    print("\n价格相关性矩阵:")
    print(merged.corr().to_string())
    
    # 计算涨跌幅
    print("\n最近30天涨跌幅:")
    recent_30d = merged.tail(30)
    for col in merged.columns:
        if len(recent_30d) > 1:
            change = (recent_30d[col].iloc[-1] - recent_30d[col].iloc[0]) / recent_30d[col].iloc[0] * 100
            print(f"  {col}: {change:+.2f}%")
    
    # 显示最新价格
    print("\n最新价格:")
    latest = merged.iloc[-1]
    for col in merged.columns:
        print(f"  {col}: ${latest[col]:.2f}")


def main():
    """主函数"""
    print("="*80)
    print("yfinance 金银铜历史数据获取测试")
    print("="*80)
    
    # 定义商品代码
    # 注意：期货代码需要加 =F 后缀
    metals_tickers = {
        '黄金': 'GC=F',      # COMEX黄金期货
        '白银': 'SI=F',      # COMEX白银期货
        '铜': 'HG=F',        # COMEX铜期货
    }
    
    # 也可以使用ETF代码（可选）
    # metals_tickers_etf = {
    #     '黄金ETF': 'GLD',
    #     '白银ETF': 'SLV',
    #     '铜ETF': 'CPER',
    # }
    
    # 获取数据
    # 方式1: 使用日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')  # 最近1年
    
    print(f"\n数据获取参数:")
    print(f"  开始日期: {start_date}")
    print(f"  结束日期: {end_date}")
    
    # 获取数据
    # parallel=True 使用并行下载（多线程），parallel=False 使用串行下载（默认）
    data_dict = get_metals_data(
        tickers=metals_tickers,
        start_date=start_date,
        end_date=end_date,
        parallel=False  # 改为 True 启用并行下载
    )
    
    # 方式2: 使用周期（示例，已注释）
    # data_dict = get_metals_data(
    #     tickers=metals_tickers,
    #     period="1y"  # 最近1年
    # )
    
    # 对比分析
    if data_dict:
        compare_metals(data_dict)
        
        # 保存到Excel
        output_file = "data/metals_data.xlsx"
        os.makedirs("data", exist_ok=True)
        save_to_excel(data_dict, output_file)
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    main()
