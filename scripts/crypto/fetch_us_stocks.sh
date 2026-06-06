#!/bin/bash

echo "============================================================"
echo "富途API - 美股数据获取工具"
echo "============================================================"
echo ""

# 检查FutuOpenD是否在运行
check_futu_running() {
    if nc -z 127.0.0.1 11111 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

echo "检查环境..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "✗ 未找到python3"
    exit 1
fi
echo "✓ Python已安装"

# 检查依赖
if python3 -c "import futu" 2>/dev/null; then
    echo "✓ futu-api已安装"
else
    echo "⚠ 未安装futu-api，正在安装..."
    pip3 install futu-api
fi

# 检查FutuOpenD连接
echo ""
echo "检查FutuOpenD连接..."
if check_futu_running; then
    echo "✓ FutuOpenD正在运行（端口11111）"
else
    echo "✗ 无法连接到FutuOpenD"
    echo ""
    echo "请确保："
    echo "1. 已下载并安装FutuOpenD客户端"
    echo "   下载地址: https://www.futunn.com/download/OpenAPI"
    echo "2. FutuOpenD客户端正在运行"
    echo "3. 已登录富途账号"
    echo ""
    read -p "是否继续尝试运行? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "============================================================"
echo "开始获取美股数据..."
echo "============================================================"
echo ""

# 运行脚本
python3 futu_us_stock_fetcher.py

echo ""
echo "============================================================"
echo "任务完成"
echo "============================================================"

