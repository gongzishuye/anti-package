# 监控 + 报警子系统设计

恢复 `0a99af6`（首次提交）的"动态配置 → 监控 → 报警"链路到当前精简分支 `19ae5e1`，对齐 production 页面 `http://43.156.245.36:8866/token-config`。

## 1. 范围

**包含：**
- Web 页面 `token-config` 与 production 行为一致（4 路由 + 完整前端）
- `tokens-config-dynamic.md` mtime 热重载
- 调度器在 Flask 进程内运行（APScheduler）
- 反包检测（向上/向下反包形态识别）
- 企业微信 Webhook 推送（markdown + K 线图）
- `WECOM_WEBHOOK_URL2` 配置驱动动态配置通道

**不包含：**
- ~~PriceUpdater / 斐波那契回撤~~（用户剔除）
- ~~FundingRateMonitor~~
- ~~MetalReversalDetector~~
- ~~静态配置 `tokens-config.md` 通道 + `WECOM_WEBHOOK_URL1`~~（保留变量但本期不消费）
- ~~Equity（US/HK/A 股）相关~~
- ~~反包图表保存到本地 `data/charts/`~~（本期仅发送，不落盘历史图表）

## 2. 架构

```
token_config_server.py (单进程 Flask, 端口 8866)
├── Flask web routes         # 4 个路由（GET/POST）
└── APScheduler BackgroundScheduler  # 启动时拉起
    ├── 5M / 10M / 15M / 30M 反包检测
    ├── 1H / 2H 反包检测
    ├── 4H / 6H / 8H / 12H 反包检测
    ├── 1D / 3D 反包检测
    ├── 1W 反包检测（仅周一）
    └── 2D / 5D / 1M 高频反包检测（每日 00:10）

数据流：
  /token-config → save → tokens-config-dynamic.md
                                       ↓ mtime
  monitor_config._load_tokens_config_dynamic()
                                       ↓
  CryptoReversalDetector.detect_*_dynamic(interval)
    for ticker in get_dynamic_symbols():
        check_reversal_pattern(ticker, 'bn_futures', interval, force=True)
        check_bearish_reversal_pattern(...)
                                       ↓ 命中
  _send_priority_alert(reversal)
    notifier.send_markdown_message(content)
    notifier.send_image_message(chart_path)
                                       ↓ requests.post
  WECOM_WEBHOOK_URL2
```

## 3. 文件结构

### 新增/恢复文件（来自 `0a99af6`）

```
src/alert/
├── monitor_config.py              # mtime 热重载（保留）
├── wecom_notifier.py              # WeCom 推送
├── crypto_reversal_detector.py    # 反包形态识别
├── combined_scheduler.py          # 改造：仅保留反包检测任务
└── tokens-config-dynamic.md       # 数据源（保留）

src/crypto/
├── binance_data_fetcher.py        # 币安 K 线获取（detector 依赖）
└── token_config_server.py         # 改造：增加 APScheduler 集成 + 新 HTML 模板

src/database/
└── db_manager.py                  # SQLite 存储（detector 依赖）
```

### 删除文件（当前没有、恢复时会留空）

- ~~`src/alert/price_updater.py`~~ — 不搬回
- ~~`src/alert/funding_rate_monitor.py`~~ — 不搬回
- ~~`src/alert/excel_to_db_sync.py`~~ — 反包检测器需要 SQLite，搬回 `db_manager.py` 即可
- ~~`src/alert/daily_sync.py`~~ — 不搬回
- ~~`src/alert/excel_to_db_importer.py`~~ — 不搬回
- ~~`src/alert/scheduler.py`~~ — 用 APScheduler 替代 schedule

## 4. 前端：HTML 模板

目标与 production（`http://43.156.245.36:8866/token-config`）一致：

1. **info-box 详细化**：列出 0/1/2/3 各级别语义（15m+/1h+/4h+/日线+）
2. **3 个按钮**：[💾 保存配置] [✅ 验证配置] [🔄 重新加载]
3. **token 标签按级别上色** + 徽章（CSS `.token-tag.level-0/1/2/3`）
4. **校验结果面板**：errors / warnings / summary（总计 + 各级别计数）
5. **XSS 防护**：所有 `innerHTML` 拼接前调 `escapeHtml()`

后端 `/api/token-config/validate` 已在精简版本中实现，前端加上对应按钮和渲染即可。

## 5. 后端模块

### 5.1 `monitor_config.py`（小改动）
- 仅保留 `_load_tokens_config_dynamic()` 和 `get_dynamic_symbols()`
- 删除 `_load_tokens_config()`、`get_monitored_symbols()`、`MONITORED_INTERVALS` 中不需要的部分
- 保留 `INTERVAL_MAP`（detector 需要映射）

### 5.2 `wecom_notifier.py`（原样恢复）
- `WeComNotifier` 类
- `send_text_message()`、`send_markdown_message()`、`send_image_message()`
- 从环境变量 `WECOM_WEBHOOK_URL2` 读取（动态配置通道）

### 5.3 `db_manager.py`（简化恢复）
- 反包检测器需要的最小表：
  - `monitors` (id, exchange, date, interval, ticker, high, low, current_price, source, update_time)
  - `alerts` (id, ticker, exchange, interval, trigger_signal, update_time)
- `get_all_monitors()`、`add_monitor()`、`delete_monitor()`、`get_alerts()`、`add_alert()`

### 5.4 `binance_data_fetcher.py`（原样恢复）
- `BinanceDataFetcher(market_type='futures')`
- `get_klines(symbol, interval, limit)` 返回 DataFrame
- 公开 Binance API，无需认证

### 5.5 `crypto_reversal_detector.py`（精简恢复）
- 仅保留 `detect_*_dynamic()` 方法（动态配置通道）
- 删除 `detect_priority_reversals()`、`detect_all_monitors()`、`detect_high_frequency_reversals()`（非 dynamic 版本）
- 删除 MA100/MA52/EMA144 检测代码（已禁用）
- 删除 OKX 通道（本期仅币安）
- 删除 `funding_rate_monitor` 相关引用
- 删除图表保存到 `data/charts/` 的逻辑（仅发送）

### 5.6 `combined_scheduler.py`（精简重写）
- 继承原结构，但只保留动态配置的反包检测任务
- 改造为可被 Flask 直接调用：`start()` 方法启动 APScheduler
- 调度点（与原系统对齐）：
  - 5M/10M/15M/30M：每 30 分钟整点附近执行
  - 1H/2H：每 2 小时整点附近执行
  - 4H/6H/8H/12H：每 12 小时整点附近执行
  - 1D/3D：每天 08:02 执行
  - 1W：每周一 08:02 执行
  - 2D/5D/1M：每天 00:10 执行（高频）

### 5.7 `token_config_server.py`（整合）
- 在 `main()` 中：
  ```python
  scheduler = CombinedScheduler()
  scheduler.start()  # 启动 APScheduler 后台调度
  app.run(host='0.0.0.0', port=args.port, debug=False)
  ```
- 新 HTML 模板替换原 `get_token_config_html_template()`
- 保留现有 4 个 API 路由

## 6. 进程模型

```
单进程：
  PID = python3 src/crypto/token_config_server.py [port]
  ├── Flask web server (主线程)
  └── APScheduler BackgroundScheduler (后台线程)
      └── Job 线程池执行具体的反包检测任务

服务管理（沿用 scripts/crypto/start_token_config.sh）：
  PID 文件：logs/token_config_server.pid
  日志：logs/token_config_server.log
  停止：kill $(cat logs/token_config_server.pid)
  pkill -f token_config_server.py 兜底
```

## 7. 依赖

```
# requirements.txt 新增：
flask>=2.0.0
flask-cors>=3.0.0
requests>=2.28.0      # WeCom 推送
schedule>=1.2.0       # （如使用 schedule）或 APScheduler
pandas>=1.5.0         # K 线数据处理
matplotlib>=3.5.0     # K 线图生成
python-dotenv>=1.0.0  # .env 加载
```

注：原 `crypto_reversal_detector.py` 依赖 APScheduler，统一选用 APScheduler 即可（替代 `schedule`）。

## 8. 配置与环境变量

`.env`（gitignored，本期新增读取）：
```bash
WECOM_WEBHOOK_URL2=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=37f7e3c5-...
# 可选：发送图片最大字节（避免过大）
WECOM_IMAGE_MAX_BYTES=2097152  # 2MB
```

`env.example` 同步更新：
```bash
# 动态配置监控报警通道（必须）
WECOM_WEBHOOK_URL2=your-webhook-url-here
```

**降级行为**：`WECOM_WEBHOOK_URL2` 未配置时，调度器启动正常但报警发送会被跳过（detector 内置 fallback）。

## 9. 验证策略

| 阶段 | 验证方式 |
|------|---------|
| 文件恢复后 | `python3 -c "import src.alert.monitor_config"` 无语法错误 |
| 依赖安装 | `pip install -r requirements.txt` 成功 |
| 冷启动 | `bash scripts/crypto/start_token_config.sh 8869` → 服务启动 + 调度器启动，日志出现 `⏰ 定时任务已启动` |
| Web 页面 | `curl /token-config` 返回 200，包含"验证配置"按钮 + level-0/1/2/3 CSS |
| 配置保存 / 读取 | `POST /api/token-config/save` 写文件，`GET /api/token-config` 读回一致 |
| 校验 | `POST /api/token-config/validate` 返回 summary 含 level_0_count 等字段 |
| Token 热重载 | 修改 `tokens-config-dynamic.md` 后等下次调度触发，日志出现"检测到变化，已重新加载" |
| 反包检测 dry-run | 临时把 webhook 指向 `https://httpbin.org/post`，跑一次 `detect_priority_reversals_dynamic('1H')`，确认请求到达 |
| XSS 防护 | 配置里写 `<img src=x onerror=alert(1)>`，保存后页面预览不应触发 |
| 配置可逆性 | 测试结束后从 git HEAD 还原 `tokens-config-dynamic.md`，md5 校验 |

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 调度器在 Web 进程内，长任务阻塞请求 | Flask 走主线程，调度器走 BackgroundScheduler + 独立线程池 |
| Binance API 限流 | 单次 fetch 仅拉 10 根 K 线，单 detector 跑完一批后休眠 |
| 频繁报警 | `_send_priority_alert` 内置去重（DB `alerts` 表 24h 内同 ticker+interval 不重复） |
| matplotlib 启动慢 | 进程启动时立即 `import matplotlib`，避免首次报警时延迟 |
| 反包检测代码量大 | 从 `0a99af6` 复制后立即 grep 删除 `metal/equity/funding/static-config` 相关引用 |

## 11. 不在范围

- ~~静态配置 `tokens-config.md` 通道 + `WECOM_WEBHOOK_URL`~~
- ~~资金费率监控~~
- ~~贵金属反包~~
- ~~历史图表保存~~
- ~~多 webhook 路由（每标的独立 webhook）~~
- ~~自动同步 Excel 到数据库（detector 不需要，删表都不影响核心流程）~~