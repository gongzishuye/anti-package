# K线数据获取指南

## 币安支持的K线间隔

### 🟢 原生支持（可直接获取）

#### 分钟级别
- `1m` - 1分钟
- `3m` - 3分钟
- `5m` - 5分钟
- `15m` - 15分钟
- `30m` - 30分钟

#### 小时级别
- `1h` - 1小时
- `2h` - 2小时
- `4h` - 4小时
- `6h` - 6小时
- `8h` - 8小时
- `12h` - 12小时

#### 日/周/月级别
- `1d` - 1日（日K） ✓
- `3d` - 3日 ✓ **有3日K线**
- `1w` - 1周（周K） ✓
- `1M` - 1月（月K） ✓

### 🔴 不支持（需要聚合）

- `2d` - 2日 ❌ **没有直接的2日K线**
- `5d` - 5日 ❌ **没有直接的5日K线**

## 解决方案

### 方案1：使用3日K线（最接近）

如果你需要类似2日或5日的中期数据，可以使用币安原生支持的**3日K线**：

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 获取3日K线
df = fetcher.get_klines('BTCUSDT', days=90, interval='3d')
```

### 方案2：聚合1日K线创建2日/5日K线

如果一定需要2日或5日K线，可以通过聚合1日K线来实现：

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 方法A：手动聚合
# 1. 先获取1日K线
df_1d = fetcher.get_klines('BTCUSDT', days=30, interval='1d')

# 2. 聚合为2日K线
df_2d = fetcher.aggregate_to_n_days(df_1d, n_days=2)

# 3. 聚合为5日K线
df_5d = fetcher.aggregate_to_n_days(df_1d, n_days=5)
```

### 方案3：批量获取前100代币的2日/5日K线

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 获取前100个代币的2日K线（自动聚合）
df = fetcher.fetch_top_n_daily_data(
    days=16,
    delay=0.2,
    top_n=100,
    interval='1d',      # 使用1日K线
    aggregate_days=2    # 自动聚合为2日K线
)

# 保存数据
fetcher.save_to_csv(df, 'top100_2day_klines.csv')
```

## 完整使用示例

### 示例1：获取单个币种的不同周期K线

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 1日K线
df_1d = fetcher.get_klines('BTCUSDT', days=30, interval='1d')

# 3日K线（币安原生）
df_3d = fetcher.get_klines('BTCUSDT', days=90, interval='3d')

# 周K线
df_1w = fetcher.get_klines('BTCUSDT', days=180, interval='1w')

# 4小时K线
df_4h = fetcher.get_klines('BTCUSDT', days=30, interval='4h')
```

### 示例2：创建2日K线

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 获取1日K线
df_1d = fetcher.get_klines('BTCUSDT', days=30, interval='1d')
print(f"1日K线: {len(df_1d)} 根")

# 聚合为2日K线
df_2d = fetcher.aggregate_to_n_days(df_1d, n_days=2)
print(f"2日K线: {len(df_2d)} 根")

# 显示数据
print(df_2d[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())
```

### 示例3：创建5日K线

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 获取1日K线
df_1d = fetcher.get_klines('BTCUSDT', days=60, interval='1d')
print(f"1日K线: {len(df_1d)} 根")

# 聚合为5日K线
df_5d = fetcher.aggregate_to_n_days(df_1d, n_days=5)
print(f"5日K线: {len(df_5d)} 根")

# 显示数据
print(df_5d[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail())
```

### 示例4：批量获取前100代币的2日K线

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 自动获取并聚合为2日K线
df = fetcher.fetch_top_n_daily_data(
    days=16,            # 获取16天的数据
    delay=0.2,          # 请求间隔
    top_n=100,          # 前100个代币
    interval='1d',      # 使用1日K线
    aggregate_days=2    # 聚合为2日K线
)

print(f"总共获取 {len(df)} 根2日K线")
print(f"涵盖 {df['symbol'].nunique()} 个代币")

# 保存
fetcher.save_to_csv(df)
```

### 示例5：批量获取前100代币的5日K线

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 自动获取并聚合为5日K线
df = fetcher.fetch_top_n_daily_data(
    days=30,            # 获取30天的数据
    delay=0.2,
    top_n=100,
    interval='1d',
    aggregate_days=5    # 聚合为5日K线
)

print(f"总共获取 {len(df)} 根5日K线")
print(f"涵盖 {df['symbol'].nunique()} 个代币")

# 保存
fetcher.save_to_csv(df)
```

## 聚合规则说明

当使用 `aggregate_to_n_days()` 聚合K线时，遵循以下规则：

- **开盘价 (open)**: 取周期内第一根K线的开盘价
- **最高价 (high)**: 取周期内所有K线的最高价
- **最低价 (low)**: 取周期内所有K线的最低价
- **收盘价 (close)**: 取周期内最后一根K线的收盘价
- **成交量 (volume)**: 周期内所有成交量求和
- **USDT成交量 (quote_asset_volume)**: 周期内所有USDT成交量求和
- **交易次数 (number_of_trades)**: 周期内所有交易次数求和

## 运行示例程序

我创建了完整的示例程序，可以直接运行：

```bash
# 查看K线间隔说明
python3 kline_intervals_example.py

# 运行使用示例
python3 kline_usage_examples.py
```

## 推荐方案

根据你的需求：

| 需求 | 推荐方案 | 原因 |
|------|---------|------|
| 2日K线 | 方案1：使用3日K线<br>方案2：聚合1日K线 | 3日线最接近，或自行聚合 |
| 5日K线 | 聚合1日K线 | 周线(7日)略大，聚合更精确 |
| 3日K线 | 直接使用3日K线 | 币安原生支持，速度快 |
| 周线 | 直接使用周K线(1w) | 币安原生支持 |

## 注意事项

1. **数据对齐**: 聚合时按自然日对齐，可能与交易日不完全一致
2. **时区**: 币安日K线以北京时间早上8点为收盘时间
3. **数据完整性**: 聚合前请确保1日K线数据完整
4. **性能**: 原生支持的K线（如3日）获取速度更快

## 快速测试

```bash
# 测试获取不同周期的K线
python3 kline_usage_examples.py
```

选择示例3或4来测试2日和5日K线的创建。

