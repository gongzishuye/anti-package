# 贵金属数据获取和反包检测系统

## 概述

本模块使用 MetalPriceAPI 获取贵金属（黄金XAU、白银XAG等）的OHLC数据，并执行反包检测。

## 功能特性

1. **每日数据获取**: 每天早晨8点02分自动获取昨天的贵金属数据
2. **数据存储**: 数据存储在 Excel 文件中，每天一个 sheet
3. **数据清理**: 自动清理超过3周的历史数据
4. **反包检测**: 自动检测反包形态的贵金属
5. **历史数据检查**: 只有在有足够历史数据（至少2条）时才执行反包检测

## 快速开始

### 1. 手动运行数据获取和反包检测

```bash
cd /home/ubuntu/code/anti-package
venv/bin/python src/metal/daily_fetch_metal_and_detect.py
```

### 2. 使用综合调度器（推荐方式，每天8点02分自动执行）

贵金属任务已集成到 `combined_scheduler.py` 中，使用 `schedule` 库进行调度，无需crontab。

#### 启动综合调度器（包含所有任务）

```bash
cd /home/ubuntu/code/anti-package
venv/bin/python src/alert/combined_scheduler.py
```

#### 只运行贵金属任务

```bash
cd /home/ubuntu/code/anti-package
venv/bin/python src/alert/combined_scheduler.py --metal-only
```

#### 启动时立即执行贵金属任务

```bash
cd /home/ubuntu/code/anti-package
venv/bin/python src/alert/combined_scheduler.py --run-metal-now
```

### 3. 使用crontab（已废弃，不推荐）

如果需要使用crontab方式（不推荐），可以使用：

```bash
cd /home/ubuntu/code/anti-package
src/metal/setup_metal_daily_cron.sh
```

**注意**: 推荐使用综合调度器方式，因为它与equity模块使用相同的调度机制，更易于管理和维护。

## 数据格式

### API 返回格式

MetalPriceAPI 返回的OHLC数据格式：

```json
{
  "success": true,
  "base": "XAU",
  "quote": "USD",
  "timestamp": 1738108799,
  "rate": {
    "open": 2741.97,
    "high": 2764.96,
    "low": 2735.11,
    "close": 2742.22
  }
}
```

### 数据存储格式

数据存储在 `src/metal/data/metal_daily_history.xlsx` 文件中：
- 每个日期一个 sheet，sheet 名称为日期格式 `YYYY-MM-DD`
- 包含以下字段：
  - `symbol`: 商品代码（如 "XAU/USD", "XAG/USD"）
  - `timestamp`: 时间戳（datetime类型）
  - `open`: 开盘价
  - `high`: 最高价
  - `low`: 最低价
  - `close`: 收盘价
  - `date`: 数据日期

### 反包结果格式

反包检测结果存储在 `src/metal/data/metal_reversal_results.xlsx` 文件中：
- 每个检测日期一个 sheet，sheet 名称为日期格式 `YYYY-MM-DD`
- 包含以下字段：
  - `symbol`: 商品代码
  - `open_t2`, `close_t2`, `high_t2`, `low_t2`: T-2（前天）的OHLC数据
  - `t2_change_pct`: T-2涨跌幅百分比
  - `open_t1`, `close_t1`, `high_t1`, `low_t1`: T-1（昨天）的OHLC数据
  - `t1_change_pct`: T-1涨跌幅百分比
  - `price_change_increase_pct`: 价格变化增幅百分比（替代成交量增幅）
  - `reversal_strength`: 反包强度（T-1收盘价 - T-2开盘价）

## 反包检测逻辑

反包检测需要满足以下条件（针对贵金属，由于没有成交量，使用价格变化幅度作为替代指标）：

1. **T-1的价格变化幅度大于T-2**: T-1的|收盘价-开盘价| > T-2的|收盘价-开盘价|
2. **T-2是阴线**: T-2收盘价 < T-2开盘价
3. **T-1是阳线**: T-1收盘价 > T-1开盘价
4. **T-1收盘价大于T-2开盘价**: T-1收盘价 > T-2开盘价

## API 限制

- **免费计划限制**: MetalPriceAPI 免费计划仅支持查询最近5天的历史数据
- **查询超过5天的数据**: 需要付费计划

## 使用示例

### Python 代码示例

```python
from src.metal.metal_reversal_detector import MetalReversalDetector

# 创建检测器
detector = MetalReversalDetector()

# 运行反包检测
results = detector.run_reversal_detection()

if not results.empty:
    print(f"找到 {len(results)} 个符合反包条件的贵金属")
    print(results)
```

### 手动获取数据

```python
from src.metal.metalpriceapi_fetcher import MetalPriceAPIFetcher

# 创建数据获取器
fetcher = MetalPriceAPIFetcher()

# 获取单日数据
ohlc = fetcher.get_ohlc('XAU', 'USD', '2025-01-28')

# 获取多天数据
df = fetcher.get_klines('XAU', 'USD', days=5)
```

## 日志文件

- **运行日志**: `logs/metal_daily_fetch.log`
- **定时任务日志**: `logs/metal_daily_fetch_cron.log`

## 支持的贵金属

- **XAU**: 黄金（Gold）
- **XAG**: 白银（Silver）

可以根据需要扩展 `MetalReversalDetector.supported_metals` 列表来支持更多贵金属。

## 注意事项

1. **时区**: 系统使用服务器本地时区，定时任务在每天8点02分执行
2. **周末处理**: 系统会自动跳过周末，获取最近的交易日数据
3. **数据清理**: 系统会自动清理超过3周的历史数据，以节省存储空间
4. **错误处理**: 如果API请求失败，系统会记录错误日志并继续执行

## 文件结构

```
src/metal/
├── __init__.py                      # 模块初始化
├── metalpriceapi_fetcher.py         # MetalPriceAPI数据获取器
├── metal_reversal_detector.py       # 反包检测器
├── daily_fetch_metal_and_detect.py  # 每日数据获取和检测脚本
├── setup_metal_daily_cron.sh        # 定时任务设置脚本
├── README.md                        # 本文档
└── data/                            # 数据存储目录
    ├── metal_daily_history.xlsx      # 历史数据文件
    └── metal_reversal_results.xlsx  # 反包检测结果文件
```
