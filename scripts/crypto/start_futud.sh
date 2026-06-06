#!/bin/bash

echo "============================================================"
echo "启动 FutuOpenD 服务"
echo "============================================================"
echo ""

FUTUD_DIR="$HOME/FutuOpenD"
FUTUD_BIN="$FUTUD_DIR/FutuOpenD"

# 检查是否已安装
if [ ! -f "$FUTUD_BIN" ]; then
    echo "✗ 未找到 FutuOpenD"
    echo ""
    echo "请先安装 FutuOpenD:"
    echo "  ./install_futud.sh"
    echo ""
    echo "或手动下载:"
    echo "  https://www.futunn.com/download/OpenAPI"
    exit 1
fi

# 检查是否已在运行
if netstat -tuln 2>/dev/null | grep -q 11111 || ss -tuln 2>/dev/null | grep -q 11111; then
    echo "⚠ FutuOpenD 似乎已在运行（端口 11111 已被监听）"
    echo ""
    read -p "是否重启? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在停止现有进程..."
        pkill -f FutuOpenD
        sleep 2
    else
        echo "取消启动"
        exit 0
    fi
fi

# 启动 FutuOpenD
echo "正在后台启动 FutuOpenD..."
cd "$FUTUD_DIR"
nohup ./FutuOpenD > futu.log 2>&1 &
FUTU_PID=$!

echo "✓ FutuOpenD 已启动"
echo "  进程ID: $FUTU_PID"
echo "  日志文件: $FUTUD_DIR/futu.log"
echo ""

echo "等待 FutuOpenD 启动..."
for i in {1..10}; do
    sleep 1
    if netstat -tuln 2>/dev/null | grep -q 11111 || ss -tuln 2>/dev/null | grep -q 11111; then
        echo ""
        echo "✓ FutuOpenD 启动成功！端口 11111 已监听"
        echo ""
        echo "管理命令:"
        echo "  查看日志: tail -f $FUTUD_DIR/futu.log"
        echo "  停止服务: pkill -f FutuOpenD"
        echo "  检查连接: python3 check_futu_connection.py"
        echo ""
        echo "============================================================"
        exit 0
    fi
    echo -n "."
done

echo ""
echo "⚠ 等待超时，FutuOpenD 可能启动失败"
echo ""
echo "请检查日志:"
echo "  tail -f $FUTUD_DIR/futu.log"
echo ""
echo "可能的问题:"
echo "1. 需要图形界面登录（FutuOpenD 需要 GUI）"
echo "2. 端口被占用"
echo "3. 权限不足"
echo ""


