#!/bin/bash
# 设置crontab定时任务
# 每天早上8:30自动执行数据同步

echo "========================================================================"
echo "设置每日自动同步定时任务"
echo "========================================================================"
echo ""

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 定义crontab任务
CRON_JOB="30 8 * * * cd $SCRIPT_DIR && $SCRIPT_DIR/start_daily_sync.sh >> $SCRIPT_DIR/logs/cron.log 2>&1"

echo "将要添加的crontab任务:"
echo "$CRON_JOB"
echo ""

# 检查是否已经存在
if crontab -l 2>/dev/null | grep -q "start_daily_sync.sh"; then
    echo "⚠️  检测到已存在的同步任务"
    echo ""
    echo "当前的crontab任务:"
    crontab -l | grep "start_daily_sync.sh"
    echo ""
    read -p "是否要替换现有任务? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消操作"
        exit 0
    fi
    
    # 删除旧任务
    crontab -l | grep -v "start_daily_sync.sh" | crontab -
    echo "✅ 已删除旧任务"
fi

# 添加新任务
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo ""
echo "✅ Crontab任务已设置成功!"
echo ""
echo "任务信息:"
echo "  - 执行时间: 每天早上 8:30"
echo "  - 执行脚本: $SCRIPT_DIR/start_daily_sync.sh"
echo "  - 日志文件: $SCRIPT_DIR/logs/cron.log"
echo ""
echo "查看crontab:"
echo "  crontab -l"
echo ""
echo "查看日志:"
echo "  tail -f $SCRIPT_DIR/logs/cron.log"
echo ""
echo "删除任务:"
echo "  crontab -e  (然后删除对应行)"
echo ""
echo "========================================================================"

