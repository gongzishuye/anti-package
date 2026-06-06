# OKX数据获取器 - days参数详解

## 📚 核心概念

**`days` 参数表示的是你想要获取多少个K线周期的数据，而不是日历天数！**

## 🔍 不同周期的days含义

| K线周期 | days=10的含义 | 实际时间跨度 | 数据条数 |
|---------|---------------|--------------|----------|
| `1d` (日K线) | 获取10根日K线 | ~10个日历日 | 10条 |
| `3d` (3日K线) | 获取10根3日K线 | ~30个日历日 | 10条 |
| `1w` (周K线) | 获取10根周K线 | ~70个日历日 | 10条 |

## 🎯 回答你的问题

**问题：如果我要获取1w粒度的kline数据，days传入10表示什么意思？**

**答案：**
- `days=10, interval='1w'` 表示获取 **10根周K线**
- 时间跨度约为 **70个日历日**（10 × 7天）
- 返回 **10条数据记录**

## 📊 实际示例

### 示例1：获取周K线数据
```python
# 获取10根周K线
df = fetcher.get_klines('BTC-USDT', days=10, interval='1w')
# 结果：10条记录，时间跨度约70天
```

### 示例2：获取日K线数据
```python
# 获取10根日K线  
df = fetcher.get_klines('BTC-USDT', days=10, interval='1d')
# 结果：10条记录，时间跨度约10天
```

## 🔄 代码内部逻辑

在 `fetch_top_n_daily_data` 方法中，系统会根据周期自动调整实际获取的天数：

```python
# 根据周期确定获取天数
if interval == '1d':
    actual_days = days          # 日K线：直接使用days
elif interval == '3d':
    actual_days = days * 3      # 3日K线：days × 3
elif interval == '1w':
    actual_days = days * 7      # 周K线：days × 7
```

## 💡 常见使用场景

### 场景1：获取过去10周的数据
```python
df = fetcher.fetch_top_n_daily_data(
    days=10,           # 10根周K线
    interval='1w',     # 周K线
    top_n=100
)
```

### 场景2：获取过去70天的日K线数据
```python
df = fetcher.fetch_top_n_daily_data(
    days=70,           # 70根日K线
    interval='1d',     # 日K线
    top_n=100
)
```

### 场景3：获取相同时间跨度的不同周期数据
```python
# 约70天的数据，不同粒度
df_daily = fetcher.fetch_top_n_daily_data(days=70, interval='1d')   # 70条日K线
df_weekly = fetcher.fetch_top_n_daily_data(days=10, interval='1w')  # 10条周K线
```

## ⚠️ 注意事项

1. **API限制**：OKX API最多返回300条记录
2. **时间跨度**：实际获取的时间跨度可能略多于计算值
3. **数据对齐**：K线数据按交易所规则对齐（如周K线从周日开始）

## 🎯 快速参考

| 你想要... | 设置参数 |
|-----------|----------|
| 过去10天的日K线 | `days=10, interval='1d'` |
| 过去10周的周K线 | `days=10, interval='1w'` |
| 过去30天的3日K线 | `days=10, interval='3d'` |
| 过去70天的数据 | `days=70, interval='1d'` 或 `days=10, interval='1w'` |
