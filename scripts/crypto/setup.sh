#!/bin/bash

echo "设置币安数据获取工具..."

# 检查Python版本
python3 --version

# 尝试使用系统包管理器安装依赖
echo "尝试使用系统包管理器安装依赖..."
sudo apt update
sudo apt install -y python3-pip python3-venv python3-full

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境并安装依赖
echo "激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "设置完成！"
echo "使用方法："
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 运行程序: python binance_data_fetcher.py"
