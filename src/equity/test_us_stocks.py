#!/usr/bin/env python3
"""
美股数据获取测试脚本
测试富途API连接和美股数据获取功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from us_stock_fetcher import USStockFetcher
from us_stock_analyzer import USStockAnalyzer
from us_stock_screener import USStockScreener, ScreeningCriteria


def test_connection():
    """测试富途API连接"""
    print("="*80)
    print("测试富途API连接")
    print("="*80)
    
    try:
        with USStockFetcher() as fetcher:
            if fetcher.is_connected:
                print("✓ 富途API连接成功")
                
                # 测试获取市场概览
                print("\n获取市场概览...")
                overview = fetcher.get_market_overview()
                if overview:
                    print("主要指数:")
                    for code, info in overview.items():
                        print(f"  {code}: {info['last_price']} ({info['change_rate']:+.2f}%)")
                else:
                    print("✗ 获取市场概览失败")
                
                return True
            else:
                print("✗ 富途API连接失败")
                return False
                
    except Exception as e:
        print(f"✗ 连接测试异常: {e}")
        return False


def test_stock_search():
    """测试股票搜索"""
    print("\n" + "="*80)
    print("测试股票搜索")
    print("="*80)
    
    try:
        with USStockFetcher() as fetcher:
            if not fetcher.is_connected:
                print("✗ 连接失败，跳过测试")
                return False
            
            # 搜索苹果公司
            print("搜索苹果公司股票...")
            apple_stocks = fetcher.search_stocks("AAPL", limit=5)
            
            if not apple_stocks.empty:
                print("✓ 搜索成功:")
                for _, stock in apple_stocks.iterrows():
                    print(f"  {stock['symbol']}: {stock['name']} ({stock['stock_type']})")
            else:
                print("✗ 搜索失败")
                return False
            
            # 搜索特斯拉
            print("\n搜索特斯拉股票...")
            tesla_stocks = fetcher.search_stocks("TSLA", limit=3)
            
            if not tesla_stocks.empty:
                print("✓ 搜索成功:")
                for _, stock in tesla_stocks.iterrows():
                    print(f"  {stock['symbol']}: {stock['name']}")
            else:
                print("✗ 搜索失败")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ 股票搜索测试异常: {e}")
        return False


def test_stock_snapshot():
    """测试股票快照数据"""
    print("\n" + "="*80)
    print("测试股票快照数据")
    print("="*80)
    
    try:
        with USStockFetcher() as fetcher:
            if not fetcher.is_connected:
                print("✗ 连接失败，跳过测试")
                return False
            
            # 获取知名股票的快照数据
            test_symbols = ['US.AAPL', 'US.TSLA', 'US.MSFT', 'US.GOOG']
            
            print(f"获取 {len(test_symbols)} 只股票的快照数据...")
            snapshots = fetcher.get_stock_snapshot(test_symbols)
            
            if not snapshots.empty:
                print("✓ 快照数据获取成功:")
                for _, stock in snapshots.iterrows():
                    price = stock.get('last_price', 0)
                    change_rate = stock.get('change_rate', 0)
                    volume = stock.get('volume', 0)
                    print(f"  {stock['code']}: ${price:.2f} ({change_rate:+.2f}%) 成交量:{volume:,}")
                
                return True
            else:
                print("✗ 快照数据获取失败")
                return False
                
    except Exception as e:
        print(f"✗ 快照数据测试异常: {e}")
        return False


def test_stock_kline():
    """测试K线数据"""
    print("\n" + "="*80)
    print("测试K线数据")
    print("="*80)
    
    try:
        with USStockFetcher() as fetcher:
            if not fetcher.is_connected:
                print("✗ 连接失败，跳过测试")
                return False
            
            # 获取苹果公司的K线数据
            symbol = 'US.AAPL'
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            print(f"获取 {symbol} 近30天K线数据...")
            kline_data = fetcher.get_stock_kline(symbol, start_date, end_date)
            
            if not kline_data.empty:
                print(f"✓ K线数据获取成功: {len(kline_data)} 条记录")
                
                # 显示最新几条数据
                print("最新5条数据:")
                for _, row in kline_data.tail(5).iterrows():
                    print(f"  {row['time']}: 开{row['open']:.2f} 高{row['high']:.2f} 低{row['low']:.2f} 收{row['close']:.2f} 量{row['volume']:,}")
                
                return True
            else:
                print("✗ K线数据获取失败")
                return False
                
    except Exception as e:
        print(f"✗ K线数据测试异常: {e}")
        return False


def test_technical_analysis():
    """测试技术分析"""
    print("\n" + "="*80)
    print("测试技术分析")
    print("="*80)
    
    try:
        # 先获取K线数据
        with USStockFetcher() as fetcher:
            if not fetcher.is_connected:
                print("✗ 连接失败，跳过测试")
                return False
            
            symbol = 'US.AAPL'
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
            
            print(f"获取 {symbol} K线数据用于分析...")
            kline_data = fetcher.get_stock_kline(symbol, start_date, end_date)
            
            if kline_data.empty:
                print("✗ 无法获取K线数据，跳过技术分析测试")
                return False
        
        # 进行技术分析
        analyzer = USStockAnalyzer()
        
        print("进行技术分析...")
        
        # 计算技术指标
        technical = analyzer.calculate_technical_indicators(kline_data)
        print(f"✓ 技术指标:")
        print(f"  SMA(20): ${technical.sma_20:.2f}")
        print(f"  SMA(50): ${technical.sma_50:.2f}")
        print(f"  RSI: {technical.rsi:.2f}")
        print(f"  MACD: {technical.macd:.4f}")
        
        # 分析价格趋势
        trend = analyzer.analyze_price_trend(kline_data)
        print(f"✓ 趋势分析:")
        print(f"  趋势: {trend['trend']}")
        print(f"  强度: {trend['strength']}")
        print(f"  信号: {trend['signal']}")
        
        # 计算波动率
        volatility = analyzer.calculate_volatility(kline_data)
        print(f"✓ 波动率分析:")
        print(f"  年化波动率: {volatility['volatility']:.2f}%")
        print(f"  最大回撤: {volatility['max_drawdown']:.2f}%")
        
        # 生成交易信号
        signals = analyzer.generate_trading_signals(kline_data)
        print(f"✓ 交易信号:")
        print(f"  最终信号: {signals['final_signal']}")
        print(f"  信心度: {signals['confidence']:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"✗ 技术分析测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stock_screening():
    """测试股票筛选"""
    print("\n" + "="*80)
    print("测试股票筛选")
    print("="*80)
    
    try:
        screener = USStockScreener()
        
        # 测试自定义筛选条件
        print("测试自定义筛选条件...")
        criteria = ScreeningCriteria(
            min_market_cap=10,  # 最小市值10亿美元
            max_pe_ratio=30,    # 最大市盈率30
            min_volume=1000000, # 最小成交量100万
            exclude_etf=True    # 排除ETF
        )
        
        result = screener.screen_stocks(criteria, include_analysis=False)
        
        if result.qualified_stocks > 0:
            print(f"✓ 筛选成功: {result.qualified_stocks} 只股票符合条件")
            
            # 显示前5只股票
            print("前5只股票:")
            for i, (_, stock) in enumerate(result.stocks.head(5).iterrows()):
                symbol = stock.get('symbol', '')
                name = stock.get('name', '')
                price = stock.get('last_price', 0)
                change_rate = stock.get('change_rate', 0)
                print(f"  {i+1}. {symbol}: {name} - ${price:.2f} ({change_rate:+.2f}%)")
            
            return True
        else:
            print("✗ 筛选结果为空")
            return False
            
    except Exception as e:
        print(f"✗ 股票筛选测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_screening():
    """测试策略筛选"""
    print("\n" + "="*80)
    print("测试策略筛选")
    print("="*80)
    
    try:
        screener = USStockScreener()
        
        # 测试价值投资策略
        print("测试价值投资策略...")
        value_result = screener.screen_by_strategy('value', max_pe_ratio=20, max_pb_ratio=3)
        
        if value_result.qualified_stocks > 0:
            print(f"✓ 价值投资策略: {value_result.qualified_stocks} 只股票")
        else:
            print("✗ 价值投资策略无结果")
        
        # 测试成长投资策略
        print("测试成长投资策略...")
        growth_result = screener.screen_by_strategy('growth', max_pe_ratio=40)
        
        if growth_result.qualified_stocks > 0:
            print(f"✓ 成长投资策略: {growth_result.qualified_stocks} 只股票")
        else:
            print("✗ 成长投资策略无结果")
        
        return True
        
    except Exception as e:
        print(f"✗ 策略筛选测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("美股数据获取功能测试")
    print("="*80)
    
    # 检查富途API是否可用
    try:
        import futu
        print("✓ 富途API已安装")
    except ImportError:
        print("✗ 富途API未安装，请运行: pip install futu-api")
        return
    
    # 运行测试
    tests = [
        ("连接测试", test_connection),
        ("股票搜索", test_stock_search),
        ("快照数据", test_stock_snapshot),
        ("K线数据", test_stock_kline),
        ("技术分析", test_technical_analysis),
        ("股票筛选", test_stock_screening),
        ("策略筛选", test_strategy_screening)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} 通过")
            else:
                print(f"✗ {test_name} 失败")
        except Exception as e:
            print(f"✗ {test_name} 异常: {e}")
    
    # 测试结果汇总
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！美股数据获取功能正常")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查相关功能")
    
    print("\n注意事项:")
    print("1. 需要运行FutuOpenD客户端")
    print("2. 需要登录富途账户")
    print("3. 需要开通美股交易权限")
    print("4. 确保网络连接正常")


if __name__ == "__main__":
    main()
