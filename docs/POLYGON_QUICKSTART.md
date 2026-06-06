# Polygon.io 快速开始指南

## 🚀 5分钟快速上手

### 第一步：获取 API 密钥

1. 访问 [Polygon.io](https://polygon.io/) 并注册账户
2. 登录后访问 [API Keys 页面](https://polygon.io/dashboard/api-keys)
3. 复制你的 API 密钥

💡 **提示**: 免费套餐每分钟可以调用 5 次 API，适合个人使用和测试。

### 第二步：配置环境

在项目根目录创建 `.env` 文件：

```bash
cd /home/ubuntu/code/anti-package
echo "POLYGON_KEY=your-api-key-here" > .env
```

或者手动创建：

```bash
nano .env
```

添加内容：
```
POLYGON_KEY=pk_xxxxxxxxxxxxxxxxxxxxxxxxxx
```

💡 **提示**: 代码也支持 `POLYGON_API_KEY` 变量名，但推荐使用 `POLYGON_KEY`。

### 第三步：运行测试

```bash
# 运行主程序
python3 src/equity/polygon_us_stock_fetcher.py

# 或运行测试程序
python3 src/equity/test_polygon.py
```

## 📊 使用示例

### 示例 1: 获取最近交易日的所有美股数据

```python
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher

# 创建获取器
fetcher = PolygonUSStockFetcher()

# 获取最近一个交易日的数据
df = fetcher.get_latest_market_summary()

print(f"获取到 {len(df)} 只股票数据")
print(df.head())
```

### 示例 2: 获取指定日期的数据

```python
# 获取 2024-10-07 的数据
df = fetcher.get_daily_market_summary('2024-10-07')

# 打印摘要
fetcher.print_summary(df)
```

### 示例 3: 筛选涨幅最大的股票

```python
# 计算涨跌幅
df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100

# 筛选涨幅超过 5% 的股票
gainers = df[df['change_pct'] > 5].sort_values('change_pct', ascending=False)

print("涨幅超过 5% 的股票:")
print(gainers[['symbol', 'open', 'close', 'volume', 'change_pct']].head(10))
```

### 示例 4: 筛选成交量最大的股票

```python
# 获取成交量前 20 名
top_volume = df.nlargest(20, 'volume')[['symbol', 'close', 'volume', 'vwap']]

print("成交量前 20 名:")
print(top_volume)
```

### 示例 5: 保存数据

```python
# 保存为 CSV
fetcher.save_to_csv(df, filename='us_stocks_today.csv', data_dir='data/polygon')

# 保存为 Excel
fetcher.save_to_excel(df, filename='us_stocks_today.xlsx', data_dir='data/polygon')
```

### 示例 6: 获取多日数据

```python
# 获取最近一周的数据
df = fetcher.get_multi_day_summary(
    start_date='2024-10-01',
    end_date='2024-10-07'
)

# 按日期分组统计
daily_stats = df.groupby('date').agg({
    'symbol': 'count',
    'volume': 'sum',
    'close': 'mean'
}).rename(columns={
    'symbol': 'stock_count',
    'volume': 'total_volume',
    'close': 'avg_price'
})

print(daily_stats)
```

## 🔧 高级用法

### 数据筛选与分析

```python
import pandas as pd
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher

fetcher = PolygonUSStockFetcher()
df = fetcher.get_latest_market_summary()

# 计算涨跌幅
df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100

# 多条件筛选
filtered = df[
    (df['volume'] > 1000000) &        # 成交量大于 100 万
    (df['close'] > 10) &              # 股价大于 10 美元
    (df['change_pct'] > 3)            # 涨幅大于 3%
]

print(f"符合条件的股票: {len(filtered)} 只")
print(filtered[['symbol', 'close', 'volume', 'change_pct']].sort_values('change_pct', ascending=False))
```

### 价格区间分析

```python
# 定义价格区间
bins = [0, 10, 50, 100, 500, float('inf')]
labels = ['$0-10', '$10-50', '$50-100', '$100-500', '$500+']

df['price_range'] = pd.cut(df['close'], bins=bins, labels=labels)

# 统计各价格区间的股票数量
price_dist = df['price_range'].value_counts().sort_index()
print("\n价格区间分布:")
print(price_dist)
```

### 成交量分析

```python
# 计算成交量统计信息
volume_stats = df['volume'].describe()
print("\n成交量统计:")
print(volume_stats)

# 筛选异常成交量（大于 75% 分位数的 2 倍）
threshold = df['volume'].quantile(0.75) * 2
high_volume_stocks = df[df['volume'] > threshold]

print(f"\n异常成交量股票（共 {len(high_volume_stocks)} 只）:")
print(high_volume_stocks[['symbol', 'close', 'volume']].sort_values('volume', ascending=False))
```

## 📈 实战案例

### 案例 1: 每日选股策略

```python
from datetime import datetime
from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher

def daily_stock_screening():
    """每日选股"""
    fetcher = PolygonUSStockFetcher()
    df = fetcher.get_latest_market_summary()
    
    # 计算指标
    df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
    df['price_range'] = ((df['high'] - df['low']) / df['low']) * 100
    
    # 选股条件
    selected = df[
        (df['close'] >= 5) &                    # 价格 >= $5
        (df['close'] <= 100) &                  # 价格 <= $100
        (df['volume'] >= 500000) &              # 成交量 >= 50万
        (df['change_pct'] >= 2) &               # 涨幅 >= 2%
        (df['change_pct'] <= 15) &              # 涨幅 <= 15%（排除暴涨）
        (df['price_range'] >= 3)                # 波动 >= 3%
    ].sort_values('volume', ascending=False)
    
    # 保存结果
    today = datetime.now().strftime('%Y%m%d')
    filename = f'selected_stocks_{today}.xlsx'
    fetcher.save_to_excel(
        selected[['symbol', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'change_pct']],
        filename=filename,
        data_dir='data/screened'
    )
    
    print(f"✓ 筛选出 {len(selected)} 只股票")
    print(f"✓ 结果已保存: data/screened/{filename}")
    
    return selected

# 运行选股
stocks = daily_stock_screening()
```

### 案例 2: 行业对比分析

```python
def sector_analysis(df):
    """行业分析（需要额外的行业数据）"""
    # 示例：按首字母分组（实际应该用真实的行业分类）
    df['first_letter'] = df['symbol'].str[0]
    
    sector_stats = df.groupby('first_letter').agg({
        'symbol': 'count',
        'volume': 'sum',
        'close': 'mean',
        'change_pct': 'mean'
    }).round(2)
    
    sector_stats.columns = ['股票数量', '总成交量', '平均价格', '平均涨跌幅']
    
    print("\n行业统计:")
    print(sector_stats.sort_values('平均涨跌幅', ascending=False))
```

## ⚠️ 注意事项

1. **API 限制**
   - 免费套餐: 5 请求/分钟
   - 超过限制会返回 429 错误
   - 建议在循环中添加延迟: `time.sleep(12)`

2. **数据延迟**
   - 免费套餐数据延迟到交易日结束
   - 付费套餐可获取实时数据

3. **非交易日**
   - 周末和节假日无数据
   - 程序会自动查找最近的交易日

4. **历史数据**
   - 免费套餐: 2 年历史数据
   - 付费套餐: 更长历史数据

## 🆚 与富途 API 对比

| 特性 | Polygon.io | 富途 API |
|------|-----------|---------|
| 部署 | ✅ 纯云端 | ❌ 需要本地客户端 |
| 依赖 | ✅ 仅需 requests | ❌ 需要 FutuOpenD |
| 稳定性 | ✅ 高 | ⚠️ 中等 |
| 易用性 | ✅ 简单 | ⚠️ 复杂 |
| 免费额度 | ✅ 有 | ❌ 需要账户 |

## 📚 相关文档

- [Polygon.io 完整文档](./README_POLYGON.md)
- [API 官方文档](https://polygon.io/docs)
- [定价方案](https://polygon.io/pricing)

## 🐛 常见问题

### Q: 如何处理 API 限制？

```python
import time

# 在循环中添加延迟
for date in date_list:
    df = fetcher.get_daily_market_summary(date)
    time.sleep(12)  # 免费套餐建议 12 秒间隔
```

### Q: 如何获取实时数据？

A: 免费套餐不支持实时数据，需要升级到付费套餐。

### Q: 数据为什么是空的？

A: 检查以下几点：
1. 日期是否为交易日（非周末、节假日）
2. 免费套餐是否有数据延迟
3. API 密钥是否有效

## 💡 下一步

1. ✅ 完成基本配置
2. ✅ 测试 API 调用
3. 📊 开发自己的选股策略
4. 🔄 设置定时任务自动获取数据
5. 📈 结合技术分析指标

开始使用 Polygon.io 获取美股数据吧！🚀


