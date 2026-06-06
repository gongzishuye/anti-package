# 富途API - 美股数据获取工具

使用富途OpenAPI获取美股所有股票的信息数据。

## 功能特点

- 🚀 获取所有美股股票列表（主板股票、ETF、权证等）
- 📊 获取实时行情快照（价格、成交量、市值等）
- 📈 获取历史K线数据
- 💾 自动保存为CSV格式
- 🔄 支持批量请求，自动处理API限制
- 📱 完整的错误处理和进度显示

## 前置要求

### 1. 安装FutuOpenD客户端

富途API需要通过FutuOpenD客户端来访问数据。

**下载地址：**
- 官方网站：https://www.futunn.com/download/OpenAPI
- 文档：https://openapi.futunn.com/futu-api-doc/

**支持平台：**
- Windows
- macOS
- Linux

### 2. 启动FutuOpenD

下载并安装后，启动FutuOpenD客户端：

1. 打开FutuOpenD应用
2. 登录你的富途账号
3. 确保客户端保持运行状态
4. 默认监听端口：`11111`

**注意事项：**
- 免费账号有API调用次数限制
- 实时行情需要相应的市场权限
- 建议使用有美股权限的账号

## 安装依赖

```bash
pip install -r requirements.txt
```

或单独安装富途API：

```bash
pip install futu-api
```

## 配置说明

### 方法1：使用环境变量（推荐）

在 `.env` 文件中添加（可选）：

```env
# FutuOpenD连接配置
FUTU_HOST=127.0.0.1  # FutuOpenD地址，默认本地
FUTU_PORT=11111      # FutuOpenD端口，默认11111
```

### 方法2：在代码中配置

```python
from futu_us_stock_fetcher import FutuUSStockFetcher

# 自定义连接参数
fetcher = FutuUSStockFetcher(host='127.0.0.1', port=11111)
```

## 使用方法

### 基本使用

直接运行主程序：

```bash
python3 futu_us_stock_fetcher.py
```

这将：
1. 连接到FutuOpenD
2. 获取所有美股股票列表
3. 获取实时行情数据
4. 合并并保存为CSV文件

### 编程使用

#### 1. 获取所有美股股票基本信息

```python
from futu_us_stock_fetcher import FutuUSStockFetcher

# 创建数据获取器
fetcher = FutuUSStockFetcher()

# 连接
fetcher.connect()

# 获取所有美股股票列表
stocks_df = fetcher.get_all_us_stocks()

# 显示数据
print(stocks_df.head())

# 断开连接
fetcher.disconnect()
```

#### 2. 获取实时行情

```python
# 获取指定股票的实时行情
stock_codes = ['US.AAPL', 'US.TSLA', 'US.GOOGL', 'US.MSFT']
quotes_df = fetcher.get_stock_snapshot(stock_codes)

print(quotes_df)
```

#### 3. 获取历史K线数据

```python
# 获取某只股票的历史K线
from futu import KLType

kline_df = fetcher.get_stock_kline(
    stock_code='US.AAPL',
    start_date='2024-01-01',
    end_date='2024-12-31',
    ktype=KLType.K_DAY  # 日K线
)

print(kline_df)
```

#### 4. 完整流程：获取所有股票及行情

```python
# 一键获取所有数据
df = fetcher.fetch_all_us_stocks_with_quotes()

# 保存到CSV
fetcher.save_to_csv(df, 'my_us_stocks.csv')
```

## 输出数据说明

### 股票基本信息字段

- `code`: 股票代码（如 US.AAPL）
- `name`: 股票名称
- `stock_type`: 证券类型（STOCK/ETF/WARRANT）
- `listing_date`: 上市日期
- `lot_size`: 每手股数
- `stock_id`: 股票ID

### 实时行情字段

- `last_price`: 最新价格
- `open_price`: 开盘价
- `high_price`: 最高价
- `low_price`: 最低价
- `prev_close_price`: 昨收价
- `change_rate`: 涨跌幅（%）
- `volume`: 成交量
- `turnover`: 成交额
- `market_val`: 市值
- `pe_ratio`: 市盈率
- `pb_ratio`: 市净率
- 更多字段参见CSV输出

## 常见问题

### Q1: 连接FutuOpenD失败

**解决方法：**
1. 确保FutuOpenD客户端已启动
2. 检查端口号是否正确（默认11111）
3. 确认防火墙未拦截连接
4. 尝试重启FutuOpenD客户端

### Q2: 获取行情数据为空

**可能原因：**
1. 没有相应市场的行情权限
2. 账号未开通美股权限
3. 非交易时间（部分数据可能不可用）

**解决方法：**
- 登录富途牛牛App确认权限
- 联系富途客服开通相应权限

### Q3: API调用次数限制

富途API有以下限制：
- 免费账号：每天有调用次数限制
- 付费账号：限制更宽松

**建议：**
- 合理安排请求频率
- 使用批量接口（每次最多200只股票）
- 保存数据到本地，避免重复请求

### Q4: 获取数据速度慢

**优化建议：**
1. 使用批量接口（每次200只）
2. 适当调整延迟时间（脚本中已设置）
3. 只获取必要的数据字段
4. 考虑分时段获取数据

## API限制说明

根据富途OpenAPI文档：

- 每次最多请求200只股票的行情
- 有分钟级请求频率限制
- K线数据每次最多获取1000根
- 具体限制请参考：https://openapi.futunn.com/futu-api-doc/qa/frequency-limit.html

## 示例输出

```
================================================================================
富途API - 美股数据获取工具
================================================================================
✓ 成功连接到FutuOpenD (127.0.0.1:11111)

正在获取美股股票列表...
✓ 获取到美股主板股票: 8526 只
✓ 获取到美股ETF: 2341 只
✓ 获取到美股权证: 156 只

✓ 总共获取到 11023 只美股证券

正在获取 11023 只股票的实时行情...
✓ 已获取 200/11023 只股票行情
✓ 已获取 400/11023 只股票行情
...

✓ 成功获取 10856 只股票的实时行情
✓ 成功合并数据，共 11023 条记录

数据统计:
  总股票数: 11023
  按类型统计:
    STOCK: 8526
    ETF: 2341
    WARRANT: 156

✓ 数据已保存到: us_stocks_20251003_120000.csv
  文件大小: 2458.36 KB
  股票数量: 11023

================================================================================
✓ 所有任务完成！
================================================================================
```

## 相关链接

- 富途OpenAPI官方文档：https://openapi.futunn.com/futu-api-doc/
- Python SDK文档：https://openapi.futunn.com/futu-api-doc/api/python-api.html
- API限制说明：https://openapi.futunn.com/futu-api-doc/qa/frequency-limit.html
- 富途牛牛下载：https://www.futunn.com/download

## 注意事项

1. **账号要求**
   - 需要有富途账号
   - 建议开通美股行情权限
   - 推荐使用付费账号以获得更高的API调用限制

2. **数据延迟**
   - 免费行情可能有15-20分钟延迟
   - 实时行情需要付费订阅

3. **交易时间**
   - 美股交易时间：周一至周五 09:30-16:00（美东时间）
   - 盘前交易：04:00-09:30
   - 盘后交易：16:00-20:00
   - 非交易时间部分数据可能不可用

4. **数据更新**
   - 建议每天收盘后获取数据
   - 避免在高峰时段频繁请求

## 许可证

本项目仅供学习和研究使用。使用富途API需遵守富途证券的服务条款和API使用协议。

