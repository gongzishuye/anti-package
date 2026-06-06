#!/bin/bash

echo "============================================================"
echo "项目目录重组脚本"
echo "============================================================"
echo ""

# 创建新目录结构
echo "创建目录结构..."
mkdir -p src
mkdir -p data
mkdir -p docs
mkdir -p scripts
mkdir -p logs

echo "✓ 目录创建完成"
echo ""

# 移动Python文件到src/
echo "移动Python文件到 src/ ..."
mv -n binance_data_fetcher.py src/ 2>/dev/null
mv -n check_futu_connection.py src/ 2>/dev/null
mv -n fetch_multi_period_data.py src/ 2>/dev/null
mv -n futu_examples.py src/ 2>/dev/null
mv -n futu_us_stock_fetcher.py src/ 2>/dev/null
mv -n kline_intervals_example.py src/ 2>/dev/null
mv -n kline_usage_examples.py src/ 2>/dev/null
mv -n multi_period_web_server.py src/ 2>/dev/null
mv -n run_without_deps.py src/ 2>/dev/null
mv -n simple_web_server.py src/ 2>/dev/null
mv -n test_beijing_time.py src/ 2>/dev/null
mv -n test_multi_period.py src/ 2>/dev/null
mv -n token_filter_multi_period.py src/ 2>/dev/null
mv -n token_filter.py src/ 2>/dev/null
mv -n web_server.py src/ 2>/dev/null
echo "✓ Python文件移动完成"
echo ""

# 移动Shell脚本到scripts/
echo "移动Shell脚本到 scripts/ ..."
mv -n fetch_multi_period.sh scripts/ 2>/dev/null
mv -n fetch_us_stocks.sh scripts/ 2>/dev/null
mv -n filter_multi_period.sh scripts/ 2>/dev/null
mv -n install_futud.sh scripts/ 2>/dev/null
mv -n setup.sh scripts/ 2>/dev/null
mv -n start_futud.sh scripts/ 2>/dev/null
mv -n start_multi_web.sh scripts/ 2>/dev/null
mv -n start_web.sh scripts/ 2>/dev/null
echo "✓ Shell脚本移动完成"
echo ""

# 移动数据文件到data/
echo "移动数据文件到 data/ ..."
mv -n *.csv data/ 2>/dev/null
mv -n *.xlsx data/ 2>/dev/null
echo "✓ 数据文件移动完成"
echo ""

# 移动文档到docs/
echo "移动Markdown文档到 docs/ ..."
mv -n *.md docs/ 2>/dev/null
echo "✓ 文档移动完成"
echo ""

# 移动日志文件到logs/
echo "移动日志文件到 logs/ ..."
mv -n *.log logs/ 2>/dev/null
mv -n *.pid logs/ 2>/dev/null
echo "✓ 日志文件移动完成"
echo ""

echo "============================================================"
echo "✓ 目录重组完成！"
echo "============================================================"
echo ""
echo "新的目录结构："
echo "  src/       - Python源代码"
echo "  data/      - 数据文件（CSV、XLSX）"
echo "  docs/      - Markdown文档"
echo "  scripts/   - Shell脚本"
echo "  logs/      - 日志和PID文件"
echo "  static/    - Web静态资源"
echo "  templates/ - Web模板"
echo "  venv/      - Python虚拟环境"
echo ""
echo "请运行以下命令查看新结构："
echo "  tree -L 2 -I 'venv|__pycache__'"
echo ""

