# 多周期K线数据获取工具

## 功能介绍

一键获取币安Top100代币的多周期K线数据：
- **1日K线**：最近16天
- **3日K线**：最近30天  
- **周K线**：最近180天（约26周）

所有数据保存在**一个Excel文件的不同sheet**中，方便对比分析。

## 快速开始

### 方法1：使用启动脚本（推荐）

```bash
./fetch_multi_period.sh
```

### 方法2：直接运行Python

```bash
python3 fetch_multi_period_data.py
```

## 输出格式

### 选项1：Excel文件（推荐）

生成一个Excel文件，包含3个sheet：

```
binance_top100_multi_period_20251003_120000.xlsx
├── Sheet "1日K线"  - 1600条记录（100币种 × 16天）
├── Sheet "3日K线"  - 1000条记录（100币种 × 10个3日周期）
└── Sheet "周K线"   - 2600条记录（100币种 × 26周）
```

**优点：**
- 所有数据在一个文件中
- 可以方便地在不同sheet间切换查看
- Excel中可以直接分析和制图

### 选项2：多个CSV文件

如果无法安装openpyxl，会生成3个独立CSV文件：

```
binance_top100_20251003_120000_1dkline.csv
binance_top100_20251003_120000_3dkline.csv
binance_top100_20251003_120000_weekkline.csv
```

## 数据字段说明

每个sheet/文件包含以下字段：

| 字段 | 说明 |
|------|------|
| symbol | 交易对符号（如BTCUSDT） |
| timestamp | K线开盘时间 |
| close_time | K线收盘时间 |
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| close | 收盘价 |
| volume | 成交量 |
| quote_asset_volume | USDT成交量 |
| number_of_trades | 交易次数 |

## 配置参数

可以在 `fetch_multi_period_data.py` 中修改以下参数：

```python
TOP_N = 100        # 获取前N个代币
DAYS_1D = 16       # 1日K线获取天数
DAYS_3D = 30       # 3日K线获取天数
DAYS_WEEK = 180    # 周K线获取天数
```

## 使用示例

### 编程使用

```python
from fetch_multi_period_data import fetch_all_periods_data, save_to_excel

# 获取数据
data_dict = fetch_all_periods_data(
    top_n=100,
    days_for_daily=16,
    days_for_3d=30,
    days_for_week=180
)

# 保存到Excel
save_to_excel(data_dict, 'my_data.xlsx')
```

### 分析数据

```python
import pandas as pd

# 读取Excel文件
excel_file = 'binance_top100_multi_period_20251003_120000.xlsx'

# 读取不同周期的数据
df_1d = pd.read_excel(excel_file, sheet_name='1日K线')
df_3d = pd.read_excel(excel_file, sheet_name='3日K线')
df_week = pd.read_excel(excel_file, sheet_name='周K线')

# 查看某个币种的数据
btc_1d = df_1d[df_1d['symbol'] == 'BTCUSDT']
print(btc_1d[['timestamp', 'close', 'volume']])
```

## 依赖安装

需要安装openpyxl以支持Excel格式：

```bash
pip3 install openpyxl
```

或添加到系统包：

```bash
pip3 install openpyxl --break-system-packages
```

## 运行时间

- **获取Top100的1日K线**：约3-5分钟
- **获取Top100的3日K线**：约3-5分钟
- **获取Top100的周K线**：约3-5分钟
- **总计**：约10-15分钟

*注：时间取决于网络速度和API响应速度*

## 常见问题

### Q1: 为什么选择这些周期？

- **1日K线（16天）**：适合短期分析，覆盖最近2周多的交易日
- **3日K线（30天）**：适合中期趋势分析
- **周K线（180天）**：适合长期趋势分析，覆盖半年

### Q2: 可以获取更多天数的数据吗？

可以，修改脚本中的参数即可：

```python
# 在 fetch_multi_period_data.py 的 main() 函数中修改
DAYS_1D = 30      # 获取30天的1日K线
DAYS_3D = 60      # 获取60天的3日K线
DAYS_WEEK = 365   # 获取1年的周K线
```

### Q3: 为什么不获取2日或5日K线？

币安API原生支持：1日、3日、周（7日）、月线

如需2日或5日K线，可使用聚合功能：

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 获取2日K线
df = fetcher.fetch_top_n_daily_data(
    days=16,
    top_n=100,
    interval='1d',
    aggregate_days=2  # 聚合为2日
)
```

### Q4: Excel文件太大怎么办？

1. 减少天数：
   ```python
   DAYS_1D = 10      # 减少到10天
   DAYS_3D = 20      # 减少到20天
   DAYS_WEEK = 90    # 减少到3个月
   ```

2. 减少币种数量：
   ```python
   TOP_N = 50        # 只获取前50个
   ```

3. 使用CSV格式（文件更小）

### Q5: 如何只获取特定周期？

修改 `fetch_multi_period_data.py` 的 `fetch_all_periods_data()` 函数，注释掉不需要的部分。

或直接使用 `binance_data_fetcher.py`：

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()

# 只获取周K线
df = fetcher.fetch_top_n_daily_data(
    days=180,
    top_n=100,
    interval='1w'
)

fetcher.save_to_csv(df, 'week_klines.csv')
```

## 输出示例

```
================================================================================
币安Top100代币多周期K线数据获取工具
================================================================================

将获取以下周期的K线数据:
  - 1日K线（最近16天）
  - 3日K线（最近30天）
  - 周K线（最近180天）

================================================================================
开始获取Top 100 代币的多周期K线数据
================================================================================

【1/3】获取1日K线数据...
--------------------------------------------------------------------------------
获取到 100 个 USDT 交易对
开始获取 100 个代币的 16 天 1d K线数据...
正在获取 1/100: BTCUSDT
  ✓ 获取到 16 条记录
...
✓ 1日K线: 1600 条记录，100 个代币

【2/3】获取3日K线数据...
--------------------------------------------------------------------------------
...

【3/3】获取周K线数据...
--------------------------------------------------------------------------------
...

================================================================================
保存数据到Excel文件...
================================================================================
✓ Sheet '1日K线': 1600 行 x 10 列
✓ Sheet '3日K线': 1000 行 x 10 列
✓ Sheet '周K线': 2600 行 x 10 列

✓ 数据已成功保存到: binance_top100_multi_period_20251003_120000.xlsx
  文件大小: 458.23 KB
  包含 3 个sheet

💡 提示: 使用Excel打开文件，可以看到3个sheet标签页

================================================================================
✓ 所有任务完成！
================================================================================
```

## 相关文件

- `fetch_multi_period_data.py` - 主程序
- `fetch_multi_period.sh` - 启动脚本
- `binance_data_fetcher.py` - 币安数据获取核心库
- `KLINE_GUIDE.md` - K线数据详细指南

## 注意事项

1. 获取大量数据需要时间，请耐心等待
2. 确保网络连接稳定
3. 币安API有请求频率限制，脚本已内置延迟保护
4. Excel文件用Excel、WPS或LibreOffice打开
5. CSV文件用任何文本编辑器或Excel打开

