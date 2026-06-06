#!/bin/bash

echo "============================================================"
echo "FutuOpenD 自动安装脚本 (Linux)"
echo "============================================================"
echo ""

# 检测系统架构
ARCH=$(uname -m)
echo "检测到系统架构: $ARCH"

# FutuOpenD 目录
INSTALL_DIR="$HOME/FutuOpenD"

# 下载 FutuOpenD
echo ""
echo "正在下载 FutuOpenD..."
cd ~

if [ "$ARCH" = "x86_64" ]; then
    DOWNLOAD_URL="https://softwarefile.futunn.com/FutuOpenD_Latest_Linux.tar.gz"
    echo "下载地址: $DOWNLOAD_URL"
    
    if command -v wget &> /dev/null; then
        wget -O FutuOpenD_Latest_Linux.tar.gz "$DOWNLOAD_URL"
    elif command -v curl &> /dev/null; then
        curl -L -o FutuOpenD_Latest_Linux.tar.gz "$DOWNLOAD_URL"
    else
        echo "错误: 未找到 wget 或 curl"
        exit 1
    fi
    
    # 解压
    echo ""
    echo "正在解压..."
    tar -xzf FutuOpenD_Latest_Linux.tar.gz
    
    # 给予执行权限
    if [ -f "$INSTALL_DIR/FutuOpenD" ]; then
        chmod +x "$INSTALL_DIR/FutuOpenD"
        echo ""
        echo "✓ FutuOpenD 安装成功！"
        echo ""
        echo "安装位置: $INSTALL_DIR"
        echo ""
        echo "============================================================"
        echo "启动 FutuOpenD"
        echo "============================================================"
        echo ""
        echo "选择启动方式:"
        echo ""
        echo "1. 前台运行（按 Ctrl+C 停止）："
        echo "   cd $INSTALL_DIR && ./FutuOpenD"
        echo ""
        echo "2. 后台运行（推荐）："
        echo "   cd $INSTALL_DIR && nohup ./FutuOpenD > futu.log 2>&1 &"
        echo ""
        echo "3. 使用启动脚本："
        echo "   ./start_futud.sh"
        echo ""
        echo "============================================================"
        echo ""
        
        read -p "是否现在启动 FutuOpenD? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo ""
            echo "在后台启动 FutuOpenD..."
            cd "$INSTALL_DIR"
            nohup ./FutuOpenD > futu.log 2>&1 &
            FUTU_PID=$!
            echo "✓ FutuOpenD 已在后台启动 (PID: $FUTU_PID)"
            echo ""
            echo "等待 5 秒让 FutuOpenD 启动..."
            sleep 5
            
            # 检查端口
            if netstat -tuln 2>/dev/null | grep -q 11111 || ss -tuln 2>/dev/null | grep -q 11111; then
                echo "✓ 端口 11111 已监听"
                echo ""
                echo "现在可以运行测试:"
                echo "  cd /home/ubuntu/code/anti-package"
                echo "  python3 check_futu_connection.py"
            else
                echo "⚠ 端口 11111 未监听，请检查日志:"
                echo "  tail -f $INSTALL_DIR/futu.log"
            fi
        fi
    else
        echo "✗ 安装失败: 未找到 FutuOpenD 可执行文件"
        exit 1
    fi
    
else
    echo "✗ 不支持的系统架构: $ARCH"
    echo ""
    echo "请手动下载适合你系统的版本:"
    echo "https://www.futunn.com/download/OpenAPI"
    exit 1
fi

echo ""
echo "============================================================"


