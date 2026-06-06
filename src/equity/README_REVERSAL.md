# 美股反包检测器使用说明

## 功能概述

美股反包检测器（USStockReversalDetector）是一个基于 Polygon.io API 的股票形态检测工具，用于识别符合"反包"形态的美股股票。

## 反包形态定义

反包是一种技术分析形态，表示股票可能从下跌趋势转为上涨。具体定义为：

1. **T-2（前天）是阴线**：收盘价 < 开盘价
2. **T-1（昨天）是阳线**：开盘价 < 收盘价
3. **T-1 收盘价突破 T-2 开盘价**：收盘价(T-1) > 开盘价(T-2)
4. **成交量放大**：成交量(T-1) > 成交量(T-2)

这种形态表明：
- 前天股票下跌
- 昨天不仅反弹，还突破了前天的开盘价
- 成交量放大，说明有资金介入

## 快速开始

### 1. 配置 API 密钥

在项目根目录的 `.env` 文件中配置：

```bash
POLYGON_KEY=your-polygon-api-key-here
```

### 2. 运行检测

```bash
# 运行主程序
python3 src/equity/us_stock_reversal_detector.py

# 或运行测试脚本
python3 src/equity/test_reversal_detector.py
```

## 使用示例

### 示例 1: 基本用法

```python
from src.equity import USStockReversalDetector

# 创建检测器
detector = USStockReversalDetector()

# 运行反包检测
results = detector.run_reversal_detection()

# 查看结果
if not results.empty:
    print(f"找到 {len(results)} 只符合反包条件的股票")
    print(results[['symbol', 'volume_increase_pct', 'reversal_strength']].head())
```

### 示例 2: 自定义数据目录

```python
# 指定数据存储目录
detector = USStockReversalDetector(data_dir='custom/data/path')
results = detector.run_reversal_detection()
```

### 示例 3: 手动指定日期检测

```python
detector = USStockReversalDetector()

# 获取指定日期的数据
data_dict = detector.ensure_data_available(['2024-10-06', '2024-10-07'])

# 手动检测反包
if '2024-10-06' in data_dict and '2024-10-07' in data_dict:
    results = detector.detect_reversal_pattern(
        df_t2=data_dict['2024-10-06'],
        df_t1=data_dict['2024-10-07']
    )
    print(f"符合条件股票: {len(results)}")
```

## 数据存储

### 历史数据文件

- **文件路径**: `src/equity/data/us_stock_daily_history.xlsx`
- **格式**: Excel 文件，每个日期一个 sheet
- **Sheet 命名**: 日期格式 `YYYY-MM-DD`
- **内容**: 当日所有美股的 OHLC、成交量等数据

### 反包结果文件

- **文件路径**: `src/equity/data/us_stock_reversal_results.xlsx`
- **格式**: Excel 文件，每次检测结果一个 sheet
- **Sheet 命名**: 检测日期 `YYYY-MM-DD`
- **内容**: 符合反包条件的股票及相关指标

## 结果字段说明

反包检测结果包含以下字段：

### 基本信息
- `symbol`: 股票代码

### T-2（前天）数据
- `open_t2`: 开盘价
- `close_t2`: 收盘价
- `high_t2`: 最高价
- `low_t2`: 最低价
- `volume_t2`: 成交量
- `t2_change_pct`: 涨跌幅百分比

### T-1（昨天）数据
- `open_t1`: 开盘价
- `close_t1`: 收盘价
- `high_t1`: 最高价
- `low_t1`: 最低价
- `volume_t1`: 成交量
- `t1_change_pct`: 涨跌幅百分比

### 反包指标
- `volume_increase_pct`: 成交量增幅百分比
- `reversal_strength`: 反包强度（T-1收盘价 - T-2开盘价）

## API 说明

### USStockReversalDetector 类

#### 初始化

```python
USStockReversalDetector(api_key=None, data_dir=None)
```

**参数：**
- `api_key` (str, 可选): Polygon.io API 密钥，默认从环境变量读取
- `data_dir` (str, 可选): 数据存储目录，默认为 `src/equity/data`

#### 主要方法

##### run_reversal_detection()

运行完整的反包检测流程。

```python
results = detector.run_reversal_detection()
```

**返回：** 符合反包条件的股票 DataFrame

**流程：**
1. 计算交易日日期（T、T-1、T-2）
2. 检查并获取必要的历史数据
3. 执行反包形态检测
4. 保存检测结果
5. 打印结果摘要

##### detect_reversal_pattern(df_t2, df_t1)

检测反包形态。

```python
results = detector.detect_reversal_pattern(df_t2, df_t1)
```

**参数：**
- `df_t2` (DataFrame): T-2（前天）的数据
- `df_t1` (DataFrame): T-1（昨天）的数据

**返回：** 符合反包条件的股票 DataFrame

##### ensure_data_available(dates)

确保指定日期的数据可用，如果不存在则自动获取。

```python
data_dict = detector.ensure_data_available(['2024-10-06', '2024-10-07'])
```

**参数：**
- `dates` (List[str]): 日期列表，格式 'YYYY-MM-DD'

**返回：** 日期到 DataFrame 的字典

##### get_trading_date(days_back)

获取交易日日期（自动跳过周末）。

```python
yesterday = detector.get_trading_date(1)  # 获取昨天（T-1）
```

**参数：**
- `days_back` (int): 往前推几个交易日，0表示今天

**返回：** 日期字符串 'YYYY-MM-DD'

## 工作流程

1. **日期计算**
   - 计算今天、昨天（T-1）、前天（T-2）的交易日期
   - 自动跳过周末

2. **数据获取**
   - 检查历史数据文件中是否有 T-1 和 T-2 的数据
   - 如果没有，调用 Polygon.io API 获取
   - 将数据保存到 Excel 文件的对应 sheet

3. **形态检测**
   - 合并 T-2 和 T-1 的数据（按 symbol）
   - 应用反包条件筛选股票
   - 计算额外指标（成交量增幅、反包强度等）

4. **结果保存**
   - 将检测结果保存到新的 Excel 文件
   - Sheet 名称为检测日期
   - 按成交量增幅排序

5. **结果展示**
   - 打印检测摘要
   - 显示 TOP 10 股票
   - 显示统计信息

## 使用场景

### 场景 1: 每日自动检测

设置定时任务，每天收盘后自动运行：

```bash
# crontab 示例（每天下午 5 点执行）
0 17 * * 1-5 cd /path/to/anti-package && python3 src/equity/us_stock_reversal_detector.py
```

### 场景 2: 批量历史回测

```python
from datetime import datetime, timedelta

detector = USStockReversalDetector()

# 回测最近 30 个交易日
for i in range(1, 31):
    t1_date = detector.get_trading_date(i)
    t2_date = detector.get_trading_date(i + 1)
    
    data = detector.ensure_data_available([t2_date, t1_date])
    if len(data) == 2:
        results = detector.detect_reversal_pattern(
            df_t2=data[t2_date],
            df_t1=data[t1_date]
        )
        print(f"{t1_date}: {len(results)} 只股票")
```

### 场景 3: 结合其他筛选条件

```python
detector = USStockReversalDetector()
results = detector.run_reversal_detection()

# 进一步筛选：价格在 10-100 美元之间
filtered = results[
    (results['close_t1'] >= 10) &
    (results['close_t1'] <= 100)
]

# 筛选：成交量增幅超过 50%
high_volume = results[results['volume_increase_pct'] >= 50]
```

## 注意事项

1. **API 限制**
   - 免费套餐：5 次/分钟
   - 代码已内置延迟（0.5秒/请求）
   - 建议避免频繁调用

2. **交易日计算**
   - 自动跳过周末
   - 不考虑节假日（需要手动处理）

3. **数据质量**
   - Polygon.io 免费套餐数据延迟到收盘
   - 建议在收盘后运行检测

4. **文件大小**
   - 每日数据约 2-5 MB
   - 定期清理旧数据以节省空间

## 故障排除

### 问题 1: "未找到 API 密钥"

**解决：**
```bash
# 检查 .env 文件
cat .env | grep POLYGON_KEY

# 如果没有，添加
echo "POLYGON_KEY=your-api-key-here" >> .env
```

### 问题 2: "未获取到数据"

**可能原因：**
- 指定日期不是交易日
- API 密钥无效
- 网络连接问题

**解决：**
- 检查日期是否正确
- 验证 API 密钥
- 检查网络连接

### 问题 3: "未找到符合条件的股票"

**正常情况：** 并非每天都有符合反包条件的股票

**建议：**
- 连续几天运行观察
- 调整检测条件
- 扩大筛选范围

## 相关文档

- [Polygon.io 快速开始](POLYGON_QUICKSTART.md)
- [Polygon.io API 文档](README_POLYGON.md)
- [环境变量配置](../../ENV_SETUP_GUIDE.md)

## 版本历史

- **v1.0.0** (2025-10-08)
  - 初始版本
  - 支持反包形态检测
  - 自动数据管理
  - Excel 多 sheet 存储

