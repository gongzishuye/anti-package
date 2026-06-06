#!/usr/bin/env python3
"""
数据库查看工具
提供命令行界面查看和管理数据库
"""

import argparse
from db_manager import DatabaseManager
from datetime import datetime


def view_monitors(db: DatabaseManager, exchange: str = None):
    """查看监控记录（详细模式）"""
    print("\n" + "=" * 120)
    print("📊 监控标的列表（详细信息）")
    print("=" * 120)
    
    with db:
        monitors = db.get_all_monitors()
    
    # 如果指定了exchange，手动过滤
    if exchange:
        monitors = [m for m in monitors if m.get('exchange') == exchange]
    
    if not monitors:
        print("⚠️  暂无监控记录")
        print("\n提示: 运行以下命令导入数据:")
        print("  python3 src/alert/excel_to_db_sync.py --exchange bn_futures")
        return
    
    print(f"\n找到 {len(monitors)} 条监控记录\n")
    
    # 详细显示每条记录
    for i, m in enumerate(monitors, 1):
        current_price = m.get('current_price', 0) or 0
        high = m['high']
        low = m['low']
        
        # 计算价格区间
        price_range = high - low
        
        # 计算斐波那契回撤位
        fib_levels = {}
        if price_range > 0:
            fib_levels = {
                '50.0%': high - price_range * 0.5,
                '61.8%': high - price_range * 0.618,
                '78.6%': high - price_range * 0.786,
                '88.6%': high - price_range * 0.886
            }
        
        # 计算当前价格位置（如果有当前价）
        current_position = ""
        if current_price > 0 and price_range > 0:
            pct_from_high = ((high - current_price) / price_range) * 100
            current_position = f"{pct_from_high:.1f}%"
        
        # 计算过期日期
        from datetime import datetime, timedelta
        try:
            record_date = datetime.strptime(m['date'], '%Y-%m-%d').date()
            interval_days = db._parse_interval_to_days(m['interval'])
            expire_date = record_date + timedelta(days=interval_days * 4)
            today = datetime.now().date()
            days_left = (expire_date - today).days
            
            if days_left >= 0:
                expire_info = f"{expire_date} (还剩{days_left}天)"
            else:
                expire_info = f"{expire_date} (已过期{-days_left}天)"
        except Exception:
            expire_info = "N/A"
        
        print("━" * 120)
        print(f"📌 记录 #{i}")
        print("━" * 120)
        
        # 基本信息
        print(f"{'ID':<15}: {m['id']}")
        print(f"{'交易对':<15}: {m['ticker']}")
        print(f"{'交易所':<15}: {m['exchange']}")
        print(f"{'时间周期':<15}: {m['interval']}")
        print(f"{'监控日期':<15}: {m['date']}")
        print(f"{'数据来源':<15}: {m.get('source', 'auto')} {'(人工导入)' if m.get('source') == 'manual' else '(自动导入)'}")
        print(f"{'过期日期':<15}: {expire_info}")
        print(f"{'更新时间':<15}: {m.get('update_time', 'N/A')}")
        
        print()
        
        # 价格信息
        print("💰 价格信息:")
        print(f"  最高价: ${high:,.6f}")
        print(f"  最低价: ${low:,.6f}")
        print(f"  价格区间: ${price_range:,.6f}")
        if current_price > 0:
            print(f"  当前价: ${current_price:,.6f}")
            if current_position:
                print(f"  当前位置: 从最高价回撤 {current_position}")
        else:
            print(f"  当前价: 未更新")
        
        print()
        
        # 斐波那契回撤位
        if fib_levels:
            print("🎯 斐波那契回撤位:")
            for level, price in sorted(fib_levels.items(), key=lambda x: x[1], reverse=True):
                # 检查是否已触发
                triggered = ""
                if current_price > 0 and current_price <= price:
                    triggered = " ✅ 已触发"
                print(f"  {level:<8} → ${price:,.6f}{triggered}")
        
        print()
    
    # 汇总统计
    print("=" * 120)
    print("📈 汇总统计")
    print("=" * 120)
    print(f"总计: {len(monitors)} 个监控标的\n")
    
    # 按交易所统计
    exchange_counts = {}
    for m in monitors:
        ex = m.get('exchange', 'unknown')
        exchange_counts[ex] = exchange_counts.get(ex, 0) + 1
    print("按交易所:")
    for ex, count in sorted(exchange_counts.items()):
        print(f"  • {ex}: {count} 个")
    
    print()
    
    # 按周期统计
    interval_counts = {}
    for m in monitors:
        iv = m.get('interval', 'unknown')
        interval_counts[iv] = interval_counts.get(iv, 0) + 1
    print("按时间周期:")
    for iv, count in sorted(interval_counts.items()):
        print(f"  • {iv}: {count} 个")
    
    print()
    
    # 按日期统计
    date_counts = {}
    for m in monitors:
        dt = m.get('date', 'unknown')
        date_counts[dt] = date_counts.get(dt, 0) + 1
    print("按监控日期:")
    for dt, count in sorted(date_counts.items(), reverse=True):
        print(f"  • {dt}: {count} 个")
    
    print("=" * 120)


def view_alerts(db: DatabaseManager, ticker: str = None, 
                exchange: str = None, hours: int = None, limit: int = 50):
    """查看报警记录"""
    print("\n" + "=" * 120)
    print("📋 报警记录列表")
    print("=" * 120)
    
    with db:
        # 查询报警记录
        if hours:
            from datetime import datetime, timedelta
            cutoff_time = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            # 使用SQL直接查询最近N小时的记录
            sql = "SELECT * FROM alert WHERE update_time >= ? ORDER BY update_time DESC"
            if limit:
                sql += f" LIMIT {limit}"
            db.cursor.execute(sql, (cutoff_time,))
            alerts = [dict(row) for row in db.cursor.fetchall()]
        else:
            alerts = db.get_alerts(ticker=ticker, exchange=exchange, limit=limit)
    
    if not alerts:
        print("⚠️  暂无报警记录")
        return
    
    print(f"\n找到 {len(alerts)} 条报警记录\n")
    
    # 显示报警记录
    for i, alert in enumerate(alerts, 1):
        print("━" * 120)
        print(f"🔔 报警 #{i}")
        print("━" * 120)
        print(f"{'ID':<15}: {alert['id']}")
        print(f"{'时间':<15}: {alert['update_time']}")
        print(f"{'交易对':<15}: {alert['ticker']}")
        print(f"{'交易所':<15}: {alert['exchange']}")
        print(f"{'周期':<15}: {alert['interval']}")
        print(f"{'触发信号':<15}: {alert['trigger_signal']}")
        print(f"{'最高价':<15}: ${alert.get('high', 0):,.6f}")
        print(f"{'最低价':<15}: ${alert.get('low', 0):,.6f}")
        print(f"{'当前价':<15}: ${alert.get('current_price', 0):,.6f}")
        print()
    
    print("=" * 120)


def view_stats(db: DatabaseManager):
    """查看统计信息"""
    print("\n" + "=" * 80)
    print("数据库统计信息")
    print("=" * 80)
    
    # 监控统计
    with db:
        monitors = db.get_all_monitors()
    
    if monitors:
        print("\n【监控统计】")
        print(f"  总监控数: {len(monitors)}")
        
        # 按交易所统计
        exchange_counts = {}
        for m in monitors:
            ex = m.get('exchange', 'unknown')
            exchange_counts[ex] = exchange_counts.get(ex, 0) + 1
        print(f"  按交易所:")
        for exchange, count in exchange_counts.items():
            print(f"    - {exchange}: {count}")
        
        # 按时间粒度统计
        interval_counts = {}
        for m in monitors:
            iv = m.get('interval', 'unknown')
            interval_counts[iv] = interval_counts.get(iv, 0) + 1
        print(f"  按时间粒度:")
        for interval, count in interval_counts.items():
            print(f"    - {interval}: {count}")
        
        # 按日期统计
        date_counts = {}
        for m in monitors:
            dt = m.get('date', 'unknown')
            date_counts[dt] = date_counts.get(dt, 0) + 1
        print(f"  按日期:")
        for date, count in sorted(date_counts.items(), reverse=True)[:5]:
            print(f"    - {date}: {count}")
    else:
        print("\n【监控统计】")
        print("  暂无监控记录")
    
    # 报警统计
    with db:
        alerts = db.get_all_alerts()
    
    if alerts:
        print("\n【报警统计】")
        print(f"  总报警数: {len(alerts)}")
        
        # 按交易所统计
        exchange_counts = {}
        for a in alerts:
            ex = a.get('exchange', 'unknown')
            exchange_counts[ex] = exchange_counts.get(ex, 0) + 1
        print(f"  按交易所:")
        for exchange, count in exchange_counts.items():
            print(f"    - {exchange}: {count}")
        
        # 按触发信号统计
        signal_counts = {}
        for a in alerts:
            signal = a.get('trigger_signal', 'unknown')
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        print(f"  按触发信号:")
        for signal, count in sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    - {signal}: {count}")
    else:
        print("\n【报警统计】")
        print("  暂无报警记录")


def delete_monitor(db: DatabaseManager, ticker: str, exchange: str, interval: str):
    """删除监控记录"""
    with db:
        # 手动删除（使用SQL）
        db.cursor.execute(
            "DELETE FROM monitor WHERE ticker=? AND exchange=? AND interval=?",
            (ticker, exchange, interval)
        )
        deleted = db.cursor.rowcount
        db.commit()
    
    if deleted > 0:
        print(f"✅ 已删除监控: {exchange} {ticker} {interval}")
        return True
    else:
        print(f"❌ 未找到监控记录: {exchange} {ticker} {interval}")
        return False


def clean_old_alerts(db: DatabaseManager, days: int):
    """清理旧报警记录"""
    print(f"⚠️  报警清理功能待实现（计划清理 {days} 天前的记录）")


def main():
    parser = argparse.ArgumentParser(description='数据库查看和管理工具')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # monitors - 查看监控
    monitor_parser = subparsers.add_parser('monitors', help='查看监控记录')
    monitor_parser.add_argument('--exchange', '-e', help='过滤交易所')
    
    # alerts - 查看报警
    alert_parser = subparsers.add_parser('alerts', help='查看报警记录')
    alert_parser.add_argument('--ticker', '-t', help='过滤ticker')
    alert_parser.add_argument('--exchange', '-e', help='过滤交易所')
    alert_parser.add_argument('--hours', type=int, help='最近N小时')
    alert_parser.add_argument('--limit', '-l', type=int, default=50, help='限制返回数量')
    
    # stats - 查看统计
    subparsers.add_parser('stats', help='查看统计信息')
    
    # delete - 删除监控
    delete_parser = subparsers.add_parser('delete', help='删除监控记录')
    delete_parser.add_argument('ticker', help='Ticker名称')
    delete_parser.add_argument('exchange', help='交易所名称')
    delete_parser.add_argument('interval', help='时间粒度（1D/3D/1W）')
    
    # clean - 清理旧报警
    clean_parser = subparsers.add_parser('clean', help='清理旧报警记录')
    clean_parser.add_argument('--days', '-d', type=int, default=30, 
                            help='清理N天前的记录（默认30天）')
    
    args = parser.parse_args()
    
    # 创建数据库管理器
    db = DatabaseManager()
    
    if args.command == 'monitors':
        view_monitors(db, exchange=args.exchange)
    
    elif args.command == 'alerts':
        view_alerts(db, ticker=args.ticker, exchange=args.exchange, 
                   hours=args.hours, limit=args.limit)
    
    elif args.command == 'stats':
        view_stats(db)
    
    elif args.command == 'delete':
        delete_monitor(db, args.ticker, args.exchange, args.interval)
    
    elif args.command == 'clean':
        clean_old_alerts(db, args.days)
    
    else:
        # 默认显示统计信息
        view_stats(db)
        print("\n提示: 使用 --help 查看所有可用命令")


if __name__ == "__main__":
    main()

