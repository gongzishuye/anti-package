#!/bin/bash

# OKX多周期Token筛选脚本
# 使用BN的过滤逻辑处理OKX数据

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
echo -e "${BLUE}OKX多周期Token筛选${NC}"
echo "================================================================================"
echo ""

# 查找最新的OKX数据文件
echo -e "${YELLOW}查找最新的OKX数据文件...${NC}"
LATEST_FILE=$(ls -t data/okx_top*_multi_period_*.xlsx 2>/dev/null | head -1)

if [ -z "$LATEST_FILE" ]; then
    echo -e "${RED}✗ 未找到OKX数据文件${NC}"
    echo ""
    echo -e "${YELLOW}请先运行:${NC}"
    echo "  bash scripts/okx/fetch_multi_period.sh [TOP_N]"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ 找到数据文件: $(basename "$LATEST_FILE")${NC}"
echo ""

# 检查Python环境
echo -e "${YELLOW}检查Python环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 未安装${NC}"
    exit 1
fi

# 检查必要的Python包
echo -e "${YELLOW}检查Python依赖...${NC}"
python3 -c "import pandas, openpyxl" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}正在安装依赖包...${NC}"
    pip3 install pandas openpyxl --break-system-packages 2>/dev/null || \
    pip3 install pandas openpyxl
fi

echo -e "${GREEN}✓ 依赖检查完成${NC}"
echo ""

# 使用BN的过滤逻辑处理OKX数据
echo -e "${YELLOW}开始筛选OKX Token...${NC}"
echo ""

# 创建一个临时的Python脚本来处理OKX数据
python3 -c "
import sys
import os
from datetime import datetime
sys.path.insert(0, 'src/crypto')

from token_filter_multi_period import MultiPeriodTokenFilter

# 处理OKX数据文件
excel_file = '$LATEST_FILE'
print(f'处理文件: {excel_file}')

try:
    # 创建筛选器实例
    filter_obj = MultiPeriodTokenFilter(excel_file)
    
    # 执行筛选
    results = filter_obj.filter_all_periods()
    
    # 保存结果 - 修改文件名前缀为okx
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'okx_qualified_tokens_multi_period_{timestamp}.xlsx'
    output_file = filter_obj.save_results_to_excel(results, output_filename)
    
    if output_file:
        print(f'\\n✓ OKX筛选完成，结果已保存到: {output_file}')
    else:
        print('\\n✗ 保存失败')
        sys.exit(1)
        
except Exception as e:
    print(f'\\n✗ 筛选失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}✓ OKX Token筛选完成${NC}"
    echo "================================================================================"
    echo ""
    echo -e "${BLUE}结果文件:${NC}"
    echo "  data/okx_qualified_tokens_multi_period_*.xlsx"
    echo ""
    echo -e "${BLUE}后续步骤:${NC}"
    echo "  1. 使用BN的展示逻辑查看OKX筛选结果"
    echo "  2. 可以同时运行BN和OKX的自动化服务"
    echo ""
else
    echo ""
    echo "================================================================================"
    echo -e "${RED}✗ OKX Token筛选失败${NC}"
    echo "================================================================================"
    echo ""
    echo -e "${YELLOW}请检查:${NC}"
    echo "  1. 数据文件格式是否正确"
    echo "  2. 筛选条件是否合理"
    echo "  3. 查看详细错误信息"
    echo ""
    exit 1
fi
