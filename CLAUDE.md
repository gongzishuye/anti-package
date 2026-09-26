# CLAUDE.md

项目协作与开发约定文档。

## 启动服务

### Flask Web 服务（推荐方式）

启动入口脚本：`scripts/crypto/start_token_config.sh`，会调用 `src/crypto/token_config_server.py` 并以 `nohup` 后台方式运行。

```bash
# 默认端口（5000）
bash scripts/crypto/start_token_config.sh

# 指定端口（与之前的习惯一致：8866）
bash scripts/crypto/start_token_config.sh 8866
```

参数顺序：
- 第 1 个：端口（默认 `5000`）

### 访问地址

启动成功后会输出访问地址，例如：

```
http://localhost:8866/token-config
http://127.0.0.1:8866/token-config
http://<局域网 IP>:8866/token-config
```

### 服务管理

```bash
# 查看进程 ID
cat logs/token_config_server.pid

# 实时查看日志
tail -f logs/token_config_server.log

# 停止服务
kill $(cat logs/token_config_server.pid)

# 或强制结束
pkill -f token_config_server.py
```

启动脚本已内置"检测到旧进程会自动停止并清理 PID 文件"的逻辑，再次执行 `start_token_config.sh` 等价于重启。

### 功能说明

本服务**仅提供 Token 配置管理**功能：
- Web 页面：`/token-config`
- API 接口：`/api/token-config`、`/api/token-config/save`、`/api/token-config/validate`
- 数据来源：`src/alert/tokens-config-dynamic.md`
- 日志写入 `logs/token_config_server.log`

### 依赖与配置

```bash
# 安装核心依赖
pip3 install flask flask-cors --break-system-packages
```

`requirements.txt` 仅包含 `flask` 和 `flask-cors`。
