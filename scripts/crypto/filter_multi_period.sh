#!/bin/bash

echo "============================================================"
echo "多周期币安Token筛选器"
echo "============================================================"
echo ""

# 检查依赖
if ! python3 -c "import openpyxl" 2>/dev/null; then
    echo "⚠ 未安装openpyxl"
    echo "正在安装..."
    pip3 install openpyxl --break-system-packages
fi

echo "开始筛选..."
echo ""

# 运行筛选脚本
cd "$(dirname "$0")/../.." && python3 src/crypto/token_filter_multi_period.py

echo ""
echo "============================================================"
echo "筛选完成"
echo "============================================================"

