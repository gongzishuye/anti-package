# BinanceDataFetcher 现货与合约数据支持

## 功能概述

`BinanceDataFetcher` 类现在支持获取币安的现货和合约数据。用户可以通过 `market_type` 参数来选择获取哪种类型的数据。

## 新增功能

### 1. 市场类型选择

- **现货数据** (`market_type='spot'`) - 默认选项
- **合约数据** (`market_type='futures'`)

### 2. 支持的方法

所有原有方法都已更新支持市场类型选择：

- `get_top_n_tokens()` - 获取Top N交易对
- `get_klines()` - 获取K线数据  
- `fetch_top_n_daily_data()` - 批量获取数据
- `save_to_csv()` - 保存数据（自动区分文件名）

## 使用方法

### 基本用法

```python
from binance_data_fetcher import BinanceDataFetcher

# 获取现货数据（默认）
spot_fetcher = BinanceDataFetcher()
# 或者明确指定
spot_fetcher = BinanceDataFetcher(market_type='spot')

# 获取合约数据
futures_fetcher = BinanceDataFetcher(market_type='futures')
```

### 命令行使用

```bash
# 获取现货数据（默认）
python3 src/crypto/binance_data_fetcher.py --market-type spot --top-n 10

# 获取合约数据
python3 src/crypto/binance_data_fetcher.py --market-type futures --top-n 10

# 查看帮助
python3 src/crypto/binance_data_fetcher.py --help
```

### 完整示例

```python
# 对比现货和合约数据
spot_fetcher = BinanceDataFetcher(market_type='spot')
futures_fetcher = BinanceDataFetcher(market_type='futures')

# 获取Top5交易对
spot_symbols = spot_fetcher.get_top_n_tokens(top_n=5)
futures_symbols = futures_fetcher.get_top_n_tokens(top_n=5)

# 获取BTCUSDT的K线数据
spot_data = spot_fetcher.get_klines('BTCUSDT', days=7)
futures_data = futures_fetcher.get_klines('BTCUSDT', days=7)

# 批量获取数据
spot_df = spot_fetcher.fetch_top_n_daily_data(top_n=10, days=7)
futures_df = futures_fetcher.fetch_top_n_daily_data(top_n=10, days=7)

# 保存数据（文件名会自动区分）
spot_file = spot_fetcher.save_to_csv(spot_df)
futures_file = futures_fetcher.save_to_csv(futures_df)
```

## 数据差异

### 交易对差异

现货和合约市场的交易对可能不同：

- **现货独有**: USDCUSDT, XPLUSDT 等
- **合约独有**: AIAUSDT, ALPACAUSDT 等  
- **共同交易对**: BTCUSDT, ETHUSDT, SOLUSDT 等

### 成交量差异

合约市场的成交量通常远大于现货市场：

```
ETHUSDT 3日成交量对比:
- 现货: $3.12B
- 合约: $28.77B  
- 合约/现货比: 9.21x
```

### 价格差异

现货和合约价格可能存在小幅差异（通常<0.1%）：

```
ETHUSDT 最新价格:
- 现货: $4487.22
- 合约: $4485.42
- 价差: -$1.80 (-0.0401%)
```

## 文件命名

保存的文件会自动根据市场类型命名：

- 现货: `binance_spot_top_n_daily_YYYYMMDD_HHMMSS.csv`
- 合约: `binance_futures_top_n_daily_YYYYMMDD_HHMMSS.csv`

## 运行示例

查看完整的使用示例：

```bash
python3 src/crypto/example_market_types.py
```

这个示例会展示：
- 现货vs合约交易对对比
- 价格和成交量差异分析
- 不同市场类型的使用方法
- 批量数据处理

## 注意事项

1. **API限制**: 现货和合约使用不同的API端点，各自有独立的请求频率限制
2. **数据格式**: 两种市场的数据格式完全一致，便于后续处理
3. **时间同步**: 现货和合约数据的时间戳都是UTC时间，收盘时间都是北京时间早上8点
4. **错误处理**: 如果某个市场的数据获取失败，不会影响另一个市场的操作
