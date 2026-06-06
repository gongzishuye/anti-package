#!/bin/bash
###############################################################################
# 斐波那契回撤预警系统 - 快速配置脚本
###############################################################################

echo "=========================================================================="
echo "🎯 斐波那契回撤预警系统 - 快速配置"
echo "=========================================================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查Python
echo "1. 检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} Python已安装: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python未安装，请先安装Python3"
    exit 1
fi

# 检查依赖
echo ""
echo "2. 检查依赖包..."
REQUIRED_PACKAGES=("requests" "pandas" "schedule")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $package"
    else
        echo -e "  ${RED}✗${NC} $package (缺失)"
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}需要安装缺失的包...${NC}"
    pip3 install "${MISSING_PACKAGES[@]}"
fi

# 配置企业微信Webhook
echo ""
echo "3. 配置企业微信Webhook..."
echo ""
echo "请按照以下步骤获取Webhook地址:"
echo "  1) 打开企业微信群聊"
echo "  2) 右键点击 → 添加群机器人"
echo "  3) 创建机器人并复制Webhook地址"
echo ""

# 检查.env文件是否存在
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env 文件已存在"
    
    # 检查是否配置了WECOM_WEBHOOK_URL
    if grep -q "WECOM_WEBHOOK_URL=" .env && ! grep -q "WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key-here" .env; then
        echo -e "${GREEN}✓${NC} WECOM_WEBHOOK_URL 已配置"
    else
        echo -e "${YELLOW}⚠ WECOM_WEBHOOK_URL 未配置或使用的是示例值${NC}"
        read -p "是否现在配置? (y/n): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo ""
            read -p "请输入企业微信Webhook地址: " webhook_url
            
            if [ -n "$webhook_url" ]; then
                # 更新.env文件
                sed -i "s|WECOM_WEBHOOK_URL=.*|WECOM_WEBHOOK_URL=$webhook_url|" .env
                echo -e "${GREEN}✓${NC} Webhook地址已保存到 .env"
            fi
        fi
    fi
else
    echo -e "${YELLOW}⚠ .env 文件不存在${NC}"
    read -p "是否创建 .env 文件? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 复制模板
        if [ -f "env.example" ]; then
            cp env.example .env
            echo -e "${GREEN}✓${NC} 已从 env.example 创建 .env"
        else
            # 创建基本的.env文件
            cat > .env << EOF
# 企业微信webhook地址
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key-here

# 价格更新间隔（分钟）
PRICE_UPDATE_INTERVAL=15

# Excel同步时间
EXCEL_SYNC_TIME=08:30
EOF
            echo -e "${GREEN}✓${NC} 已创建 .env 文件"
        fi
        
        echo ""
        read -p "请输入企业微信Webhook地址: " webhook_url
        
        if [ -n "$webhook_url" ]; then
            sed -i "s|WECOM_WEBHOOK_URL=.*|WECOM_WEBHOOK_URL=$webhook_url|" .env
            echo -e "${GREEN}✓${NC} Webhook地址已保存到 .env"
        fi
    fi
fi

# 测试功能
echo ""
echo "4. 测试功能..."
echo ""
read -p "是否运行功能测试? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 test_fibonacci_retracement.py
fi

# 使用说明
echo ""
echo "=========================================================================="
echo "✅ 配置完成!"
echo "=========================================================================="
echo ""
echo "📚 使用方法:"
echo ""
echo "1. 单次测试 (测试价格更新和回撤检测):"
echo "   python3 src/alert/price_updater.py --once"
echo ""
echo "2. 持续运行 (每15分钟自动更新):"
echo "   python3 src/alert/price_updater.py"
echo ""
echo "3. 综合调度器 (推荐，包含Excel同步+价格更新):"
echo "   python3 src/alert/combined_scheduler.py --run-all-now"
echo ""
echo "4. 后台运行:"
echo "   nohup python3 src/alert/combined_scheduler.py --run-all-now > logs/alerts.log 2>&1 &"
echo ""
echo "5. 查看日志:"
echo "   tail -f logs/alerts.log"
echo ""
echo "=========================================================================="
echo "📖 详细文档:"
echo "   - src/alert/FIBONACCI_RETRACEMENT_GUIDE.md"
echo "   - src/alert/README.md"
echo "=========================================================================="
echo ""

