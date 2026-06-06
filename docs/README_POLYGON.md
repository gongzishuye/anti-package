# Polygon.io 美股数据获取指南

## 简介

本项目已支持使用 Polygon.io API 获取美股市场数据，替代之前的富途 API。Polygon.io 提供更稳定、更全面的美股市场数据服务。

## API 文档

- [每日市场摘要 API](https://polygon.io/docs/rest/stocks/aggregates/daily-market-summary)
- 端点: `GET /v2/aggs/grouped/locale/us/market/stocks/{date}`
- 功能: 获取指定日期所有美股的 OHLC（开盘价、最高价、最低价、收盘价）、成交量和 VWAP 数据

## 快速开始

### 1. 获取 API 密钥

1. 访问 [Polygon.io](https://polygon.io/)
2. 注册账户（有免费套餐）
3. 在 [Dashboard - API Keys](https://polygon.io/dashboard/api-keys) 获取 API 密钥

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
POLYGON_KEY=your-api-key-here
```

或者在 shell 中设置：

```bash
export POLYGON_KEY='your-api-key-here'
```

💡 **提示**: 代码也支持 `POLYGON_API_KEY` 变量名，但推荐使用 `POLYGON_KEY`。

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

或单独安装：

```bash
pip install requests pandas openpyxl python-dotenv
```

### 4. 运行示例

```bash
# 基本用法
python src/equity/polygon_us_stock_fetcher.py

# 运行测试
python src/equity/test_polygon.py
```

## 使用方法

### 基本用法

```python
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher

# 创建获取器
fetcher = PolygonUSStockFetcher()

# 获取指定日期的市场数据
df = fetcher.get_daily_market_summary('2024-10-07')

# 打印摘要
fetcher.print_summary(df)

# 保存数据
fetcher.save_to_csv(df)
fetcher.save_to_excel(df)
```

### 获取最近交易日数据

```python
# 获取最近一个交易日的数据
df = fetcher.get_latest_market_summary(days_back=1)
```

### 获取多日数据

```python
# 获取一段时间内的数据
df = fetcher.get_multi_day_summary(
    start_date='2024-10-01',
    end_date='2024-10-07'
)
```

### 参数说明

- `adjusted`: 是否调整拆股（默认 True）
- `include_otc`: 是否包含 OTC 证券（默认 False）

## 数据字段说明

返回的 DataFrame 包含以下字段：

| 字段 | 说明 | 原始字段 |
|------|------|----------|
| symbol | 股票代码 | T |
| open | 开盘价 | o |
| high | 最高价 | h |
| low | 最低价 | l |
| close | 收盘价 | c |
| volume | 成交量 | v |
| vwap | 成交量加权平均价 | vw |
| transactions | 交易次数 | n |
| timestamp | 时间戳（毫秒） | t |
| is_otc | 是否为 OTC 证券 | otc |
| datetime | 转换后的日期时间 | - |
| date | 数据日期 | - |

## API 限制

### 免费套餐 (Stocks Basic)

- 访问权限: ✓
- 数据时效: 延迟到交易日结束
- 历史数据: 2 年
- 请求频率: 5 请求/分钟

### 付费套餐

不同套餐有不同的限制，请查看 [Polygon.io 定价](https://polygon.io/pricing) 了解详情。

## 功能特性

✅ 获取所有美股的每日 OHLC 数据  
✅ 支持调整拆股  
✅ 支持 OTC 证券  
✅ 自动处理周末和非交易日  
✅ 支持多日数据批量获取  
✅ 数据可导出为 CSV 和 Excel  
✅ 内置数据摘要和统计分析  

## 常见问题

### Q: API 返回 401 错误？
A: 请检查 API 密钥是否正确设置，是否已过期。

### Q: API 返回 403 错误？
A: 权限不足，请检查您的订阅计划是否支持该 API。

### Q: API 返回空数据？
A: 可能原因：
- 指定日期是非交易日（周末、节假日）
- 数据还未发布（免费套餐有延迟）
- 日期超出您订阅计划的历史范围

### Q: 请求频率超限？
A: 免费套餐限制为 5 请求/分钟，请在代码中添加适当的延迟。

## 与富途 API 的对比

| 特性 | Polygon.io | 富途 API |
|------|-----------|---------|
| 部署方式 | REST API（云端） | 需要本地 FutuOpenD |
| 依赖 | 仅需 HTTP 客户端 | 需要客户端软件 |
| 稳定性 | 高 | 中等 |
| 数据覆盖 | 全市场 | 取决于账户权限 |
| 使用复杂度 | 低 | 中等 |
| 成本 | 有免费套餐 | 需要富途账户 |

## 示例输出

```
正在获取 2024-10-07 的美股市场摘要数据...
✓ 成功获取 8234 只股票的数据
  查询数量: 8234
  结果数量: 8234
  是否调整: True

数据摘要
================================================================================
总记录数: 8234
日期范围: 2024-10-07
总成交量: 12,456,789,012

涨幅前 5 名:
symbol    open    close    volume  change_pct
AAPL    175.50  182.30  98234567      3.87
TSLA    245.20  258.90  76543210      5.58
...

成交量前 10 名:
symbol    close     volume        vwap
AAPL    182.30  98234567     180.25
MSFT    325.50  67891234     323.75
...
```

## 进阶功能

### 数据分析示例

```python
# 计算涨跌幅
df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100

# 筛选大涨股票
gainers = df[df['change_pct'] > 5].sort_values('change_pct', ascending=False)

# 筛选大成交量股票
high_volume = df[df['volume'] > df['volume'].quantile(0.9)]

# 筛选高价股
high_price = df[df['close'] > 100]
```

### 与现有数据整合

```python
# 可以将 Polygon.io 数据与加密货币数据整合
from src.crypto.binance_data_fetcher import BinanceDataFetcher

# 获取美股数据
polygon_fetcher = PolygonUSStockFetcher()
us_stocks = polygon_fetcher.get_latest_market_summary()

# 获取加密货币数据
binance_fetcher = BinanceDataFetcher()
crypto_data = binance_fetcher.fetch_spot_data(days=1)

# 进行跨市场分析
# ...
```

## 参考链接

- [Polygon.io 官网](https://polygon.io/)
- [API 文档](https://polygon.io/docs)
- [定价方案](https://polygon.io/pricing)
- [Dashboard](https://polygon.io/dashboard)

## 许可证

本代码遵循项目主许可证。使用 Polygon.io API 需遵守其[服务条款](https://polygon.io/terms)。


