#!/usr/bin/env python3
"""
测试北京时间K线数据获取
"""

import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta

def test_beijing_time_klines():
    """测试北京时间K线接口"""
    
    print("="*60)
    print("测试币安K线时区设置")
    print("="*60)
    
    # 计算时间范围
    end_time = datetime.now()
    start_time = end_time - timedelta(days=3)
    
    # 测试1：北京时间模式
    print("\n【测试1】北京时间模式（早上8点收盘）")
    print("-"*60)
    
    params_beijing = {
        'symbol': 'BTCUSDT',
        'interval': '1d',
        'startTime': int(start_time.timestamp() * 1000),
        'endTime': int(end_time.timestamp() * 1000),
        'timeZone': '+08:00',
        'limit': 10
    }
    
    url_beijing = f"https://api.binance.com/api/v3/uiKlines?{urllib.parse.urlencode(params_beijing)}"
    
    try:
        with urllib.request.urlopen(url_beijing) as response:
            data_beijing = json.loads(response.read().decode('utf-8'))
            
        print(f"获取到 {len(data_beijing)} 条K线记录")
        print("\n最近3条K线（北京时间）：")
        for i, kline in enumerate(data_beijing[-3:], 1):
            open_time = datetime.fromtimestamp(kline[0] / 1000)
            close_time = datetime.fromtimestamp(kline[6] / 1000)
            print(f"\n{i}. 开盘时间: {open_time}")
            print(f"   收盘时间: {close_time}")
            print(f"   开盘价: ${float(kline[1]):,.2f}")
            print(f"   收盘价: ${float(kline[4]):,.2f}")
            print(f"   成交量: {float(kline[5]):,.2f}")
            
            # 验证时间
            if open_time.hour == 8 or open_time.hour == 0:
                print(f"   ✓ 时间正确：{open_time.hour}点")
            else:
                print(f"   ⚠ 时间可能不对：{open_time.hour}点")
    
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 测试2：UTC时间模式
    print("\n\n【测试2】UTC时间模式（凌晨0点收盘）")
    print("-"*60)
    
    params_utc = {
        'symbol': 'BTCUSDT',
        'interval': '1d',
        'startTime': int(start_time.timestamp() * 1000),
        'endTime': int(end_time.timestamp() * 1000),
        'limit': 10
    }
    
    url_utc = f"https://api.binance.com/api/v3/klines?{urllib.parse.urlencode(params_utc)}"
    
    try:
        with urllib.request.urlopen(url_utc) as response:
            data_utc = json.loads(response.read().decode('utf-8'))
            
        print(f"获取到 {len(data_utc)} 条K线记录")
        print("\n最近3条K线（UTC时间）：")
        for i, kline in enumerate(data_utc[-3:], 1):
            open_time = datetime.fromtimestamp(kline[0] / 1000)
            close_time = datetime.fromtimestamp(kline[6] / 1000)
            print(f"\n{i}. 开盘时间: {open_time}")
            print(f"   收盘时间: {close_time}")
            print(f"   开盘价: ${float(kline[1]):,.2f}")
            print(f"   收盘价: ${float(kline[4]):,.2f}")
            print(f"   成交量: {float(kline[5]):,.2f}")
    
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 对比说明
    print("\n\n" + "="*60)
    print("时区对比说明")
    print("="*60)
    print("\n北京时间模式（timeZone='+08:00'）：")
    print("  • 每根日K线从早上8:00开始，到次日7:59:59结束")
    print("  • 适合中国用户使用习惯")
    print("  • 与国内市场时间对应")
    print("\nUTC时间模式（默认）：")
    print("  • 每根日K线从0:00开始，到23:59:59结束")
    print("  • 国际标准时间")
    print("  • 全球统一标准")
    
    print("\n建议：使用北京时间模式，更符合中国用户习惯！")
    print("="*60)

if __name__ == "__main__":
    test_beijing_time_klines()
