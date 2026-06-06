#!/bin/bash

# 项目根目录快捷命令脚本
# 用法: ./run.sh [命令]

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助
show_help() {
    echo "================================================================"
    echo "币安Token分析系统 - 快捷命令"
    echo "================================================================"
    echo ""
    echo "数据获取:"
    echo "  fetch [N]       获取多周期K线数据 (1日、3日、周)，默认Top100"
    echo "                  示例: ./run.sh fetch 50  # Top50"
    echo "  fetch-single    获取单周期(1日)K线数据"
    echo ""
    echo "OKX数据获取:"
    echo "  okx-fetch [N]   获取OKX多周期K线数据 (1日、2日、3日、5日、周)，默认Top100"
    echo "                  示例: ./run.sh okx-fetch 50  # Top50"
    echo ""
    echo "数据筛选:"
    echo "  filter          筛选多周期Token"
    echo "  filter-single   筛选单周期Token"
    echo "  okx-filter      筛选OKX多周期Token"
    echo ""
    echo "Web服务:"
    echo "  web-auto [PORT] [TOP_N] [KLINE] 启动三市场自动化Flask服务"
    echo "                    PORT: 端口号，默认5000"
    echo "                    TOP_N: TopN代币，默认100"
    echo "                    KLINE: 每个Token的K线数据条数，默认200"
    echo "                  示例: ./run.sh web-auto 8866 200 30  # 端口8866，Top200，30条K线"
    echo "  web-stop        停止所有Web服务"
    echo "  web-status      查看Web服务状态"
    echo ""
    echo "数据管理:"
    echo "  list-data       列出所有数据文件"
    echo "  latest-data     显示最新数据文件"
    echo "  clean-data      清理旧数据文件（保留最新3个）"
    echo ""
    echo "富途API:"
    echo "  futu-check      检查FutuOpenD连接"
    echo "  futu-start      启动FutuOpenD"
    echo "  futu-fetch      获取美股数据"
    echo ""
    echo "Alert服务:"
    echo "  alert-start     启动Alert服务（价格监控+反包检测）"
    echo "  alert-stop      停止Alert服务"
    echo "  alert-restart   重启Alert服务"
    echo "  alert-status    查看Alert服务状态"
    echo "  alert-logs      查看Alert服务实时日志"
    echo "  alert-test      执行一次Alert测试"
    echo ""
    echo "文档:"
    echo "  docs            列出所有文档"
    echo "  readme          查看主文档"
    echo "  structure       查看项目结构"
    echo ""
    echo "工具:"
    echo "  setup           初始化项目环境"
    echo "  install-deps    安装Python依赖"
    echo "  test            运行测试"
    echo "  clean           清理临时文件"
    echo ""
    echo "帮助:"
    echo "  help            显示此帮助信息"
    echo ""
    echo "================================================================"
}

# 数据获取
cmd_fetch() {
    local top_n=${1:-100}
    echo -e "${GREEN}获取Top${top_n}多周期K线数据...${NC}"
    bash scripts/crypto/fetch_multi_period.sh $top_n
}

cmd_fetch_single() {
    echo -e "${GREEN}获取单周期K线数据...${NC}"
    cd "$PROJECT_ROOT" && python3 src/crypto/binance_data_fetcher.py
}

# 数据筛选
cmd_filter() {
    echo -e "${GREEN}筛选多周期Token...${NC}"
    bash scripts/crypto/filter_multi_period.sh
}

cmd_filter_single() {
    echo -e "${GREEN}筛选单周期Token...${NC}"
    cd "$PROJECT_ROOT" && python3 src/crypto/token_filter.py
}

# Web服务

cmd_web_auto() {
    local port=${1:-5000}
    local top_n=${2:-100}
    local kline_records=${3:-200}
    echo -e "${GREEN}启动自动化Flask服务...${NC}"
    echo -e "${BLUE}配置: Top${top_n} 代币，端口 ${port}，每个Token ${kline_records}条K线${NC}"
    echo -e "${BLUE}功能: 每天早上8点自动获取和筛选数据${NC}"
    bash scripts/crypto/start_flask_auto.sh $port $top_n $kline_records
}

# OKX数据获取
cmd_okx_fetch() {
    local top_n=${1:-100}
    echo -e "${GREEN}获取OKX Top${top_n}多周期K线数据...${NC}"
    bash scripts/okx/fetch_multi_period.sh $top_n
}

cmd_okx_filter() {
    echo -e "${GREEN}筛选OKX多周期Token...${NC}"
    bash scripts/okx/filter_multi_period.sh
}

cmd_web_stop() {
    echo -e "${YELLOW}停止所有自动化Web服务...${NC}"
    pkill -f "flask_auto_server.py" 2>/dev/null
    rm -f logs/*.pid 2>/dev/null
    echo -e "${GREEN}✓ 所有自动化Web服务已停止${NC}"
}

cmd_web_status() {
    echo -e "${BLUE}Web服务状态:${NC}"
    echo ""
    
    if pgrep -f "flask_auto_server.py" > /dev/null; then
        echo -e "${GREEN}✓ 三市场自动化服务: 运行中${NC}"
        ps aux | grep "flask_auto_server" | grep -v grep | awk '{print "  PID: "$2", 端口: 8866 (BN市场+OK市场+US股票)"}'
    else
        echo -e "${YELLOW}○ 三市场自动化服务: 未运行${NC}"
    fi
}

# 数据管理
cmd_list_data() {
    echo -e "${BLUE}数据文件列表:${NC}"
    echo ""
    echo "【多周期K线数据】"
    ls -lht data/binance_top100_multi_period_*.xlsx 2>/dev/null | head -5
    echo ""
    echo "【单周期K线数据】"
    ls -lht data/binance_top_n_daily_*.csv 2>/dev/null | head -5
    echo ""
    echo "【筛选结果 - 多周期】"
    ls -lht data/qualified_tokens_multi_period_*.xlsx 2>/dev/null | head -5
    echo ""
    echo "【筛选结果 - 单周期】"
    ls -lht data/qualified_tokens_*.csv 2>/dev/null | head -5
}

cmd_latest_data() {
    echo -e "${BLUE}最新数据文件:${NC}"
    echo ""
    latest_multi=$(ls -t data/binance_top100_multi_period_*.xlsx 2>/dev/null | head -1)
    latest_filter=$(ls -t data/qualified_tokens_multi_period_*.xlsx 2>/dev/null | head -1)
    
    if [ -n "$latest_multi" ]; then
        echo "最新K线数据: $latest_multi"
        ls -lh "$latest_multi"
    fi
    
    if [ -n "$latest_filter" ]; then
        echo "最新筛选结果: $latest_filter"
        ls -lh "$latest_filter"
    fi
}

cmd_clean_data() {
    echo -e "${YELLOW}清理旧数据文件（保留最新3个）...${NC}"
    
    # 清理旧的K线数据
    ls -t data/binance_top100_multi_period_*.xlsx 2>/dev/null | tail -n +4 | xargs rm -f
    ls -t data/binance_top_n_daily_*.csv 2>/dev/null | tail -n +4 | xargs rm -f
    
    # 清理旧的筛选结果
    ls -t data/qualified_tokens_multi_period_*.xlsx 2>/dev/null | tail -n +4 | xargs rm -f
    ls -t data/qualified_tokens_*.csv 2>/dev/null | tail -n +4 | xargs rm -f
    
    echo -e "${GREEN}✓ 清理完成${NC}"
}

# 富途API
cmd_futu_check() {
    echo -e "${GREEN}检查FutuOpenD连接...${NC}"
    cd "$PROJECT_ROOT" && python3 src/crypto/check_futu_connection.py
}

cmd_futu_start() {
    echo -e "${GREEN}启动FutuOpenD...${NC}"
    bash scripts/crypto/start_futud.sh
}

cmd_futu_fetch() {
    echo -e "${GREEN}获取美股数据...${NC}"
    bash scripts/crypto/fetch_us_stocks.sh
}

# 文档
cmd_docs() {
    echo -e "${BLUE}文档列表:${NC}"
    ls -1 docs/*.md
}

cmd_readme() {
    cat docs/README.md
}

cmd_structure() {
    cat PROJECT_STRUCTURE.md
}

# 工具
cmd_setup() {
    echo -e "${GREEN}初始化项目环境...${NC}"
    bash scripts/crypto/setup.sh
}

cmd_install_deps() {
    echo -e "${GREEN}安装Python依赖...${NC}"
    pip3 install -r requirements.txt --break-system-packages 2>/dev/null || \
    pip3 install -r requirements.txt
}

cmd_test() {
    echo -e "${GREEN}运行测试...${NC}"
    cd "$PROJECT_ROOT" && python3 src/crypto/test_multi_period.py
}

cmd_clean() {
    echo -e "${YELLOW}清理临时文件...${NC}"
    rm -rf __pycache__ src/__pycache__ src/crypto/__pycache__
    rm -f logs/*.log logs/*.pid
    echo -e "${GREEN}✓ 清理完成${NC}"
}

# Alert服务管理
cmd_alert_start() {
    echo -e "${GREEN}启动Alert服务...${NC}"
    ./start_alert.sh start
}

cmd_alert_stop() {
    echo -e "${YELLOW}停止Alert服务...${NC}"
    ./start_alert.sh stop
}

cmd_alert_restart() {
    echo -e "${BLUE}重启Alert服务...${NC}"
    ./start_alert.sh restart
}

cmd_alert_status() {
    ./start_alert.sh status
}

cmd_alert_logs() {
    ./start_alert.sh logs
}

cmd_alert_test() {
    ./start_alert.sh test
}

# 主命令分发
case "${1:-help}" in
    fetch)
        cmd_fetch "$2"
        ;;
    fetch-single)
        cmd_fetch_single
        ;;
    filter)
        cmd_filter
        ;;
    filter-single)
        cmd_filter_single
        ;;
    web-auto)
        cmd_web_auto "$2" "$3" "$4"
        ;;
    okx-fetch)
        cmd_okx_fetch "$2"
        ;;
    okx-filter)
        cmd_okx_filter
        ;;
    web-stop)
        cmd_web_stop
        ;;
    web-status)
        cmd_web_status
        ;;
    list-data)
        cmd_list_data
        ;;
    latest-data)
        cmd_latest_data
        ;;
    clean-data)
        cmd_clean_data
        ;;
    futu-check)
        cmd_futu_check
        ;;
    futu-start)
        cmd_futu_start
        ;;
    futu-fetch)
        cmd_futu_fetch
        ;;
    docs)
        cmd_docs
        ;;
    readme)
        cmd_readme
        ;;
    structure)
        cmd_structure
        ;;
    setup)
        cmd_setup
        ;;
    install-deps)
        cmd_install_deps
        ;;
    test)
        cmd_test
        ;;
    clean)
        cmd_clean
        ;;
    alert-start)
        cmd_alert_start
        ;;
    alert-stop)
        cmd_alert_stop
        ;;
    alert-restart)
        cmd_alert_restart
        ;;
    alert-status)
        cmd_alert_status
        ;;
    alert-logs)
        cmd_alert_logs
        ;;
    alert-test)
        cmd_alert_test
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

