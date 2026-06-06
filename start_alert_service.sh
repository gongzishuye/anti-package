#!/bin/bash
###############################################################################
# 反包监控报警服务 - 统一启动脚本
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

echo -e "${BLUE}=========================================================================="
echo "🚀 反包监控报警服务启动"
echo -e "==========================================================================${NC}"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python: $(python3 --version)"

# 检查依赖
echo ""
echo "检查依赖包..."
REQUIRED_PACKAGES=("pandas" "openpyxl" "schedule" "requests" "python-dotenv")
MISSING=0

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $package"
    else
        echo -e "  ${RED}✗${NC} $package (缺失)"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}正在安装缺失的包...${NC}"
    pip3 install pandas openpyxl schedule requests python-dotenv
fi

# 检查配置文件
echo ""
echo "检查配置文件..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env 文件存在"
    
    # 检查webhook配置
    if grep -q "WECOM_WEBHOOK_URL=" .env && ! grep -q "your-key-here" .env; then
        echo -e "${GREEN}✓${NC} 企业微信Webhook已配置"
    else
        echo -e "${YELLOW}⚠${NC} 企业微信Webhook未配置或使用示例值"
        echo "  提示: 编辑 .env 文件配置 WECOM_WEBHOOK_URL"
    fi
else
    echo -e "${YELLOW}⚠${NC} .env 文件不存在"
    if [ -f "env.example" ]; then
        echo "  提示: 运行 'cp env.example .env' 创建配置文件"
    fi
fi

# 创建日志目录
mkdir -p logs
echo -e "${GREEN}✓${NC} 日志目录: logs/"

# 显示服务配置
echo ""
echo -e "${BLUE}=========================================================================="
echo "📋 服务配置"
echo -e "==========================================================================${NC}"
echo ""
echo "定时任务1: Excel数据同步"
echo "  - 执行时间: 每天早上 08:30"
echo "  - 功能: 从Excel读取筛选结果并导入数据库"
echo "  - 数据源: data/qualified_tokens_multi_period_*.xlsx"
echo ""
echo "定时任务2: 价格监控和报警"
echo "  - 执行间隔: 每 15 分钟"
echo "  - 功能: "
echo "    1. 清理过期数据（date + interval×4 < 今天）"
echo "    2. 获取最新价格"
echo "    3. 检测斐波那契回撤（50%, 61.8%, 78.6%, 88.6%）"
echo "    4. 触发企业微信报警"
echo ""

# 询问启动选项
echo -e "${BLUE}=========================================================================="
echo "🎬 启动选项"
echo -e "==========================================================================${NC}"
echo ""
echo "1. 前台运行（可看到实时日志）"
echo "2. 后台运行（日志输出到文件）"
echo "3. 立即执行一次测试"
echo "4. 退出"
echo ""

read -p "请选择 [1-4]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}启动前台服务...${NC}"
        echo "按 Ctrl+C 停止服务"
        echo ""
        sleep 2
        python3 src/alert/combined_scheduler.py --run-all-now
        ;;
    
    2)
        echo ""
        echo -e "${GREEN}启动后台服务...${NC}"
        
        # 检查是否已运行
        if pgrep -f "combined_scheduler.py" > /dev/null; then
            echo -e "${YELLOW}⚠ 服务可能已在运行${NC}"
            echo ""
            ps aux | grep "[c]ombined_scheduler.py"
            echo ""
            read -p "是否停止现有服务并重启? (y/n): " restart
            
            if [ "$restart" = "y" ]; then
                pkill -f "combined_scheduler.py"
                echo "已停止现有服务"
                sleep 2
            else
                exit 0
            fi
        fi
        
        # 后台启动
        nohup python3 src/alert/combined_scheduler.py --run-all-now \
            > logs/alert_service.log 2>&1 &
        
        SERVICE_PID=$!
        echo ""
        echo -e "${GREEN}✓ 服务已启动（后台运行）${NC}"
        echo "  进程ID: $SERVICE_PID"
        echo "  日志文件: logs/alert_service.log"
        echo ""
        echo "查看日志: tail -f logs/alert_service.log"
        echo "停止服务: pkill -f combined_scheduler.py"
        echo ""
        
        # 等待服务启动
        sleep 3
        
        # 检查服务状态
        if ps -p $SERVICE_PID > /dev/null; then
            echo -e "${GREEN}✓ 服务运行正常${NC}"
            
            # 显示最新日志
            echo ""
            echo "最新日志:"
            echo "----------------------------------------"
            tail -20 logs/alert_service.log
        else
            echo -e "${RED}✗ 服务启动失败${NC}"
            echo "查看错误日志: cat logs/alert_service.log"
        fi
        ;;
    
    3)
        echo ""
        echo -e "${GREEN}执行一次性测试...${NC}"
        echo ""
        
        echo "1️⃣  测试Excel数据同步..."
        python3 src/alert/excel_to_db_sync.py
        
        echo ""
        echo "2️⃣  测试价格更新和报警..."
        python3 src/alert/price_updater.py --once
        
        echo ""
        echo -e "${GREEN}✓ 测试完成${NC}"
        ;;
    
    4)
        echo ""
        echo "退出"
        exit 0
        ;;
    
    *)
        echo ""
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}=========================================================================="
echo "✅ 完成"
echo -e "==========================================================================${NC}"
echo ""

