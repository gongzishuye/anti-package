#!/usr/bin/env python3
"""
SQLite数据库管理器
用于管理监控表(monitor)和报警表(alert)
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite数据库管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，默认为 src/database/trading_monitor.db
        """
        if db_path is None:
            # 默认路径：项目根目录下的 src/database/trading_monitor.db
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'trading_monitor.db')
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化数据库，创建表结构"""
        logger.info(f"初始化数据库: {self.db_path}")
        
        # 连接数据库
        self.connect()
        
        # 创建 monitor 表
        self._create_monitor_table()
        
        # 添加 source 字段（如果不存在）
        self._add_monitor_source_column()
        
        # 创建 alert 表
        self._create_alert_table()
        
        # 提交并关闭
        self.commit()
        self.close()
        
        logger.info("数据库初始化完成")
    
    def _create_monitor_table(self):
        """创建监控表 (monitor)"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS monitor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange TEXT NOT NULL,
            date DATE NOT NULL,
            interval TEXT NOT NULL,
            ticker TEXT NOT NULL,
            high REAL,
            low REAL,
            current_price REAL,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(exchange, date, interval, ticker)
        )
        """
        
        self.cursor.execute(create_table_sql)
        
        # 创建索引以提高查询性能
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_monitor_ticker 
            ON monitor(ticker)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_monitor_exchange 
            ON monitor(exchange)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_monitor_date 
            ON monitor(date)
        """)
        
        logger.info("Monitor 表创建成功")
    
    def _add_monitor_source_column(self):
        """添加source字段到monitor表（如果不存在）"""
        try:
            # 检查source字段是否存在
            self.cursor.execute("PRAGMA table_info(monitor)")
            columns = [row[1] for row in self.cursor.fetchall()]
            
            if 'source' not in columns:
                # 添加source字段，默认值为'auto'
                self.cursor.execute("""
                    ALTER TABLE monitor 
                    ADD COLUMN source TEXT DEFAULT 'auto'
                """)
                logger.info("Monitor表添加source字段成功")
            else:
                logger.debug("Monitor表source字段已存在")
        except Exception as e:
            logger.error(f"添加source字段失败: {e}")
    
    def _create_alert_table(self):
        """创建报警表 (alert)"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange TEXT NOT NULL,
            date DATE NOT NULL,
            interval TEXT NOT NULL,
            ticker TEXT NOT NULL,
            high REAL,
            low REAL,
            current_price REAL,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            trigger_signal TEXT NOT NULL
        )
        """
        
        self.cursor.execute(create_table_sql)
        
        # 创建索引
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_ticker 
            ON alert(ticker)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_exchange 
            ON alert(exchange)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_date 
            ON alert(date)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_signal 
            ON alert(trigger_signal)
        """)
        
        logger.info("Alert 表创建成功")
    
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # 增加超时时间，避免并发时锁等待
            check_same_thread=False  # 允许跨线程使用连接（每个线程有独立连接）
        )
        self.conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        self.cursor = self.conn.cursor()
        # 设置WAL模式，提高并发性能
        self.cursor.execute("PRAGMA journal_mode=WAL")
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def commit(self):
        """提交事务"""
        if self.conn:
            self.conn.commit()
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if exc_type is None:
            self.commit()
        self.close()
    
    # ==================== Monitor 表操作 ====================
    
    def add_monitor(self, exchange: str, date: str, interval: str, ticker: str,
                   high: float = None, low: float = None, current_price: float = None,
                   source: str = 'auto') -> int:
        """
        添加监控记录（如果已存在则更新）
        
        Args:
            exchange: 交易所名称 (如: 'binance', 'okx')
            date: 产生日期 (格式: 'YYYY-MM-DD')
            interval: 时间粒度 (如: '1D', '3D', '1W')
            ticker: ticker名称 (如: 'BTCUSDT')
            high: 最高价
            low: 最低价
            current_price: 当前价
            source: 数据来源 ('auto' 自动导入 / 'manual' 人工导入，默认'auto')
            
        Returns:
            记录ID
        """
        sql = """
        INSERT INTO monitor (exchange, date, interval, ticker, high, low, current_price, update_time, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(exchange, date, interval, ticker) 
        DO UPDATE SET 
            high = excluded.high,
            low = excluded.low,
            current_price = excluded.current_price,
            update_time = excluded.update_time,
            source = excluded.source
        """
        
        update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.cursor.execute(sql, (exchange, date, interval, ticker, high, low, current_price, update_time, source))
        self.commit()
        
        logger.info(f"添加/更新监控: {exchange} {ticker} {interval} (source={source})")
        return self.cursor.lastrowid
    
    def get_monitor(self, ticker: str = None, exchange: str = None, 
                   interval: str = None, date: str = None) -> List[Dict]:
        """
        查询监控记录
        
        Args:
            ticker: ticker名称（可选）
            exchange: 交易所名称（可选）
            interval: 时间粒度（可选）
            date: 日期（可选）
            
        Returns:
            监控记录列表
        """
        sql = "SELECT * FROM monitor WHERE 1=1"
        params = []
        
        if ticker:
            sql += " AND ticker = ?"
            params.append(ticker)
        
        if exchange:
            sql += " AND exchange = ?"
            params.append(exchange)
        
        if interval:
            sql += " AND interval = ?"
            params.append(interval)
        
        if date:
            sql += " AND date = ?"
            params.append(date)
        
        sql += " ORDER BY update_time DESC"
        
        self.cursor.execute(sql, params)
        rows = self.cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_all_monitors(self) -> List[Dict]:
        """获取所有监控记录"""
        self.cursor.execute("SELECT * FROM monitor ORDER BY update_time DESC")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def _parse_interval_to_days(self, interval: str) -> int:
        """
        将interval字符串转换为天数
        
        Args:
            interval: 时间周期字符串，如'1D', '3D', '1W'
            
        Returns:
            对应的天数
        """
        interval = interval.upper().strip()
        
        # 周期映射
        interval_map = {
            '1D': 1,
            '2D': 2,
            '3D': 3,
            '5D': 5,
            '1W': 7,
            '4H': 1,  # 4小时周期按1天计算
            '1H': 1   # 1小时周期按1天计算
        }
        
        return interval_map.get(interval, 1)  # 默认1天
    
    def delete_expired_monitors(self, expire_multiplier: int = 4) -> int:
        """
        删除过期的监控记录
        
        过期逻辑：date + interval * expire_multiplier < 当前日期
        例如：date=2025-10-01, interval=3D, expire_multiplier=4
              过期日期 = 2025-10-01 + 3*4 = 2025-10-13
              如果今天 >= 2025-10-13，则删除该记录
        
        Args:
            expire_multiplier: 过期乘数，默认为4
            
        Returns:
            删除的记录数
        """
        from datetime import datetime, timedelta
        
        # 获取所有监控记录
        self.cursor.execute("SELECT id, date, interval FROM monitor")
        rows = self.cursor.fetchall()
        
        today = datetime.now().date()
        expired_ids = []
        
        for row in rows:
            record_id = row['id']
            record_date_str = row['date']
            record_interval = row['interval']
            
            # 解析日期
            try:
                record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"无法解析日期: {record_date_str}, 跳过记录 ID={record_id}")
                continue
            
            # 计算interval对应的天数
            interval_days = self._parse_interval_to_days(record_interval)
            
            # 计算过期日期
            expire_date = record_date + timedelta(days=interval_days * expire_multiplier)
            
            # 判断是否过期
            if today >= expire_date:
                expired_ids.append(record_id)
                logger.info(f"记录过期: ID={record_id}, date={record_date}, "
                          f"interval={record_interval}, expire_date={expire_date}")
        
        # 批量删除过期记录
        if expired_ids:
            placeholders = ','.join('?' * len(expired_ids))
            delete_sql = f"DELETE FROM monitor WHERE id IN ({placeholders})"
            self.cursor.execute(delete_sql, expired_ids)
            self.commit()
            
            logger.info(f"✓ 删除了 {len(expired_ids)} 条过期记录")
            return len(expired_ids)
        else:
            logger.info("✓ 没有过期记录需要删除")
            return 0
    
    def get_expired_monitors_info(self, expire_multiplier: int = 4) -> List[Dict]:
        """
        获取即将过期的监控记录信息（用于预览）
        
        Args:
            expire_multiplier: 过期乘数，默认为4
            
        Returns:
            过期记录的详细信息列表
        """
        from datetime import datetime, timedelta
        
        # 获取所有监控记录
        self.cursor.execute("SELECT * FROM monitor")
        rows = self.cursor.fetchall()
        
        today = datetime.now().date()
        expired_records = []
        
        for row in rows:
            record = dict(row)
            record_date_str = record['date']
            record_interval = record['interval']
            
            # 解析日期
            try:
                record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
            except ValueError:
                continue
            
            # 计算interval对应的天数
            interval_days = self._parse_interval_to_days(record_interval)
            
            # 计算过期日期
            expire_date = record_date + timedelta(days=interval_days * expire_multiplier)
            
            # 计算剩余天数
            days_left = (expire_date - today).days
            
            # 判断是否过期或即将过期
            if today >= expire_date:
                record['expire_date'] = expire_date.strftime('%Y-%m-%d')
                record['days_left'] = days_left
                record['status'] = '已过期'
                expired_records.append(record)
        
        return expired_records
    
    def delete_monitor(self, ticker: str, exchange: str, interval: str, date: str) -> bool:
        """
        删除监控记录
        
        Args:
            ticker: ticker名称
            exchange: 交易所名称
            interval: 时间粒度
            date: 日期
            
        Returns:
            是否删除成功
        """
        sql = """
        DELETE FROM monitor 
        WHERE ticker = ? AND exchange = ? AND interval = ? AND date = ?
        """
        
        self.cursor.execute(sql, (ticker, exchange, interval, date))
        self.commit()
        
        deleted = self.cursor.rowcount > 0
        if deleted:
            logger.info(f"删除监控: {exchange} {ticker} {interval} {date}")
        
        return deleted
    
    def update_monitor_price(self, ticker: str, exchange: str, interval: str, date: str,
                            high: float = None, low: float = None, current_price: float = None) -> bool:
        """
        更新监控记录的价格信息
        
        Args:
            ticker: ticker名称
            exchange: 交易所名称
            interval: 时间粒度
            date: 日期
            high: 最高价（可选）
            low: 最低价（可选）
            current_price: 当前价（可选）
            
        Returns:
            是否更新成功
        """
        updates = []
        params = []
        
        if high is not None:
            updates.append("high = ?")
            params.append(high)
        
        if low is not None:
            updates.append("low = ?")
            params.append(low)
        
        if current_price is not None:
            updates.append("current_price = ?")
            params.append(current_price)
        
        if not updates:
            return False
        
        updates.append("update_time = ?")
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        sql = f"""
        UPDATE monitor 
        SET {', '.join(updates)}
        WHERE ticker = ? AND exchange = ? AND interval = ? AND date = ?
        """
        
        params.extend([ticker, exchange, interval, date])
        
        self.cursor.execute(sql, params)
        self.commit()
        
        updated = self.cursor.rowcount > 0
        if updated:
            logger.info(f"更新监控价格: {exchange} {ticker} {interval}")
        
        return updated
    
    # ==================== Alert 表操作 ====================
    
    def add_alert(self, exchange: str, date: str, interval: str, ticker: str,
                 trigger_signal: str, high: float = None, low: float = None, 
                 current_price: float = None) -> int:
        """
        添加报警记录
        
        Args:
            exchange: 交易所名称
            date: 产生日期
            interval: 时间粒度
            ticker: ticker名称
            trigger_signal: 触发信号（如: '突破阻力位', '跌破支撑位'）
            high: 最高价
            low: 最低价
            current_price: 当前价
            
        Returns:
            记录ID
        """
        sql = """
        INSERT INTO alert (exchange, date, interval, ticker, high, low, current_price, update_time, trigger_signal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.cursor.execute(sql, (exchange, date, interval, ticker, high, low, 
                                 current_price, update_time, trigger_signal))
        self.commit()
        
        logger.info(f"添加报警: {exchange} {ticker} - {trigger_signal}")
        return self.cursor.lastrowid
    
    def get_alerts(self, ticker: str = None, exchange: str = None, 
                  interval: str = None, date: str = None, 
                  trigger_signal: str = None, limit: int = None) -> List[Dict]:
        """
        查询报警记录
        
        Args:
            ticker: ticker名称（可选）
            exchange: 交易所名称（可选）
            interval: 时间粒度（可选）
            date: 日期（可选）
            trigger_signal: 触发信号（可选）
            limit: 返回记录数限制（可选）
            
        Returns:
            报警记录列表
        """
        sql = "SELECT * FROM alert WHERE 1=1"
        params = []
        
        if ticker:
            sql += " AND ticker = ?"
            params.append(ticker)
        
        if exchange:
            sql += " AND exchange = ?"
            params.append(exchange)
        
        if interval:
            sql += " AND interval = ?"
            params.append(interval)
        
        if date:
            sql += " AND date = ?"
            params.append(date)
        
        if trigger_signal:
            sql += " AND trigger_signal = ?"
            params.append(trigger_signal)
        
        sql += " ORDER BY update_time DESC"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        self.cursor.execute(sql, params)
        rows = self.cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_all_alerts(self, limit: int = None) -> List[Dict]:
        """
        获取所有报警记录
        
        Args:
            limit: 返回记录数限制（可选）
            
        Returns:
            报警记录列表
        """
        sql = "SELECT * FROM alert ORDER BY update_time DESC"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def delete_alert(self, alert_id: int) -> bool:
        """
        删除报警记录
        
        Args:
            alert_id: 报警记录ID
            
        Returns:
            是否删除成功
        """
        sql = "DELETE FROM alert WHERE id = ?"
        
        self.cursor.execute(sql, (alert_id,))
        self.commit()
        
        deleted = self.cursor.rowcount > 0
        if deleted:
            logger.info(f"删除报警记录: ID={alert_id}")
        
        return deleted
    
    def clear_old_alerts(self, days: int = 30) -> int:
        """
        清理指定天数之前的报警记录
        
        Args:
            days: 保留最近多少天的记录
            
        Returns:
            删除的记录数
        """
        sql = """
        DELETE FROM alert 
        WHERE date < date('now', ?)
        """
        
        self.cursor.execute(sql, (f'-{days} days',))
        self.commit()
        
        deleted_count = self.cursor.rowcount
        logger.info(f"清理旧报警记录: 删除了 {deleted_count} 条")
        
        return deleted_count
    
    # ==================== 统计查询 ====================
    
    def get_monitor_stats(self) -> Dict:
        """获取监控表统计信息"""
        stats = {}
        
        # 总记录数
        self.cursor.execute("SELECT COUNT(*) as count FROM monitor")
        stats['total_monitors'] = self.cursor.fetchone()['count']
        
        # 按交易所统计
        self.cursor.execute("""
            SELECT exchange, COUNT(*) as count 
            FROM monitor 
            GROUP BY exchange
        """)
        stats['by_exchange'] = {row['exchange']: row['count'] for row in self.cursor.fetchall()}
        
        # 按时间粒度统计
        self.cursor.execute("""
            SELECT interval, COUNT(*) as count 
            FROM monitor 
            GROUP BY interval
        """)
        stats['by_interval'] = {row['interval']: row['count'] for row in self.cursor.fetchall()}
        
        return stats
    
    def get_alert_stats(self) -> Dict:
        """获取报警表统计信息"""
        stats = {}
        
        # 总记录数
        self.cursor.execute("SELECT COUNT(*) as count FROM alert")
        stats['total_alerts'] = self.cursor.fetchone()['count']
        
        # 按交易所统计
        self.cursor.execute("""
            SELECT exchange, COUNT(*) as count 
            FROM alert 
            GROUP BY exchange
        """)
        stats['by_exchange'] = {row['exchange']: row['count'] for row in self.cursor.fetchall()}
        
        # 按触发信号统计
        self.cursor.execute("""
            SELECT trigger_signal, COUNT(*) as count 
            FROM alert 
            GROUP BY trigger_signal
            ORDER BY count DESC
        """)
        stats['by_signal'] = {row['trigger_signal']: row['count'] for row in self.cursor.fetchall()}
        
        # 今日报警数
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM alert 
            WHERE date = date('now')
        """)
        stats['today_alerts'] = self.cursor.fetchone()['count']
        
        return stats


def main():
    """示例用法"""
    print("=" * 70)
    print("SQLite 数据库管理器 - 示例")
    print("=" * 70)
    
    # 创建数据库管理器
    db = DatabaseManager()
    
    with db:
        # ========== Monitor 表操作示例 ==========
        print("\n【Monitor 表操作】")
        print("-" * 70)
        
        # 添加监控记录
        print("\n1. 添加监控记录:")
        db.add_monitor(
            exchange='binance',
            date='2025-10-12',
            interval='1D',
            ticker='BTCUSDT',
            high=112125.51,
            low=109565.06,
            current_price=111708.43
        )
        
        db.add_monitor(
            exchange='binance',
            date='2025-10-12',
            interval='1D',
            ticker='ETHUSDT',
            high=3500.00,
            low=3300.00,
            current_price=3450.00
        )
        
        db.add_monitor(
            exchange='okx',
            date='2025-10-12',
            interval='4H',
            ticker='BTCUSDT',
            high=111900.00,
            low=110500.00,
            current_price=111700.00
        )
        
        # 查询监控记录
        print("\n2. 查询所有监控记录:")
        monitors = db.get_all_monitors()
        for m in monitors:
            print(f"   {m['exchange']:10} {m['ticker']:10} {m['interval']:5} "
                  f"价格: ${m['current_price']:,.2f} (H: ${m['high']:,.2f}, L: ${m['low']:,.2f})")
        
        # 按条件查询
        print("\n3. 查询 Binance 的 BTCUSDT:")
        btc_monitors = db.get_monitor(ticker='BTCUSDT', exchange='binance')
        for m in btc_monitors:
            print(f"   {m['date']} {m['interval']} - ${m['current_price']:,.2f}")
        
        # 更新价格
        print("\n4. 更新价格:")
        db.update_monitor_price(
            ticker='BTCUSDT',
            exchange='binance',
            interval='1D',
            date='2025-10-12',
            current_price=111800.00
        )
        print("   价格已更新")
        
        # ========== Alert 表操作示例 ==========
        print("\n\n【Alert 表操作】")
        print("-" * 70)
        
        # 添加报警记录
        print("\n1. 添加报警记录:")
        db.add_alert(
            exchange='binance',
            date='2025-10-12',
            interval='1D',
            ticker='BTCUSDT',
            trigger_signal='突破阻力位',
            high=112125.51,
            low=109565.06,
            current_price=112200.00
        )
        
        db.add_alert(
            exchange='binance',
            date='2025-10-12',
            interval='1D',
            ticker='ETHUSDT',
            trigger_signal='跌破支撑位',
            high=3500.00,
            low=3250.00,
            current_price=3240.00
        )
        
        db.add_alert(
            exchange='okx',
            date='2025-10-12',
            interval='4H',
            ticker='BTCUSDT',
            trigger_signal='价格异动',
            high=112500.00,
            low=111000.00,
            current_price=112450.00
        )
        
        # 查询报警记录
        print("\n2. 查询最近10条报警:")
        alerts = db.get_all_alerts(limit=10)
        for a in alerts:
            print(f"   [{a['update_time']}] {a['exchange']:10} {a['ticker']:10} - {a['trigger_signal']}")
        
        # 按条件查询
        print("\n3. 查询 BTCUSDT 的报警:")
        btc_alerts = db.get_alerts(ticker='BTCUSDT')
        for a in btc_alerts:
            print(f"   {a['date']} {a['interval']} - {a['trigger_signal']} (价格: ${a['current_price']:,.2f})")
        
        # ========== 统计信息 ==========
        print("\n\n【统计信息】")
        print("-" * 70)
        
        monitor_stats = db.get_monitor_stats()
        print(f"\nMonitor 统计:")
        print(f"  总记录数: {monitor_stats['total_monitors']}")
        print(f"  按交易所: {monitor_stats['by_exchange']}")
        print(f"  按时间粒度: {monitor_stats['by_interval']}")
        
        alert_stats = db.get_alert_stats()
        print(f"\nAlert 统计:")
        print(f"  总记录数: {alert_stats['total_alerts']}")
        print(f"  今日报警: {alert_stats['today_alerts']}")
        print(f"  按交易所: {alert_stats['by_exchange']}")
        print(f"  按触发信号: {alert_stats['by_signal']}")
    
    print("\n" + "=" * 70)
    print(f"✅ 数据库文件位置: {db.db_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
