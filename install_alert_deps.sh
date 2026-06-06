#!/bin/bash
###############################################################################
# 反包监控报警服务 - 依赖安装脚本
###############################################################################

echo "=========================================================================="
echo "📦 安装反包监控报警服务依赖"
echo "=========================================================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

echo "✓ Python: $(python3 --version)"
echo ""

# 安装依赖
echo "正在安装依赖包..."
echo ""

pip3 install --break-system-packages \
  pandas \
  openpyxl \
  requests \
  python-dotenv \
  schedule \
  psutil

echo ""
echo "=========================================================================="
echo "✅ 依赖安装完成"
echo "=========================================================================="
echo ""
echo "已安装的包:"
pip3 list | grep -E "pandas|openpyxl|requests|dotenv|schedule|psutil"
echo ""
echo "下一步: 配置并启动服务"
echo "  1. cp env.example .env"
echo "  2. nano .env  # 填入企业微信webhook"
echo "  3. python3 alert_service.py start --run-now"
echo ""

