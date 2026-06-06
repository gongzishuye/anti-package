# 斐波那契回撤检测与企业微信推送功能

## 📊 功能概述

本功能在价格更新模块中集成了斐波那契回撤检测，当代币价格回撤到关键位置（50%、61.8%、78.6%、88.6%）时，自动通过企业微信机器人推送通知。

## 🎯 斐波那契回撤原理

### 计算公式

```
回撤价格 = 最高价 - (最高价 - 最低价) × 回撤比例
```

### 回撤位说明

| 回撤比例 | 说明 | 支撑强度 |
|---------|------|---------|
| 50.0% | 半价回撤位 | 重要支撑 |
| 61.8% | 黄金分割位 | 强支撑 ⭐ |
| 78.6% | 深度回撤位 | 关键支撑 |
| 88.6% | 极限回撤位 | 最后支撑 |

### 示例

假设某代币：
- 最高价：$100
- 最低价：$80
- 价格区间：$20

回撤位计算：
- 50%回撤：$100 - $20 × 0.5 = $90
- 61.8%回撤：$100 - $20 × 0.618 = $87.64
- 78.6%回撤：$100 - $20 × 0.786 = $84.28
- 88.6%回撤：$100 - $20 × 0.886 = $82.28

## 🚀 快速开始

### 1. 获取企业微信机器人Webhook

1. 打开企业微信群聊
2. 右键点击 → 添加群机器人
3. 创建机器人并复制 Webhook 地址

Webhook 格式：
```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 2. 配置方式

#### 方式1：使用 .env 文件（推荐）⭐

```bash
# 1. 复制配置模板
cp env.example .env

# 2. 编辑 .env 文件，填入你的webhook地址
nano .env

# 在 .env 文件中填入：
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key-here
```

#### 方式2：环境变量

```bash
export WECOM_WEBHOOK_URL='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key-here'
```

#### 方式3：命令行参数

```bash
python3 src/alert/price_updater.py --wecom-webhook 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key-here'
```

### 3. 测试企业微信推送

```bash
# 确保已配置 .env 文件或设置环境变量
# 运行测试
python3 src/alert/wecom_notifier.py
```

应该会收到两条测试消息：
1. 文本消息测试
2. 斐波那契回撤预警测试

## 📋 使用方法

### 方法1：单次执行（测试用）

```bash
# 确保已配置 .env 文件
# 只执行一次价格更新和回撤检测
python3 src/alert/price_updater.py --once

# 或使用命令行指定webhook（会覆盖.env配置）
python3 src/alert/price_updater.py --once --wecom-webhook 'your-webhook-url'
```

### 方法2：持续运行（推荐）

```bash
# 每15分钟自动更新价格并检测回撤
python3 src/alert/price_updater.py

# 自定义更新间隔为5分钟
python3 src/alert/price_updater.py --interval 5
```

### 方法3：使用综合调度器（最佳实践）

```bash
# 启动综合调度器（Excel同步 + 价格更新 + 回撤检测）
python3 src/alert/combined_scheduler.py --run-all-now

# 使用指定的webhook
python3 src/alert/combined_scheduler.py --run-all-now --wecom-webhook 'your-webhook-url'

# 自定义价格更新间隔
python3 src/alert/combined_scheduler.py --price-interval 5
```

### 方法4：后台运行（生产环境）

```bash
# 使用nohup后台运行
nohup python3 src/alert/combined_scheduler.py --run-all-now > logs/combined_scheduler.log 2>&1 &

# 或使用 screen
screen -S alert
python3 src/alert/combined_scheduler.py --run-all-now
# 按 Ctrl+A+D 退出screen
```

## 📨 推送消息示例

当触发回撤位时，会收到如下格式的企业微信消息：

```
## 🎯 斐波那契回撤预警

**交易对**: BTCUSDT
**交易所**: BN
**周期**: 1D

---

**价格信息**
- 最高价: $50000.000000
- 最低价: $45000.000000
- 当前价: $47500.000000
- 价格变化: -5.00%

---

**回撤位置**
- 触发50.0%回撤位
- 回撤价格: $47500.000000

---

**时间**: 2025-10-18 14:30:15

> 提示：价格已回撤至关键斐波那契位置，请关注!
```

## 🔧 工作机制

### 1. 价格更新流程

```
获取监控列表 → 逐个获取最新价格 → 检测回撤 → 更新数据库
    ↓
检测到回撤 → 发送企业微信通知 → 记录已触发位置
```

### 2. 回撤检测逻辑

```python
# 触发条件
if 当前价格 <= 回撤价格 and 当前价格 < 最高价:
    触发回撤位
    发送通知
    记录该回撤位（避免重复推送）
```

### 3. 智能去重机制

- 每个监控记录的每个回撤位只推送一次
- 当价格创新高时，清除该记录的所有回撤触发记录
- 下次价格回撤时，可以重新触发推送

### 4. 回撤触发示例

```
价格走势：$100 → $95 → $90 → $85 → $95 → $105

时间线：
1. $100 - 初始最高价
2. $95 - 未触及任何回撤位
3. $90 - ✅ 触发50%回撤（推送通知）
4. $85 - ✅ 触发61.8%回撤（推送通知）
5. $95 - 价格反弹，无新触发
6. $105 - 创新高，清除回撤记录，可重新触发
```

## ⚙️ 配置选项

### .env 文件配置（推荐）

在项目根目录创建 `.env` 文件：

```bash
# 复制模板
cp env.example .env

# 编辑配置
nano .env
```

`.env` 文件内容：

```ini
# 企业微信webhook地址（必填）
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key

# 价格更新间隔（可选，默认15分钟）
PRICE_UPDATE_INTERVAL=15

# Excel同步时间（可选，默认08:30）
EXCEL_SYNC_TIME=08:30
```

### 环境变量

| 变量名 | 说明 | 示例 |
|-------|------|------|
| `WECOM_WEBHOOK_URL` | 企业微信webhook地址 | `https://qyapi.weixin.qq.com/...` |
| `PRICE_UPDATE_INTERVAL` | 价格更新间隔（分钟） | `15` |
| `EXCEL_SYNC_TIME` | Excel同步时间 | `08:30` |

### 命令行参数

#### price_updater.py

```bash
--once                    # 只执行一次
--interval 15             # 更新间隔（分钟）
--wecom-webhook URL       # 企业微信webhook
```

#### combined_scheduler.py

```bash
--price-interval 15       # 价格更新间隔（分钟）
--wecom-webhook URL       # 企业微信webhook
--run-all-now            # 启动时立即执行
--price-only             # 只运行价格更新
```

## 📊 斐波那契回撤位配置

在 `price_updater.py` 中可以自定义回撤位：

```python
# 默认回撤位
FIBONACCI_LEVELS = [0.5, 0.618, 0.786, 0.886]

# 可以修改为其他斐波那契比例
FIBONACCI_LEVELS = [0.382, 0.5, 0.618, 0.786, 0.886, 1.0]
```

## 🎨 消息格式自定义

可以在 `wecom_notifier.py` 的 `send_fibonacci_alert` 方法中自定义消息格式：

```python
def send_fibonacci_alert(self, ...):
    content = f"""## 🎯 自定义标题
    
**交易对**: {ticker}
... 自定义内容 ...
"""
    return self.send_markdown_message(content)
```

## 🔍 故障排查

### 1. 未收到推送通知

检查清单：
- ✅ webhook地址是否正确
- ✅ 企业微信机器人是否被禁用
- ✅ 网络连接是否正常
- ✅ 查看日志中是否有错误信息

```bash
# 查看详细日志
python3 src/alert/price_updater.py --once 2>&1 | tee test.log
```

### 2. 重复推送

- 检查是否启动了多个实例
- 确认回撤触发记录是否正常工作

### 3. 不触发回撤位

检查条件：
- 当前价格必须 <= 回撤价格
- 当前价格必须 < 最高价
- 该回撤位之前未被触发

## 📈 使用建议

### 1. 回撤位的交易策略

- **50%**: 适合短线反弹交易
- **61.8%**: 黄金分割位，中线建仓点 ⭐
- **78.6%**: 深度回调，长线建仓点
- **88.6%**: 极限支撑，加仓或止损点

### 2. 多周期配合

```
1D周期 - 短线交易参考
3D周期 - 中线趋势判断
1W周期 - 长线方向确认
```

### 3. 风控建议

- 不要仅依靠回撤位做决策
- 结合成交量、市场情绪等多方面分析
- 设置止损位，控制风险

## 🔐 安全建议

1. **webhook保护**
   - 不要将webhook地址提交到代码库
   - 使用环境变量存储敏感信息
   - 定期更换webhook密钥

2. **访问控制**
   - 限制服务器访问权限
   - 使用防火墙保护服务端口
   - 定期审查日志文件

## 📚 相关文档

- [价格更新功能说明](./README.md)
- [企业微信机器人API文档](https://developer.work.weixin.qq.com/document/path/91770)
- [斐波那契回撤理论](https://www.investopedia.com/terms/f/fibonacciretracement.asp)

## 🆘 技术支持

遇到问题？
1. 查看日志文件：`logs/combined_scheduler.log`
2. 测试企业微信推送：`python3 src/alert/wecom_notifier.py`
3. 手动测试单次更新：`python3 src/alert/price_updater.py --once`

