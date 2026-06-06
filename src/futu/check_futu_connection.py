#!/usr/bin/env python3
"""
FutuOpenD 连接检测工具
用于诊断 FutuOpenD 连接问题
"""

import socket
import sys
import os


def check_port_open(host='127.0.0.1', port=11111, timeout=3):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"检查端口时出错: {e}")
        return False


def check_futu_api_installed():
    """检查 futu-api 是否已安装"""
    try:
        import futu
        version = getattr(futu, '__version__', '未知版本')
        return True, version
    except ImportError:
        return False, None


def test_futu_connection(host='127.0.0.1', port=11111):
    """测试 FutuOpenD 连接"""
    try:
        from futu import OpenQuoteContext, RET_OK
        
        quote_ctx = OpenQuoteContext(host=host, port=port)
        
        # 尝试获取一个简单的数据来验证连接
        ret, data = quote_ctx.get_market_state(['US.AAPL'])
        quote_ctx.close()
        
        if ret == RET_OK:
            return True, "连接成功"
        else:
            return False, f"API调用失败: {data}"
            
    except Exception as e:
        return False, str(e)


def print_diagnostics():
    """打印诊断信息"""
    print("="*70)
    print("FutuOpenD 连接诊断工具")
    print("="*70)
    print()
    
    # 1. 检查 futu-api 安装
    print("【1】检查 futu-api 包安装...")
    installed, version = check_futu_api_installed()
    if installed:
        print(f"  ✓ futu-api 已安装 (版本: {version})")
    else:
        print("  ✗ futu-api 未安装")
        print("  ► 解决方法: pip install futu-api")
        print()
        return
    
    print()
    
    # 2. 检查端口
    print("【2】检查 FutuOpenD 端口 (127.0.0.1:11111)...")
    port_open = check_port_open()
    if port_open:
        print("  ✓ 端口 11111 正在监听")
    else:
        print("  ✗ 端口 11111 未监听")
        print()
        print("  原因: FutuOpenD 客户端未启动")
        print()
        print("  解决方法:")
        print("  1. 下载 FutuOpenD: https://www.futunn.com/download/OpenAPI")
        print("  2. 安装并启动 FutuOpenD")
        print("  3. 登录你的富途账号")
        print("  4. 确保看到绿色的连接状态")
        print()
        print("  详细安装说明请查看: INSTALL_FUTU.md")
        print()
        return
    
    print()
    
    # 3. 测试 API 连接
    print("【3】测试 FutuOpenD API 连接...")
    success, message = test_futu_connection()
    if success:
        print(f"  ✓ {message}")
        print()
        print("="*70)
        print("✓ 所有检查通过！可以正常使用 Futu API")
        print("="*70)
        print()
        print("现在可以运行:")
        print("  python3 futu_us_stock_fetcher.py")
        print()
    else:
        print(f"  ✗ 连接失败: {message}")
        print()
        print("  可能的原因:")
        print("  1. FutuOpenD 未登录账号")
        print("  2. 防火墙阻止连接")
        print("  3. FutuOpenD 配置错误")
        print()
        print("  解决方法:")
        print("  1. 打开 FutuOpenD 客户端窗口")
        print("  2. 点击登录按钮，输入账号密码")
        print("  3. 等待连接状态变为绿色")
        print("  4. 重新运行此检测脚本")
        print()


def main():
    """主函数"""
    try:
        print_diagnostics()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


