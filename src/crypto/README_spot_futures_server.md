# 现货&合约统一Flask服务

## 功能概述

这是一个统一的Flask自动化服务，能够同时处理币安现货和合约数据，提供统一的Web界面来展示两种市场类型的筛选结果。

## 主要特性

### 🔄 **双市场支持**
- **现货市场**: 获取币安现货Top N交易对数据
- **合约市场**: 获取币安合约Top N交易对数据
- **同步处理**: 使用多线程并发处理两种市场数据

### 📊 **多周期分析**
- **1日K线**: 日线数据分析
- **3日K线**: 3日线数据分析  
- **周K线**: 周线数据分析

### ⏰ **自动化任务**
- **定时执行**: 每天早上8点自动获取和筛选数据
- **手动触发**: 支持Web界面手动触发任务
- **实时状态**: 显示任务执行状态和进度

### 🎨 **统一界面**
- **市场切换**: 在现货和合约之间切换查看
- **周期切换**: 在1日、3日、周K线之间切换
- **搜索功能**: 支持Token符号搜索
- **实时刷新**: 自动更新数据

## 使用方法

### 启动服务

```bash
# 基本启动（默认Top100，端口5000）
python3 src/crypto/flask_auto_server.py

# 自定义配置
python3 src/crypto/flask_auto_server.py 5003 --top-n 50
```

### 访问界面

- **Web界面**: http://localhost:5003
- **状态API**: http://localhost:5003/api/status
- **数据API**: http://localhost:5003/api/data
- **触发API**: http://localhost:5003/api/trigger

### API接口

#### 获取数据 `/api/data`
返回现货和合约的筛选结果数据：

```json
{
  "success": true,
  "spot": {
    "success": true,
    "file": "/path/to/spot_file.xlsx",
    "update_time": "2025-10-05 10:28:42",
    "sheets": {
      "1日筛选结果": [...],
      "3日筛选结果": [...],
      "周筛选结果": [...]
    }
  },
  "futures": {
    "success": true,
    "file": "/path/to/futures_file.xlsx", 
    "update_time": "2025-10-05 10:28:43",
    "sheets": {
      "1日筛选结果": [...],
      "3日筛选结果": [...],
      "周筛选结果": [...]
    }
  }
}
```

#### 获取状态 `/api/status`
返回任务执行状态：

```json
{
  "config": {"top_n": 50},
  "status": "成功",
  "message": "自动化任务完成（现货+合约）",
  "last_run": "2025-10-05 10:28:42",
  "next_run": "2025-10-06 08:00:00",
  "filter_file": {
    "spot": "/path/to/spot_file.xlsx",
    "futures": "/path/to/futures_file.xlsx"
  }
}
```

#### 触发任务 `/api/trigger`
手动触发数据更新任务：

```json
{
  "success": true,
  "message": "任务已启动，正在后台执行..."
}
```

## 数据流程

### 1. 数据获取
- 使用 `BinanceDataFetcher` 获取现货和合约数据
- 支持Top N交易对筛选
- 获取1日、3日、周K线数据

### 2. 数据处理
- 保存原始K线数据到Excel文件
- 使用 `MultiPeriodTokenFilter` 进行筛选
- 生成符合条件Token的筛选结果

### 3. 结果展示
- Web界面展示筛选结果
- 支持现货/合约切换
- 支持不同周期切换
- 提供搜索和排序功能

## 文件结构

```
data/
├── topN_multi_period_YYYYMMDD_HHMMSS.xlsx          # 现货K线数据
├── futures_topN_multi_period_YYYYMMDD_HHMMSS.xlsx  # 合约K线数据
├── qualified_tokens_multi_period_YYYYMMDD_HHMMSS.xlsx      # 现货筛选结果
└── futures_qualified_tokens_multi_period_YYYYMMDD_HHMMSS.xlsx # 合约筛选结果

logs/
└── flask_auto_server.log                           # 服务日志
```

## 配置参数

- **top_n**: 获取前N个代币（默认100）
- **port**: 服务端口（默认5000）
- **market_type**: 市场类型（spot/futures）

## 技术特点

### 并发处理
- 使用Python threading模块并发处理现货和合约数据
- 提高数据处理效率

### 错误处理
- 完善的异常处理机制
- 详细的日志记录
- 任务状态实时更新

### 数据一致性
- 现货和合约使用相同的筛选逻辑
- 统一的数据格式和展示方式

## 使用场景

1. **量化交易**: 为量化策略提供Token筛选数据
2. **市场分析**: 对比现货和合约市场的表现差异
3. **风险管理**: 识别高活跃度和高增长潜力的Token
4. **自动化监控**: 定时获取和更新市场数据

## 注意事项

1. **API限制**: 遵守币安API的请求频率限制
2. **数据延迟**: 数据获取需要一定时间，请耐心等待
3. **筛选条件**: 筛选条件较为严格，可能某些周期没有符合条件的数据
4. **资源消耗**: 并发处理会消耗更多系统资源

## 故障排除

### 常见问题

1. **任务失败**: 检查网络连接和API配置
2. **数据为空**: 筛选条件可能过于严格
3. **文件路径错误**: 确保data目录存在且有写入权限

### 日志查看

```bash
# 查看服务日志
tail -f logs/flask_auto_server.log

# 查看错误日志
grep "ERROR" logs/flask_auto_server.log
```

## 更新日志

- **v2.0**: 支持现货和合约双市场
- **v1.0**: 基础现货市场支持
