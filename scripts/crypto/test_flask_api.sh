#!/bin/bash

# Flask自动化服务API测试脚本

PORT=${1:-5000}

echo "================================================================================"
echo "Flask自动化服务 - API测试"
echo "================================================================================"
echo ""

# 测试主页
echo "1. 测试主页..."
echo "   访问: http://localhost:$PORT/"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/ | grep -q "200"; then
    echo "   ✓ 主页正常"
else
    echo "   ✗ 主页访问失败"
fi
echo ""

# 测试状态API
echo "2. 测试状态API..."
echo "   访问: http://localhost:$PORT/api/status"
STATUS=$(curl -s http://localhost:$PORT/api/status)
echo "   响应: $STATUS"
echo ""

# 测试数据API
echo "3. 测试数据API..."
echo "   访问: http://localhost:$PORT/api/data"
DATA=$(curl -s http://localhost:$PORT/api/data | head -c 200)
echo "   响应（前200字符）: $DATA..."
echo ""

echo "================================================================================"
echo "✓ API测试完成"
echo "================================================================================"
echo ""
echo "请在浏览器中访问以查看完整界面："
echo "  http://localhost:$PORT"
echo ""

