# 多周期Token筛选结果Web展示

美观的Web界面展示多周期（1日、3日、周K线）Token筛选结果，支持选项卡切换查看不同周期的数据。

## 功能特点

- ✨ 支持查看3个周期的筛选结果（1日、3日、周K线）
- 🎨 现代化设计，响应式布局
- 📊 实时数据展示和统计
- 🔍 搜索和筛选功能
- 🔄 选项卡切换不同周期
- 📈 按USDT成交量自动排序
- ⚡ 无需额外依赖（除openpyxl）

## 快速开始

### 前提条件

需要先生成筛选结果数据：

```bash
# 1. 获取多周期K线数据
./fetch_multi_period.sh

# 2. 筛选符合条件的Token
./filter_multi_period.sh
```

这将生成 `qualified_tokens_multi_period_YYYYMMDD_HHMMSS.xlsx`

### 启动Web服务

#### 方法1：使用启动脚本（推荐）

```bash
./start_multi_web.sh
```

#### 方法2：直接运行Python

```bash
# 默认端口8866
python3 multi_period_web_server.py

# 指定端口
python3 multi_period_web_server.py 5000
```

## 访问Web界面

启动成功后，在浏览器中打开：

```
http://localhost:8866
```

或

```
http://127.0.0.1:8866
```

如果在远程服务器上运行，使用服务器IP：

```
http://你的服务器IP:8866
```

## 界面功能

### 1. 周期选项卡

顶部有3个选项卡，点击可切换查看：
- **1日K线** - 短线交易信号
- **3日K线** - 中短线波段信号
- **周K线** - 中长线趋势信号

### 2. 统计卡片

每个周期显示4个关键指标：
- 符合条件Token总数
- 平均成交量增长
- 平均价格涨幅
- 最大成交量增长

### 3. 搜索框

输入Token符号快速搜索（如：BTC、ETH）

### 4. 数据表格

显示所有符合条件的Token，包含：
- Token符号（点击可跳转到币安交易页面）
- T-2和T-1的详细数据
- 成交量增长率
- 价格涨跌幅

### 5. 数据排序

自动按T-1 USDT成交量降序排序，优先显示流动性好的Token

## API接口

服务提供REST API接口：

### 获取所有周期数据

```bash
GET /api/data
```

返回示例：

```json
{
  "success": true,
  "file": "qualified_tokens_multi_period_20251004_081328.xlsx",
  "update_time": "2025-10-04 08:13:28",
  "sheets": {
    "1日筛选结果": [
      {
        "symbol": "OPENUSDT",
        "T_minus_2_date": "2025-10-02",
        "T_minus_1_date": "2025-10-03",
        "volume_growth_rate_pct": 432.65,
        ...
      }
    ],
    "3日筛选结果": [...],
    "周筛选结果": [...]
  }
}
```

## 使用示例

### 完整工作流程

```bash
# 1. 获取原始K线数据（10-15分钟）
./fetch_multi_period.sh

# 2. 筛选符合条件的Token（<1分钟）
./filter_multi_period.sh

# 3. 启动Web服务
./start_multi_web.sh

# 4. 浏览器访问
# http://localhost:8866
```

### 后台运行

服务已配置为后台运行模式：

```bash
# 启动（自动后台）
./start_multi_web.sh

# 查看日志
tail -f multi_web_server.log

# 停止服务
kill $(cat multi_web_server.pid)

# 或直接
pkill -f multi_period_web_server
```

### 查看实时日志

```bash
tail -f multi_web_server.log
```

## 技术特性

### 数据源

自动读取最新的 `qualified_tokens_multi_period_*.xlsx` 文件

### 数据更新

Web服务会自动读取最新文件，无需重启。只需：

1. 生成新的筛选结果文件
2. 在Web界面点击"刷新数据"

### 性能

- 使用Python标准库 `http.server`
- 支持并发请求
- 响应速度快（<100ms）

## 常见问题

### Q1: 页面显示"未找到数据文件"

**解决方法：**

```bash
# 确保已生成筛选结果
ls qualified_tokens_multi_period_*.xlsx

# 如果没有，先运行筛选
./filter_multi_period.sh
```

### Q2: 端口被占用

**解决方法：**

```bash
# 查看占用端口的进程
lsof -i:8866

# 停止旧服务
pkill -f multi_period_web_server

# 或使用不同端口
python3 multi_period_web_server.py 8000
```

### Q3: 某个周期没有数据

**原因：**
该周期未找到符合筛选条件的Token

**页面显示：**
"😕 当前周期暂无符合条件的Token"

### Q4: 如何更新数据？

**方法1：重新获取和筛选**

```bash
# 完整流程
./fetch_multi_period.sh
./filter_multi_period.sh
# 在Web界面点击"刷新数据"
```

**方法2：只更新筛选（使用现有K线）**

```bash
./filter_multi_period.sh
# 在Web界面点击"刷新数据"
```

### Q5: 如何在远程服务器访问？

**确保防火墙开放端口：**

```bash
# Ubuntu/Debian
sudo ufw allow 8866

# CentOS/RHEL
sudo firewall-cmd --add-port=8866/tcp --permanent
sudo firewall-cmd --reload
```

**通过浏览器访问：**

```
http://服务器IP:8866
```

## 与单周期版本的对比

| 特性 | 原版 (simple_web_server.py) | 多周期版 (multi_period_web_server.py) |
|------|---------------------------|-----------------------------------|
| 数据源 | CSV文件 | Excel文件（多sheet） |
| 周期支持 | 仅1日 | 1日、3日、周K线 |
| 切换功能 | ❌ | ✅ 选项卡切换 |
| 统计信息 | 单周期 | 各周期独立统计 |
| 数据对比 | ❌ | ✅ 可切换对比 |

## 相关文件

- `multi_period_web_server.py` - Web服务器主程序
- `start_multi_web.sh` - 启动脚本
- `multi_web_server.log` - 服务日志
- `multi_web_server.pid` - 进程ID文件
- `qualified_tokens_multi_period_*.xlsx` - 数据源文件

## 界面截图说明

### 顶部区域
- 标题："多周期Token筛选结果"
- 更新时间和文件名

### 周期选项卡
- 3个按钮：1日K线 | 3日K线 | 周K线
- 当前选中的高亮显示

### 统计卡片
- 4个卡片横向排列
- 数字大，易读

### 控制区
- 搜索框（左）
- 刷新按钮（右）

### 数据表格
- 排名 | Token | T-2数据 | T-1数据 | 增长指标
- 可点击Token符号跳转交易

## 自定义配置

### 修改默认端口

编辑 `start_multi_web.sh`：

```bash
PORT=8000  # 改为你想要的端口
```

### 修改数据文件路径

编辑 `multi_period_web_server.py` 中的 `get_latest_qualified_tokens_file()` 函数

### 添加更多统计指标

在 `get_stats()` 函数中添加计算逻辑

## 注意事项

1. **依赖要求**：需要安装 `openpyxl` 以读取Excel文件
2. **数据更新**：筛选结果不会自动更新，需手动运行筛选脚本
3. **浏览器兼容**：支持现代浏览器（Chrome、Firefox、Safari、Edge）
4. **并发访问**：支持多用户同时访问
5. **数据安全**：默认只监听本地，如需远程访问注意安全设置

## 进阶使用

### 定时更新数据

```bash
# 添加到crontab，每天早上9点自动更新
0 9 * * * cd /home/ubuntu/code/anti-package && ./fetch_multi_period.sh && ./filter_multi_period.sh
```

### 使用nginx反向代理

```nginx
location /tokens/ {
    proxy_pass http://localhost:8866/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 集成到其他系统

使用API接口：

```python
import requests

# 获取数据
response = requests.get('http://localhost:8866/api/data')
data = response.json()

# 处理各周期数据
for period, tokens in data['sheets'].items():
    print(f"{period}: {len(tokens)} 个Token")
    for token in tokens:
        print(f"  {token['symbol']}: {token['volume_growth_rate_pct']:.1f}%")
```

## 许可证

本项目仅供学习和研究使用。数据来源于币安交易所，使用时请遵守相关服务条款。

