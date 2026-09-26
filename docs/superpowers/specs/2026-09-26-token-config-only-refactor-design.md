# 设计文档：/token-config 页面独立重构

**日期**：2026-09-26
**作者**：Claude（基于与用户的头脑风暴）
**状态**：草稿，待用户审阅

## 1. 目标与背景

### 1.1 背景
当前 `anti-package` 项目功能复杂，包含多个子系统（crypto 数据筛选、alert 告警、metal 反包检测、equity 股票、futu 富途、database 持久化等）。`flask_auto_server.py` 是一个 5536 行的大文件，承载 4 个 HTML 页面 + 20+ 个 API 端点。

### 1.2 目标
从现有项目中**剥离出**仅包含 `/token-config` 页面功能的最小子集到一个新分支，使该分支可以独立运行、易于维护，同时保证 `/token-config` 功能与 main 分支完全一致。

### 1.3 非目标
- 不修改 `/token-config` 的任何功能行为（HTML、API、校验逻辑、文件格式）
- 不为 `/token-config` 增加新功能
- 不重写或美化 UI
- 不合并/拆分 markdown 配置文件的格式
- 不影响 main 分支

## 2. 新分支结构

### 2.1 目录布局（删除线 = 删除）

```
anti-package/
├── src/
│   ├── crypto/
│   │   └── token_config_server.py     ← 新建（唯一 Python 入口）
│   │   └── flask_auto_server.py       ← 删除（被新文件取代）
│   │   └── fetch_multi_period_data.py ← 删除
│   │   └── token_filter_multi_period.py ← 删除
│   │   └── 其他 .py / .sh / 日志     ← 删除
│   └── alert/
│       └── tokens-config-dynamic.md   ← 保留（数据文件）
│       └── tokens-config.md           ← 删除（仅保留 dynamic 版本）
│       └── combined_scheduler.py      ← 删除
│       └── crypto_reversal_detector.py ← 删除
│       └── monitor_config.py          ← 删除
│       └── price_updater.py           ← 删除
│   └── database/                      ← 删除整个目录
│   └── metal/                         ← 删除整个目录
│   └── equity/                        ← 删除整个目录
│   └── futu/                          ← 删除整个目录
│   └── data/                          ← 删除整个目录
├── scripts/crypto/
│   └── start_token_config.sh         ← 新建（从 start_flask_auto.sh 改造）
│   └── 其他脚本                       ← 删除全部
├── logs/                             ← 保留（运行时日志输出）
├── data/                             ← 删除或保留为空目录（运行时无数据写入）
├── requirements.txt                  ← 精简为 flask + flask-cors
├── CLAUDE.md                         ← 更新
├── env.example                       ← 简化（删除 webhook 等已无用变量）
└── docs/                             ← 保留（文档目录）
```

### 2.2 新文件：`src/crypto/token_config_server.py`

**规模**：约 750 行（原 5536 行，缩减 86%）

**结构**：
```python
#!/usr/bin/env python3
"""Token 配置管理 Flask 服务"""

# 1. 依赖（仅 4 个）
#    flask, flask-cors, datetime, os/sys/logging/argparse
#
# 2. 日志配置（保留原有格式）
#
# 3. Flask 应用初始化
#    app = Flask(__name__)
#    CORS(app)
#
# 4. 配置常量
#    CONFIG_FILE = src/alert/tokens-config-dynamic.md
#
# 5. 4 个路由（原样复制）
#    GET  /token-config                 → 渲染 HTML 模板
#    GET  /api/token-config              → 读取配置 JSON
#    POST /api/token-config/save         → 保存配置 JSON
#    POST /api/token-config/validate     → 校验配置 JSON
#
# 6. HTML 模板函数 get_token_config_html_template()
#    从原文件 line 1521-2085 原样复制
#
# 7. main() + CLI 入口
#    python3 token_config_server.py [port]
#    默认端口 5000
```

**CLI 参数**：仅 `port`（位置参数），删除原 `--top-n` 和 `--kline`（这两个参数原本用于自动调度任务，已删除）。

## 3. 一致性保证策略

### 3.1 三层一致性保证

| 层次 | 内容 | 保证方式 |
|------|------|----------|
| 代码层 | HTML 模板、API 处理器、校验逻辑 | 从原文件 `flask_auto_server.py` 第 1317-2085 行 1:1 复制，不做任何改动 |
| 接口层 | API 响应 schema（字段名、类型、含义） | 4 个 API 的入参/出参字段完全不变 |
| 数据层 | 配置文件路径、文件格式 | 路径 `src/alert/tokens-config-dynamic.md` 不变；markdown 格式不变 |

### 3.2 关键不变量

- ✅ 4 个路由 URL 路径不变：`/token-config`、`/api/token-config`、`/api/token-config/save`、`/api/token-config/validate`
- ✅ HTTP 方法不变：页面 = GET，读取 = GET，保存 = POST，校验 = POST
- ✅ JSON 响应字段名/类型/嵌套结构不变
- ✅ 校验规则的所有分支判断不变（包括级别验证、重复检查、注释处理、行号统计等）
- ✅ 文件读写编码：`utf-8`
- ✅ 日志格式：`(asctime) - (name) - (levelname) - (message)`

### 3.3 验证手段（手动）

实施时按以下步骤验证：

1. **HTML diff**：在 main 分支导出模板字符串，与新分支导出版本做字符串 diff，期望完全一致
2. **API 响应 diff**：
   ```bash
   # main 分支（先启动 8866 端口的旧服务）
   curl http://localhost:8866/api/token-config > /tmp/main_get.json
   curl -X POST http://localhost:8866/api/token-config/validate \
     -d '{"content":"BTCUSDT 0"}' > /tmp/main_validate.json

   # 新分支
   curl http://localhost:8866/api/token-config > /tmp/new_get.json
   curl -X POST http://localhost:8866/api/token-config/validate \
     -d '{"content":"BTCUSDT 0"}' > /tmp/new_validate.json

   diff /tmp/main_get.json /tmp/new_get.json       # 应无输出
   diff /tmp/main_validate.json /tmp/new_validate.json  # 应无输出
   ```
3. **端到端流程**：编辑 → 保存 → 重启服务 → 读取 → 验证，配置内容保留
4. **校验规则边界测试**：构造含错误级别、重复 symbol、行内注释等情况的输入，对比 validate 返回

## 4. 实施步骤

按顺序执行，每步独立可回滚：

| # | 步骤 | 说明 |
|---|------|------|
| 1 | 创建新分支 | `git checkout -b refactor/token-config-only` |
| 2 | 新建 `src/crypto/token_config_server.py` | 从 main 分支原文件复制相关代码段（line 1317-2085 + 必要 boilerplate） |
| 3 | 本地启动验证 | `python3 src/crypto/token_config_server.py 8866`，浏览器访问 `/token-config` 验证页面正常 |
| 4 | API 验证 | curl 4 个 endpoint，对比与 main 的响应（见 3.3） |
| 5 | 新建 `scripts/crypto/start_token_config.sh` | 基于 `start_flask_auto.sh` 改造，去掉 top_n/kline 相关逻辑 |
| 6 | 精简 `requirements.txt` | 仅保留 `flask` 与 `flask-cors` |
| 7 | 更新 `CLAUDE.md` | 反映新分支结构、新的启动命令 |
| 8 | 更新 `env.example` | 删除已不存在的 `BINANCE_API_KEY` 等运行时不再需要的变量（保留以备将来扩展） |
| 9 | 删除多余文件 | 按 2.1 节删除线标识的全部目录和文件 |
| 10 | 最终完整验证 | 从干净状态重启服务，所有功能正常 |
| 11 | 提交 | `git commit -m "refactor: extract /token-config to standalone server"` |

## 5. 风险与回滚

### 5.1 风险点

| 风险 | 影响 | 缓解 |
|------|------|------|
| 删除文件时误删 `tokens-config-dynamic.md` | 数据丢失 | 删除前 `ls -la src/alert/` 二次确认；建议先 `cp` 备份到 `/tmp/` |
| 复制代码时遗漏/改动某行 | 一致性破坏 | 复制后做 line-by-line diff；用 `wc -l` 对比前后行数 |
| 新服务启动失败 | 无法验证 | 步骤 3 单独验证，失败则在 commit 前修复 |
| 端口冲突 | 无法启动 | 启动脚本默认端口仍是 5000，可通过参数指定 |

### 5.2 回滚策略

- 新分支隔离工作，main 分支不受影响
- 任何步骤发现问题都可 `git reset --hard HEAD~N` 回退到上一步
- 若新分支整体失败：`git checkout main` 切回，不影响主线

## 6. 依赖

### 6.1 新增依赖
无（仅复用 main 分支已有的 flask/flask-cors）。

### 6.2 删除依赖
- `pandas`、`apscheduler`、`python-dotenv`（不再使用）
- `src/database/db_manager`、`src/crypto/fetch_multi_period_data`、`src/crypto/token_filter_multi_period` 等内部模块

### 6.3 requirements.txt 最终内容（草案）
```
flask>=2.0.0
flask-cors>=3.0.0
```

## 7. 后续工作（不在本次范围）

- 重构后的服务可考虑容器化（Docker）
- 配置文件的版本控制（git 跟踪）
- 多用户权限管理
- 配置文件的历史记录/回滚功能

---

**待用户审阅**