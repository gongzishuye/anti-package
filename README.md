# anti-package

轻量级 Token 配置管理服务。提供 Web 页面在线编辑监控交易对配置，并通过 REST API 支持读取、保存、校验。

## 项目结构

```
anti-package/
├── src/
│   ├── token_config_server.py     # Flask 服务入口（4 个路由）
│   └── alert/
│       └── tokens-config-dynamic.md   # 配置数据源（监控交易对列表）
├── scripts/
│   └── crypto/
│       └── start_token_config.sh      # 启动脚本（端口可配）
├── docs/
│   └── superpowers/
│       ├── specs/...                  # 重构设计文档
│       └── plans/...                  # 重构实施计划
├── logs/
│   └── token_config_server.log        # 运行日志
├── CLAUDE.md                          # Claude Code 协作约定
├── env.example
├── requirements.txt                   # 仅 flask + flask-cors
└── .gitignore
```

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
# 或：pip3 install flask flask-cors
```

### 2. 启动服务

```bash
# 默认端口 5000
bash scripts/crypto/start_token_config.sh

# 自定义端口（与历史习惯一致：8866）
bash scripts/crypto/start_token_config.sh 8866
```

### 3. 访问页面

启动成功后浏览器打开：

```
http://localhost:8866/token-config
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/token-config` | Web 管理页面 |
| GET  | `/api/token-config` | 读取当前配置（JSON） |
| POST | `/api/token-config/save` | 保存配置，Body 为 Markdown 内容 |
| POST | `/api/token-config/validate` | 校验配置内容，返回解析结果 |

## 配置格式

`src/alert/tokens-config-dynamic.md` 是 Markdown 文件，每行一个交易对，支持 `#` 注释：

```markdown
# 监控交易对配置
BTCUSDT  # 比特币
ETHUSDT
SOLUSDT
```

Web 页面的保存操作会原子写入该文件（先写临时文件再 rename，避免半写状态）。

## 服务管理

```bash
# 查看 PID
cat logs/token_config_server.pid

# 实时日志
tail -f logs/token_config_server.log

# 停止
kill $(cat logs/token_config_server.pid)
# 或
pkill -f token_config_server.py
```

启动脚本会先清理同名旧进程，再启动新进程——再次运行等价于重启。

## 变更记录

本项目从大型反包检测系统中剥离而来，仅保留 Token 配置管理功能。重构背景、方案与验收细节见：

- 设计文档：[`docs/superpowers/specs/2026-09-26-token-config-only-refactor-design.md`](docs/superpowers/specs/2026-09-26-token-config-only-refactor-design.md)
- 实施计划：[`docs/superpowers/plans/2026-09-26-token-config-only-refactor.md`](docs/superpowers/plans/2026-09-26-token-config-only-refactor.md)
- 协作约定：[`CLAUDE.md`](CLAUDE.md)