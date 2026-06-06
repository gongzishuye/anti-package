# 从富途 API 迁移到 Polygon.io API 指南

## 📋 迁移概述

本指南帮助你从富途 (Futu) API 平滑迁移到 Polygon.io API。

### 为什么迁移？

| 对比项 | 富途 API | Polygon.io API |
|--------|---------|---------------|
| **部署复杂度** | 需要本地 FutuOpenD 客户端 | ✅ 纯 REST API，无需客户端 |
| **依赖** | 需要安装客户端软件 | ✅ 仅需 HTTP 库 |
| **稳定性** | 依赖客户端运行状态 | ✅ 云端服务，高可用 |
| **数据覆盖** | 取决于账户权限 | ✅ 全市场数据 |
| **跨平台** | 需要 GUI 环境 | ✅ 任何平台 |
| **服务器部署** | 困难（需要图形界面） | ✅ 简单（仅需环境变量） |
| **免费额度** | 需要富途账户 | ✅ 有免费套餐 |

## 🔄 API 对照表

### 1. 获取所有股票列表

**富途 API:**
```python
from futu import *

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = quote_ctx.get_stock_basicinfo(Market.US, SecurityType.STOCK)
```

**Polygon.io API:**
```python
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher

fetcher = PolygonUSStockFetcher()
df = fetcher.get_daily_market_summary('2024-10-07')
# 所有交易的股票都会被包含在市场摘要中
```

### 2. 获取实时行情

**富途 API:**
```python
ret, data = quote_ctx.get_market_snapshot(['US.AAPL', 'US.TSLA'])
```

**Polygon.io API:**
```python
# 注意: 免费套餐提供延迟数据，实时数据需要付费套餐
df = fetcher.get_daily_market_summary('2024-10-07')
aapl_data = df[df['symbol'] == 'AAPL']
```

### 3. 获取历史K线数据

**富途 API:**
```python
ret, data, page_req_key = quote_ctx.request_history_kline(
    'US.AAPL', 
    start='2024-01-01', 
    end='2024-10-01',
    ktype=KLType.K_DAY
)
```

**Polygon.io API:**
```python
# 多日数据
df = fetcher.get_multi_day_summary(
    start_date='2024-01-01',
    end_date='2024-10-01'
)
aapl_history = df[df['symbol'] == 'AAPL']
```

### 4. 字段映射

| 富途字段 | Polygon.io 字段 | 说明 |
|---------|----------------|------|
| `code` | `symbol` | 股票代码 |
| `name` | - | Polygon 不提供名称（需要额外查询） |
| `last_price` | `close` | 收盘价 |
| `open_price` | `open` | 开盘价 |
| `high_price` | `high` | 最高价 |
| `low_price` | `low` | 最低价 |
| `volume` | `volume` | 成交量 |
| `turnover` | - | Polygon 不直接提供 |
| - | `vwap` | 成交量加权平均价（Polygon 特有） |
| - | `transactions` | 交易次数（Polygon 特有） |

## 📝 代码迁移示例

### 示例 1: 获取股票列表并筛选

**原代码（富途）:**
```python
from futu import *

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

# 获取股票列表
ret, stocks = quote_ctx.get_stock_basicinfo(Market.US, SecurityType.STOCK)

# 获取行情
stock_codes = stocks['code'].tolist()
ret, quotes = quote_ctx.get_market_snapshot(stock_codes)

# 合并数据
merged = pd.merge(stocks, quotes, on='code')

# 筛选
filtered = merged[
    (merged['last_price'] > 10) &
    (merged['volume'] > 1000000)
]

quote_ctx.close()
```

**新代码（Polygon.io）:**
```python
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher

fetcher = PolygonUSStockFetcher()

# 获取市场数据（已包含所有信息）
df = fetcher.get_latest_market_summary()

# 筛选
filtered = df[
    (df['close'] > 10) &
    (df['volume'] > 1000000)
]

# 无需手动关闭连接
```

### 示例 2: 涨跌幅排行

**原代码（富途）:**
```python
from futu import *

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

# 获取行情
ret, data = quote_ctx.get_market_snapshot(stock_codes)

# 计算涨跌幅
data['change_pct'] = data['change_rate'] * 100

# 排序
gainers = data.nlargest(10, 'change_pct')
losers = data.nsmallest(10, 'change_pct')

quote_ctx.close()
```

**新代码（Polygon.io）:**
```python
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher

fetcher = PolygonUSStockFetcher()
df = fetcher.get_latest_market_summary()

# 计算涨跌幅
df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100

# 排序
gainers = df.nlargest(10, 'change_pct')
losers = df.nsmallest(10, 'change_pct')
```

### 示例 3: 多日数据分析

**原代码（富途）:**
```python
from futu import *
from datetime import datetime, timedelta

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

# 获取历史数据
all_data = []
for stock_code in stock_codes:
    ret, data, _ = quote_ctx.request_history_kline(
        stock_code,
        start='2024-10-01',
        end='2024-10-07',
        ktype=KLType.K_DAY
    )
    if ret == RET_OK:
        data['code'] = stock_code
        all_data.append(data)
    time.sleep(0.1)  # 避免频率限制

df = pd.concat(all_data)
quote_ctx.close()
```

**新代码（Polygon.io）:**
```python
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher

fetcher = PolygonUSStockFetcher()

# 一次性获取所有股票的多日数据
df = fetcher.get_multi_day_summary(
    start_date='2024-10-01',
    end_date='2024-10-07'
)
# df 已包含所有股票的多日数据
```

## 🚀 快速迁移步骤

### 第 1 步: 安装依赖

```bash
# 不再需要 futu-api
pip uninstall futu-api

# 安装 Polygon.io 需要的库（已在 requirements.txt）
pip install requests pandas python-dotenv openpyxl
```

### 第 2 步: 配置 API 密钥

```bash
# 在 .env 文件中添加
POLYGON_KEY=your-api-key-here
# 或使用 POLYGON_API_KEY=your-api-key-here（两者都支持）
```

### 第 3 步: 更新导入语句

**替换:**
```python
from futu import *
from src.equity.us_stock_fetcher import USStockFetcher
```

**为:**
```python
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher
```

### 第 4 步: 更新初始化代码

**替换:**
```python
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
# 或
fetcher = USStockFetcher(host='127.0.0.1', port=11111)
```

**为:**
```python
fetcher = PolygonUSStockFetcher()
```

### 第 5 步: 更新数据获取逻辑

参考上面的"API 对照表"和"代码迁移示例"。

### 第 6 步: 测试

```bash
python3 src/equity/polygon_us_stock_fetcher.py
```

## ⚠️ 注意事项

### 1. 数据延迟

- **富途**: 取决于账户类型
- **Polygon.io 免费套餐**: 延迟到交易日结束
- **Polygon.io 付费套餐**: 可获取实时数据

### 2. 字段差异

Polygon.io 不直接提供股票名称，如需名称需要：

```python
# 方案 1: 使用额外的 API 查询股票详情
# 方案 2: 维护本地的股票代码-名称映射表
```

### 3. API 限制

**富途**:
- 每次请求最多 200 只股票
- 需要多次请求获取全市场数据

**Polygon.io**:
- 单次请求获取全市场数据
- 免费套餐: 5 请求/分钟
- 建议添加延迟: `time.sleep(12)`

### 4. 历史数据范围

**富途**: 取决于账户权限  
**Polygon.io**:
- 免费套餐: 2 年
- 付费套餐: 更长历史

## 🔧 迁移工具函数

为了平滑迁移，可以创建适配器函数：

```python
def futu_to_polygon_adapter(polygon_df):
    """
    将 Polygon.io 数据格式转换为类似富途的格式
    """
    df = polygon_df.copy()
    
    # 字段映射
    df = df.rename(columns={
        'symbol': 'code',
        'close': 'last_price',
        'open': 'open_price',
        'high': 'high_price',
        'low': 'low_price'
    })
    
    # 计算涨跌幅（类似富途的 change_rate）
    df['change_rate'] = ((df['last_price'] - df['open_price']) / df['open_price'])
    
    return df

# 使用示例
fetcher = PolygonUSStockFetcher()
polygon_data = fetcher.get_latest_market_summary()
futu_like_data = futu_to_polygon_adapter(polygon_data)
```

## 📊 功能对比

| 功能 | 富途 API | Polygon.io API | 备注 |
|------|---------|---------------|------|
| 股票列表 | ✅ | ✅ | Polygon 通过市场摘要获取 |
| 实时行情 | ✅ | ⭐ 付费 | Polygon 免费套餐有延迟 |
| 历史K线 | ✅ | ✅ | |
| 盘口数据 | ✅ | ❌ | Polygon 不提供 |
| 财务数据 | ✅ | ⭐ 额外 API | 需要其他端点 |
| 交易功能 | ✅ | ❌ | Polygon 仅提供数据 |
| VWAP | ❌ | ✅ | Polygon 特有 |
| 交易次数 | ❌ | ✅ | Polygon 特有 |

## 🎯 迁移检查清单

- [ ] 获取 Polygon.io API 密钥
- [ ] 配置环境变量
- [ ] 更新 requirements.txt
- [ ] 替换导入语句
- [ ] 更新初始化代码
- [ ] 调整数据获取逻辑
- [ ] 更新字段引用
- [ ] 测试核心功能
- [ ] 调整 API 调用频率
- [ ] 更新错误处理
- [ ] 测试生产环境

## 📚 相关资源

- [Polygon.io 快速开始](./POLYGON_QUICKSTART.md)
- [Polygon.io 完整文档](./README_POLYGON.md)
- [示例代码](../examples/polygon_examples.py)
- [Polygon.io 官方文档](https://polygon.io/docs)

## 💡 最佳实践

1. **逐步迁移**: 先在测试环境验证，再迁移生产代码
2. **保留备份**: 迁移前备份原代码
3. **监控日志**: 注意 API 错误和限制
4. **优化请求**: 利用 Polygon.io 的批量特性减少请求次数
5. **缓存数据**: 避免重复请求相同数据

## ❓ 常见问题

### Q: 迁移需要多长时间？
A: 简单项目 1-2 小时，复杂项目 1-2 天。

### Q: 如何处理实时数据需求？
A: 如需实时数据，需要升级到 Polygon.io 付费套餐。

### Q: 迁移后性能如何？
A: 通常更好，因为：
- 单次请求获取更多数据
- 无需本地客户端
- 云端服务响应快

### Q: 可以同时使用两个 API 吗？
A: 可以，但建议尽快完成迁移以减少维护成本。

---

祝迁移顺利！🚀 如有问题，请参考 [完整文档](./README_POLYGON.md) 或提交 issue。


