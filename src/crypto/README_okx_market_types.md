# OKX数据获取器 - 现货&合约支持

## 概述

`OKXDataFetcher` 类已升级，现在支持同时获取现货和合约数据，与 `BinanceDataFetcher` 保持一致的API接口。

## 主要特性

- ✅ **双市场支持**: 现货 (SPOT) 和合约 (SWAP)
- ✅ **统一API接口**: 与BinanceDataFetcher完全兼容
- ✅ **自动文件命名**: 根据市场类型自动添加前缀
- ✅ **数据格式一致**: 输出格式与Binance保持一致
- ✅ **灵活配置**: 支持命令行参数配置

## 使用方法

### 基本用法

```python
from okx_data_fetcher import OKXDataFetcher

# 创建现货数据获取器
spot_fetcher = OKXDataFetcher(market_type='spot')

# 创建合约数据获取器  
futures_fetcher = OKXDataFetcher(market_type='futures')
```

### 获取交易对列表

```python
# 获取现货前10个交易对
spot_symbols = spot_fetcher.get_top_n_tokens('USDT', 10)
print(spot_symbols)  # ['BTC-USDT', 'ETH-USDT', 'OKB-USDT', ...]

# 获取合约前10个交易对
futures_symbols = futures_fetcher.get_top_n_tokens('USDT', 10)
print(futures_symbols)  # ['SATS-USDT-SWAP', 'PEPE-USDT-SWAP', ...]
```

### 获取K线数据

```python
# 获取现货K线数据
spot_df = spot_fetcher.fetch_top_n_daily_data(
    days=16,
    top_n=100,
    interval='1d'
)

# 获取合约K线数据
futures_df = futures_fetcher.fetch_top_n_daily_data(
    days=16,
    top_n=100,
    interval='1d'
)
```

### 保存数据

```python
# 自动文件名前缀
spot_fetcher.save_to_csv(spot_df)  # okx_spot_top_n_daily_20251005_112453.csv
futures_fetcher.save_to_csv(futures_df)  # okx_futures_top_n_daily_20251005_112453.csv
```

## 命令行使用

### 现货数据获取

```bash
# 获取现货前10个代币的5天数据
python3 src/crypto/okx_data_fetcher.py --market-type spot --top-n 10 --days 5
```

### 合约数据获取

```bash
# 获取合约前10个代币的5天数据
python3 src/crypto/okx_data_fetcher.py --market-type futures --top-n 10 --days 5
```

## 数据格式

### 现货交易对格式
- `BTC-USDT`
- `ETH-USDT`
- `OKB-USDT`

### 合约交易对格式
- `BTC-USDT-SWAP`
- `ETH-USDT-SWAP`
- `SATS-USDT-SWAP`

## 输出数据格式

与BinanceDataFetcher完全一致：

```python
columns = [
    'symbol', 'timestamp', 'close_time', 'open', 'high', 'low', 'close',
    'volume', 'quote_asset_volume', 'number_of_trades'
]
```

## 示例代码

运行完整示例：

```bash
python3 src/crypto/example_okx_market_types.py
```

## 与BinanceDataFetcher的兼容性

两个数据获取器现在具有完全一致的接口：

```python
# Binance
from binance_data_fetcher import BinanceDataFetcher
bn_spot = BinanceDataFetcher(market_type='spot')
bn_futures = BinanceDataFetcher(market_type='futures')

# OKX
from okx_data_fetcher import OKXDataFetcher
okx_spot = OKXDataFetcher(market_type='spot')
okx_futures = OKXDataFetcher(market_type='futures')

# 相同的API调用
spot_data = bn_spot.fetch_top_n_daily_data(days=16, top_n=100)
okx_spot_data = okx_spot.fetch_top_n_daily_data(days=16, top_n=100)
```

## 注意事项

1. **API限制**: OKX API有请求频率限制，建议设置适当的延迟
2. **数据格式**: 合约交易对以`-SWAP`结尾，现货交易对以`-USDT`结尾
3. **时区**: 数据时间戳使用UTC时区
4. **交易量**: 合约数据使用24小时交易量排序

## 更新日志

- ✅ 添加合约市场支持
- ✅ 统一API接口设计
- ✅ 自动文件命名前缀
- ✅ 完整的命令行参数支持
- ✅ 与BinanceDataFetcher完全兼容
