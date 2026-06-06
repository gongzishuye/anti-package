# 美股数据获取模块

基于富途API的美股数据获取、分析和筛选系统。

## 功能特性

### 🔄 数据获取
- **股票列表**: 获取所有美股股票、ETF、权证信息
- **实时行情**: 获取股票实时价格、成交量、涨跌幅等数据
- **历史数据**: 获取K线数据（日线、周线等）
- **市场概览**: 获取主要指数行情
- **股票搜索**: 支持关键词搜索股票

### 📊 技术分析
- **技术指标**: SMA、EMA、RSI、MACD、布林带等
- **趋势分析**: 价格趋势识别和强度评估
- **波动率分析**: 年化波动率、最大回撤计算
- **成交量分析**: 价量关系分析
- **支撑阻力**: 自动识别支撑阻力位
- **交易信号**: 综合多个指标生成交易信号

### 🔍 股票筛选
- **自定义筛选**: 支持市值、PE、PB、股息率等多维度筛选
- **策略筛选**: 内置价值、成长、股息、动量等投资策略
- **技术面筛选**: 基于技术指标的筛选条件
- **行业筛选**: 支持行业包含/排除筛选
- **结果导出**: 筛选结果可导出为CSV文件

## 安装要求

### 1. 富途API安装
```bash
pip install futu-api
```

### 2. 富途OpenD客户端
- 下载地址: https://www.futunn.com/download
- 安装并启动FutuOpenD客户端
- 登录富途账户
- 开通美股交易权限

### 3. 依赖包
```bash
pip install pandas numpy python-dotenv
```

## 快速开始

### 1. 基本连接测试

```python
from src.equity import USStockFetcher

# 创建数据获取器
with USStockFetcher() as fetcher:
    if fetcher.is_connected:
        print("✓ 连接成功")
        
        # 获取市场概览
        overview = fetcher.get_market_overview()
        print("主要指数:", overview)
    else:
        print("✗ 连接失败")
```

### 2. 获取股票数据

```python
from src.equity import USStockFetcher

with USStockFetcher() as fetcher:
    # 搜索股票
    apple_stocks = fetcher.search_stocks("AAPL")
    print("苹果股票:", apple_stocks)
    
    # 获取实时行情
    snapshots = fetcher.get_stock_snapshot(['US.AAPL', 'US.TSLA'])
    print("实时行情:", snapshots)
    
    # 获取K线数据
    kline_data = fetcher.get_stock_kline('US.AAPL', '2024-01-01', '2024-12-31')
    print("K线数据:", kline_data)
```

### 3. 技术分析

```python
from src.equity import USStockAnalyzer

analyzer = USStockAnalyzer()

# 计算技术指标
technical = analyzer.calculate_technical_indicators(kline_data)
print(f"RSI: {technical.rsi}")
print(f"MACD: {technical.macd}")

# 分析价格趋势
trend = analyzer.analyze_price_trend(kline_data)
print(f"趋势: {trend['trend']}")
print(f"信号: {trend['signal']}")

# 生成交易信号
signals = analyzer.generate_trading_signals(kline_data)
print(f"最终信号: {signals['final_signal']}")
```

### 4. 股票筛选

```python
from src.equity import USStockScreener, ScreeningCriteria

# 创建筛选器
screener = USStockScreener()

# 自定义筛选条件
criteria = ScreeningCriteria(
    min_market_cap=10,    # 最小市值10亿美元
    max_pe_ratio=20,      # 最大市盈率20
    min_volume=1000000,   # 最小成交量100万
    exclude_etf=True      # 排除ETF
)

result = screener.screen_stocks(criteria)
print(f"符合条件股票: {result.qualified_stocks} 只")

# 使用策略筛选
value_result = screener.screen_by_strategy('value', max_pe_ratio=15)
growth_result = screener.screen_by_strategy('growth', max_pe_ratio=30)
```

## 详细使用说明

### USStockFetcher 类

#### 初始化参数
- `host`: FutuOpenD服务器地址（默认: 127.0.0.1）
- `port`: FutuOpenD服务器端口（默认: 11111）

#### 主要方法

| 方法 | 说明 | 参数 |
|------|------|------|
| `connect()` | 连接富途API | - |
| `get_all_us_stocks()` | 获取所有美股股票 | `include_etf`, `include_warrant` |
| `get_stock_snapshot()` | 获取实时行情 | `stock_codes`, `batch_size` |
| `get_stock_kline()` | 获取K线数据 | `stock_code`, `start_date`, `end_date`, `ktype` |
| `search_stocks()` | 搜索股票 | `keyword`, `limit` |
| `get_market_overview()` | 获取市场概览 | - |
| `get_top_gainers_losers()` | 获取涨跌排行榜 | `limit` |

### USStockAnalyzer 类

#### 主要方法

| 方法 | 说明 | 参数 |
|------|------|------|
| `calculate_technical_indicators()` | 计算技术指标 | `price_data` |
| `analyze_price_trend()` | 分析价格趋势 | `price_data`, `short_period`, `long_period` |
| `calculate_volatility()` | 计算波动率 | `price_data`, `period` |
| `analyze_volume()` | 分析成交量 | `price_data` |
| `calculate_support_resistance()` | 计算支撑阻力位 | `price_data`, `lookback` |
| `generate_trading_signals()` | 生成交易信号 | `price_data` |

### USStockScreener 类

#### 筛选策略

| 策略 | 说明 | 典型参数 |
|------|------|----------|
| `value` | 价值投资 | 低PE、低PB、有股息 |
| `growth` | 成长投资 | 高PE、高增长潜力 |
| `dividend` | 股息投资 | 高股息率、稳定 |
| `momentum` | 动量投资 | 价格动量强 |
| `technical` | 技术分析 | 基于技术指标 |
| `quality` | 质量投资 | 高质量公司 |

#### 筛选条件

```python
criteria = ScreeningCriteria(
    # 基本面条件
    min_market_cap=10,        # 最小市值（亿美元）
    max_market_cap=1000,      # 最大市值
    min_pe_ratio=0,           # 最小市盈率
    max_pe_ratio=50,          # 最大市盈率
    min_pb_ratio=0,           # 最小市净率
    max_pb_ratio=10,          # 最大市净率
    min_dividend_yield=0,     # 最小股息率
    
    # 技术面条件
    min_volume=1000000,       # 最小成交量
    min_price=1.0,            # 最小股价
    max_price=1000.0,         # 最大股价
    
    # 其他条件
    exclude_etf=False,        # 是否排除ETF
    exclude_warrants=True,    # 是否排除权证
    min_listing_days=0        # 最小上市天数
)
```

## 测试

运行测试脚本验证功能：

```bash
cd src/equity
python test_us_stocks.py
```

测试内容包括：
- 富途API连接测试
- 股票搜索功能
- 实时行情获取
- K线数据获取
- 技术分析功能
- 股票筛选功能
- 策略筛选功能

## 配置说明

### 环境变量

创建 `.env` 文件配置富途API连接：

```env
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
```

### 数据目录

默认数据保存目录：
- 股票数据: `data/`
- 筛选结果: `data/`
- 日志文件: `logs/`

## 注意事项

### 1. 富途API限制
- 需要有效的富途账户
- 需要开通美股交易权限
- 有请求频率限制
- 部分数据需要订阅权限

### 2. 数据时效性
- 实时行情有延迟
- 历史数据可能有时滞
- 注意美股交易时间

### 3. 错误处理
- 网络连接异常
- API请求超时
- 数据格式变化
- 权限不足

## 常见问题

### Q: 连接失败怎么办？
A: 检查以下几点：
1. FutuOpenD客户端是否运行
2. 端口号是否正确
3. 是否已登录富途账户
4. 是否开通美股权限
5. 网络连接是否正常

### Q: 数据获取失败？
A: 可能原因：
1. 请求过于频繁
2. 股票代码不正确
3. 市场休市时间
4. API权限不足

### Q: 筛选结果为空？
A: 检查筛选条件：
1. 条件是否过于严格
2. 市值范围是否合理
3. 是否排除了太多股票
4. 数据是否完整

## 扩展开发

### 添加新的技术指标

```python
def calculate_custom_indicator(self, price_data: pd.DataFrame) -> float:
    """自定义技术指标"""
    if price_data.empty:
        return 0.0
    
    # 计算逻辑
    close_prices = price_data['close'].values
    # ... 自定义计算逻辑
    
    return indicator_value
```

### 添加新的筛选策略

```python
def _custom_strategy(self, **kwargs) -> ScreeningCriteria:
    """自定义筛选策略"""
    return ScreeningCriteria(
        min_market_cap=kwargs.get('min_market_cap', 5),
        max_pe_ratio=kwargs.get('max_pe_ratio', 25),
        # ... 其他条件
    )
```

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和富途API使用条款。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件
- 技术讨论群

---

**免责声明**: 本模块提供的数据和信息仅供参考，不构成投资建议。投资有风险，入市需谨慎。
