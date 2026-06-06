#!/bin/bash
# 启动综合调度器 (Excel同步 + 价格更新)

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 创建日志目录
mkdir -p logs

# 启动综合调度器
echo "启动综合调度器..."
echo "  - Excel同步: 每天8:30"
echo "  - 价格更新: 每15分钟"
echo ""
echo "日志文件: logs/combined_scheduler.log"
echo "按 Ctrl+C 停止"
echo ""

# 运行综合调度器，并启动时立即执行所有任务
python3 src/alert/combined_scheduler.py --run-all-now

