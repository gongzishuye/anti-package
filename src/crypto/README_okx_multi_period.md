# OKX多周期数据获取工具 - 现货&合约支持

## 概述

`okx_fetch_multi_period_data.py` 工具已升级，现在支持同时获取现货和合约的多周期K线数据，与 `fetch_multi_period_data.py` 保持一致的API接口。

## 主要特性

- ✅ **双市场支持**: 现货 (SPOT) 和合约 (SWAP)
- ✅ **多周期数据**: 1日、3日、周K线
- ✅ **自动文件命名**: 根据市场类型自动添加前缀
- ✅ **Excel格式**: 多sheet保存，便于分析
- ✅ **命令行支持**: 完整的参数配置

## 使用方法

### 命令行使用

#### 获取现货数据
```bash
# 获取现货Top100代币的多周期数据
python3 src/crypto/okx_fetch_multi_period_data.py --market-type spot --top-n 100

# 自定义周期天数
python3 src/crypto/okx_fetch_multi_period_data.py \
    --market-type spot \
    --top-n 50 \
    --days-1d 16 \
    --days-3d 30 \
    --days-week 180

# 自动模式（用于脚本）
python3 src/crypto/okx_fetch_multi_period_data.py \
    --market-type spot \
    --top-n 100 \
    --auto
```

#### 获取合约数据
```bash
# 获取合约Top100代币的多周期数据
python3 src/crypto/okx_fetch_multi_period_data.py --market-type futures --top-n 100

# 自定义周期天数
python3 src/crypto/okx_fetch_multi_period_data.py \
    --market-type futures \
    --top-n 50 \
    --days-1d 16 \
    --days-3d 30 \
    --days-week 180
```

### Python API使用

```python
from okx_fetch_multi_period_data import fetch_all_periods_data, save_to_excel

# 获取现货数据
spot_data = fetch_all_periods_data(
    top_n=100,
    days_for_daily=16,
    days_for_3d=30,
    days_for_week=180,
    market_type='spot'
)

# 获取合约数据
futures_data = fetch_all_periods_data(
    top_n=100,
    days_for_daily=16,
    days_for_3d=30,
    days_for_week=180,
    market_type='futures'
)

# 保存数据
spot_file = save_to_excel(spot_data, top_n=100, market_type='spot')
futures_file = save_to_excel(futures_data, top_n=100, market_type='futures')
```

## 参数说明

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--market-type` | 选择 | spot | 市场类型：spot(现货) 或 futures(合约) |
| `--top-n` | 整数 | 100 | 获取前N个代币 |
| `--days-1d` | 整数 | 16 | 1日K线获取天数 |
| `--days-3d` | 整数 | 30 | 3日K线获取天数 |
| `--days-week` | 整数 | 180 | 周K线获取天数 |
| `--auto` | 标志 | False | 自动模式，直接保存Excel |

### days参数含义

- `--days-1d 16`: 获取16根日K线（约16天）
- `--days-3d 30`: 获取30根3日K线（约90天）
- `--days-week 180`: 获取180根周K线（约1260天）

## 输出文件

### 现货数据文件
```
okx_top100_multi_period_20251005_115016.xlsx
```

### 合约数据文件
```
okx_futures_top100_multi_period_20251005_115027.xlsx
```

### Excel文件结构
每个Excel文件包含3个sheet：
- **1日K线**: 日K线数据
- **3日K线**: 3日K线数据  
- **周K线**: 周K线数据

## 数据格式

与Binance数据格式完全一致：

```python
columns = [
    'symbol', 'timestamp', 'close_time', 'open', 'high', 'low', 'close',
    'volume', 'quote_asset_volume', 'number_of_trades'
]
```

### 现货交易对格式
- `BTC-USDT`
- `ETH-USDT`
- `OKB-USDT`

### 合约交易对格式
- `BTC-USDT-SWAP`
- `ETH-USDT-SWAP`
- `SATS-USDT-SWAP`

## 示例输出

### 现货数据示例
```
================================================================================
OKX Top100 现货代币多周期K线数据获取工具
================================================================================

将获取以下周期的K线数据:
  - 1日K线（最近16天）
  - 3日K线（最近30天）
  - 周K线（最近180天）

【1日K线】 总记录数: 1600, 代币数量: 100
【3日K线】 总记录数: 3000, 代币数量: 100  
【周K线】  总记录数: 18000, 代币数量: 100
```

### 合约数据示例
```
================================================================================
OKX Top100 合约代币多周期K线数据获取工具
================================================================================

【1日K线】 总记录数: 1600, 代币数量: 100
【3日K线】 总记录数: 3000, 代币数量: 100
【周K线】  总记录数: 18000, 代币数量: 100
```

## 与Binance工具的兼容性

两个工具现在具有完全一致的接口：

```python
# Binance
from fetch_multi_period_data import fetch_all_periods_data
bn_data = fetch_all_periods_data(top_n=100, market_type='spot')

# OKX  
from okx_fetch_multi_period_data import fetch_all_periods_data
okx_data = fetch_all_periods_data(top_n=100, market_type='spot')
```

## 运行示例

```bash
# 运行示例脚本
python3 src/crypto/example_okx_multi_period.py

# 查看帮助
python3 src/crypto/okx_fetch_multi_period_data.py --help
```

## 注意事项

1. **API限制**: OKX API有请求频率限制，建议设置适当的延迟
2. **文件保存**: 数据保存到 `data/` 目录
3. **依赖安装**: 需要安装 `openpyxl` 用于Excel文件处理
4. **数据对齐**: K线数据按交易所规则对齐

## 更新日志

- ✅ 添加合约市场支持
- ✅ 统一API接口设计
- ✅ 自动文件命名前缀
- ✅ 完整的命令行参数支持
- ✅ 与Binance工具完全兼容
