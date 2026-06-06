# Flask自动化服务 - 多周期Token筛选

## 📋 概述

这是一个集成了自动化定时任务的Flask Web服务，可以：
- ⏰ **每天早上8点自动执行**数据获取和筛选
- 🎯 **实时展示**最新的筛选结果
- 🔄 **手动触发**立即更新数据
- 📊 **多周期展示**：1日、3日、周K线数据

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install flask flask-cors apscheduler --break-system-packages
```

或者使用requirements.txt：

```bash
pip3 install -r requirements.txt --break-system-packages
```

### 2. 启动服务

```bash
# 使用默认端口5000
bash scripts/start_flask_auto.sh

# 或指定端口
bash scripts/start_flask_auto.sh 8080
```

### 3. 访问Web界面

打开浏览器访问：
- http://localhost:5000
- http://127.0.0.1:5000

## ✨ 主要功能

### 自动化流程

服务启动后会自动执行以下流程：

1. **定时任务**：每天早上 08:00 自动执行
2. **数据获取**：
   - 获取Binance Top100币种
   - 获取1日、3日、周K线数据
   - 保存到Excel文件（多个sheet）
3. **数据筛选**：
   - 应用技术指标筛选条件
   - 筛选出符合条件的Token
   - 保存筛选结果到Excel
4. **Web展示**：
   - 自动读取最新筛选结果
   - 在Web界面实时展示
   - 支持多周期切换查看

### 手动触发

如果不想等到早上8点，可以在Web界面点击"手动触发任务"按钮，立即执行更新流程。

**注意**：手动更新需要10-15分钟完成，请耐心等待。

### 任务状态监控

Web界面会实时显示：
- ✅ 任务状态（未运行/运行中/成功/失败）
- 💬 执行消息
- 🕐 上次运行时间
- ⏰ 下次运行时间

## 📊 筛选条件

与之前的筛选脚本一致：

1. **T-1成交量 > T-2成交量**
2. **T-2是阴线**（收盘价 < 开盘价）
3. **T-1是阳线**（收盘价 > 开盘价）
4. **T-1收盘价 > T-2开盘价**

## 🎨 Web界面功能

### 多周期切换
- 1日K线筛选结果
- 3日K线筛选结果
- 周K线筛选结果

### 统计信息
- 符合条件Token数量
- 平均成交量增长率
- 平均价格涨幅
- 最大成交量增长率

### 搜索功能
- 实时搜索Token名称
- 快速定位目标币种

### 数据展示
- 按USDT成交量排序
- 显示详细K线数据
- 点击Token跳转Binance交易页面

## 📁 文件说明

```
anti-package/
├── src/
│   └── flask_auto_server.py      # Flask自动化服务主程序
├── scripts/
│   └── start_flask_auto.sh       # 服务启动脚本
├── logs/
│   ├── flask_auto_server.log     # 服务运行日志
│   └── flask_auto_server.pid     # 进程ID文件
├── data/
│   ├── binance_top100_multi_period_*.xlsx      # K线原始数据
│   └── qualified_tokens_multi_period_*.xlsx    # 筛选结果
└── docs/
    └── README_FLASK_AUTO.md      # 本文档
```

## 🔧 服务管理

### 查看服务状态

```bash
ps aux | grep flask_auto_server
```

### 查看日志

```bash
# 实时查看
tail -f logs/flask_auto_server.log

# 查看最近100行
tail -100 logs/flask_auto_server.log
```

### 停止服务

```bash
# 方法1：使用PID文件
kill $(cat logs/flask_auto_server.pid)

# 方法2：直接杀进程
pkill -f flask_auto_server.py
```

### 重启服务

```bash
# 启动脚本会自动检测并停止旧服务
bash scripts/start_flask_auto.sh
```

## ⚙️ 配置说明

### 修改定时任务时间

编辑 `src/flask_auto_server.py`，找到 `init_scheduler()` 函数：

```python
# 修改hour和minute参数
scheduler.add_job(
    func=auto_fetch_and_filter,
    trigger='cron',
    hour=8,        # 小时（0-23）
    minute=0,      # 分钟（0-59）
    ...
)
```

### 修改端口

```bash
# 启动时指定端口
bash scripts/start_flask_auto.sh 8080
```

## 🎯 使用场景

### 场景1：日常使用
1. 启动服务，让它在后台运行
2. 每天早上8点自动更新数据
3. 随时打开浏览器查看最新筛选结果

### 场景2：立即查看
1. 访问Web界面
2. 点击"手动触发任务"
3. 等待10-15分钟
4. 查看最新数据

### 场景3：多设备访问
1. 在服务器上启动服务
2. 在其他设备浏览器访问：http://服务器IP:5000
3. 随时随地查看数据

## 🐛 故障排查

### 问题1：服务无法启动

**检查依赖**：
```bash
python3 -c "import flask, flask_cors, apscheduler"
```

如果报错，安装缺失的包：
```bash
pip3 install flask flask-cors apscheduler --break-system-packages
```

### 问题2：端口被占用

```bash
# 查找占用端口的进程
lsof -i :5000

# 使用其他端口
bash scripts/start_flask_auto.sh 8080
```

### 问题3：任务执行失败

查看日志：
```bash
tail -f logs/flask_auto_server.log
```

常见原因：
- Binance API连接失败
- 数据文件权限问题
- Python包缺失

### 问题4：无法访问Web界面

1. 检查服务是否运行：
```bash
ps aux | grep flask_auto_server
```

2. 检查端口是否监听：
```bash
netstat -tuln | grep 5000
```

3. 检查防火墙设置

## 💡 最佳实践

1. **后台运行**：使用启动脚本，服务会自动后台运行
2. **定期检查**：偶尔查看日志，确保任务正常执行
3. **数据备份**：定期备份 `data/` 目录
4. **资源监控**：如果运行在小内存机器上，注意监控资源使用

## 🔄 更新日志

### v1.0.0 (2025-10-04)
- ✅ 集成Flask Web服务
- ✅ 添加定时任务功能（每天早上8点）
- ✅ 支持手动触发更新
- ✅ 实时任务状态监控
- ✅ 多周期数据展示
- ✅ 自动化数据获取和筛选流程

## 📞 技术支持

如有问题，请查看：
1. 日志文件：`logs/flask_auto_server.log`
2. 筛选脚本文档：`docs/README_MULTI_FILTER.md`
3. 数据获取文档：`docs/README_MULTI_PERIOD.md`

---

🎉 享受自动化带来的便利！

