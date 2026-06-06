# TopN 配置指南

## 概述

从版本更新后，系统支持灵活配置获取的代币数量（TopN），不再固定为Top100。

## 配置方式

### 1. 数据获取脚本

#### 方式1：使用命令行参数
```bash
# 获取Top50代币
python3 src/fetch_multi_period_data.py --top-n 50

# 获取Top200代币
python3 src/fetch_multi_period_data.py --top-n 200

# 还可以自定义天数
python3 src/fetch_multi_period_data.py --top-n 50 --days-1d 30 --days-3d 60
```

#### 方式2：使用Shell脚本
```bash
# 默认Top100
bash scripts/fetch_multi_period.sh

# Top50
bash scripts/fetch_multi_period.sh 50

# Top200
bash scripts/fetch_multi_period.sh 200
```

#### 方式3：使用run.sh快捷命令
```bash
# 默认Top100
./run.sh fetch

# Top50
./run.sh fetch 50

# Top200
./run.sh fetch 200
```

### 2. Flask自动化服务

#### 方式1：命令行参数（推荐）
```bash
# 启动时指定TopN
bash scripts/start_flask_auto.sh 5000 50   # 端口5000, Top50

# 或者只指定TopN（使用默认端口5000）
bash scripts/start_flask_auto.sh 5000 200  # Top200
```

#### 方式2：使用run.sh
```bash
# 默认配置（端口5000, Top100）
./run.sh web-auto

# Top50
./run.sh web-auto 5000 50

# Top200, 端口8080
./run.sh web-auto 8080 200
```

#### 方式3：环境变量
```bash
# 设置环境变量
export TOP_N=50

# 启动服务（将使用环境变量）
bash scripts/start_flask_auto.sh
```

#### 方式4：直接运行Python脚本
```bash
# Top50
python3 src/flask_auto_server.py 5000 --top-n 50

# Top200
python3 src/flask_auto_server.py 8080 --top-n 200
```

## 文件命名规则

更新后，生成的文件名会反映实际的TopN配置：

### 原始数据文件
- **Top100**: `binance_top100_multi_period_20251004_120000.xlsx`
- **Top50**: `binance_top50_multi_period_20251004_120000.xlsx`
- **Top200**: `binance_top200_multi_period_20251004_120000.xlsx`

### 筛选结果文件
- 文件名保持通用格式：`qualified_tokens_multi_period_20251004_120000.xlsx`
- 内容根据原始数据自动适配

## 使用建议

### 推荐配置

| 场景 | TopN | 说明 |
|-----|------|------|
| **快速测试** | 10-20 | 获取速度快，适合调试 |
| **日常分析** | 50-100 | 平衡速度和覆盖面 |
| **深度挖掘** | 200+ | 更全面，但耗时较长 |

### 性能参考

| TopN | 预计耗时 | 数据量 |
|------|---------|--------|
| 10 | 1-2分钟 | 约30条K线 |
| 50 | 5-6分钟 | 约150条K线 |
| 100 | 10-15分钟 | 约300条K线 |
| 200 | 20-30分钟 | 约600条K线 |

## 查看当前配置

### Web界面
访问 http://localhost:5000，在"任务状态"卡片可以看到：
- **配置**: Top{N} 代币

### API接口
```bash
curl http://localhost:5000/api/status
```

返回示例：
```json
{
  "config": {
    "top_n": 50
  },
  "status": "未运行",
  ...
}
```

### 日志文件
```bash
tail logs/flask_auto_server.log
```

会显示：
```
配置: Top50 代币
```

## 常见问题

### Q1: 如何修改正在运行的服务的TopN？

**A**: 需要重启服务
```bash
# 停止服务
./run.sh web-stop

# 用新配置启动
./run.sh web-auto 5000 200  # Top200
```

### Q2: TopN可以设置多大？

**A**: 理论上无限制，但建议：
- 最小：10（太少可能筛选不出结果）
- 最大：500（再大获取时间过长，且低市值币种质量下降）
- 推荐：50-200

### Q3: 不同TopN的筛选结果可以共存吗？

**A**: 可以！文件名包含TopN信息，不会互相覆盖。
- `binance_top50_multi_period_*.xlsx`
- `binance_top100_multi_period_*.xlsx`
- `binance_top200_multi_period_*.xlsx`

### Q4: 自动化任务使用哪个TopN？

**A**: 使用服务启动时指定的TopN。
```bash
# 启动时指定Top50，每天早上8点会自动获取Top50
bash scripts/start_flask_auto.sh 5000 50
```

### Q5: 如何查看数据文件对应的TopN？

**A**: 从文件名即可看出：
```bash
ls -lh data/binance_top*_multi_period_*.xlsx
```

## 完整示例

### 示例1：快速测试（Top10）
```bash
# 1. 获取数据
./run.sh fetch 10

# 2. 筛选
./run.sh filter

# 3. 启动服务
./run.sh web-auto 5000 10
```

### 示例2：日常使用（Top50）
```bash
# 启动自动化服务
./run.sh web-auto 5000 50

# 浏览器访问 http://localhost:5000
# 点击"手动触发任务"立即更新
```

### 示例3：深度分析（Top200）
```bash
# 1. 启动服务（每天自动获取Top200）
bash scripts/start_flask_auto.sh 5000 200

# 2. 等待自动更新，或手动触发
# 3. 在Web界面查看结果
```

## 技术细节

### 优先级

配置优先级（从高到低）：
1. **命令行参数** `--top-n 50`
2. **环境变量** `export TOP_N=50`
3. **默认值** `100`

### 代码位置

如需进一步自定义，可修改以下文件：
- `src/fetch_multi_period_data.py` - 数据获取
- `src/flask_auto_server.py` - Flask服务配置
- `scripts/fetch_multi_period.sh` - Shell脚本
- `scripts/start_flask_auto.sh` - 服务启动脚本

## 相关文档

- [快速启动指南](../QUICKSTART_AUTO.md)
- [Flask自动化服务文档](README_FLASK_AUTO.md)
- [数据获取文档](README_MULTI_PERIOD.md)

---

更新时间：2025-10-04

