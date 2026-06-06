# Flask服务器 - 美股市场更新说明

## 📊 更新内容

已成功在Flask自动化服务器中添加**美股（US市场）**支持！

### 新增功能

1. **美股反包数据展示**
   - 自动读取 `src/equity/data/us_stock_reversal_results.xlsx` 文件
   - 显示今天的反包股票数据
   - 支持实时查看和搜索

2. **交易额排序**
   - 默认按交易额（turnover）倒序排列
   - 可手动点击列头进行升序/降序切换
   - 交易额计算：vwap × volume

3. **三市场支持**
   - 📈 BN市场（币安合约）
   - 🟠 OK市场（OKX合约）
   - 🇺🇸 US股票（美股反包）

## 🚀 使用方法

### 1. 启动服务器

```bash
cd /home/ubuntu/code/anti-package/src/crypto
python3 flask_auto_server.py 5000
```

### 2. 访问Web界面

打开浏览器访问：
```
http://localhost:5000
```

### 3. 切换到美股市场

1. 点击页面顶部的 **"🇺🇸 US股票"** 选项卡
2. 自动显示 **"今日反包"** 数据
3. 默认按 **交易额（从高到低）** 排序

### 4. 数据展示

美股市场显示以下列：

| 列名 | 说明 | 示例 |
|------|------|------|
| 排名 | 按交易额排序的名次 | 1, 2, 3... |
| Symbol | 股票代码（可点击跳转） | CISS, XTLB |
| T-2价格 | 前天收盘价 | $2.21 |
| T-1价格 | 昨天收盘价 | $4.07 |
| 成交量增长 | 成交量增幅百分比 | +148,341% |
| 涨幅 | 昨天涨跌幅 | +26.40% |
| **交易额** | T-1日交易额（vwap×volume） | **$394M** |

## 📁 数据文件

### 数据源

- **文件路径**: `src/equity/data/us_stock_reversal_results.xlsx`
- **Sheet格式**: 每个日期一个sheet（如 `2025-10-08`）
- **自动读取**: 读取今天日期对应的sheet

### 数据要求

Excel文件必须包含以下列：
- `symbol` - 股票代码
- `open_t2`, `close_t2` - T-2开盘价、收盘价
- `volume_t2` - T-2成交量
- `t2_change_pct` - T-2涨跌幅
- `open_t1`, `close_t1` - T-1开盘价、收盘价
- `volume_t1` - T-1成交量
- `t1_change_pct` - T-1涨跌幅
- `volume_increase_pct` - 成交量增幅
- `reversal_strength` - 反包强度
- `turnover_t1` 或 `vwap_t1` - 交易额或VWAP

## 🔧 功能特性

### 1. 智能排序

- **默认排序**：按交易额从高到低
- **手动排序**：点击列头的↕️按钮
- **支持的排序列**：
  - 成交量增长
  - 涨幅
  - 交易额（仅US市场）

### 2. 搜索功能

在搜索框输入股票代码，实时过滤：
```
输入: CISS
结果: 只显示包含"CISS"的股票
```

### 3. 数据新鲜度

- 显示数据更新时间
- 支持手动刷新
- 自动读取最新数据文件

## 💡 示例数据

### 显示效果

```
排名  Symbol  T-2价格   T-1价格   成交量增长      涨幅      交易额
──────────────────────────────────────────────────────────────
1     CISS    $2.21    $4.07    +148,341.2%   +26.40%   $394M
2     XTLB    $1.14    $1.40    +110,307.2%   +21.74%   $46.7M
3     SPHL    $0.55    $0.61    +21,065.4%    +12.81%   $22.1M
4     XBB     $41.08   $41.21   +17,287.1%    +0.22%    $103M
5     BGMS    $4.57    $4.72    +16,782.1%    +3.28%    $22.0M
```

## 🔄 数据更新流程

### 自动流程

1. **运行反包检测**
   ```bash
   python3 src/equity/us_stock_reversal_detector.py
   ```

2. **生成数据文件**
   - 保存到：`src/equity/data/us_stock_reversal_results.xlsx`
   - Sheet名称：今天的日期（如 `2025-10-08`）

3. **Web自动读取**
   - Flask服务器自动检测文件更新
   - 读取今天日期的sheet
   - 展示在US市场选项卡

### 手动刷新

在Web界面点击 **"🔄 刷新数据"** 按钮

## 🎯 技术实现

### 后端API

**路由**: `GET /api/data`

**返回格式**:
```json
{
  "success": true,
  "bn": { "success": true, "sheets": {...} },
  "ok": { "success": true, "sheets": {...} },
  "us": {
    "success": true,
    "update_time": "2025-10-08 23:22:15",
    "sheets": {
      "today": [
        {
          "symbol": "CISS",
          "close_t2": 2.21,
          "close_t1": 4.07,
          "volume_increase_pct": 148341.2,
          "t1_change_pct": 26.40,
          "turnover_t1": 394342225,
          "market_type": "stock"
        }
      ]
    }
  }
}
```

### 前端展示

- **框架**: 原生JavaScript
- **样式**: 响应式CSS
- **功能**: 
  - 动态切换市场
  - 实时排序
  - 搜索过滤
  - 数据格式化

## 📊 对比：三个市场

| 市场 | 数据类型 | 周期选项 | 排序默认 | 链接目标 |
|------|----------|----------|----------|----------|
| BN | 加密货币合约 | 1日、3日、周 | USDT成交量 | Binance |
| OK | 加密货币合约 | 1日、2日、3日、5日、周 | USDT成交量 | Binance |
| **US** | **美股反包** | **今日反包** | **交易额** | **Google Finance** |

## ⚠️ 注意事项

1. **数据依赖**
   - 确保已运行反包检测生成数据
   - 数据文件必须包含今天日期的sheet

2. **文件路径**
   - 固定路径：`src/equity/data/us_stock_reversal_results.xlsx`
   - 不支持其他路径或文件名

3. **日期格式**
   - Sheet名称必须为：`YYYY-MM-DD` 格式
   - 如：`2025-10-08`

4. **交易额计算**
   - 优先使用 `turnover_t1` 字段
   - 其次使用 `vwap_t1 × volume_t1`
   - 最后使用 `close_t1 × volume_t1`

## 🔍 故障排除

### 问题1: 未显示US市场数据

**检查**:
```bash
# 1. 检查数据文件是否存在
ls -l src/equity/data/us_stock_reversal_results.xlsx

# 2. 检查文件内容
python3 -c "
import pandas as pd
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
xls = pd.ExcelFile('src/equity/data/us_stock_reversal_results.xlsx')
print('可用sheets:', xls.sheet_names)
print(f'今天({today})的sheet存在:', today in xls.sheet_names)
"
```

### 问题2: 交易额显示为0

**原因**: 数据文件缺少 `turnover_t1` 或 `vwap_t1` 字段

**解决**: 重新运行反包检测（已修复版本）

### 问题3: 排序不生效

**刷新页面**: Ctrl+F5 强制刷新浏览器缓存

## 📝 更新日志

**版本**: v1.1.0  
**日期**: 2025-10-09  
**更新内容**:
- ✅ 添加US市场选项卡
- ✅ 支持美股反包数据展示
- ✅ 添加交易额列和排序功能
- ✅ 自动读取今天的数据
- ✅ 默认按交易额倒序排列
- ✅ 自适应显示不同市场的数据格式

---

**完成时间**: 2025-10-09 00:10  
**开发者**: AI Assistant  
**状态**: ✅ 已完成并测试

