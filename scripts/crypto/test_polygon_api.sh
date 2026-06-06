#!/bin/bash
# Polygon.io API 测试脚本

echo "=========================================="
echo "Polygon.io 美股数据获取测试"
echo "=========================================="

# 切换到项目根目录
cd "$(dirname "$0")/../.."

# 检查 .env 文件
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  未找到 .env 文件"
    echo ""
    echo "请先创建 .env 文件并添加 Polygon.io API 密钥:"
    echo ""
    echo "1. 复制示例文件:"
    echo "   cp .env.example .env"
    echo ""
    echo "2. 编辑 .env 文件，设置 API 密钥:"
    echo "   POLYGON_KEY=your-api-key-here"
    echo ""
    echo "3. 获取 API 密钥:"
    echo "   https://polygon.io/dashboard/api-keys"
    echo ""
    exit 1
fi

# 检查是否设置了 API 密钥（支持 POLYGON_KEY 和 POLYGON_API_KEY）
if ! grep -q "POLYGON_KEY=.*[^=]" .env && ! grep -q "POLYGON_API_KEY=.*[^=]" .env; then
    echo ""
    echo "⚠️  未设置 POLYGON_KEY 或 POLYGON_API_KEY"
    echo ""
    echo "请编辑 .env 文件，设置有效的 API 密钥"
    echo ""
    exit 1
fi

echo ""
echo "✓ 环境配置检查通过"
echo ""

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ 虚拟环境已激活"
fi

echo ""
echo "开始运行测试..."
echo ""

# 运行主程序
python src/equity/polygon_us_stock_fetcher.py

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="


