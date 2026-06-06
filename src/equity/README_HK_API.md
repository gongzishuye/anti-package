# EM API 港股数据获取和反包检测使用说明

## 概述

本模块使用 EM API (`http://127.0.0.1:8080/api/public/stock_hk_spot_em`) 获取港股数据，并执行反包检测。

## 功能特性

1. **每日数据获取**: 每天早晨8点自动获取昨天的港股数据
2. **数据存储**: 数据存储在 Excel 文件中，每天一个 sheet
3. **数据清理**: 自动清理超过3周的历史数据
4. **反包检测**: 自动检测反包形态的股票
5. **历史数据检查**: 只有在有足够历史数据（至少2条）时才执行反包检测

## 快速开始

### 1. 手动运行数据获取和反包检测

```bash
cd /home/ubuntu/code/anti-package
venv/bin/python src/equity/daily_fetch_hk_and_detect.py
```

### 2. 设置定时任务（每天8点自动执行）

```bash
cd /home/ubuntu/code/anti-package
src/equity/setup_hk_daily_cron.sh
```

### 3. 查看定时任务

```bash
crontab -l
```

### 4. 删除定时任务

```bash
crontab -l | grep -v "# HK Equity daily fetch" | grep -v "daily_fetch_hk_and_detect.py" | crontab -
```

## 数据格式

### API 返回格式

```json
[
  {
    "序号": 1,
    "代码": "02546",
    "名称": "智汇矿业",
    "最新价": 8.6,
    "涨跌额": 4.09,
    "涨跌幅": 90.69,
    "今开": 10.8,
    "最高": 10.92,
    "最低": 8.0,
    "昨收": 4.51,
    "成交量": 30390200.0,
    "成交额": 295547312.0
  }
]
```

### 数据存储格式

数据存储在 `src/equity/data/hk_stock_daily_history.xlsx` 文件中：
- 每个日期一个 sheet，sheet 名称为日期格式 `YYYY-MM-DD`
- 包含以下字段：
  - `symbol`: 股票代码（如 "02546"）
  - `code`: 原始代码
  - `name`: 股票名称
  - `open`: 开盘价（今开）
  - `high`: 最高价
  - `low`: 最低价
  - `close`: 收盘价（最新价）
  - `volume`: 成交量
  - `turnover`: 成交额
  - `vwap`: 成交量加权平均价
  - `date`: 数据日期
  - 其他字段...

## 反包检测逻辑

反包检测需要满足以下条件：

1. **T-1的成交量大于T-2**
2. **T-2是阴线**（收盘价低于开盘价）
3. **T-1是阳线**（开盘价低于收盘价）且**T-1收盘价大于T-2的开盘价**
4. **T-1的交易额 >= 1000万港币**（默认）

### 反包检测结果

结果保存在 `src/equity/data/hk_stock_reversal_results.xlsx` 文件中，包含：
- `symbol`: 股票代码
- `open_t2`, `close_t2`, `volume_t2`: T-2（前天）数据
- `open_t1`, `close_t1`, `volume_t1`: T-1（昨天）数据
- `t2_change_pct`: T-2 涨跌幅
- `t1_change_pct`: T-1 涨跌幅
- `volume_increase_pct`: 成交量增幅
- `reversal_strength`: 反包强度
- 其他指标...

## 代码示例

### 使用 EM API 获取港股数据

```python
from src.equity.em_hk_stock_fetcher import EMHKStockFetcher

# 创建获取器
fetcher = EMHKStockFetcher()

# 获取最新数据
df = fetcher.get_latest_market_data()
print(f"获取到 {len(df)} 只股票的数据")
```

### 使用反包检测器

```python
from src.equity.hk_stock_reversal_detector import HKStockReversalDetector

# 创建检测器
detector = HKStockReversalDetector()

# 运行反包检测
results = detector.run_reversal_detection()

if not results.empty:
    print(f"找到 {len(results)} 只符合反包条件的股票")
```

### 手动获取和保存数据

```python
from src.equity.hk_stock_reversal_detector import HKStockReversalDetector
from datetime import datetime, timedelta

detector = HKStockReversalDetector()

# 获取昨天的日期
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

# 获取数据
df = detector.fetcher.get_daily_market_summary(yesterday)

# 保存数据
if not df.empty:
    detector.save_daily_data(yesterday, df)
```

## 日志文件

- 主日志: `logs/equity_hk_daily_fetch.log`
- Cron 日志: `logs/equity_hk_daily_cron.log`

## 注意事项

1. **API 服务**: 确保 `http://127.0.0.1:8080/api/public/stock_hk_spot_em` 服务正在运行
2. **数据日期**: 接口返回的是最新数据，脚本会将其标记为昨天的日期
3. **历史数据**: 反包检测需要至少2条历史数据，如果数据不足会跳过检测
4. **数据清理**: 系统会自动清理超过3周的数据，只保留最近3周的数据
5. **交易日**: 脚本会自动跳过周末，只处理交易日

## 故障排查

### API 连接失败

```
ERROR: ✗ 请求失败: HTTPConnectionPool(host='127.0.0.1', port=8080): Read timed out.
```

**解决方案**: 检查 API 服务是否正在运行

```bash
curl http://127.0.0.1:8080/api/public/stock_hk_spot_em
```

### 数据不足

```
WARNING: ✗ 历史数据不足，无法判断反包
```

**解决方案**: 等待至少2天的数据积累后再运行检测

### 定时任务未执行

**检查步骤**:
1. 查看 cron 日志: `tail -f logs/equity_hk_daily_cron.log`
2. 检查 cron 服务: `systemctl status cron`
3. 验证定时任务: `crontab -l`

## 相关文件

- `src/equity/em_hk_stock_fetcher.py`: EM API 港股数据获取器
- `src/equity/hk_stock_reversal_detector.py`: 港股反包检测器
- `src/equity/daily_fetch_hk_and_detect.py`: 每日任务脚本
- `src/equity/setup_hk_daily_cron.sh`: 定时任务设置脚本
- `src/equity/data/hk_stock_daily_history.xlsx`: 历史数据文件
- `src/equity/data/hk_stock_reversal_results.xlsx`: 反包检测结果文件

## 与美股模块的区别

1. **数据源**: 使用不同的 API 端点
2. **股票代码**: 港股代码直接使用（如 "02546"），不需要解析前缀
3. **数据文件**: 使用独立的 Excel 文件（`hk_stock_daily_history.xlsx`）
4. **结果文件**: 使用独立的 Excel 文件（`hk_stock_reversal_results.xlsx`）
5. **日志文件**: 使用独立的日志文件（`equity_hk_daily_fetch.log`）

