#!/usr/bin/env python3
"""
币安K线间隔类型说明和使用示例
展示币安支持的所有K线周期
"""

from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta

# 币安支持的所有K线间隔
BINANCE_KLINE_INTERVALS = {
    # 分钟级别
    '1m': Client.KLINE_INTERVAL_1MINUTE,    # 1分钟
    '3m': Client.KLINE_INTERVAL_3MINUTE,    # 3分钟
    '5m': Client.KLINE_INTERVAL_5MINUTE,    # 5分钟
    '15m': Client.KLINE_INTERVAL_15MINUTE,  # 15分钟
    '30m': Client.KLINE_INTERVAL_30MINUTE,  # 30分钟
    
    # 小时级别
    '1h': Client.KLINE_INTERVAL_1HOUR,      # 1小时
    '2h': Client.KLINE_INTERVAL_2HOUR,      # 2小时
    '4h': Client.KLINE_INTERVAL_4HOUR,      # 4小时
    '6h': Client.KLINE_INTERVAL_6HOUR,      # 6小时
    '8h': Client.KLINE_INTERVAL_8HOUR,      # 8小时
    '12h': Client.KLINE_INTERVAL_12HOUR,    # 12小时
    
    # 日/周/月级别
    '1d': Client.KLINE_INTERVAL_1DAY,       # 1日（日K）
    '3d': Client.KLINE_INTERVAL_3DAY,       # 3日 ✓ 有3日线
    '1w': Client.KLINE_INTERVAL_1WEEK,      # 1周（周K）
    '1M': Client.KLINE_INTERVAL_1MONTH,     # 1月（月K）
}


def print_supported_intervals():
    """打印所有支持的K线间隔"""
    print("="*70)
    print("币安支持的K线间隔类型")
    print("="*70)
    print()
    
    print("【分钟级别】")
    print("  1m  - 1分钟")
    print("  3m  - 3分钟")
    print("  5m  - 5分钟")
    print("  15m - 15分钟")
    print("  30m - 30分钟")
    print()
    
    print("【小时级别】")
    print("  1h  - 1小时")
    print("  2h  - 2小时")
    print("  4h  - 4小时")
    print("  6h  - 6小时")
    print("  8h  - 8小时")
    print("  12h - 12小时")
    print()
    
    print("【日/周/月级别】")
    print("  1d  - 1日（日K）")
    print("  3d  - 3日 ⭐")
    print("  1w  - 1周（周K）")
    print("  1M  - 1月（月K）")
    print()
    
    print("❌ 不支持:")
    print("  2d  - 2日")
    print("  5d  - 5日")
    print()
    
    print("💡 如果需要2日或5日K线，有以下方案:")
    print("  1. 使用3日K线（最接近）")
    print("  2. 使用1日K线自行聚合")
    print("  3. 使用周线（1w = 7日）")
    print("="*70)


def aggregate_klines_to_n_days(df: pd.DataFrame, n_days: int) -> pd.DataFrame:
    """
    将1日K线聚合为N日K线
    
    Args:
        df: 1日K线DataFrame（需包含：timestamp, open, high, low, close, volume等）
        n_days: 聚合周期（如2日、5日）
        
    Returns:
        聚合后的N日K线DataFrame
    """
    if df.empty:
        return df
    
    # 确保按时间排序
    df = df.sort_values('timestamp').copy()
    
    # 设置时间索引
    df.set_index('timestamp', inplace=True)
    
    # 聚合规则
    agg_rules = {
        'open': 'first',      # 开盘价取第一个
        'high': 'max',        # 最高价取最大值
        'low': 'min',         # 最低价取最小值
        'close': 'last',      # 收盘价取最后一个
        'volume': 'sum',      # 成交量求和
        'quote_asset_volume': 'sum',  # USDT成交量求和
        'number_of_trades': 'sum',    # 交易次数求和
    }
    
    # 按N日重采样
    result = df.resample(f'{n_days}D').agg(agg_rules)
    
    # 移除空行
    result = result.dropna()
    
    # 重置索引
    result.reset_index(inplace=True)
    
    return result


# 示例：使用不同的K线间隔
def example_get_klines_with_interval(symbol='BTCUSDT', interval='1d', days=30):
    """
    获取指定间隔的K线数据
    
    Args:
        symbol: 交易对
        interval: K线间隔（如 '1d', '3d', '1w', '4h'等）
        days: 获取天数
    """
    client = Client()
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    print(f"\n获取 {symbol} 的 {interval} K线数据...")
    print(f"时间范围: {start_time.date()} 到 {end_time.date()}")
    
    try:
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=BINANCE_KLINE_INTERVALS[interval],
            start_str=start_time.strftime('%d %b %Y %H:%M:%S'),
            end_str=end_time.strftime('%d %b %Y %H:%M:%S')
        )
        
        if klines:
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"✓ 获取到 {len(df)} 根K线")
            print(f"\n最近5根K线:")
            print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())
            
            return df
        else:
            print("✗ 未获取到数据")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"✗ 获取失败: {e}")
        return pd.DataFrame()


def example_create_2day_klines(symbol='BTCUSDT', days=30):
    """
    示例：创建2日K线（通过1日K线聚合）
    """
    print("\n" + "="*70)
    print("示例：通过1日K线聚合创建2日K线")
    print("="*70)
    
    # 1. 先获取1日K线
    df_1d = example_get_klines_with_interval(symbol, '1d', days)
    
    if df_1d.empty:
        return
    
    # 2. 聚合为2日K线
    print(f"\n将 {len(df_1d)} 根1日K线聚合为2日K线...")
    df_2d = aggregate_klines_to_n_days(df_1d, n_days=2)
    
    print(f"✓ 聚合完成，得到 {len(df_2d)} 根2日K线")
    print(f"\n2日K线数据:")
    print(df_2d[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())


def example_create_5day_klines(symbol='BTCUSDT', days=60):
    """
    示例：创建5日K线（通过1日K线聚合）
    """
    print("\n" + "="*70)
    print("示例：通过1日K线聚合创建5日K线")
    print("="*70)
    
    # 1. 先获取1日K线
    df_1d = example_get_klines_with_interval(symbol, '1d', days)
    
    if df_1d.empty:
        return
    
    # 2. 聚合为5日K线
    print(f"\n将 {len(df_1d)} 根1日K线聚合为5日K线...")
    df_5d = aggregate_klines_to_n_days(df_1d, n_days=5)
    
    print(f"✓ 聚合完成，得到 {len(df_5d)} 根5日K线")
    print(f"\n5日K线数据:")
    print(df_5d[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())


def main():
    """主函数"""
    print_supported_intervals()
    
    print("\n请选择示例:")
    print("1. 获取1日K线")
    print("2. 获取3日K线（币安原生支持）")
    print("3. 获取周K线")
    print("4. 创建2日K线（通过1日聚合）")
    print("5. 创建5日K线（通过1日聚合）")
    print("6. 获取4小时K线")
    print("0. 退出")
    
    try:
        choice = input("\n请输入选项 (0-6): ").strip()
        
        if choice == '1':
            example_get_klines_with_interval('BTCUSDT', '1d', 30)
        elif choice == '2':
            example_get_klines_with_interval('BTCUSDT', '3d', 90)
        elif choice == '3':
            example_get_klines_with_interval('BTCUSDT', '1w', 180)
        elif choice == '4':
            example_create_2day_klines('BTCUSDT', 30)
        elif choice == '5':
            example_create_5day_klines('BTCUSDT', 60)
        elif choice == '6':
            example_get_klines_with_interval('BTCUSDT', '4h', 30)
        elif choice == '0':
            print("\n退出")
            return
        else:
            print("\n无效选项")
            
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

