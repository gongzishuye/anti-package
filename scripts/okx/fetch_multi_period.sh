#!/bin/bash

# OKX多周期K线数据获取脚本
# 用法: ./fetch_multi_period.sh [TOP_N]
# TOP_N: 获取前N个代币，默认100

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
echo -e "${BLUE}OKX多周期K线数据获取${NC}"
echo "================================================================================"
echo ""

# 参数配置
TOP_N=${1:-100}

echo -e "${BLUE}配置参数:${NC}"
echo "  Top N: $TOP_N"
echo ""

# 检查Python环境
echo -e "${YELLOW}检查Python环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 未安装${NC}"
    exit 1
fi

# 检查必要的Python包
echo -e "${YELLOW}检查Python依赖...${NC}"
python3 -c "import pandas, requests, openpyxl" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}正在安装依赖包...${NC}"
    pip3 install pandas requests openpyxl --break-system-packages 2>/dev/null || \
    pip3 install pandas requests openpyxl
fi

echo -e "${GREEN}✓ 依赖检查完成${NC}"
echo ""

# 创建必要的目录
mkdir -p data logs

echo -e "${YELLOW}开始获取OKX Top${TOP_N}多周期K线数据...${NC}"
echo ""

# 执行数据获取
python3 src/crypto/okx_fetch_multi_period_data.py --top-n $TOP_N --auto

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}✓ OKX数据获取完成${NC}"
    echo "================================================================================"
    echo ""
    echo -e "${BLUE}数据文件位置:${NC}"
    echo "  data/okx_top${TOP_N}_multi_period_*.xlsx"
    echo ""
    echo -e "${BLUE}后续步骤:${NC}"
    echo "  1. 使用BN的过滤逻辑处理OKX数据"
    echo "  2. 使用BN的展示逻辑展示OKX结果"
    echo ""
else
    echo ""
    echo "================================================================================"
    echo -e "${RED}✗ OKX数据获取失败${NC}"
    echo "================================================================================"
    echo ""
    echo -e "${YELLOW}请检查:${NC}"
    echo "  1. 网络连接是否正常"
    echo "  2. OKX API是否可访问"
    echo "  3. 查看详细错误信息"
    echo ""
    exit 1
fi
