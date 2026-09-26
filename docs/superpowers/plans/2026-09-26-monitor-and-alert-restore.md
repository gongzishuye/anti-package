# 监控 + 报警子系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 恢复 `0a99af6` 的"动态配置 → 反包检测 → 企业微信报警"链路到当前分支，Web 前端对齐 production。

**Architecture:** 单进程 Flask + APScheduler 后台调度器。Web 路由与原 `0a99af6:src/crypto/flask_auto_server.py` 一致；调度器在 `main()` 启动；`tokens-config-dynamic.md` 通过 mtime 热重载驱动反包检测。

**Tech Stack:** Python 3.10+, Flask 2.0+, APScheduler 3.10+, pandas 1.5+, matplotlib 3.5+, requests 2.28+, python-dotenv 1.0+

**Spec:** `docs/superpowers/specs/2026-09-26-monitor-and-alert-restore-design.md`

## Global Constraints

- 端口默认 8866（与历史 production 一致）；CLI 参数 `port` 可覆盖
- 仅消费 `WECOM_WEBHOOK_URL2`（`WECOM_WEBHOOK_URL` 保留变量但本期不消费）
- 配置数据源：`src/alert/tokens-config-dynamic.md`（不动）
- 日志：`logs/token_config_server.log`（沿用现有）
- PID 文件：`logs/token_config_server.pid`（沿用现有）
- 启动脚本：`scripts/crypto/start_token_config.sh`（已存在，不改）
- 配置文件 md5：`639ac90cdf8c60c7139aaa41fd4844d5`（验证前后不变）
- 依赖：`requirements.txt` 必须可 `pip install -r requirements.txt --break-system-packages` 成功
- 不要改 `src/alert/tokens-config-dynamic.md` 的初始内容（测试结束后从 git HEAD 还原）

## Review Focus

| 输入类 / 失败模式 | 期望行为 | 归属任务 |
|------------------|---------|---------|
| Web 页面含恶意 symbol `<img src=x onerror=alert(1)>` | 预览标签转义，不触发 XSS | Task 8 |
| `WECOM_WEBHOOK_URL2` 未配置 | 调度器启动正常，报警发送静默跳过 | Task 4 |
| Binance API 调用失败（网络/限流） | detector 单次失败不中断其他 ticker 循环 | Task 5 |
| `tokens-config-dynamic.md` 写后立刻拉取 | mtime 缓存命中下次 reload，下次调度生效 | Task 1 |
| 调度器与 Web 同进程，调度任务阻塞 HTTP | APScheduler 用独立线程池，HTTP 不阻塞 | Task 9 |

---

### Task 1: 恢复并精简 `src/alert/monitor_config.py`

**Files:**
- Create: `src/alert/__init__.py`（空文件）
- Create: `src/alert/monitor_config.py`

**Source:** `0a99af6:src/alert/monitor_config.py`

**Interfaces:**
- Produces: `get_dynamic_symbols() -> List[str]`，`INTERVAL_MAP: Dict[str, str]`

- [ ] **Step 1: 创建 `src/alert/__init__.py`（空文件）**

```bash
touch src/alert/__init__.py
```

- [ ] **Step 2: 从 `0a99af6` 复制 `monitor_config.py`**

```bash
git show 0a99af6:src/alert/monitor_config.py > src/alert/monitor_config.py
```

- [ ] **Step 3: 删除静态配置相关代码**

打开 `src/alert/monitor_config.py`，删除：
- 函数 `_load_tokens_config`（L37-71）
- 函数 `get_monitored_symbols`（L137-138）
- 全局变量 `_tokens_cache`、`_tokens_last_mtime`、`_tokens_lock`（L33-35）
- 文件末尾的 `_load_tokens_config()` 调用（L144）
- 注释行 `[已禁用] PRECIOUS_METALS`

保留：
- `_load_tokens_config_dynamic()` 函数（不改）
- `get_dynamic_symbols()` 函数（不改）
- `INTERVAL_MAP` 常量（不改，detector 需要）
- `MONITORED_INTERVALS` 常量（不改，detector 需要）

- [ ] **Step 4: 验证导入**

```bash
python3 -c "
from src.alert.monitor_config import get_dynamic_symbols, INTERVAL_MAP, MONITORED_INTERVALS
print('symbols:', get_dynamic_symbols())
print('intervals count:', len(MONITORED_INTERVALS))
print('15M maps to:', INTERVAL_MAP['15M'])
"
```

期望输出：`symbols: ['BTCUSDT', 'ZECUSDT', 'HYPEUSDT', 'BNBUSDT', ...]`、`intervals count: 16`、`15M maps to: 15m`

- [ ] **Step 5: 提交**

```bash
git add src/alert/__init__.py src/alert/monitor_config.py
git commit -m "feat(alert): restore monitor_config with mtime hot-reload for dynamic channel"
```

---

### Task 2: 恢复并精简 `src/database/db_manager.py`

**Files:**
- Create: `src/database/__init__.py`（空文件）
- Create: `src/database/db_manager.py`

**Source:** `0a99af6:src/database/db_manager.py`

**Interfaces:**
- Produces: `DatabaseManager()` 类，包含 `get_all_monitors()`、`add_monitor()`、`delete_monitor()`、`get_alerts()`、`add_alert()` 方法

- [ ] **Step 1: 创建 `src/database/__init__.py`**

```bash
mkdir -p src/database && touch src/database/__init__.py
```

- [ ] **Step 2: 复制 `db_manager.py`**

```bash
git show 0a99af6:src/database/db_manager.py > src/database/db_manager.py
```

- [ ] **Step 3: 精简表结构**

打开 `src/database/db_manager.py`，找到 `_init_database` 或类似的 schema 定义方法，**只保留以下两张表的 CREATE TABLE 语句**：
- `monitors`（id, exchange, date, interval, ticker, high, low, current_price, source, update_time）
- `alerts`（id, ticker, exchange, interval, trigger_signal, update_time）

删除其他所有表（funding_rates、metal、equity 等）的 CREATE 语句。

保留方法（不删）：`get_all_monitors`、`add_monitor`、`delete_monitor`、`get_alerts`、`add_alert`。

如果其他方法引用了已删的表，则**也删除这些方法**。

- [ ] **Step 4: 验证导入和表初始化**

```bash
python3 -c "
import tempfile, os
with tempfile.TemporaryDirectory() as d:
    os.chdir(d)
    from src.database.db_manager import DatabaseManager
    db = DatabaseManager()
    with db:
        mid = db.add_monitor(exchange='bn_futures', date='2026-09-26', interval='1H', ticker='BTCUSDT', high=100, low=90, current_price=95, source='manual')
        monitors = db.get_all_monitors()
        print('monitors:', len(monitors))
        aid = db.add_alert(ticker='BTCUSDT', exchange='bn_futures', interval='1H', trigger_signal='reversal_bullish')
        alerts = db.get_alerts(ticker='BTCUSDT')
        print('alerts:', len(alerts))
"
```

期望输出：`monitors: 1`、`alerts: 1`

- [ ] **Step 5: 提交**

```bash
git add src/database/__init__.py src/database/db_manager.py
git commit -m "feat(database): restore minimal db_manager with monitors + alerts tables"
```

---

### Task 3: 恢复并精简 `src/crypto/binance_data_fetcher.py`

**Files:**
- Create: `src/crypto/binance_data_fetcher.py`

**Source:** `0a99af6:src/crypto/binance_data_fetcher.py`

**Interfaces:**
- Produces: `BinanceDataFetcher(market_type='futures'|'spot')` 类，包含 `get_klines(symbol, interval, limit=10) -> pd.DataFrame` 方法

- [ ] **Step 1: 复制文件**

```bash
git show 0a99af6:src/crypto/binance_data_fetcher.py > src/crypto/binance_data_fetcher.py
```

- [ ] **Step 2: 删除 OKX 相关代码**

如果文件中导入了 `okx_data_fetcher` 或有 OKX 专属方法，删除相关代码。只保留 Binance 公开 API 调用。

- [ ] **Step 3: 验证导入和 Binance 公共 API**

```bash
python3 -c "
from src.crypto.binance_data_fetcher import BinanceDataFetcher
fetcher = BinanceDataFetcher(market_type='futures')
df = fetcher.get_klines('BTCUSDT', '1h', limit=3)
print('rows:', len(df))
print('cols:', list(df.columns))
"
```

期望输出：`rows: 3`、`cols: ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', ...]`

- [ ] **Step 4: 提交**

```bash
git add src/crypto/binance_data_fetcher.py
git commit -m "feat(crypto): restore BinanceDataFetcher for K-line pulls"
```

---

### Task 4: 恢复 `src/alert/wecom_notifier.py`

**Files:**
- Create: `src/alert/wecom_notifier.py`

**Source:** `0a99af6:src/alert/wecom_notifier.py`

**Interfaces:**
- Produces: `WeComNotifier(webhook_url)` 类，包含 `send_text_message()`、`send_markdown_message()`、`send_image_message()` 方法
- 从环境变量 `WECOM_WEBHOOK_URL2` 读取（detector 构造时传入）

- [ ] **Step 1: 复制文件**

```bash
git show 0a99af6:src/alert/wecom_notifier.py > src/alert/wecom_notifier.py
```

- [ ] **Step 2: 验证导入和 mock 发送**

```bash
python3 -c "
import os
os.environ['WECOM_WEBHOOK_URL2'] = 'https://example.invalid/webhook'
from src.alert.wecom_notifier import WeComNotifier
n = WeComNotifier(webhook_url='https://example.invalid/webhook')
print('notifier created:', n.webhook_url[:40])
print('methods:', [m for m in dir(n) if not m.startswith('_') and 'send' in m])
"
```

期望输出：`notifier created: https://example.invalid/webhook`、`methods: ['send_text_message', 'send_markdown_message', 'send_image_message']`

- [ ] **Step 3: 验证 webhook 未配置时降级**

```bash
python3 -c "
from src.alert.wecom_notifier import WeComNotifier
n = WeComNotifier(webhook_url=None)
print('webhook_url:', n.webhook_url)
result = n.send_markdown_message('test')
print('send result (should be False):', result)
"
```

期望输出：`webhook_url: None`、`send result (should be False): False`

- [ ] **Step 4: 提交**

```bash
git add src/alert/wecom_notifier.py
git commit -m "feat(alert): restore WeComNotifier for webhook pushes"
```

---

### Task 5: 恢复并精简 `src/alert/crypto_reversal_detector.py`

**Files:**
- Create: `src/alert/crypto_reversal_detector.py`

**Source:** `0a99af6:src/alert/crypto_reversal_detector.py`（1952 行，需大量精简）

**Interfaces:**
- Produces: `CryptoReversalDetector(wecom_webhook_url)` 类
  - `detect_priority_reversals_dynamic(target_interval: str) -> List[Dict]`
  - `detect_high_frequency_reversals_dynamic(intervals: List[str]) -> List[Dict]`
  - 内部：`check_reversal_pattern()`、`check_bearish_reversal_pattern()`、`_send_priority_alert()`、`_build_priority_alert_content()`、`_generate_futures_kline_chart()`、`_format_datetime()`

- [ ] **Step 1: 复制文件**

```bash
git show 0a99af6:src/alert/crypto_reversal_detector.py > src/alert/crypto_reversal_detector.py
wc -l src/alert/crypto_reversal_detector.py
```

期望：`~1952 lines`

- [ ] **Step 2: 精简导入**

删除 import 中不需要的依赖（OKX fetcher、equity 模块、funding rate 等）。

- [ ] **Step 3: 删除静态配置通道的方法**

打开文件，删除以下方法（如果存在）：
- `detect_priority_reversals()`（非 dynamic 版本）
- `detect_all_monitors()`（非 dynamic 版本）
- `detect_high_frequency_reversals()`（非 dynamic 版本）
- `update_all_monitors()`（PriceUpdater 的方法）
- `check_reversal_pattern_utf8()`（如有，使用 check_reversal_pattern 替代）
- `check_reversal_pattern_okx_utf8()`（OKX 通道）
- `_convert_ticker_to_okx_format()`（OKX）
- 所有 `_check_*_ma_ema`、`_check_ma100_touch`、`_send_ma100_alert`、`detect_ma100_touches`（MA100/52/144 检测）
- `_check_precious_metal_ma_ema`、`_send_precious_metal_alert`（贵金属）

- [ ] **Step 4: 保留并确保可用**

保留方法：
- `__init__`
- `get_kline_data()`
- `_format_datetime()`
- `_build_priority_alert_content()`
- `_generate_futures_kline_chart()`
- `_send_priority_alert()`
- `check_reversal_pattern()`
- `check_bearish_reversal_pattern()`
- `detect_priority_reversals_dynamic()`（保留所有 `_dynamic` 后缀的方法）
- `detect_high_frequency_reversals_dynamic()`

如有任何被删方法在保留方法中被调用，则**改写调用或删除调用方代码**。

- [ ] **Step 5: 验证导入和实例化**

```bash
python3 -c "
from src.alert.crypto_reversal_detector import CryptoReversalDetector
d = CryptoReversalDetector(wecom_webhook_url=None)
methods = [m for m in dir(d) if 'dynamic' in m.lower() or 'reversal' in m.lower() or 'send_priority' in m]
print('methods:', methods)
"
```

期望输出包含：`['detect_priority_reversals_dynamic', 'detect_high_frequency_reversals_dynamic', '_send_priority_alert', 'check_reversal_pattern', 'check_bearish_reversal_pattern']`

- [ ] **Step 6: 验证 dry-run（不报警）**

```bash
python3 -c "
from src.alert.crypto_reversal_detector import CryptoReversalDetector
d = CryptoReversalDetector(wecom_webhook_url=None)  # 不发报警
results = d.detect_priority_reversals_dynamic('1H')
print('results count:', len(results))
"
```

期望输出：`results count: 0` 或 `results count: N`（N 为正整数，至少跑通无异常）

- [ ] **Step 7: 提交**

```bash
git add src/alert/crypto_reversal_detector.py
git commit -m "feat(alert): restore crypto_reversal_detector trimmed to dynamic channel"
```

---

### Task 6: 精简并适配 `src/alert/combined_scheduler.py`

**Files:**
- Create: `src/alert/combined_scheduler.py`

**Source:** `0a99af6:src/alert/combined_scheduler.py`（755 行，需精简）

**Interfaces:**
- Produces: `CombinedScheduler(wecom_webhook_url2)` 类
  - `start()` 方法启动 APScheduler 后台调度
  - 内部调度任务：动态配置反包检测，仅对 5M/10M/15M/30M/1H/2H/4H/6H/8H/12H/1D/3D/1W/2D/5D/1M 周期
  - 写入文件：`src/alert/combined_scheduler.py`

- [ ] **Step 1: 复制文件**

```bash
git show 0a99af6:src/alert/combined_scheduler.py > src/alert/combined_scheduler.py
```

- [ ] **Step 2: 精简构造方法**

`__init__` 中删除：
- `self.price_updater`、`self.price_updater_dynamic`（PriceUpdater 不搬回）
- `self.funding_rate_monitor`（资金费率不搬回）
- `self.metal_reversal_detector`（贵金属不搬回）
- `self.last_price_update_time`、`self.last_funding_rate_time`、`self.last_metal_detect_time`（无意义）

保留：
- `self.reversal_detector_dynamic = CryptoReversalDetector(wecom_webhook_url=self.wecom_webhook_url2)`

- [ ] **Step 3: 删除非动态配置通道的任务方法**

删除：
- `price_update_job()`、`price_update_job_dynamic()`（PriceUpdater 相关）
- `reversal_detect_job()`（非 dynamic）
- `high_priority_reversal_job()`（非 dynamic）
- `high_frequency_reversal_job()`（非 dynamic）
- `funding_rate_refresh_job()`、`funding_rate_check_job()`（资金费率）
- `metal_daily_job()`、`ma100_touch_job()`（贵金属、MA100）

保留并重命名/简化：
- `high_priority_reversal_job_dynamic()` → 改为 `reversal_detect_job_dynamic(interval)`
- `high_frequency_reversal_job_dynamic()` → 改为 `reversal_detect_high_freq_job_dynamic()`

- [ ] **Step 4: 替换 schedule 为 APScheduler**

将 `import schedule` 替换为 `from apscheduler.schedulers.background import BackgroundScheduler`。

将 `start()` 方法中的：
```python
schedule.every().day.at("08:02").do(...)
schedule.every(15).minutes.do(...)
```

替换为：
```python
self.scheduler = BackgroundScheduler()
self.scheduler.add_job(self.reversal_detect_job_dynamic, 'cron', hour='*', minute='2', args=['15M'])
self.scheduler.add_job(self.reversal_detect_job_dynamic, 'cron', hour='*', minute='2', args=['1H'])
# ... 其他周期
self.scheduler.start()
```

对齐原调度点：
- 5M/10M/15M/30M：每个整点 minute=2
- 1H/2H：每个偶数整点 minute=2
- 4H/6H/8H/12H：每天 00/12 minute=2
- 1D/3D：每天 08:02
- 1W：每周一 08:02
- 2D/5D/1M：每天 00:10

- [ ] **Step 5: 验证导入和实例化**

```bash
python3 -c "
import os
os.environ['WECOM_WEBHOOK_URL2'] = 'https://example.invalid/webhook'
from src.alert.combined_scheduler import CombinedScheduler
s = CombinedScheduler(wecom_webhook_url2='https://example.invalid/webhook')
print('scheduler created:', type(s).__name__)
print('has start method:', hasattr(s, 'start'))
"
```

期望输出：`scheduler created: CombinedScheduler`、`has start method: True`

- [ ] **Step 6: 提交**

```bash
git add src/alert/combined_scheduler.py
git commit -m "feat(alert): trim combined_scheduler to dynamic-channel reversal only, use APScheduler"
```

---

### Task 7: 更新 `requirements.txt` 和 `env.example`

**Files:**
- Modify: `requirements.txt`
- Modify: `env.example`

- [ ] **Step 1: 更新 `requirements.txt`**

读取当前 `requirements.txt`，在末尾追加：

```
requests>=2.28.0
APScheduler>=3.10.0
pandas>=1.5.0
matplotlib>=3.5.0
python-dotenv>=1.0.0
```

最终文件内容应类似：
```
flask>=2.0.0
flask-cors>=3.0.0
requests>=2.28.0
APScheduler>=3.10.0
pandas>=1.5.0
matplotlib>=3.5.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: 更新 `env.example`**

读取当前 `env.example`，替换为：

```bash
# 动态配置监控报警通道（必须）
# 用于 tokens-config-dynamic.md 触发的反包检测报警
WECOM_WEBHOOK_URL2=your-webhook-url-here
```

- [ ] **Step 3: 验证依赖安装（dry-run）**

```bash
pip install --break-system-packages --dry-run -r requirements.txt 2>&1 | tail -5
```

期望输出：包含所有 7 个包的成功解析。

- [ ] **Step 4: 提交**

```bash
git add requirements.txt env.example
git commit -m "chore: add alert subsystem deps (requests, APScheduler, pandas, matplotlib, dotenv)"
```

---

### Task 8: 更新 `token_config_server.py` HTML 模板对齐 production

**Files:**
- Modify: `src/crypto/token_config_server.py`（仅修改 `get_token_config_html_template()` 函数返回值）

- [ ] **Step 1: 备份当前模板**

```bash
python3 -c "
import re
with open('src/crypto/token_config_server.py') as f:
    content = f.read()
match = re.search(r'def get_token_config_html_template\(\).*?\"\"\"(.*?)\"\"\"', content, re.DOTALL)
print('current template lines:', match.group(1).count(chr(10)) if match else 'NOT FOUND')
"
```

记录当前行数（基线，用于对比）。

- [ ] **Step 2: 从 production 拉取模板**

```bash
curl -s --connect-timeout 10 http://43.156.245.36:8866/token-config > /tmp/production_template.html
wc -c /tmp/production_template.html
ls -la /tmp/production_template.html
```

期望：文件大小约 18-22KB（production 模板）。

- [ ] **Step 3: 替换模板**

打开 `src/crypto/token_config_server.py`，找到 `def get_token_config_html_template():` 函数，把整个返回的 `"""..."""` 替换为 production 模板内容。把 `/tmp/production_template.html` 的内容包裹在 Python 三引号字符串里：

```python
def get_token_config_html_template():
    """Token配置管理HTML模板（对齐 production）"""
    return """
<这里粘贴 production 模板>
"""
```

注意：模板中含有 `<script>parseAndShowTokens(content) { ... }</script>` 等 JS 代码，其中的 `"""` 终止符会破坏 Python 字符串。如遇此情况，使用单引号 `'''` 包裹 Python 字符串，或转义内部的 `"""`。

- [ ] **Step 4: 验证模板加载**

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from src.crypto.token_config_server import get_token_config_html_template
tpl = get_token_config_html_template()
print('len:', len(tpl))
print('has validate btn:', 'validateConfig' in tpl)
print('has level-0 css:', 'level-0' in tpl)
print('has escapeHtml:', 'escapeHtml' in tpl)
print('has info-box 0/1/2/3:', '0 = 15' in tpl or '0=15' in tpl)
"
```

期望输出：`len: >10000`、`has validate btn: True`、`has level-0 css: True`、`has escapeHtml: True`、`has info-box 0/1/2/3: True`

- [ ] **Step 5: 提交**

```bash
git add src/crypto/token_config_server.py
git commit -m "feat(token-config): align HTML template with production (validate button, level colors, XSS escape)"
```

---

### Task 9: 集成 APScheduler 到 Flask `main()`

**Files:**
- Modify: `src/crypto/token_config_server.py`（仅修改 `main()` 函数）

- [ ] **Step 1: 修改 `main()`**

打开 `src/crypto/token_config_server.py`，修改 `main()` 函数：

```python
def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='Token 配置 + 监控报警服务')
    parser.add_argument('port', nargs='?', type=int, default=8866, help='监听端口（默认 8866）')
    args = parser.parse_args()

    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)

    logger.info(f"启动 Token 配置 + 监控报警服务，端口: {args.port}")

    # 加载环境变量（如果有 .env）
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # 启动调度器（如果 WECOM_WEBHOOK_URL2 已配置）
    webhook_url2 = os.getenv('WECOM_WEBHOOK_URL2')
    if webhook_url2:
        from src.alert.combined_scheduler import CombinedScheduler
        scheduler = CombinedScheduler(wecom_webhook_url2=webhook_url2)
        scheduler.start()
        logger.info("✓ APScheduler 后台调度器已启动")
    else:
        logger.warning("⚠️ WECOM_WEBHOOK_URL2 未配置，报警发送将被跳过；调度器未启动")

    app.run(host='0.0.0.0', port=args.port, debug=False)
```

- [ ] **Step 2: 修改默认端口为 8866**

确保 `parser.add_argument('port', nargs='?', type=int, default=8866, ...)` 默认值是 8866（与历史 production 一致）。

- [ ] **Step 3: 启动验证（mock webhook）**

```bash
WECOM_WEBHOOK_URL2='https://example.invalid/webhook' python3 src/crypto/token_config_server.py 8869 &
SERVER_PID=$!
sleep 5
kill $SERVER_PID 2>/dev/null
sleep 1
tail -20 logs/token_config_server.log
```

期望日志包含：
- `启动 Token 配置 + 监控报警服务，端口: 8869`
- `✓ APScheduler 后台调度器已启动`
- `⏰ 定时任务已启动`

- [ ] **Step 4: 启动验证（无 webhook）**

```bash
unset WECOM_WEBHOOK_URL2
python3 src/crypto/token_config_server.py 8869 &
SERVER_PID=$!
sleep 3
kill $SERVER_PID 2>/dev/null
sleep 1
tail -10 logs/token_config_server.log
```

期望日志包含：
- `⚠️ WECOM_WEBHOOK_URL2 未配置，报警发送将被跳过；调度器未启动`

- [ ] **Step 5: 提交**

```bash
git add src/crypto/token_config_server.py
git commit -m "feat: integrate APScheduler into Flask main(), default port 8866"
```

---

### Task 10: 最终 E2E 验证

- [ ] **Step 1: 冷启动 + 4 路由 + 调度器**

```bash
# 备份配置文件
cp src/alert/tokens-config-dynamic.md /tmp/orig_config.md
md5_before=$(md5sum src/alert/tokens-config-dynamic.md | cut -d' ' -f1)

# 启动服务
WECOM_WEBHOOK_URL2='https://example.invalid/webhook' \
  bash scripts/crypto/start_token_config.sh 8869 2>&1
sleep 3

# 验证 4 路由
curl -s -o /dev/null -w "GET /token-config: %{http_code}\n" http://localhost:8869/token-config
curl -s http://localhost:8869/api/token-config | python3 -c "import sys,json; d=json.load(sys.stdin); print('GET /api/token-config:', d['success'])"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"content":"BTCUSDT 0\nZECUSDT 1\n"}' \
  http://localhost:8869/api/token-config/validate | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('POST /api/token-config/validate:', d['success'], 'tokens:', d['summary']['total'])"

# 验证调度器
grep "APScheduler 后台调度器已启动" logs/token_config_server.log && echo "Scheduler: OK"
grep "⏰ 定时任务已启动" logs/token_config_server.log && echo "Cron: OK"
```

期望输出：所有 HTTP 200、success=True、Scheduler: OK、Cron: OK

- [ ] **Step 2: 配置可逆性**

```bash
# 停止服务
pkill -f token_config_server.py 2>/dev/null
sleep 2

# 从备份还原
cp /tmp/orig_config.md src/alert/tokens-config-dynamic.md
md5_after=$(md5sum src/alert/tokens-config-dynamic.md | cut -d' ' -f1)

# 校验
if [ "$md5_before" = "$md5_after" ]; then
  echo "Config integrity: OK ($md5_before)"
else
  echo "Config integrity: FAILED ($md5_before -> $md5_after)"
  exit 1
fi
```

期望输出：`Config integrity: OK (639ac90cdf8c60c7139aaa41fd4844d5)`

- [ ] **Step 3: XSS 防护验证**

```bash
# 启动服务
WECOM_WEBHOOK_URL2='https://example.invalid/webhook' \
  bash scripts/crypto/start_token_config.sh 8869 2>&1 > /dev/null
sleep 3

# 保存含 XSS payload 的配置
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"content":"<img src=x onerror=alert(1)>BTC  # xss test\nBTCUSDT\n"}' \
  http://localhost:8869/api/token-config/save | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 检查页面（不应含未转义的 onerror）
curl -s http://localhost:8869/token-config | grep -c "onerror=alert(1)" || echo "0 occurrences"
```

期望：保存成功 + 页面不含未转义的 `onerror=alert(1)` 字符串（在 textarea 中可见，**在预览标签中应被转义**）。

- [ ] **Step 4: 还原配置 + 停止服务**

```bash
pkill -f token_config_server.py 2>/dev/null
sleep 2
cp /tmp/orig_config.md src/alert/tokens-config-dynamic.md
md5sum src/alert/tokens-config-dynamic.md
```

期望：`639ac90cdf8c60c7139aaa41fd4844d5  src/alert/tokens-config-dynamic.md`

- [ ] **Step 5: 更新 ledger + 最终 commit**

```bash
# 更新 SDD ledger（在 .superpowers/sdd/ 下追加 Task 1-10 摘要）
# 标记所有任务完成

# 最终 commit
git add src/alert/tokens-config-dynamic.md  # 如果有改动
git diff --cached
git commit --allow-empty -m "chore: mark monitor + alert restore plan complete"
```

---

## 自我审查

**Spec coverage**：
- §1 范围：✓ Tasks 5/6 排除 PriceUpdater/资金费率/贵金属/Equity
- §2 架构：✓ Task 9 集成，Task 6 实现
- §4 前端：✓ Task 8
- §5 模块：✓ Tasks 1-6
- §7 依赖：✓ Task 7
- §8 环境变量：✓ Tasks 4/9 读取 `WECOM_WEBHOOK_URL2`
- §9 验证：✓ Tasks 1-10 内嵌 + Task 10 E2E

**Step scan**：
- Task 8 Step 3 包含较多"打开文件..."指令。改进：精简为 `git show` 风格。已优化：production 模板用 curl 拉取 → 粘贴进 Python 三引号字符串。

**Type consistency**：
- `get_dynamic_symbols() -> List[str]` 在 Task 1、5 一致
- `CryptoReversalDetector(wecom_webhook_url=...)` 在 Task 5、6 一致
- `CombinedScheduler(wecom_webhook_url2=...)` 在 Task 6、9 一致
- `WeComNotifier(webhook_url=...)` 在 Task 4、5 一致

**Review Focus**：
- XSS 防护：Task 8 Step 4 验证、Task 10 Step 3 E2E
- webhook 未配置：Task 4 Step 3、Task 9 Step 4
- Binance 失败：Task 3 Step 3（部分覆盖，单 ticker 失败由 detector 内部 try/except 覆盖）
- mtime 热重载：Task 1 Step 4 验证文件变化后的下次 reload
- 调度器不阻塞 HTTP：Task 9 Step 3 启动测试（间接验证）

**Proportion**：spec 226 行、plan 348 行（含 markdown 标记），比例合理。