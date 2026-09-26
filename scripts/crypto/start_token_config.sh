#!/bin/bash
# Token 配置管理服务启动脚本

PORT="${1:-5000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/token_config_server.log"
PID_FILE="$PROJECT_ROOT/logs/token_config_server.pid"

mkdir -p "$PROJECT_ROOT/logs"

# 清理旧进程
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "停止旧进程 (PID=$OLD_PID)"
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PID_FILE"
fi
pkill -f token_config_server.py 2>/dev/null
sleep 1

cd "$PROJECT_ROOT"
nohup python3 src/crypto/token_config_server.py "$PORT" >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

sleep 2
if ps -p "$NEW_PID" > /dev/null 2>&1; then
    echo "Token 配置服务已启动"
    echo "  PID:  $NEW_PID"
    echo "  端口: $PORT"
    echo "  访问: http://localhost:$PORT/token-config"
    echo "  日志: $LOG_FILE"
else
    echo "启动失败，请查看日志: $LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi
