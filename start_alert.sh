#!/bin/bash
###############################################################################
# Alert服务管理脚本 - 快速启动/停止/状态查看
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 显示使用说明
show_help() {
    echo -e "${BLUE}=========================================================================="
    echo "🚀 Alert服务管理脚本"
    echo -e "==========================================================================${NC}"
    echo ""
    echo "用法: ./start_alert.sh [command]"
    echo ""
    echo "命令:"
    echo "  start      启动服务（后台运行，立即执行一次）"
    echo "  stop       停止服务"
    echo "  restart    重启服务"
    echo "  status     查看服务状态"
    echo "  logs       查看实时日志"
    echo "  test       执行一次测试（不启动服务）"
    echo "  help       显示帮助信息"
    echo ""
    echo -e "${BLUE}==========================================================================${NC}"
}

# 启动服务
start_service() {
    echo -e "${BLUE}=========================================================================="
    echo "🚀 启动Alert服务"
    echo -e "==========================================================================${NC}"
    echo ""
    
    # 检查是否已运行
    if pgrep -f "combined_scheduler.py" > /dev/null; then
        echo -e "${YELLOW}⚠️  服务已在运行中${NC}"
        echo ""
        read -p "是否重启服务? (y/n): " restart
        if [ "$restart" != "y" ]; then
            echo "操作取消"
            exit 0
        fi
        echo ""
        echo "停止现有服务..."
        pkill -f "combined_scheduler.py"
        sleep 2
    fi
    
    echo -e "${GREEN}配置信息:${NC}"
    echo "  • Excel同步: 每天早上 08:30"
    echo "  • 价格监控: 每 15 分钟"
    echo "  • 过期清理: 每次价格更新前"
    echo "  • 斐波那契回撤: 50%, 61.8%, 78.6%, 88.6%"
    echo ""
    echo "  🎯 反包检测:"
    echo "    - 2H: 每2小时 (00:00, 02:00, 04:00, ...)"
    echo "    - 4H: 每4小时 (00:00, 04:00, 08:00, ...)"
    echo "    - 8H: 每8小时 (00:00, 08:00, 16:00)"
    echo "    - 12H: 每12小时 (00:00, 12:00)"
    echo "    - 1D: 每天 08:00"
    echo ""
    echo "  ⚡ 高频反包监控 (1D/3D/周线/月线):"
    echo "    - 每天 00:10 (UTC+8) 执行"
    echo "    - 使用UTC+8时区K线数据"
    echo "    - 检测周期: 1D, 3D, 1W, 1M"
    echo ""
    echo "  🥇 贵金属监控:"
    echo "    - 每天 08:02 执行"
    echo "    - 监控标的: XAU (黄金), XAG (白银)"
    echo "    - 检测T-1和T-2反包形态"
    echo ""
    echo "  🥈 贵金属 1H K线监控:"
    echo "    - 每个整点后第二分钟执行 (00:02, 01:02, ..., 23:02)"
    echo "    - 监控标的: XAGUSDT (合约), XAUUSDT (合约)"
    echo "    - 检测内容: 反包形态 + MA52跌破 + EMA144跌破"
    echo "    - K线数量: 150根（一次获取，用于所有检测）"
    echo "    - 报警目标: Core2企业微信群"
    echo ""
    echo "  🥈 贵金属 2H K线监控:"
    echo "    - 每2小时后的第二分钟执行 (02:02, 04:02, ..., 24:02)"
    echo "    - 监控标的: XAGUSDT (合约), XAUUSDT (合约)"
    echo "    - 检测内容: 反包形态 + MA52跌破 + EMA144跌破"
    echo "    - K线数量: 150根（一次获取，用于所有检测）"
    echo "    - 报警目标: Core2企业微信群"
    echo ""
    
    # 创建日志目录
    mkdir -p logs
    echo -e "${BLUE}启动服务...${NC}"
    
    # 启动服务
    nohup python3 src/alert/combined_scheduler.py \
        > logs/alert_service.log 2>&1 &
    
    SERVICE_PID=$!
    echo $SERVICE_PID > logs/alert_service.pid
    
    echo ""
    echo -e "${GREEN}✅ 服务已启动${NC}"
    echo "  进程ID: $SERVICE_PID"
    echo "  PID文件: logs/alert_service.pid"
    echo "  日志文件: logs/alert_service.log"
    echo ""
    
    # 等待服务启动
    sleep 3
    
    # 检查服务状态
    if ps -p $SERVICE_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 服务运行正常${NC}"
        echo ""
        echo "管理命令:"
        echo "  查看状态: ./start_alert.sh status"
        echo "  查看日志: ./start_alert.sh logs"
        echo "  停止服务: ./start_alert.sh stop"
        echo ""
    else
        echo -e "${RED}✗ 服务启动失败${NC}"
        echo ""
        echo "查看错误日志:"
        echo "  tail -n 50 logs/alert_service.log"
        echo ""
    fi
}

# 停止服务
stop_service() {
    echo -e "${BLUE}=========================================================================="
    echo "🛑 停止Alert服务"
    echo -e "==========================================================================${NC}"
    echo ""
    
    if ! pgrep -f "combined_scheduler.py" > /dev/null; then
        echo -e "${YELLOW}⚠️  服务未运行${NC}"
        exit 0
    fi
    
    echo "正在停止服务..."
    pkill -f "combined_scheduler.py"
    
    # 等待进程结束
    sleep 2
    
    if ! pgrep -f "combined_scheduler.py" > /dev/null; then
        echo -e "${GREEN}✅ 服务已停止${NC}"
        
        # 删除PID文件
        if [ -f "logs/alert_service.pid" ]; then
            rm -f logs/alert_service.pid
        fi
    else
        echo -e "${YELLOW}进程未响应，强制停止...${NC}"
        pkill -9 -f "combined_scheduler.py"
        sleep 1
        echo -e "${GREEN}✅ 服务已强制停止${NC}"
    fi
    
    echo ""
}

# 重启服务
restart_service() {
    echo -e "${BLUE}=========================================================================="
    echo "🔄 重启Alert服务"
    echo -e "==========================================================================${NC}"
    echo ""
    
    stop_service
    sleep 2
    start_service
}

# 查看状态
status_service() {
    echo -e "${BLUE}=========================================================================="
    echo "📊 Alert服务状态"
    echo -e "==========================================================================${NC}"
    echo ""
    
    if pgrep -f "combined_scheduler.py" > /dev/null; then
        PID=$(pgrep -f "combined_scheduler.py")
        echo -e "状态: ${GREEN}🟢 运行中${NC}"
        echo "进程ID: $PID"
        
        # 获取进程信息
        if command -v ps &> /dev/null; then
            echo ""
            echo "进程信息:"
            ps aux | grep "[c]ombined_scheduler.py"
        fi
        
        echo ""
        echo "最近日志 (最后10行):"
        echo "----------------------------------------"
        if [ -f "logs/alert_service.log" ]; then
            tail -10 logs/alert_service.log
        else
            echo "日志文件不存在"
        fi
    else
        echo -e "状态: ${RED}🔴 未运行${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}==========================================================================${NC}"
}

# 查看实时日志
view_logs() {
    echo -e "${BLUE}=========================================================================="
    echo "📋 实时日志"
    echo -e "==========================================================================${NC}"
    echo ""
    echo "按 Ctrl+C 退出"
    echo ""
    
    if [ -f "logs/alert_service.log" ]; then
        tail -f logs/alert_service.log
    else
        echo -e "${YELLOW}⚠️  日志文件不存在${NC}"
        echo "服务可能未运行，尝试先启动: ./start_alert.sh start"
    fi
}

# 执行一次测试
test_service() {
    echo -e "${BLUE}=========================================================================="
    echo "🧪 Alert服务测试"
    echo -e "==========================================================================${NC}"
    echo ""
    
    echo "1️⃣  测试Excel数据同步..."
    python3 src/alert/excel_to_db_sync.py --exchange bn_futures
    
    echo ""
    echo "2️⃣  测试价格更新..."
    python3 src/alert/price_updater.py --once
    
    echo ""
    echo "3️⃣  测试反包检测..."
    python3 src/alert/crypto_reversal_detector.py
    
    echo ""
    echo "4️⃣  测试贵金属 1H监控 (XAGUSDT + XAUUSDT)..."
    python3 src/alert/combined_scheduler.py --run-xag-now --xag-only
    
    echo ""
    echo -e "${GREEN}✅ 测试完成${NC}"
    echo ""
}

# 主逻辑
case "${1:-help}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    test)
        test_service
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}未知命令: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

