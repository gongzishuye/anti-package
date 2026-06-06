# 北京时间K线数据获取说明

## 📅 时间设置说明

### 收盘时间对比

| 模式 | K线收盘时间 | 适用场景 |
|------|------------|---------|
| **北京时间模式** | 每天早上8:00 | 符合中国用户习惯，每天早上8点作为日线收盘 |
| **UTC时间模式** | 每天凌晨0:00 UTC | 国际标准时间，全球统一 |

### 时区转换

- **北京时间 = UTC+8**
- 北京时间早上8:00 = UTC时间凌晨0:00
- 这意味着使用北京时间模式，每根日K线从前一天8:00到当天8:00

## 🔧 技术实现

### 币安API支持

程序使用币安的 `/api/v3/uiKlines` 接口，该接口支持 `timeZone` 参数：

```python
params = {
    'symbol': 'BTCUSDT',
    'interval': '1d',
    'timeZone': '+08:00',  # 北京时间 UTC+8
    'startTime': start_timestamp,
    'endTime': end_timestamp
}
```

### 默认行为

**所有程序默认使用北京时间模式（早上8点收盘）**

这样设置是因为：
1. 更符合中国用户的使用习惯
2. 与国内股市收盘时间更接近
3. 便于与其他中国市场数据对比

## 🚀 使用方法

### 方法1：使用默认设置（北京时间）

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 默认使用北京时间（早上8点收盘）
df = fetcher.fetch_top_n_daily_data(days=30, top_n=100)
```

### 方法2：明确指定北京时间

```python
# 显式指定使用北京时间
df = fetcher.fetch_top_n_daily_data(
    days=30, 
    top_n=100, 
    use_beijing_time=True  # 北京时间模式
)
```

### 方法3：使用UTC时间

```python
# 如果需要使用UTC时间（0点收盘）
df = fetcher.fetch_top_n_daily_data(
    days=30, 
    top_n=100, 
    use_beijing_time=False  # UTC时间模式
)
```

### 单个Token获取

```python
# 获取单个Token的K线数据
# 北京时间模式
btc_df = fetcher.get_daily_klines('BTCUSDT', days=30, use_beijing_time=True)

# UTC时间模式
btc_df = fetcher.get_daily_klines('BTCUSDT', days=30, use_beijing_time=False)
```

## 📊 数据示例对比

### 北京时间模式（早上8:00收盘）

```
timestamp: 2025-10-02 08:00:00
close_time: 2025-10-03 07:59:59
```

这根K线包含：
- 开始时间：2025-10-02 08:00:00（北京时间）
- 结束时间：2025-10-03 07:59:59（北京时间）

### UTC时间模式（凌晨0:00收盘）

```
timestamp: 2025-10-02 00:00:00
close_time: 2025-10-02 23:59:59
```

这根K线包含：
- 开始时间：2025-10-02 00:00:00（UTC时间）
- 结束时间：2025-10-02 23:59:59（UTC时间）

## ⚠️ 重要提示

### 1. 筛选规则的影响

如果你使用 `token_filter.py` 进行筛选，请注意：
- 筛选器基于CSV文件中的timestamp字段
- 确保数据获取和筛选使用相同的时间模式
- 北京时间模式下，"最新日期"指的是早上8点收盘的那根K线

### 2. 数据一致性

**建议始终使用同一种时间模式**，以保持数据分析的一致性：
- 获取数据时使用北京时间
- 筛选数据时也基于北京时间
- 分析数据时理解时间含义

### 3. 历史数据对比

如果你之前获取过UTC时间的数据：
- 两种模式的K线数据会有差异
- 北京时间模式的K线会比UTC时间模式晚8小时
- 不要混合使用两种模式的数据

## 📝 示例代码

### 完整使用示例

```python
#!/usr/bin/env python3
from binance_data_fetcher import BinanceDataFetcher

# 创建数据获取器
fetcher = BinanceDataFetcher()

# 获取前100个Token，30天数据，北京时间模式
print("获取北京时间模式的K线数据...")
df = fetcher.fetch_top_n_daily_data(
    days=30,
    delay=0.2,
    top_n=100,
    use_beijing_time=True  # 早上8点收盘
)

# 保存数据
if not df.empty:
    filename = fetcher.save_to_csv(df)
    print(f"数据已保存: {filename}")
    
    # 查看数据信息
    print(f"\n数据范围:")
    print(f"最早时间: {df['timestamp'].min()}")
    print(f"最晚时间: {df['timestamp'].max()}")
    
    # 查看BTC的最新K线
    btc_data = df[df['symbol'] == 'BTCUSDT'].tail(1)
    print(f"\nBTC最新K线:")
    print(btc_data[['timestamp', 'close_time', 'open', 'close', 'volume']])
```

### 简化版程序使用

```bash
# 运行简化版（默认北京时间）
python3 run_without_deps.py
```

简化版程序也默认使用北京时间模式，你会看到输出：
```
开始获取 100 个代币的 7 天日线数据（北京时间（早上8点收盘））...
```

## 🎯 最佳实践

1. **使用北京时间模式**（推荐）
   - 符合中国用户习惯
   - 便于理解和分析
   - 与国内交易时间对应

2. **保持一致性**
   - 整个项目使用同一时间模式
   - 在README中注明使用的时间模式
   - 文件名中标注时间模式（可选）

3. **文档记录**
   - 记录数据获取时使用的时间模式
   - 在数据分析报告中说明时间基准
   - 与团队成员统一时间标准

## 🔍 验证方法

如何验证获取的数据确实是北京时间：

```python
import pandas as pd

# 读取数据
df = pd.read_csv('your_data_file.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 查看某个Token的时间
btc = df[df['symbol'] == 'BTCUSDT']
print(btc[['timestamp', 'close_time']].head())

# 检查时间是否在早上8点附近
# 北京时间模式下，timestamp应该是 XX:XX:XX 08:00:00 或类似格式
```

---

**更新时间**: 2025-10-02
**版本**: v2.0 - 支持北京时间K线
