#!/bin/bash
# 设置每日港股数据获取和反包检测的定时任务
# 每天早晨8点执行

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/daily_fetch_hk_and_detect.py"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

# 检查虚拟环境是否存在
if [ ! -f "$VENV_PYTHON" ]; then
    echo "错误: 虚拟环境不存在，请先创建虚拟环境"
    exit 1
fi

# 检查脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "错误: 脚本不存在: $PYTHON_SCRIPT"
    exit 1
fi

# 创建日志目录
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 构建cron任务
CRON_TIME="0 8 * * *"  # 每天8点
CRON_CMD="$VENV_PYTHON $PYTHON_SCRIPT >> $LOG_DIR/equity_hk_daily_cron.log 2>&1"
CRON_JOB="$CRON_TIME $CRON_CMD"

# 检查cron任务是否已存在
CRON_COMMENT="# HK Equity daily fetch and reversal detection"
if crontab -l 2>/dev/null | grep -q "$CRON_COMMENT"; then
    echo "定时任务已存在，正在更新..."
    # 删除旧任务
    crontab -l 2>/dev/null | grep -v "$CRON_COMMENT" | grep -v "$PYTHON_SCRIPT" | crontab -
fi

# 添加新任务
(crontab -l 2>/dev/null; echo "$CRON_COMMENT"; echo "$CRON_JOB") | crontab -

echo "✓ 港股定时任务设置成功"
echo ""
echo "任务详情:"
echo "  时间: 每天 08:00"
echo "  脚本: $PYTHON_SCRIPT"
echo "  Python: $VENV_PYTHON"
echo "  日志: $LOG_DIR/equity_hk_daily_fetch.log"
echo ""
echo "查看当前cron任务:"
echo "  crontab -l"
echo ""
echo "删除此任务:"
echo "  crontab -l | grep -v '$CRON_COMMENT' | grep -v '$PYTHON_SCRIPT' | crontab -"

