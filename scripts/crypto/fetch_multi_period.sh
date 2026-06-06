#!/bin/bash

# 默认参数
TOP_N=${1:-100}

echo "============================================================"
echo "币安Top${TOP_N}代币多周期K线数据获取工具"
echo "============================================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "✗ 未找到python3"
    exit 1
fi

# 检查openpyxl
echo "检查依赖..."
if python3 -c "import openpyxl" 2>/dev/null; then
    echo "✓ openpyxl已安装"
else
    echo "⚠ 未安装openpyxl（Excel支持库）"
    echo ""
    echo "正在尝试安装..."
    
    # 尝试使用pip安装
    if pip3 install openpyxl 2>/dev/null; then
        echo "✓ openpyxl安装成功"
    else
        echo "⚠ 自动安装失败"
        echo ""
        echo "请手动安装:"
        echo "  pip3 install openpyxl --break-system-packages"
        echo ""
        echo "或使用备用方案（保存为多个CSV文件）"
        echo ""
        read -p "是否继续运行（将使用CSV格式）? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo ""
echo "============================================================"
echo "开始获取数据..."
echo "============================================================"
echo ""
echo "配置:"
echo "  前N个代币: $TOP_N"
echo ""
echo "将获取以下周期的K线数据:"
echo "  ✓ 1日K线（最近16天）"
echo "  ✓ 3日K线（最近30天）" 
echo "  ✓ 周K线（最近180天）"
echo ""
echo "预计耗时: 约10-15分钟（取决于网络速度）"
echo ""

# 运行脚本（--auto参数用于自动化，不询问用户）
cd "$(dirname "$0")/../.." && python3 src/crypto/fetch_multi_period_data.py --top-n $TOP_N --auto

echo ""
echo "============================================================"
echo "任务完成"
echo "============================================================"

