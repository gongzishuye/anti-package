# Token筛选器使用指南

## 概述

`token_filter_multi_period.py` 是一个多周期Token筛选工具，能够从Excel文件中的多个sheet中筛选符合条件的Token。支持自动查找最新文件和指定输入文件路径。

## 主要特性

- ✅ **自动文件查找**: 自动查找data目录下的最新Excel文件
- ✅ **指定输入文件**: 支持通过命令行参数指定输入文件路径
- ✅ **多周期筛选**: 支持1日、3日、周K线数据筛选
- ✅ **智能筛选条件**: 成交量增长 + 技术形态分析
- ✅ **多种输出格式**: Excel和CSV格式支持
- ✅ **自动模式**: 支持自动化脚本使用

## 使用方法

### 命令行参数

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--input` | `-i` | 输入Excel文件路径 | `--input /path/to/file.xlsx` |
| `--output` | `-o` | 输出文件名前缀 | `--output my_results` |
| `--auto` | - | 自动模式，直接保存Excel | `--auto` |

### 使用示例

#### 1. 自动模式（推荐）
```bash
# 自动查找最新文件并筛选
python3 src/crypto/token_filter_multi_period.py --auto
```

#### 2. 指定输入文件
```bash
# 指定特定的Excel文件
python3 src/crypto/token_filter_multi_period.py \
    --input /home/ubuntu/code/anti-package/data/top200_multi_period_20251005_110139.xlsx \
    --auto
```

#### 3. 自定义输出文件名
```bash
# 指定输出文件前缀
python3 src/crypto/token_filter_multi_period.py \
    --input /path/to/input.xlsx \
    --output my_analysis \
    --auto
```

#### 4. 交互模式
```bash
# 交互式选择保存方式
python3 src/crypto/token_filter_multi_period.py
```

#### 5. 查看帮助
```bash
python3 src/crypto/token_filter_multi_period.py --help
```

## 支持的文件格式

### 自动查找支持的文件模式
- `binance_top*_multi_period_*.xlsx`
- `binance_futures_top*_multi_period_*.xlsx`
- `okx_top*_multi_period_*.xlsx`
- `okx_futures_top*_multi_period_*.xlsx`
- `*_top*_multi_period_*.xlsx` (通用模式)
- `top*_multi_period_*.xlsx` (简化模式)
- `futures_top*_multi_period_*.xlsx` (合约模式)

### Excel文件结构要求
Excel文件应包含多个sheet，每个sheet对应一个周期：
- **1日**: 日K线数据
- **3日**: 3日K线数据
- **周**: 周K线数据

## 筛选条件

### 技术指标要求
1. **成交量增长**: T-1成交量 > T-2成交量
2. **技术形态**: T-2为阴线（收盘价 < 开盘价）
3. **反转信号**: T-1为阳线且收盘价 > T-2开盘价

### 数据要求
- 每个Token需要至少3个周期的数据
- 自动使用每个Token最新的3个周期进行分析
- 支持多个周期的并发筛选

## 输出结果

### Excel输出格式
每个sheet包含以下列：
- `symbol`: 代币符号
- `T_minus_2_date`: T-2日期
- `T_minus_2_open/high/low/close`: T-2价格数据
- `T_minus_2_volume/quote_asset_volume`: T-2成交量数据
- `T_minus_2_change_pct`: T-2涨跌幅
- `T_minus_1_date`: T-1日期
- `T_minus_1_open/high/low/close`: T-1价格数据
- `T_minus_1_volume/quote_asset_volume`: T-1成交量数据
- `T_minus_1_change_pct`: T-1涨跌幅
- `volume_growth_rate_pct`: 成交量增长率
- `usdt_volume_growth_rate_pct`: USDT成交量增长率

### 文件命名规则
- 默认: `qualified_tokens_multi_period_YYYYMMDD_HHMMSS.xlsx`
- 自定义: `{output_prefix}_YYYYMMDD_HHMMSS.xlsx`

## 示例输出

### 筛选结果摘要
```
================================================================================
筛选结果总览
================================================================================

【1日】
  符合条件: 5 个Token
  平均成交量增长: 40.8%
  最大成交量增长: 80.4%
  Top 5 Token:
    1. ZENUSDT      - 成交量增长:  +38.6% | USDT成交量: 95,791,571
    2. ORDERUSDT    - 成交量增长:  +40.0% | USDT成交量: 70,509,566
    3. DASHUSDT     - 成交量增长:   +8.0% | USDT成交量: 67,867,525
    4. MUSDT        - 成交量增长:  +80.4% | USDT成交量: 65,679,633
    5. AWEUSDT      - 成交量增长:  +37.0% | USDT成交量: 31,665,131

【3日】
  符合条件: 51 个Token
  平均成交量增长: 139.1%
  最大成交量增长: 1638.9%

总计: 所有周期共找到 56 个符合条件的Token
```

## Python API使用

```python
from token_filter_multi_period import MultiPeriodTokenFilter

# 创建筛选器
filter_tool = MultiPeriodTokenFilter('path/to/file.xlsx')

# 筛选所有周期
results = filter_tool.filter_all_periods()

# 筛选单个周期
daily_results = filter_tool.filter_single_period(
    filter_tool.data_dict['1日'], '1日'
)

# 保存结果
output_file = filter_tool.save_results_to_excel(results)
```

## 运行示例

```bash
# 运行示例脚本
python3 src/crypto/example_token_filter.py
```

## 注意事项

1. **文件路径**: 确保Excel文件路径正确
2. **数据格式**: Excel文件必须包含正确的列名和数据类型
3. **权限**: 确保有写入data目录的权限
4. **依赖**: 需要安装pandas和openpyxl库

## 更新日志

- ✅ 添加命令行参数支持
- ✅ 支持指定输入文件路径
- ✅ 支持自定义输出文件名
- ✅ 支持自动模式
- ✅ 扩展文件格式支持
- ✅ 改进错误处理和用户提示
