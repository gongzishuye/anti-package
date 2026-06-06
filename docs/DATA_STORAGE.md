# 数据存储说明

## 📁 目录结构

所有数据文件统一存储在项目根目录的 `data/` 目录下：

```
anti-package/
├── data/                                    # 数据目录
│   ├── binance_top{N}_multi_period_*.xlsx  # K线原始数据
│   └── qualified_tokens_multi_period_*.xlsx # 筛选结果
├── src/                                     # 源代码
├── scripts/                                 # 脚本
└── logs/                                    # 日志
```

## 📊 数据文件类型

### 1. K线原始数据

**文件名格式**: `binance_top{N}_multi_period_{timestamp}.xlsx`

**示例**:
- `binance_top50_multi_period_20251004_120000.xlsx` - Top50数据
- `binance_top100_multi_period_20251004_120000.xlsx` - Top100数据
- `binance_top200_multi_period_20251004_120000.xlsx` - Top200数据

**包含内容**: 3个Sheet
- `1日K线` - 1日周期K线数据
- `3日K线` - 3日周期K线数据
- `周K线` - 周周期K线数据

### 2. 筛选结果数据

**文件名格式**: `qualified_tokens_multi_period_{timestamp}.xlsx`

**示例**:
- `qualified_tokens_multi_period_20251004_120000.xlsx`

**包含内容**: 3个Sheet
- `1日筛选结果` - 符合1日K线条件的Token
- `3日筛选结果` - 符合3日K线条件的Token
- `周筛选结果` - 符合周K线条件的Token

### 3. 单周期数据（旧版）

**文件名格式**:
- `binance_top_n_daily_{timestamp}.csv` - 单日K线数据
- `qualified_tokens_{timestamp}.csv` - 单日筛选结果

## 🔄 自动化流程

### 数据获取
```bash
# 获取数据（自动保存到data目录）
./run.sh fetch 50

# 文件位置
ls data/binance_top50_multi_period_*.xlsx
```

### 数据筛选
```bash
# 筛选数据（自动保存到data目录）
./run.sh filter

# 文件位置
ls data/qualified_tokens_multi_period_*.xlsx
```

### Flask自动化
```bash
# 启动服务（每天早上8点自动获取和筛选）
./run.sh web-auto 5000 50

# 数据自动保存到data目录
# 服务自动读取最新的数据文件
```

## 📂 查看数据文件

### 方法1：使用run.sh
```bash
# 列出所有数据文件
./run.sh list-data

# 查看最新数据文件
./run.sh latest-data
```

### 方法2：直接查看
```bash
# 查看所有K线数据
ls -lht data/binance_top*_multi_period_*.xlsx

# 查看所有筛选结果
ls -lht data/qualified_tokens_multi_period_*.xlsx

# 查看最新文件
ls -lt data/*.xlsx | head -5
```

## 🧹 数据清理

### 清理旧数据文件
```bash
# 保留最新3个文件，删除旧文件
./run.sh clean-data
```

### 手动清理
```bash
# 删除所有K线数据
rm data/binance_top*_multi_period_*.xlsx

# 删除所有筛选结果
rm data/qualified_tokens_multi_period_*.xlsx

# 清空data目录（谨慎操作！）
rm -rf data/*
```

## 💾 存储空间

### 文件大小参考

| TopN | Excel文件大小 | 说明 |
|------|--------------|------|
| Top10 | ~50KB | 适合快速测试 |
| Top50 | ~150KB | 日常分析 |
| Top100 | ~300KB | 标准配置 |
| Top200 | ~600KB | 深度分析 |
| Top300 | ~900KB | 完整覆盖 |

### 存储建议

- **开发环境**: 定期清理，保留最新3-5个文件
- **生产环境**: 建议设置定时任务，每周清理旧数据
- **备份**: 重要数据建议备份到其他位置

## 🔧 技术细节

### 数据保存逻辑

所有数据获取和筛选脚本都会自动：
1. 检查 `data/` 目录是否存在
2. 如果不存在，自动创建
3. 将文件保存到 `data/` 目录
4. 返回完整的文件路径

### 代码位置

数据保存逻辑在以下文件中：
- `src/fetch_multi_period_data.py` - K线数据保存
- `src/token_filter_multi_period.py` - 筛选结果保存

## 📋 常见问题

### Q1: 为什么要统一存储到data目录？

**A**: 
- ✅ 统一管理，便于查找
- ✅ 避免污染项目根目录
- ✅ 便于备份和清理
- ✅ 符合项目结构规范

### Q2: data目录不存在会怎样？

**A**: 脚本会自动创建 `data/` 目录，无需手动创建。

### Q3: 可以修改存储位置吗？

**A**: 可以，修改以下文件中的 `data_dir` 变量：
- `src/fetch_multi_period_data.py`
- `src/token_filter_multi_period.py`

### Q4: 旧数据文件会自动删除吗？

**A**: 不会。需要手动清理或使用 `./run.sh clean-data` 命令。

### Q5: 数据文件太多了怎么办？

**A**: 使用清理命令：
```bash
# 保留最新3个
./run.sh clean-data

# 或手动删除指定日期的文件
rm data/*_20251001_*.xlsx
```

## 📊 数据流程图

```
数据获取 (fetch)
    ↓
data/binance_top{N}_multi_period_*.xlsx
    ↓
数据筛选 (filter)
    ↓
data/qualified_tokens_multi_period_*.xlsx
    ↓
Web展示 (web/web-auto)
    ↓
浏览器查看结果
```

## 🔗 相关文档

- [TopN配置指南](CONFIG_TOPN.md)
- [Flask自动化服务](README_FLASK_AUTO.md)
- [项目结构](../PROJECT_STRUCTURE.md)

---

更新时间：2025-10-04

