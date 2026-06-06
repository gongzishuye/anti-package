# 价格实时更新功能

## 功能概述

在 alert 模块中新增了价格实时更新功能，可以每隔15分钟从币安获取最新价格并更新数据库。

## 核心特性

### 1. 智能更新策略

- **获取数据**：从币安API获取当天的K线数据
- **智能判断**：
  - 如果当天最高价 > 数据库中的high → 同时更新 high 和 current_price
  - 否则 → 仅更新 current_price
- **时间戳**：每次更新都会更新 update_time 字段

### 2. 新增文件

#### `price_updater.py` - 价格更新核心模块

```python
class PriceUpdater:
    def update_single_monitor(monitor)  # 更新单条监控记录
    def update_all_monitors()           # 更新所有监控记录
```

**功能**：
- 支持单条或批量更新监控数据的价格
- 从币安获取最新K线数据（high, close）
- 智能判断是否需要更新high字段
- API友好：请求之间有0.5秒延迟

#### `combined_scheduler.py` - 综合调度器

```python
class CombinedScheduler:
    def excel_sync_job()      # Excel同步任务
    def price_update_job()    # 价格更新任务
    def start()               # 启动定时任务
```

**功能**：
- 同时管理两个定时任务
- Excel同步：每天8:30执行
- 价格更新：每15分钟执行（可配置）
- 支持独立运行或组合运行

## 使用方法

### 1. 测试功能

```bash
# 测试价格更新功能
python3 test_price_updater.py
```

### 2. 手动更新

```bash
# 更新一次所有监控代币的价格
python3 src/alert/price_updater.py --once
```

### 3. 定时更新

```bash
# 每15分钟自动更新（默认）
python3 src/alert/price_updater.py

# 自定义更新间隔为5分钟
python3 src/alert/price_updater.py --interval 5
```

### 4. 综合调度器（推荐）

```bash
# 快速启动
./start_combined_scheduler.sh

# 或者手动启动，并立即执行所有任务
python3 src/alert/combined_scheduler.py --run-all-now

# 只运行价格更新
python3 src/alert/combined_scheduler.py --price-only

# 自定义价格更新间隔
python3 src/alert/combined_scheduler.py --price-interval 5
```

## 工作流程

```
┌─────────────────────────────────────────────────────────┐
│                  综合调度器启动                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ├──────────────────┬──────────────────┐
                          ▼                  ▼                  ▼
                    ┌──────────┐      ┌──────────┐      ┌──────────┐
                    │ 每天8:30  │      │ 每15分钟  │      │  实时监控 │
                    └──────────┘      └──────────┘      └──────────┘
                          │                  │                  │
                          ▼                  ▼                  ▼
              ┌────────────────────┐  ┌────────────────┐  ┌──────────┐
              │ Excel数据同步       │  │ 价格更新        │  │ 日志记录  │
              │ - 读取Excel        │  │ - 获取K线      │  │ - 成功数  │
              │ - 解析数据         │  │ - 比较价格     │  │ - 失败数  │
              │ - 写入monitor表    │  │ - 更新数据库   │  │ - 突破记录│
              └────────────────────┘  └────────────────┘  └──────────┘
                          │                  │                  │
                          └──────────┬───────┴──────────────────┘
                                     ▼
                          ┌─────────────────────┐
                          │   monitor 数据表     │
                          │  - ticker           │
                          │  - high (最高价)    │
                          │  - current_price    │
                          │  - update_time      │
                          └─────────────────────┘
```

## 数据更新逻辑

```python
# 伪代码示例
for each monitor in database:
    # 1. 获取最新K线
    kline = bn.get_today_kline(ticker, interval)
    current_high = kline['high']
    current_price = kline['close']
    
    # 2. 智能更新
    if current_high > database.high:
        # 突破新高！更新high和current_price
        database.update(high=current_high, current_price=current_price)
        log.info(f"🎉 {ticker} 突破新高!")
    else:
        # 只更新当前价格
        database.update(current_price=current_price)
```

## 输出示例

### 测试输出

```
================================================================================
测试价格更新功能
================================================================================

✅ 数据库中有 45 条监控记录

前5条监控记录:
  1. bn BTCUSDT 1D - High: $67234.5600, Current: $66892.3400
  2. bn ETHUSDT 1D - High: $3456.7800, Current: $3421.9000
  ...

================================================================================
测试更新单条记录
================================================================================

测试代币: BTCUSDT
当前数据库记录:
  High: $67234.5600
  Current Price: $66892.3400
  更新时间: 2025-10-12 08:30:15

正在从币安获取最新价格...
BTCUSDT: 当前价=67123.45, 当天最高=67456.78, 数据库最高=67234.56

🎉 BTCUSDT 突破新高! 67234.56 -> 67456.78

✅ 更新成功！

更新后的数据库记录:
  High: $67456.7800
  Current Price: $67123.4500
  更新时间: 2025-10-12 14:35:22
```

### 定时更新输出

```
================================================================================
💹 开始执行价格更新任务
执行时间: 2025-10-12 14:45:00
================================================================================

共找到 45 条监控记录

处理 [1/45]: bn BTCUSDT 1D
获取 BTCUSDT 1D 的最新价格...
BTCUSDT: 当前价=67200.00, 当天最高=67456.78, 数据库最高=67456.78

处理 [2/45]: bn ETHUSDT 1D
获取 ETHUSDT 1D 的最新价格...
ETHUSDT: 当前价=3450.00, 当天最高=3468.90, 数据库最高=3456.78
✨ ETHUSDT 突破新高! 3456.78 -> 3468.90

...

================================================================================
价格更新完成
总计: 45 条
成功: 43 条
失败: 0 条
跳过: 2 条
================================================================================
```

## 生产环境部署

### 使用 systemd 服务（推荐）

创建服务文件 `/etc/systemd/system/combined-scheduler.service`：

```ini
[Unit]
Description=Combined Scheduler Service (Excel Sync + Price Update)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/code/anti-package
ExecStart=/usr/bin/python3 /home/ubuntu/code/anti-package/src/alert/combined_scheduler.py
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/code/anti-package/logs/combined_scheduler.log
StandardError=append:/home/ubuntu/code/anti-package/logs/combined_scheduler_error.log

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable combined-scheduler.service
sudo systemctl start combined-scheduler.service

# 查看状态
sudo systemctl status combined-scheduler.service

# 查看日志
sudo journalctl -u combined-scheduler.service -f
```

## 技术细节

### API调用优化

1. **延迟控制**：每次API调用之间有0.5秒延迟，避免触发限流
2. **错误处理**：单个代币更新失败不影响其他代币
3. **日志记录**：详细记录每次更新的结果

### Interval 映射

| 数据库格式 | 币安API格式 |
|-----------|------------|
| 1D        | 1d         |
| 3D        | 3d         |
| 1W        | 1w         |
| 4H        | 4h         |
| 1H        | 1h         |

### 交易所支持

当前版本仅支持币安（bn）交易所，其他交易所的数据会被跳过。

## 性能考虑

- **处理速度**：约 2秒/代币（包含0.5秒延迟）
- **45条记录**：约 90秒
- **更新频率**：15分钟（可配置）
- **网络要求**：稳定的币安API连接

## 监控和维护

### 查看更新记录

```bash
# 查看最近更新的监控数据
python3 query_db.py monitors --exchange bn | head -20

# 查看统计信息
python3 query_db.py stats
```

### 日志文件

- `logs/combined_scheduler.log` - 综合调度器日志
- `logs/combined_scheduler_error.log` - 错误日志

## 后续扩展

基于此功能，可以进一步实现：

1. **价格突破报警** - 监控价格突破high或跌破low时发送通知
2. **邮件通知** - 价格突破时发送邮件
3. **Webhook通知** - 发送到钉钉、企业微信等
4. **实时图表** - Web界面显示价格走势

## 常见问题

### Q: 如何修改更新频率？

A: 使用 `--price-interval` 参数：
```bash
python3 src/alert/combined_scheduler.py --price-interval 5  # 5分钟
```

### Q: 可以只更新特定代币吗？

A: 目前版本更新所有监控数据。如需只更新特定代币，可以修改 `price_updater.py` 添加筛选逻辑。

### Q: API调用会不会被限流？

A: 已经加入0.5秒延迟机制，正常情况下不会触发限流。

### Q: 更新失败怎么办？

A: 单个代币更新失败不影响其他代币，错误会记录在日志中。可以查看日志排查问题。

## 总结

价格实时更新功能已完整实现，提供了：

✅ 独立的价格更新器（`price_updater.py`）  
✅ 综合调度器（`combined_scheduler.py`）  
✅ 测试脚本（`test_price_updater.py`）  
✅ 启动脚本（`start_combined_scheduler.sh`）  
✅ 完整的文档和使用说明  

可以立即投入使用！

