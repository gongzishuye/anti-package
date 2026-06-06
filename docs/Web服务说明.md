# Web服务使用说明

## 🌐 功能介绍

提供一个美观的Web界面，实时展示币安Token筛选结果（qualified_tokens数据）。

### 特点

- ✨ 现代化设计，响应式布局
- 📊 实时数据展示和统计
- 🔍 搜索和筛选功能
- 📈 多种排序方式
- 🎨 渐变背景，美观大方
- ⚡ 无需额外依赖，仅使用Python标准库

## 🚀 快速开始

### 方法1：使用启动脚本（推荐）

```bash
# 给脚本添加执行权限
chmod +x start_web.sh

# 启动服务（默认端口8000）
./start_web.sh

# 或指定端口
./start_web.sh 5000
```

### 方法2：直接运行Python脚本

```bash
# 默认端口8000
python3 simple_web_server.py

# 指定端口
python3 simple_web_server.py 5000
```

## 📱 访问地址

启动成功后，在浏览器中打开：

```
http://localhost:8000
```

或

```
http://127.0.0.1:8000
```

如果你在远程服务器上运行，使用服务器IP地址：

```
http://你的服务器IP:8000
```

## 🎯 功能说明

### 主要功能

1. **统计卡片**
   - 符合条件Token总数
   - 平均成交量增长
   - 平均价格涨幅
   - 最大成交量增长

2. **数据表格**
   - 显示所有符合条件的Token
   - 包含T-2和T-1的详细数据
   - 高亮显示重要指标

3. **交互功能**
   - 🔍 搜索：输入Token符号快速查找
   - 🔄 排序：按成交量增长、价格涨幅或符号排序
   - 🔃 刷新：点击刷新按钮重新加载数据

### API接口

服务提供以下API接口：

#### 1. 获取所有Token数据
```
GET /api/tokens
```

返回示例：
```json
{
  "success": true,
  "message": "成功加载 43 个符合条件的Token",
  "file": "qualified_tokens_20251002_221320.csv",
  "update_time": "2025-10-02 22:13:20",
  "data": [...]
}
```

#### 2. 获取统计信息
```
GET /api/stats
```

返回示例：
```json
{
  "success": true,
  "data": {
    "total_count": 43,
    "avg_volume_growth": 125.5,
    "avg_price_change": 8.2,
    "max_volume_growth": 1699.4,
    "max_price_change": 39.36
  },
  "update_time": "2025-10-02 22:13:20"
}
```

## 📝 使用示例

### 完整流程

```bash
# 1. 获取币安数据
python3 binance_data_fetcher.py

# 2. 运行筛选器
python3 token_filter.py

# 3. 启动Web服务
./start_web.sh

# 4. 浏览器访问
# 打开 http://localhost:8000
```

### 只查看已有数据

如果你已经有 `qualified_tokens_*.csv` 文件：

```bash
# 直接启动服务
python3 simple_web_server.py
```

服务会自动找到最新的筛选结果文件并展示。

## 🎨 界面预览

### 页面包含

1. **顶部标题区**
   - 项目名称
   - 数据更新时间

2. **统计卡片区**（4个卡片）
   - 符合条件Token数量
   - 平均成交量增长率
   - 平均价格涨幅
   - 最大成交量增长

3. **控制栏**
   - 搜索框
   - 排序选择器
   - 刷新按钮

4. **数据表格**
   - 排名
   - Token符号
   - T-2日期和数据
   - T-1日期和数据
   - 成交量增长
   - 价格涨幅

5. **底部信息**
   - 版权信息

### 颜色说明

- 🟣 紫色渐变背景
- ⚪ 白色卡片
- 🟢 绿色：正向数据（增长、涨幅）
- 🟡 黄色高亮：重要数据（成交量>100%，涨幅>10%）

## ⚙️ 配置说明

### 修改端口

```bash
# 方法1：使用参数
python3 simple_web_server.py 5000

# 方法2：修改脚本
./start_web.sh 5000
```

### 数据文件

服务会自动查找当前目录下最新的 `qualified_tokens_*.csv` 文件。

如果有多个文件，会选择修改时间最新的。

## 🔧 故障排除

### 1. 端口被占用

```bash
# 使用其他端口
python3 simple_web_server.py 8001
```

### 2. 找不到数据文件

```bash
# 运行筛选器生成数据
python3 token_filter.py
```

### 3. 无法访问

- 检查防火墙设置
- 确认端口未被阻止
- 如果是远程服务器，确保安全组/防火墙允许该端口

### 4. 停止服务

在终端按 `Ctrl+C` 停止服务。

## 📊 数据更新

当你有新的筛选结果时：

1. 运行 `token_filter.py` 生成新的CSV文件
2. 在Web页面点击"刷新数据"按钮
3. 或重启Web服务

服务会自动读取最新的数据文件。

## 🌟 高级用法

### 在后台运行

```bash
# 使用nohup在后台运行
nohup python3 simple_web_server.py 8000 > web_server.log 2>&1 &

# 查看日志
tail -f web_server.log

# 停止服务
pkill -f simple_web_server.py
```

### 使用systemd服务（Linux）

创建服务文件 `/etc/systemd/system/binance-web.service`:

```ini
[Unit]
Description=Binance Token Web Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/code/anti-package
ExecStart=/usr/bin/python3 /home/ubuntu/code/anti-package/simple_web_server.py 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl start binance-web
sudo systemctl enable binance-web
sudo systemctl status binance-web
```

## 💡 提示

1. **定时更新数据**
   - 可以设置定时任务（cron）定期运行筛选器
   - Web服务会自动加载最新数据

2. **性能优化**
   - 数据量大时考虑添加分页功能
   - 可以添加数据缓存提升响应速度

3. **安全性**
   - 生产环境建议添加身份验证
   - 使用反向代理（如Nginx）

## 📞 技术支持

如果遇到问题：
1. 查看终端输出的错误信息
2. 检查数据文件是否存在
3. 确认Python版本（需要Python 3.6+）

---

**版本**: v1.0  
**更新时间**: 2025-10-02
