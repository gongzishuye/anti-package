# Alert 报警和定时任务模块

## 快速开始 🚀

```bash
# 1. 测试价格更新功能
python3 test_price_updater.py

# 2. 启动综合调度器（推荐）
./start_combined_scheduler.sh

# 或者手动启动
python3 src/alert/combined_scheduler.py --run-all-now
```

## 功能说明

本模块实现了以下功能：

1. **Excel数据同步** - 从 `qualified_tokens_multi_period_xxx.xlsx` 读取筛选结果并同步到数据库
2. **价格实时更新** - 每15分钟从币安获取最新价格并更新数据库
3. **定时任务调度** - 自动化执行数据同步和价格更新
4. **智能更新机制** - 如果当天最高价突破历史高点，自动更新high字段

## 文件说明

### 1. `excel_to_db_sync.py`

Excel数据同步核心模块，负责：
- 自动查找最新的 Excel 文件
- 解析多个sheet（1日、3日、周筛选结果）
- 计算过去K线的最高点和最低点
- 写入数据库

### 2. `scheduler.py`

定时任务调度器，负责：
- 设置每天8:30的定时任务
- 自动执行数据同步
- 日志记录

### 3. `price_updater.py`

价格更新模块，负责：
- 每隔15分钟从币安获取最新价格
- 更新数据库中的当前价格
- 如果当天最高价突破历史高点，同步更新high字段

### 4. `combined_scheduler.py`

综合定时任务调度器，负责：
- 同时管理Excel同步和价格更新两个定时任务
- Excel同步：每天8:30执行
- 价格更新：每15分钟执行

## 使用方法

### 方法1：手动执行一次同步

```bash
# 同步最新的Excel文件
python3 src/alert/excel_to_db_sync.py

# 指定Excel文件
python3 src/alert/excel_to_db_sync.py --excel-file data/qualified_tokens_multi_period_20251012_215327.xlsx

# 指定日期
python3 src/alert/excel_to_db_sync.py --date 2025-10-12

# 指定数据目录
python3 src/alert/excel_to_db_sync.py --data-dir /path/to/data
```

### 方法2：启动定时任务

```bash
# 默认每天8:30执行
python3 src/alert/scheduler.py

# 自定义执行时间（每天10:00）
python3 src/alert/scheduler.py --time 10:00

# 启动时立即执行一次
python3 src/alert/scheduler.py --run-now

# 只执行一次然后退出
python3 src/alert/scheduler.py --once
```

### 方法3：价格更新（新功能）

```bash
# 手动更新一次所有监控代币的价格
python3 src/alert/price_updater.py --once

# 启动价格更新器，每15分钟自动更新
python3 src/alert/price_updater.py

# 自定义更新间隔为5分钟
python3 src/alert/price_updater.py --interval 5
```

### 方法4：综合调度器（推荐）

同时运行Excel同步和价格更新：

```bash
# 启动综合调度器（Excel同步每天8:30，价格更新每15分钟）
python3 src/alert/combined_scheduler.py

# 启动时立即执行所有任务
python3 src/alert/combined_scheduler.py --run-all-now

# 自定义Excel同步时间为10:00
python3 src/alert/combined_scheduler.py --excel-time 10:00

# 自定义价格更新间隔为5分钟
python3 src/alert/combined_scheduler.py --price-interval 5

# 只运行价格更新任务
python3 src/alert/combined_scheduler.py --price-only

# 只运行Excel同步任务
python3 src/alert/combined_scheduler.py --excel-only
```

### 方法5：使用系统 crontab

编辑 crontab：
```bash
crontab -e
```

添加以下行：
```bash
# Excel数据同步：每天8:30执行
30 8 * * * cd /home/ubuntu/code/anti-package && /usr/bin/python3 src/alert/scheduler.py --once >> logs/sync.log 2>&1

# 价格更新：每15分钟执行（可选，推荐使用综合调度器）
*/15 * * * * cd /home/ubuntu/code/anti-package && /usr/bin/python3 src/alert/price_updater.py --once >> logs/price_update.log 2>&1
```

或者使用综合调度器（推荐）：
```bash
# 启动综合调度器（需要保持运行）
@reboot cd /home/ubuntu/code/anti-package && /usr/bin/python3 src/alert/combined_scheduler.py >> logs/combined_scheduler.log 2>&1
```

### 方法6：使用 systemd 服务（推荐用于生产环境）

创建服务文件 `/etc/systemd/system/excel-sync-timer.service`：
```ini
[Unit]
Description=Excel Data Sync Service
After=network.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/code/anti-package
ExecStart=/usr/bin/python3 /home/ubuntu/code/anti-package/src/alert/scheduler.py --once
StandardOutput=append:/home/ubuntu/code/anti-package/logs/sync.log
StandardError=append:/home/ubuntu/code/anti-package/logs/sync_error.log

[Install]
WantedBy=multi-user.target
```

创建定时器文件 `/etc/systemd/system/excel-sync-timer.timer`：
```ini
[Unit]
Description=Excel Data Sync Timer
Requires=excel-sync-timer.service

[Timer]
OnCalendar=*-*-* 08:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

启用并启动：
```bash
sudo systemctl daemon-reload
sudo systemctl enable excel-sync-timer.timer
sudo systemctl start excel-sync-timer.timer

# 查看状态
sudo systemctl status excel-sync-timer.timer
```

#### 使用综合调度器的 systemd 服务（推荐）

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

启用并启动：
```bash
sudo systemctl daemon-reload
sudo systemctl enable combined-scheduler.service
sudo systemctl start combined-scheduler.service

# 查看状态
sudo systemctl status combined-scheduler.service

# 查看日志
sudo journalctl -u combined-scheduler.service -f
```

## 数据映射关系

从 Excel 到数据库的字段映射：

| Excel | 数据库字段 | 说明 |
|-------|-----------|------|
| Sheet名称 | interval | '1日筛选结果'→'1D', '3日筛选结果'→'3D', '周筛选结果'→'1W' |
| symbol | ticker | 代币名称（如: BTCUSDT） |
| - | exchange | 固定为 'bn' (Binance) |
| - | date | 当天日期 |
| T_minus_2_low, T_minus_1_low | low | 取两者最小值 |
| T_minus_2_high, T_minus_1_high | high | 取两者最大值 |
| high | current_price | 使用high的值 |

## Excel 文件格式

期望的 Excel 文件格式：

**文件名**: `qualified_tokens_multi_period_YYYYMMDD_HHMMSS.xlsx`

**Sheet 结构**:
- Sheet 1: `1日筛选结果`
- Sheet 2: `3日筛选结果`
- Sheet 3: `周筛选结果`

**每个 Sheet 的列**:
- symbol: 交易对名称
- T_minus_2_date, T_minus_2_high, T_minus_2_low: T-2日的数据
- T_minus_1_date, T_minus_1_high, T_minus_1_low: T-1日的数据
- 其他列...

## 查询同步的数据

使用 `query_db.py` 工具查询：

```bash
# 查询所有bn交易所的监控数据
python3 query_db.py monitors --exchange bn

# 查询特定ticker
python3 query_db.py monitors --ticker BTCUSDT --exchange bn

# 查询特定时间粒度
python3 query_db.py monitors --interval 1D

# 查看统计信息
python3 query_db.py stats
```

## 日志

定时任务的日志会输出到：
- 标准输出：同步过程信息
- 标准错误：错误信息

建议使用系统日志服务或重定向到文件：
```bash
python3 src/alert/scheduler.py >> logs/sync.log 2>&1
```

## 依赖包

确保安装了以下Python包：
```bash
pip install pandas openpyxl schedule
```

## 常见问题

### 1. 找不到Excel文件

**问题**: `未找到匹配的文件`

**解决**: 
- 检查 data 目录下是否有 `qualified_tokens_multi_period_*.xlsx` 文件
- 使用 `--data-dir` 参数指定正确的目录

### 2. 数据库连接失败

**问题**: 无法连接到数据库

**解决**:
- 确保数据库文件路径正确
- 检查文件权限

### 3. Sheet名称不匹配

**问题**: `未知的sheet名称`

**解决**:
- 确保Excel文件的sheet名称为：`1日筛选结果`, `3日筛选结果`, `周筛选结果`
- 或在代码中修改 `SHEET_INTERVAL_MAP` 映射

## 监控和维护

### 检查同步状态

```bash
# 查看最近的监控记录
python3 query_db.py monitors --exchange bn | head -20

# 查看数据库统计
python3 query_db.py stats
```

### 手动触发同步

如果定时任务没有执行，可以手动触发：
```bash
python3 src/alert/scheduler.py --once
```

### 清理旧数据

定期清理历史数据（可选）：
```bash
python3 query_db.py clear-old-alerts --days 30
```

## 价格更新功能详解

### 工作原理

1. **定时获取**：每15分钟（可配置）从币安获取所有监控代币的最新K线数据
2. **智能更新**：
   - 获取当天K线的最高价（high）和当前价格（close）
   - 如果当天最高价 > 数据库中的high，则同时更新high和current_price
   - 否则只更新current_price
3. **API友好**：每次请求之间有0.5秒延迟，避免触发API限流

### 应用场景

- **实时监控**：持续追踪代币价格变化
- **突破检测**：记录价格突破历史高点的时刻
- **价格预警**：为后续的报警功能提供数据基础

## 扩展功能

可以基于此模块扩展以下功能：

1. ✅ **价格实时更新** - 每15分钟自动更新价格（已实现）
2. **价格突破报警** - 监控价格突破high或跌破low（待实现）
3. **邮件通知** - 发送同步结果到邮箱（待实现）
4. **Webhook通知** - 发送到钉钉、企业微信等（待实现）
5. **数据可视化** - 展示监控的代币价格走势（待实现）

## 技术支持

如有问题，请查看：
1. 日志文件
2. 数据库内容：`python3 query_db.py stats`
3. Excel文件格式是否正确

