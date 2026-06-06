# 币安前100代币日线数据获取工具

这个Python项目可以从币安交易所获取交易量前100的代币日线K线数据。

## 功能特点

- 🚀 自动获取币安交易量前100的USDT交易对
- 📊 获取每个代币的日线K线数据（开盘价、最高价、最低价、收盘价、成交量等）
- 💾 数据保存为CSV格式，便于后续分析
- 🔄 支持自定义获取天数
- ⚡ 内置API请求限制保护，避免触发币安API限制
- 🔧 支持币安测试网和正式网

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

### 方法1：使用环境变量（推荐）

1. 复制 `.env.example` 文件为 `.env`：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的币安API密钥：
```env
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
BINANCE_TESTNET=False
```

**注意：** 如果没有API密钥，程序会使用公开API（无需密钥），但可能有请求频率限制。

### 方法2：直接在代码中配置

```python
from binance_data_fetcher import BinanceDataFetcher

# 使用API密钥
fetcher = BinanceDataFetcher(
    api_key="your_api_key",
    secret_key="your_secret_key",
    testnet=False
)

# 或者使用公开API（无需密钥）
fetcher = BinanceDataFetcher()
```

## 使用方法

### 基本使用

直接运行主程序：

```bash
python binance_data_fetcher.py
```

这将获取前100个代币最近30天的日线数据并保存为CSV文件。

### 编程使用

```python
from binance_data_fetcher import BinanceDataFetcher

# 创建数据获取器
fetcher = BinanceDataFetcher()

# 获取前100个代币最近30天的数据
df = fetcher.fetch_top_100_daily_data(days=30)

# 保存到CSV文件
fetcher.save_to_csv(df, 'my_data.csv')

# 查看数据
print(df.head())
```

### 自定义参数

```python
# 获取最近7天的数据
df = fetcher.fetch_top_100_daily_data(days=7)

# 调整请求间隔（避免API限制）
df = fetcher.fetch_top_100_daily_data(days=30, delay=0.2)

# 获取指定代币的数据
symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
for symbol in symbols:
    df = fetcher.get_daily_klines(symbol, days=30)
    print(f"{symbol}: {len(df)} 条记录")
```

## 输出数据格式

CSV文件包含以下列：

| 列名 | 说明 |
|------|------|
| symbol | 交易对符号（如 BTCUSDT） |
| timestamp | 开盘时间 |
| close_time | 收盘时间 |
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| close | 收盘价 |
| volume | 成交量 |
| quote_asset_volume | 成交额 |
| number_of_trades | 成交笔数 |

## 注意事项

1. **API限制**: 币安API有请求频率限制，程序内置了延迟保护，但如果获取大量数据可能需要更长时间。

2. **网络连接**: 确保网络连接稳定，程序会自动重试失败的请求。

3. **数据准确性**: 获取的是币安官方数据，但请注意市场数据的时效性。

4. **API密钥**: 虽然程序支持无密钥运行，但建议申请币安API密钥以获得更高的请求限制。

## 错误处理

程序包含完善的错误处理机制：

- 网络连接错误会自动重试
- API限制会通过延迟请求来避免
- 无效的交易对会被跳过
- 所有错误都会在控制台显示详细信息

## 示例输出

```
币安前100代币日线数据获取工具
==================================================
获取到 100 个 USDT 交易对
开始获取 100 个代币的 30 天日线数据...
正在获取 1/100: BTCUSDT
  ✓ 获取到 30 条记录
正在获取 2/100: ETHUSDT
  ✓ 获取到 30 条记录
...

数据统计:
总记录数: 3000
代币数量: 100
日期范围: 2024-01-01 到 2024-01-30

数据已成功保存到: /path/to/binance_top100_daily_20240130_143022.csv
```

## 许可证

MIT License
