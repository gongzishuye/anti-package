#!/bin/bash
# 设置贵金属每日数据获取和反包检测的定时任务（已废弃）
# 推荐使用 combined_scheduler.py 进行调度，而不是crontab
# 每天8点02分执行

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SCRIPT_PATH="$SCRIPT_DIR/daily_fetch_metal_and_detect.py"

# 检查虚拟环境是否存在
if [ ! -f "$VENV_PYTHON" ]; then
    echo "错误: 虚拟环境不存在，请先创建虚拟环境"
    echo "路径: $VENV_PYTHON"
    exit 1
fi

# 检查脚本是否存在
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "错误: 脚本不存在"
    echo "路径: $SCRIPT_PATH"
    exit 1
fi

# 获取当前用户的crontab
CRON_TEMP=$(mktemp)
crontab -l > "$CRON_TEMP" 2>/dev/null || true

# 检查是否已存在相同的定时任务
if grep -q "daily_fetch_metal_and_detect.py" "$CRON_TEMP"; then
    echo "警告: 定时任务已存在，将删除旧任务后添加新任务"
    # 删除旧任务
    grep -v "daily_fetch_metal_and_detect.py" "$CRON_TEMP" > "${CRON_TEMP}.new"
    mv "${CRON_TEMP}.new" "$CRON_TEMP"
fi

# 添加新任务（每天8点02分执行）
echo "# Metal daily fetch and reversal detection - 每天8点02分执行" >> "$CRON_TEMP"
echo "2 8 * * * cd $PROJECT_DIR && $VENV_PYTHON $SCRIPT_PATH >> $PROJECT_DIR/logs/metal_daily_fetch_cron.log 2>&1" >> "$CRON_TEMP"

# 安装新的crontab
crontab "$CRON_TEMP"
rm "$CRON_TEMP"

echo "✓ 定时任务已设置"
echo "  执行时间: 每天 08:02"
echo "  脚本路径: $SCRIPT_PATH"
echo ""
echo "查看定时任务: crontab -l"
echo "查看日志: tail -f $PROJECT_DIR/logs/metal_daily_fetch_cron.log"
