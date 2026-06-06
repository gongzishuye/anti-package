#!/usr/bin/env python3
"""
测试 yfinance Quick Start 示例代码

参考: https://ranaroussi.github.io/yfinance/
"""

import sys
import os
import time

try:
    import yfinance as yf
except ImportError:
    print("错误: 未安装 yfinance")
    print("请运行: pip install yfinance")
    sys.exit(1)

import pandas as pd

# 设置pandas显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


def test_single_ticker():
    """测试单个ticker"""
    print("="*80)
    print("测试1: 单个ticker符号")
    print("="*80)
    
    print("\n代码: dat = yf.Ticker('MSFT')")
    
    try:
        dat = yf.Ticker("MSFT")
        print("✓ Ticker对象创建成功")
        
        # 测试 info
        print("\n测试: dat.info")
        try:
            info = dat.info
            if info:
                print(f"✓ 获取info成功")
                print(f"  公司名称: {info.get('longName', 'N/A')}")
                print(f"  当前价格: ${info.get('currentPrice', 'N/A')}")
                print(f"  市值: ${info.get('marketCap', 'N/A'):,}" if info.get('marketCap') else "  市值: N/A")
            else:
                print("⚠️  info为空")
        except Exception as e:
            print(f"✗ 获取info失败: {e}")
        
        # 测试 calendar
        print("\n测试: dat.calendar")
        try:
            calendar = dat.calendar
            if calendar is not None and not calendar.empty:
                print(f"✓ 获取calendar成功")
                print(calendar)
            else:
                print("⚠️  calendar为空")
        except Exception as e:
            print(f"✗ 获取calendar失败: {e}")
        
        # 测试 analyst_price_targets
        print("\n测试: dat.analyst_price_targets")
        try:
            targets = dat.analyst_price_targets
            if targets is not None and not targets.empty:
                print(f"✓ 获取analyst_price_targets成功")
                print(targets)
            else:
                print("⚠️  analyst_price_targets为空")
        except Exception as e:
            print(f"✗ 获取analyst_price_targets失败: {e}")
        
        # 测试 quarterly_income_stmt
        print("\n测试: dat.quarterly_income_stmt")
        try:
            income = dat.quarterly_income_stmt
            if income is not None and not income.empty:
                print(f"✓ 获取quarterly_income_stmt成功")
                print(f"  形状: {income.shape}")
                print(income.head())
            else:
                print("⚠️  quarterly_income_stmt为空")
        except Exception as e:
            print(f"✗ 获取quarterly_income_stmt失败: {e}")
        
        # 测试 history
        print("\n测试: dat.history(period='1mo')")
        try:
            hist = dat.history(period='1mo')
            if hist is not None and not hist.empty:
                print(f"✓ 获取history成功")
                print(f"  记录数: {len(hist)}")
                print(f"  日期范围: {hist.index[0]} 至 {hist.index[-1]}")
                print(f"  最新收盘价: ${hist['Close'].iloc[-1]:.2f}")
                print("\n  最新5条数据:")
                print(hist.tail())
            else:
                print("⚠️  history为空")
        except yf.exceptions.YFRateLimitError as e:
            print(f"✗ 速率限制错误: {e}")
            print("⚠️  当前IP被速率限制")
        except Exception as e:
            print(f"✗ 获取history失败: {e}")
        
        # 测试 options
        print("\n测试: dat.options 和 option_chain")
        try:
            options = dat.options
            if options and len(options) > 0:
                print(f"✓ 获取options成功")
                print(f"  可用期权日期: {options[:5]}")
                
                # 测试 option_chain
                try:
                    chain = dat.option_chain(options[0])
                    if chain:
                        print(f"✓ 获取option_chain成功")
                        if hasattr(chain, 'calls') and not chain.calls.empty:
                            print(f"  Calls数量: {len(chain.calls)}")
                        if hasattr(chain, 'puts') and not chain.puts.empty:
                            print(f"  Puts数量: {len(chain.puts)}")
                except Exception as e:
                    print(f"✗ 获取option_chain失败: {e}")
            else:
                print("⚠️  options为空")
        except Exception as e:
            print(f"✗ 获取options失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ 创建Ticker对象失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_tickers():
    """测试多个ticker"""
    print("\n" + "="*80)
    print("测试2: 多个ticker符号")
    print("="*80)
    
    print("\n代码: tickers = yf.Tickers('MSFT AAPL GOOG')")
    
    try:
        tickers = yf.Tickers('MSFT AAPL GOOG')
        print("✓ Tickers对象创建成功")
        
        # 测试访问单个ticker的info
        print("\n测试: tickers.tickers['MSFT'].info")
        try:
            msft_info = tickers.tickers['MSFT'].info
            if msft_info:
                print(f"✓ 获取MSFT info成功")
                print(f"  公司名称: {msft_info.get('longName', 'N/A')}")
            else:
                print("⚠️  MSFT info为空")
        except Exception as e:
            print(f"✗ 获取MSFT info失败: {e}")
        
        # 测试 yf.download
        print("\n测试: yf.download(['MSFT', 'AAPL', 'GOOG'], period='1mo')")
        try:
            print("等待5秒以避免速率限制...")
            time.sleep(5)
            
            data = yf.download(['MSFT', 'AAPL', 'GOOG'], period='1mo', progress=False)
            if data is not None and not data.empty:
                print(f"✓ 批量下载成功")
                print(f"  数据形状: {data.shape}")
                print(f"  列名: {list(data.columns.levels[0]) if isinstance(data.columns, pd.MultiIndex) else list(data.columns)}")
                print("\n  最新5条数据:")
                print(data.tail())
            else:
                print("⚠️  数据为空")
        except yf.exceptions.YFRateLimitError as e:
            print(f"✗ 速率限制错误: {e}")
            print("⚠️  当前IP被速率限制")
        except Exception as e:
            print(f"✗ 批量下载失败: {e}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"✗ 创建Tickers对象失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_funds():
    """测试基金数据"""
    print("\n" + "="*80)
    print("测试3: 基金数据")
    print("="*80)
    
    print("\n代码: spy = yf.Ticker('SPY').funds_data")
    
    try:
        spy = yf.Ticker('SPY')
        print("✓ SPY Ticker对象创建成功")
        
        # 测试 funds_data
        print("\n测试: spy.funds_data")
        try:
            funds_data = spy.funds_data
            if funds_data:
                print(f"✓ 获取funds_data成功")
                
                # 测试 description
                print("\n测试: spy.funds_data.description")
                try:
                    desc = funds_data.description
                    if desc:
                        print(f"✓ 获取description成功")
                        print(f"  描述长度: {len(desc)} 字符")
                        print(f"  前200字符: {desc[:200]}...")
                    else:
                        print("⚠️  description为空")
                except Exception as e:
                    print(f"✗ 获取description失败: {e}")
                
                # 测试 top_holdings
                print("\n测试: spy.funds_data.top_holdings")
                try:
                    holdings = funds_data.top_holdings
                    if holdings is not None and not holdings.empty:
                        print(f"✓ 获取top_holdings成功")
                        print(f"  持仓数量: {len(holdings)}")
                        print(holdings.head(10))
                    else:
                        print("⚠️  top_holdings为空")
                except Exception as e:
                    print(f"✗ 获取top_holdings失败: {e}")
            else:
                print("⚠️  funds_data为空")
        except Exception as e:
            print(f"✗ 获取funds_data失败: {e}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"✗ 创建SPY Ticker对象失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("="*80)
    print("yfinance Quick Start 测试")
    print("参考: https://ranaroussi.github.io/yfinance/")
    print("="*80)
    
    # 测试1: 单个ticker
    result1 = test_single_ticker()
    
    # 等待一段时间避免速率限制
    if result1:
        print("\n等待10秒后继续测试...")
        time.sleep(10)
    
    # 测试2: 多个ticker
    result2 = test_multiple_tickers()
    
    # 等待一段时间避免速率限制
    if result2:
        print("\n等待10秒后继续测试...")
        time.sleep(10)
    
    # 测试3: 基金数据
    result3 = test_funds()
    
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    print(f"单个ticker测试: {'✓ 通过' if result1 else '✗ 失败'}")
    print(f"多个ticker测试: {'✓ 通过' if result2 else '✗ 失败'}")
    print(f"基金数据测试: {'✓ 通过' if result3 else '✗ 失败'}")
    print("="*80)


if __name__ == "__main__":
    main()
