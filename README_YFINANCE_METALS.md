# yfinance 金银铜数据获取测试

## 简介

使用 `yfinance` 库获取黄金、白银、铜的历史日K线数据。

**优化说明**: 代码使用 `yfinance.download()` 批量下载方式，比逐个使用 `Ticker` 对象更高效，更能避免速率限制。参考 [yfinance官方文档](https://ranaroussi.github.io/yfinance/reference/api/yfinance.EquityQuery.html)。

## 安装依赖

```bash
pip install yfinance pandas openpyxl
```

## 商品代码

### 期货代码（推荐）
- **黄金**: `GC=F` - COMEX黄金期货
- **白银**: `SI=F` - COMEX白银期货  
- **铜**: `HG=F` - COMEX铜期货

### ETF代码（可选）
- **黄金ETF**: `GLD`
- **白银ETF**: `SLV`
- **铜ETF**: `CPER`

## 使用方法

### 基本使用

```bash
python test_yfinance_metals.py
```

### 代码示例

**方式1: 批量下载（推荐，更高效）**

```python
import yfinance as yf
from datetime import datetime, timedelta

# 定义商品代码列表
tickers = ['GC=F', 'SI=F', 'HG=F']  # 黄金、白银、铜

# 获取最近1年的数据
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

# 批量下载所有ticker的数据
data = yf.download(
    tickers,
    start=start_date,
    end=end_date,
    group_by='ticker',
    progress=False
)

# 处理每个ticker的数据
for ticker in tickers:
    df = data[ticker]  # 获取该ticker的数据
    print(f"{ticker} 数据: {len(df)} 条记录")
    print(df.head())
```

**方式2: 逐个下载（备用方法）**

```python
import yfinance as yf
from datetime import datetime, timedelta

# 定义商品代码
tickers = {
    '黄金': 'GC=F',
    '白银': 'SI=F',
    '铜': 'HG=F'
}

# 获取最近1年的数据
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

# 逐个获取数据
for name, ticker in tickers.items():
    ticker_obj = yf.Ticker(ticker)
    df = ticker_obj.history(start=start_date, end=end_date)
    print(f"{name} 数据: {len(df)} 条记录")
    print(df.head())
```

## 输出

测试脚本会：
1. 获取最近1年的历史数据
2. 显示每个商品的基本统计信息
3. 对比分析金银铜的价格相关性
4. 将数据保存到 `data/metals_data.xlsx` 文件

## 数据字段

输出的Excel文件包含以下字段：
- `date`: 日期
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `change_pct`: 涨跌幅百分比
- `commodity`: 商品名称
- `ticker`: 商品代码

## 注意事项

1. **数据延迟**: yfinance 的数据可能有15-20分钟的延迟
2. **期货代码**: 期货代码需要加 `=F` 后缀
3. **数据可用性**: 某些商品可能在某些交易所不可用
4. **网络连接**: 需要稳定的网络连接访问Yahoo Finance API
5. **速率限制**: yfinance 有API速率限制，代码已自动处理：
   - **使用批量下载方式** (`yfinance.download()`)，比逐个下载更高效
   - 自动重试机制（默认3次）
   - 递增等待时间（10秒、20秒、30秒）
   - 如果批量下载失败，自动回退到逐个下载方式

## 常见问题

### Q: 获取不到数据怎么办？
A: 检查网络连接，确认商品代码正确，某些商品可能需要使用不同的代码。

### Q: 数据不准确？
A: yfinance 的数据来自Yahoo Finance，仅供参考。对于交易用途，建议使用专业数据源。

### Q: 如何获取更长时间的数据？
A: 修改 `period` 参数，例如 `period="5y"` 获取5年数据，或使用 `start_date` 和 `end_date` 参数。

### Q: 遇到 "Rate limited" 错误怎么办？
A: 代码已自动处理速率限制：
- 自动重试（最多3次）
- 请求之间自动延迟
- 如果仍然失败，请等待几分钟后重试，或减少请求的商品数量
