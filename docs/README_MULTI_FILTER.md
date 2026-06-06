# 多周期Token筛选器

从Excel文件的多个sheet（1日K线、3日K线、周K线）中分别筛选符合条件的Token。

## 功能介绍

自动对多周期K线数据进行筛选，识别出符合特定交易模式的Token：

### 筛选条件（应用于每个周期）

1. **成交量增长**：T-1周期的成交量大于T-2周期
2. **T-2阴线**：T-2是阴线（收盘价 < 开盘价）
3. **T-1阳线反转**：
   - T-1是阳线（收盘价 > 开盘价）
   - T-1收盘价 > T-2开盘价

这个模式通常表示：**在下跌后出现反转，且伴随成交量放大**

## 快速开始

### 前提条件

需要先获取多周期K线数据：

```bash
./fetch_multi_period.sh
```

这将生成 `binance_top100_multi_period_YYYYMMDD_HHMMSS.xlsx`

### 运行筛选

#### 方法1：使用启动脚本

```bash
./filter_multi_period.sh
```

#### 方法2：直接运行Python

```bash
python3 token_filter_multi_period.py
```

**注意**：如果你的Excel文件名不同，需要修改脚本中的文件名：

```python
# 在 token_filter_multi_period.py 的 main() 函数中
excel_file = "你的文件名.xlsx"
```

## 输出文件

### Excel格式（推荐）

生成一个Excel文件，每个周期的筛选结果在独立的sheet中：

```
qualified_tokens_multi_period_20251004_081116.xlsx
├── Sheet "1日筛选结果"  - 1日K线符合条件的Token
├── Sheet "3日筛选结果"  - 3日K线符合条件的Token
└── Sheet "周筛选结果"   - 周K线符合条件的Token
```

### CSV格式（备选）

如果选择CSV格式，会生成多个独立文件：

```
qualified_tokens_20251004_081116_1dkline.csv
qualified_tokens_20251004_081116_3dkline.csv
qualified_tokens_20251004_081116_weekkline.csv
```

## 输出字段说明

每个sheet/文件包含以下字段：

| 字段 | 说明 |
|------|------|
| symbol | 交易对符号 |
| T_minus_2_date | T-2日期 |
| T_minus_2_open | T-2开盘价 |
| T_minus_2_high | T-2最高价 |
| T_minus_2_low | T-2最低价 |
| T_minus_2_close | T-2收盘价 |
| T_minus_2_volume | T-2成交量 |
| T_minus_2_quote_asset_volume | T-2 USDT成交量 |
| T_minus_2_change_pct | T-2涨跌幅(%) |
| T_minus_1_date | T-1日期 |
| T_minus_1_open | T-1开盘价 |
| T_minus_1_high | T-1最高价 |
| T_minus_1_low | T-1最低价 |
| T_minus_1_close | T-1收盘价 |
| T_minus_1_volume | T-1成交量 |
| T_minus_1_quote_asset_volume | T-1 USDT成交量 |
| T_minus_1_change_pct | T-1涨跌幅(%) |
| volume_growth_rate_pct | 成交量增长率(%) |
| usdt_volume_growth_rate_pct | USDT成交量增长率(%) |

## 使用示例

### 示例输出

```
================================================================================
筛选结果总览
================================================================================

【1日K线】
  符合条件: 5 个Token
  平均成交量增长: 150.8%
  最大成交量增长: 432.7%
  Top 5 Token:
    1. OPENUSDT     - 成交量增长: +432.7% | USDT成交量: 75,296,375
    2. 0GUSDT       - 成交量增长: +154.3% | USDT成交量: 55,915,227
    3. LINEAUSDT    - 成交量增长:  +18.4% | USDT成交量: 34,325,839
    4. WUSDT        - 成交量增长:  +42.8% | USDT成交量: 20,084,537
    5. DOLOUSDT     - 成交量增长: +106.0% | USDT成交量: 11,417,144

【3日K线】
  未找到符合条件的Token

【周K线】
  符合条件: 1 个Token
  平均成交量增长: 42.6%
  最大成交量增长: 42.6%
  Top 5 Token:
    1. ETHFIUSDT    - 成交量增长:  +42.6% | USDT成交量: 267,726,956

总计: 所有周期共找到 6 个符合条件的Token
================================================================================
```

### 数据分析示例

```python
import pandas as pd

# 读取筛选结果
excel_file = 'qualified_tokens_multi_period_20251004_081116.xlsx'

# 读取1日K线筛选结果
df_1d = pd.read_excel(excel_file, sheet_name='1日筛选结果')

# 查看成交量增长最大的Token
print("成交量增长Top 5:")
print(df_1d.nlargest(5, 'volume_growth_rate_pct')[
    ['symbol', 'volume_growth_rate_pct', 'T_minus_1_quote_asset_volume']
])

# 查看USDT成交量最大的Token
print("\nUSDT成交量Top 5:")
print(df_1d.nlargest(5, 'T_minus_1_quote_asset_volume')[
    ['symbol', 'T_minus_1_quote_asset_volume', 'volume_growth_rate_pct']
])
```

## 完整工作流程

### 步骤1：获取多周期K线数据

```bash
./fetch_multi_period.sh
```

预计耗时：10-15分钟

输出文件：`binance_top100_multi_period_YYYYMMDD_HHMMSS.xlsx`

### 步骤2：筛选符合条件的Token

```bash
./filter_multi_period.sh
```

或手动指定文件：

```bash
python3 token_filter_multi_period.py
```

预计耗时：< 1分钟

输出文件：`qualified_tokens_multi_period_YYYYMMDD_HHMMSS.xlsx`

### 步骤3：分析结果

使用Excel打开筛选结果文件，查看不同周期的符合条件的Token。

## 筛选逻辑说明

### 为什么选择这些条件？

1. **成交量放大**：表示市场关注度增加
2. **T-2阴线**：价格下跌形成低点
3. **T-1阳线反转**：价格反转向上，突破前期开盘价

这个组合通常出现在：
- 短期调整后的反弹
- 趋势反转的初期
- 突破前期阻力位

### 不同周期的意义

| 周期 | 适用场景 | 时间跨度 |
|------|---------|---------|
| 1日K线 | 短线交易 | 2-5天 |
| 3日K线 | 中短线波段 | 1-2周 |
| 周K线 | 中长线趋势 | 数周至数月 |

## 修改筛选条件

如果你想调整筛选条件，可以编辑 `token_filter_multi_period.py` 中的 `filter_single_period` 方法：

```python
# 原始条件
condition1 = t_minus_1_data_point['volume'] > t_minus_2_data_point['volume']  
condition2 = self.is_bearish_candle(t_minus_2_data_point)  
condition3a = self.is_bullish_candle(t_minus_1_data_point)  
condition3b = t_minus_1_data_point['close'] > t_minus_2_data_point['open']  
condition3 = condition3a and condition3b

# 例如：添加成交量增长的最低要求
condition1_enhanced = (t_minus_1_data_point['volume'] > t_minus_2_data_point['volume']) and \
                     ((t_minus_1_data_point['volume'] / t_minus_2_data_point['volume']) > 1.5)  # 至少增长50%
```

## 常见问题

### Q1: 为什么某个周期没有找到符合条件的Token？

**可能原因：**
- 市场整体走势不符合筛选条件
- 该周期的数据点太少
- 筛选条件过于严格

### Q2: 如何修改Excel文件名？

在 `token_filter_multi_period.py` 的 `main()` 函数中修改：

```python
excel_file = "你的文件名.xlsx"
```

### Q3: 可以只筛选某一个周期吗？

可以，修改 `filter_all_periods()` 方法，或直接调用 `filter_single_period()`：

```python
filter_tool = MultiPeriodTokenFilter(excel_file)
df_1d = filter_tool.data_dict['1日K线']
tokens = filter_tool.filter_single_period(df_1d, '1日K线')
```

### Q4: 筛选结果可以直接用于交易吗？

**警告**：这只是技术分析工具，不构成投资建议。

在使用前请：
1. 结合其他技术指标
2. 考虑基本面分析
3. 设置止损止盈
4. 控制仓位风险

## 相关文件

- `token_filter_multi_period.py` - 多周期筛选脚本（新）
- `filter_multi_period.sh` - 快速启动脚本
- `token_filter.py` - 单文件筛选脚本（原始版本）
- `fetch_multi_period_data.py` - 数据获取脚本
- `binance_data_fetcher.py` - 币安API核心库

## 注意事项

1. **数据时效性**：K线数据有时间延迟，建议定期更新
2. **市场风险**：过去的模式不代表未来表现
3. **流动性**：关注USDT成交量，避免流动性不足的Token
4. **多空分析**：筛选结果偏向多头信号，需结合市场环境判断

## 进阶使用

### 批量处理多个文件

```bash
for file in binance_top100_multi_period_*.xlsx; do
    echo "处理文件: $file"
    python3 token_filter_multi_period.py "$file"
done
```

### 自动化定时任务

```bash
# 添加到crontab
0 9 * * * cd /home/ubuntu/code/anti-package && ./fetch_multi_period.sh && ./filter_multi_period.sh
```

每天早上9点自动获取数据并筛选。

