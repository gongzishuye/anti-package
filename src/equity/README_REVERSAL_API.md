# 反包检测 API 文档

## 概述

反包检测功能用于检测股票市场中的反包形态（反转形态），帮助识别潜在的反转机会。系统支持美股、港股和A股三个市场的反包检测。

## 数据文件

### 历史数据文件

反包检测需要至少2天的历史数据才能运行：

- **美股**: `src/equity/data/us_stock_daily_history.xlsx`
- **港股**: `src/equity/data/hk_stock_daily_history.xlsx`
- **A股**: `src/equity/data/a_stock_daily_history.xlsx`

每个文件包含多个sheet，每个sheet对应一个交易日的市场数据。

### 反包结果文件

反包检测结果保存在以下文件中：

- **美股**: `src/equity/data/us_stock_reversal_results.xlsx`
- **港股**: `src/equity/data/hk_stock_reversal_results.xlsx`
- **A股**: `src/equity/data/a_stock_reversal_results.xlsx`

每个文件包含多个sheet，每个sheet对应一个检测日期的结果。

## API 接口

### 1. 获取所有市场数据（包含反包结果）

**接口**: `GET /api/data`

**说明**: 获取所有市场（BN合约、OK合约、美股、港股、A股）的筛选结果，包括反包检测结果。

**响应格式**:

```json
{
  "success": true,
  "us": {
    "success": true,
    "file": "/path/to/us_stock_reversal_results.xlsx",
    "update_time": "2025-12-23 08:44:00",
    "data_date": "2025-12-23",
    "sheets": {
      "today": [
        {
          "symbol": "AAPL",
          "open_t2": 150.00,
          "close_t2": 148.00,
          "high_t2": 151.00,
          "low_t2": 147.00,
          "volume_t2": 1000000,
          "t2_change_pct": -1.33,
          "open_t1": 148.50,
          "close_t1": 152.00,
          "high_t1": 153.00,
          "low_t1": 148.00,
          "volume_t1": 1500000,
          "t1_change_pct": 2.36,
          "volume_increase_pct": 50.0,
          "reversal_strength": 2.00,
          "turnover_t1": 228000000,
          "market_cap": 2500000000000,
          "name": "Apple Inc.",
          "data_date": "2025-12-23"
        }
      ]
    }
  },
  "hk": {
    "success": true,
    "file": "/path/to/hk_stock_reversal_results.xlsx",
    "update_time": "2025-12-23 08:44:00",
    "data_date": "2025-12-23",
    "sheets": {
      "today": [...]
    }
  },
  "a": {
    "success": true,
    "file": "/path/to/a_stock_reversal_results.xlsx",
    "update_time": "2025-12-23 08:44:00",
    "data_date": "2025-12-23",
    "sheets": {
      "today": [...]
    }
  }
}
```

**字段说明**:

- `success`: 请求是否成功
- `us/hk/a`: 对应市场的反包检测结果
  - `success`: 该市场数据是否成功获取
  - `file`: 结果文件路径
  - `update_time`: 文件更新时间
  - `data_date`: 实际数据日期（检测日期）
  - `sheets.today`: 今日反包检测结果列表
    - `symbol`: 股票代码
    - `open_t2/close_t2/high_t2/low_t2`: T-2（前天）的开盘价/收盘价/最高价/最低价
    - `volume_t2`: T-2成交量
    - `t2_change_pct`: T-2涨跌幅百分比
    - `open_t1/close_t1/high_t1/low_t1`: T-1（昨天）的开盘价/收盘价/最高价/最低价
    - `volume_t1`: T-1成交量
    - `t1_change_pct`: T-1涨跌幅百分比
    - `volume_increase_pct`: 成交量增幅百分比
    - `reversal_strength`: 反包强度（T-1收盘价 - T-2开盘价）
    - `turnover_t1`: T-1交易额
    - `market_cap`: 市值（如果有）
    - `name`: 公司名称（如果有）
    - `data_date`: 数据日期

## 反包检测条件

反包形态的定义：

1. **T-1的成交额大于T-2**（使用成交额而不是成交量）
2. **T-2是阴线**（收盘价低于开盘价）
3. **T-1是阳线**（开盘价低于收盘价）且**T-1收盘价大于T-2的开盘价**
4. **T-1的交易额 >= 1000万**（默认值）
5. **市值 >= 10亿美元**（仅美股，默认值）

## 运行反包检测

### 手动运行

#### 美股反包检测

```bash
python3 src/equity/daily_fetch_and_detect.py
```

或使用Python代码：

```python
from src.equity.us_stock_reversal_detector import USStockReversalDetector

detector = USStockReversalDetector(use_em_api=True)
results = detector.run_reversal_detection()
```

#### 港股反包检测

```bash
python3 src/equity/daily_fetch_hk_and_detect.py
```

或使用Python代码：

```python
from src.equity.hk_stock_reversal_detector import HKStockReversalDetector

detector = HKStockReversalDetector()
results = detector.run_reversal_detection()
```

#### A股反包检测

```bash
python3 src/equity/daily_fetch_a_and_detect.py
```

或使用Python代码：

```python
from src.equity.a_stock_reversal_detector import AStockReversalDetector

detector = AStockReversalDetector()
results = detector.run_reversal_detection()
```

### 定时任务

系统已配置定时任务，每天自动运行反包检测：

- **美股**: 每天8:00运行 `daily_fetch_and_detect.py`
- **港股**: 每天8:00运行 `daily_fetch_hk_and_detect.py`
- **A股**: 每天8:00运行 `daily_fetch_a_and_detect.py`

查看定时任务：

```bash
crontab -l
```

## 前端使用

前端通过调用 `/api/data` 接口获取反包检测结果，然后在界面上显示。

### 前端代码示例

```javascript
// 获取反包数据
fetch('/api/data')
  .then(response => response.json())
  .then(data => {
    if (data.success && data.us.success) {
      const usReversalStocks = data.us.sheets.today;
      console.log(`找到 ${usReversalStocks.length} 只美股反包股票`);
      
      // 显示数据
      usReversalStocks.forEach(stock => {
        console.log(`${stock.symbol}: 反包强度 ${stock.reversal_strength}`);
      });
    }
    
    // 类似地处理港股和A股数据
    if (data.success && data.hk.success) {
      const hkReversalStocks = data.hk.sheets.today;
      // ...
    }
    
    if (data.success && data.a.success) {
      const aReversalStocks = data.a.sheets.today;
      // ...
    }
  });
```

## 注意事项

1. **数据要求**: 反包检测需要至少2天的历史数据（T-2和T-1）
2. **交易日**: 系统会自动跳过周末，只处理交易日
3. **数据更新**: 反包检测结果每天更新一次，通常在早上8点
4. **文件位置**: 反包结果文件位于 `src/equity/data/` 目录下
5. **API服务**: 确保Flask服务器正在运行（`src/crypto/flask_auto_server.py`）
6. **数据源**: 美股使用EM API，港股和A股也使用EM API

## 故障排查

### 前端没有显示反包数据

1. **检查结果文件是否存在**:
   ```bash
   ls -lh src/equity/data/*reversal*.xlsx
   ```

2. **检查API接口是否正常**:
   ```bash
   curl http://localhost:5003/api/data | jq '.us'
   ```

3. **手动运行反包检测**:
   ```bash
   python3 src/equity/daily_fetch_and_detect.py
   ```

4. **检查历史数据是否充足**:
   ```python
   from src.equity.us_stock_reversal_detector import USStockReversalDetector
   detector = USStockReversalDetector()
   sheets = detector.get_existing_sheets()
   print(f"可用日期: {sheets}")
   ```

5. **查看日志**:
   ```bash
   tail -f logs/equity_daily_fetch.log
   ```

## 相关文档

- [美股反包检测说明](README_REVERSAL.md)
- [EM API实现说明](EM_API_IMPLEMENTATION_SUMMARY.md)
- [港股API实现说明](HK_API_IMPLEMENTATION_SUMMARY.md)
- [A股API实现说明](A_API_IMPLEMENTATION_SUMMARY.md)

