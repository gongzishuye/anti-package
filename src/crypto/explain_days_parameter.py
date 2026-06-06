#!/usr/bin/env python3
"""
解释OKX数据获取器中days参数的含义
特别针对不同K线周期的理解
"""

from okx_data_fetcher import OKXDataFetcher
from datetime import datetime, timedelta

def explain_days_parameter():
    """详细解释days参数的含义"""
    
    print("="*80)
    print("OKX数据获取器 - days参数详解")
    print("="*80)
    
    print("\n📚 days参数的含义:")
    print("days参数表示：你想要获取多少个'K线周期'的数据")
    print("注意：这里的'天数'不是指日历天数，而是指K线周期数量！")
    
    print("\n🔍 不同周期的days含义:")
    print("-" * 50)
    
    # 1日K线
    print("📅 1日K线 (interval='1d'):")
    print("  - days=10 表示：获取10根日K线")
    print("  - 时间跨度：约10个日历日")
    print("  - 数据量：10条记录")
    
    # 3日K线
    print("\n📊 3日K线 (interval='3d'):")
    print("  - days=10 表示：获取10根3日K线")
    print("  - 时间跨度：约30个日历日 (10 × 3)")
    print("  - 数据量：10条记录")
    
    # 周K线
    print("\n📈 周K线 (interval='1w'):")
    print("  - days=10 表示：获取10根周K线")
    print("  - 时间跨度：约70个日历日 (10 × 7)")
    print("  - 数据量：10条记录")
    
    print("\n" + "="*80)
    print("实际示例演示")
    print("="*80)
    
    # 创建数据获取器
    fetcher = OKXDataFetcher(market_type='spot')
    
    # 获取一个测试交易对
    symbols = fetcher.get_top_n_tokens('USDT', 1)
    if not symbols:
        print("❌ 无法获取测试交易对")
        return
    
    test_symbol = symbols[0]
    print(f"\n🧪 使用交易对: {test_symbol}")
    
    # 测试不同的days参数
    test_cases = [
        {'interval': '1d', 'days': 5, 'desc': '5根日K线'},
        {'interval': '1w', 'days': 5, 'desc': '5根周K线'},
        {'interval': '1w', 'days': 10, 'desc': '10根周K线'},
    ]
    
    for case in test_cases:
        print(f"\n📊 测试: {case['desc']} (interval={case['interval']}, days={case['days']})")
        print("-" * 40)
        
        try:
            df = fetcher.get_klines(test_symbol, days=case['days'], interval=case['interval'])
            
            if not df.empty:
                print(f"✅ 获取成功:")
                print(f"   - 数据条数: {len(df)}")
                print(f"   - 时间范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}")
                
                # 计算实际时间跨度
                time_span = (df['timestamp'].max() - df['timestamp'].min()).days
                print(f"   - 实际时间跨度: {time_span} 个日历日")
                
                # 显示前几条数据
                print(f"   - 前3条数据:")
                for i, row in df.head(3).iterrows():
                    print(f"     {i+1}. {row['timestamp'].strftime('%Y-%m-%d')} - 收盘价: ${row['close']:.4f}")
            else:
                print("❌ 未获取到数据")
                
        except Exception as e:
            print(f"❌ 获取失败: {e}")
    
    print("\n" + "="*80)
    print("💡 关键理解")
    print("="*80)
    print("1. days=10, interval='1w' 表示：")
    print("   - 获取10根周K线")
    print("   - 不是获取10天的周K线数据")
    print("   - 时间跨度约70个日历日")
    print()
    print("2. 如果你想要过去10周的数据，应该设置：")
    print("   - days=10, interval='1w'")
    print()
    print("3. 如果你想要过去70天的数据，应该设置：")
    print("   - days=70, interval='1d'")
    print("   - 或者 days=10, interval='1w' (约70天)")
    
    print("\n" + "="*80)
    print("🎯 总结")
    print("="*80)
    print("days参数 = 想要的K线根数")
    print("实际时间跨度 = days × 单个K线周期长度")
    print("="*80)

if __name__ == "__main__":
    explain_days_parameter()
