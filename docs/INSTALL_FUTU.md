# FutuOpenD 安装和配置指南

## 问题：ECONNREFUSED 错误

如果你看到这个错误：
```
ECONNREFUSED: Connect fail: conn_id=1
```

说明 **FutuOpenD 客户端没有启动**。必须先启动 FutuOpenD 才能使用 API。

---

## 📥 第一步：下载 FutuOpenD

### 官方下载地址
- **主页**: https://www.futunn.com/download/OpenAPI
- **直接下载**: https://www.futunn.com/download/openAPI

### 根据你的操作系统选择：

#### Linux (Ubuntu/Debian)
```bash
# 64位
wget https://softwarefile.futunn.com/FutuOpenD_Latest_Linux.tar.gz

# 解压
tar -xzf FutuOpenD_Latest_Linux.tar.gz

# 进入目录
cd FutuOpenD
```

#### macOS
```bash
# 下载 .dmg 文件
curl -O https://softwarefile.futunn.com/FutuOpenD_Latest_MacOS.dmg

# 打开安装
open FutuOpenD_Latest_MacOS.dmg
```

#### Windows
- 下载 `.exe` 安装程序
- 运行安装程序
- 下载地址: https://softwarefile.futunn.com/FutuOpenD_Latest_Windows.exe

---

## 🚀 第二步：启动 FutuOpenD

### Linux
```bash
# 进入FutuOpenD目录
cd FutuOpenD

# 给予执行权限
chmod +x FutuOpenD

# 启动（前台运行）
./FutuOpenD

# 或后台运行
nohup ./FutuOpenD > futu.log 2>&1 &
```

### macOS
```bash
# 从应用程序启动
open /Applications/FutuOpenD.app

# 或使用命令行
/Applications/FutuOpenD.app/Contents/MacOS/FutuOpenD
```

### Windows
- 双击桌面图标启动
- 或从开始菜单找到 "FutuOpenD" 启动

---

## ✅ 第三步：验证启动成功

### 方法1：检查端口
```bash
# Linux/macOS
netstat -tuln | grep 11111
# 或
lsof -i :11111

# 应该看到类似输出：
# tcp  0  0  127.0.0.1:11111  0.0.0.0:*  LISTEN
```

### 方法2：查看进程
```bash
# Linux/macOS
ps aux | grep FutuOpenD

# 应该看到 FutuOpenD 进程在运行
```

### 方法3：使用我们的检测脚本
```bash
python3 check_futu_connection.py
```

---

## 🔧 第四步：配置（可选）

### 修改端口（如果11111被占用）

编辑 FutuOpenD 配置文件（通常在安装目录）：

**FutuOpenD.xml** 或 **config.ini**:
```xml
<FutuOpenD>
    <Api>
        <Port>11111</Port>  <!-- 修改此处 -->
    </Api>
</FutuOpenD>
```

如果修改了端口，记得在代码中也要修改：
```python
fetcher = FutuUSStockFetcher(host='127.0.0.1', port=你的端口)
```

---

## 🔐 第五步：登录富途账号

1. 启动 FutuOpenD 后，会打开一个小窗口
2. 点击 "登录" 按钮
3. 输入你的富途账号和密码
4. 登录成功后，图标会变成绿色

**注意**：
- 需要有富途账号（可以免费注册）
- 建议开通美股权限以获取完整数据
- 免费账号有 API 调用次数限制

---

## 🧪 第六步：测试连接

运行测试脚本：
```bash
python3 check_futu_connection.py
```

或运行主程序：
```bash
python3 futu_us_stock_fetcher.py
```

如果看到：
```
✓ 成功连接到FutuOpenD (127.0.0.1:11111)
```

说明一切正常！

---

## ❓ 常见问题

### Q1: 端口11111被占用
**解决方法**：
1. 查看是什么占用：`lsof -i :11111`
2. 停止占用进程或修改 FutuOpenD 端口

### Q2: 防火墙阻止连接
**解决方法**：
```bash
# Linux
sudo ufw allow 11111

# macOS
# 系统偏好设置 -> 安全性与隐私 -> 防火墙 -> 允许 FutuOpenD
```

### Q3: Linux 服务器无图形界面
**解决方法**：
FutuOpenD 需要图形界面来登录。在无图形界面的服务器上：
1. 在本地电脑启动 FutuOpenD
2. 修改 FutuOpenD 配置允许远程连接
3. 在服务器代码中连接到本地电脑的 IP

### Q4: 连接超时
**检查清单**：
- [ ] FutuOpenD 是否在运行
- [ ] 是否已登录账号
- [ ] 端口号是否正确
- [ ] 防火墙是否允许
- [ ] 如果远程连接，IP 是否正确

---

## 📚 相关资源

- **官方文档**: https://openapi.futunn.com/futu-api-doc/
- **下载页面**: https://www.futunn.com/download/OpenAPI
- **API 文档**: https://openapi.futunn.com/futu-api-doc/api/python-api.html
- **常见问题**: https://openapi.futunn.com/futu-api-doc/faq/

---

## 🆘 仍然无法解决？

请检查：
1. ✅ FutuOpenD 进程是否在运行
2. ✅ 端口 11111 是否在监听
3. ✅ 是否已登录富途账号
4. ✅ 防火墙是否允许连接
5. ✅ Python futu-api 包是否正确安装

如果都确认无误，请查看 FutuOpenD 日志文件获取更多错误信息。


