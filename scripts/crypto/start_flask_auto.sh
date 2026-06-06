#!/bin/bash

# 多周期Token筛选 - Flask自动化服务启动脚本

set -e

# 切换到项目根目录
cd "$(dirname "$0")/../.."

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================================================================"
echo -e "${BLUE}多周期Token筛选 - Flask自动化服务${NC}"
echo "================================================================================"
echo ""

# 参数配置
PORT=${1:-5000}
TOP_N=${2:-100}
KLINE_RECORDS=${3:-200}

echo -e "${BLUE}配置参数:${NC}"
echo "  端口: $PORT"
echo "  Top N: $TOP_N"
echo "  K线数据: $KLINE_RECORDS条/Token"
echo ""

# 检查依赖
echo -e "${YELLOW}检查Python依赖...${NC}"
if ! python3 -c "import flask, flask_cors, apscheduler" 2>/dev/null; then
    echo -e "${RED}✗ 缺少必要的Python包${NC}"
    echo ""
    echo "请安装依赖:"
    echo "  pip3 install flask flask-cors apscheduler --break-system-packages"
    echo ""
    echo "或者使用requirements.txt:"
    echo "  pip3 install -r requirements.txt --break-system-packages"
    exit 1
fi
echo -e "${GREEN}✓ 所有依赖已安装${NC}"
echo ""

# 创建必要的目录
mkdir -p logs data

# 检查服务是否已在运行
echo -e "${YELLOW}检查服务状态...${NC}"
if pgrep -f "flask_auto_server.py" > /dev/null; then
    echo -e "${YELLOW}⚠ 检测到服务已在运行，正在停止...${NC}"
    pkill -f "flask_auto_server.py" 2>/dev/null
    sleep 2
    echo -e "${GREEN}✓ 已停止旧服务${NC}"
fi

# 清理旧的PID文件
rm -f logs/flask_auto_server.pid 2>/dev/null

echo ""
echo -e "${YELLOW}启动Flask自动化服务...${NC}"
echo ""

# 启动服务（后台运行）
nohup python3 src/crypto/flask_auto_server.py $PORT --top-n $TOP_N --kline $KLINE_RECORDS > logs/flask_auto_server.log 2>&1 &

# 保存PID
SERVER_PID=$!
echo $SERVER_PID > logs/flask_auto_server.pid

# 等待服务启动
sleep 3

# 检查服务是否正常运行
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo ""
    echo "查看日志:"
    echo "  tail -f logs/flask_auto_server.log"
    exit 1
fi

echo "================================================================================"
echo -e "${GREEN}✓ 服务启动成功！${NC}"
echo "================================================================================"
echo ""
echo -e "${BLUE}服务信息:${NC}"
echo "  进程ID: $SERVER_PID"
echo "  端口: $PORT"
echo "  日志文件: logs/flask_auto_server.log"
echo "  PID文件: logs/flask_auto_server.pid"
echo ""
echo -e "${BLUE}访问地址:${NC}"
echo "  http://localhost:$PORT"
echo "  http://127.0.0.1:$PORT"
if command -v ip &> /dev/null; then
    IP=$(ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d'/' -f1)
    if [ -n "$IP" ]; then
        echo "  http://$IP:$PORT"
    fi
fi
echo ""
echo -e "${BLUE}自动化功能:${NC}"
echo "  ⏰ 定时任务: 每天早上 08:00 自动执行"
echo "  📊 数据获取: 自动获取Top$TOP_N币种的K线数据（每个Token $KLINE_RECORDS条）"
echo "  🔍 自动筛选: 筛选符合条件的Token"
echo "  🎯 Web展示: 实时显示最新筛选结果"
echo "  🔄 手动触发: 在Web界面可手动触发更新"
echo ""
echo -e "${BLUE}使用说明:${NC}"
echo "  默认启动: bash scripts/start_flask_auto.sh"
echo "  指定端口: bash scripts/start_flask_auto.sh 8080"
echo "  指定TopN: bash scripts/start_flask_auto.sh 5000 50  # Top50"
echo "  指定K线: bash scripts/start_flask_auto.sh 5000 100 300  # Top100, 300条K线"
echo ""
echo -e "${BLUE}常用命令:${NC}"
echo "  查看日志: tail -f logs/flask_auto_server.log"
echo "  停止服务: kill \$(cat logs/flask_auto_server.pid)"
echo "  或使用: pkill -f flask_auto_server.py"
echo ""
echo "================================================================================"
echo ""

