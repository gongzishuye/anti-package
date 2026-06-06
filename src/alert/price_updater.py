#!/usr/bin/env python3
"""
价格更新模块
每隔15分钟循环处理数据库中的所有监控数据，从币安获取最新价格并更新
集成斐波那契回撤检测和企业微信推送
"""

import os
import sys
import logging
import time
from datetime import datetime
from typing import Dict, List, Set, Tuple
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.database.db_manager import DatabaseManager
from src.crypto.binance_data_fetcher import BinanceDataFetcher
from src.alert.wecom_notifier import WeComNotifier
from src.alert.monitor_config import get_monitored_symbols, get_dynamic_symbols

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PriceUpdater:
    """价格更新器 - 定期从交易所获取最新价格并更新数据库"""
    
    # 交易所映射
    EXCHANGE_MAP = {
        'bn': 'spot'  # bn -> Binance现货
    }
    
    # Interval映射 (数据库格式 -> Binance格式)
    INTERVAL_MAP = {
        '15M': '15m', '30M': '30m', '1H': '1h', '2H': '2h',
        '4H': '4h', '6H': '6h', '8H': '8h', '12H': '12h',
        '1D': '1d', '2D': '2d', '3D': '3d', '5D': '5d', '1W': '1w', '1M': '1M'
    }
    
    # 斐波那契回撤位（从高到低）
    FIBONACCI_LEVELS = [0.5, 0.618, 0.786, 0.886]
    
    def __init__(self, wecom_webhook_url: str = None):
        """
        初始化价格更新器
        
        Args:
            wecom_webhook_url: 企业微信webhook地址，如果不提供则从环境变量读取
        """
        self.db = DatabaseManager()
        self.bn_fetcher = BinanceDataFetcher()
        
        # 初始化企业微信通知器
        if wecom_webhook_url is None:
            wecom_webhook_url = os.environ.get('WECOM_WEBHOOK_URL')
        self.notifier = WeComNotifier(wecom_webhook_url) if wecom_webhook_url else None
        
        # 记录已触发的回撤位，避免重复推送
        # 格式: {(ticker, exchange, interval, date): set([0.5, 0.618, ...])}
        self.triggered_levels: Dict[Tuple[str, str, str, str], Set[float]] = {}
    
    def calculate_fibonacci_levels(self, high: float, low: float) -> Dict[float, float]:
        """
        计算斐波那契回撤位价格
        
        Args:
            high: 最高价
            low: 最低价
            
        Returns:
            字典 {回撤比例: 回撤价格}
        """
        if high <= low:
            return {}
        
        range_price = high - low
        levels = {}
        
        for level in self.FIBONACCI_LEVELS:
            # 回撤价格 = 最高价 - (价格区间 × 回撤比例)
            retracement_price = high - (range_price * level)
            levels[level] = retracement_price
        
        return levels
    
    def check_fibonacci_retracement(self, ticker: str, exchange: str, interval: str, date: str,
                                   high: float, low: float, current_price: float) -> List[float]:
        """
        检测当前价格是否触及斐波那契回撤位
        
        Args:
            ticker: 交易对
            exchange: 交易所
            interval: 时间周期
            date: 日期
            high: 最高价
            low: 最低价
            current_price: 当前价格
            
        Returns:
            触发的回撤位列表
        """
        # 计算斐波那契回撤位
        fib_levels = self.calculate_fibonacci_levels(high, low)
        
        if not fib_levels:
            return []
        
        # 获取该监控记录的触发历史
        monitor_key = (ticker, exchange, interval, date)
        if monitor_key not in self.triggered_levels:
            self.triggered_levels[monitor_key] = set()
        
        triggered = []
        
        # 检查是否触及回撤位（从高到低检查）
        for level in sorted(self.FIBONACCI_LEVELS):
            retracement_price = fib_levels[level]
            
            # 如果已经触发过，跳过
            if level in self.triggered_levels[monitor_key]:
                continue
            
            # 检测逻辑：当前价格需要回撤到该位置或更低
            # 同时要确保价格是从高位回撤下来的（current_price < high）
            if current_price <= retracement_price and current_price < high:
                triggered.append(level)
                self.triggered_levels[monitor_key].add(level)
                
                logger.info(f"🎯 触发斐波那契回撤: {ticker} {level*100:.1f}% @ ${retracement_price:.6f}")
                
                # 记录报警到数据库
                trigger_signal = f"🎯 斐波那契回撤报警：触发{level*100:.1f}%回撤位 @ ${retracement_price:.6f}"
                try:
                    with self.db:
                        self.db.add_alert(
                            exchange=exchange,
                            date=date,
                            interval=interval,
                            ticker=ticker,
                            trigger_signal=trigger_signal,
                            high=high,
                            low=low,
                            current_price=current_price
                        )
                    logger.info(f"📝 {ticker} 斐波那契回撤报警已记录到数据库")
                except Exception as e:
                    logger.error(f"记录报警到数据库失败: {e}")
                
                # 发送企业微信通知
                if self.notifier:
                    try:
                        self.notifier.send_fibonacci_alert(
                            ticker=ticker,
                            exchange=exchange,
                            interval=interval,
                            high=high,
                            low=low,
                            current_price=current_price,
                            retracement_level=level,
                            retracement_price=retracement_price,
                            date=date
                        )
                    except Exception as e:
                        logger.error(f"发送企业微信通知失败: {e}")
        
        return triggered
    
    def update_single_monitor(self, monitor: Dict) -> bool:
        """
        更新单条监控记录的价格
        
        Args:
            monitor: 监控记录字典
            
        Returns:
            是否成功更新
        """
        ticker = monitor['ticker']
        exchange = monitor['exchange']
        interval = monitor['interval']
        date = monitor['date']
        db_high = monitor['high']
        db_low = monitor['low']
        
        try:
            # 仅处理币安交易所的数据（现货和合约）
            supported_exchanges = ['bn', 'bn_spot', 'bn_futures', 'binance', 'binance_spot', 'binance_futures']
            if exchange not in supported_exchanges:
                logger.debug(f"跳过非币安交易所: {exchange} {ticker}")
                return False
            
            # 转换interval格式
            bn_interval = self.INTERVAL_MAP.get(interval)
            if not bn_interval:
                logger.warning(f"不支持的interval: {interval}")
                return False
            
            # 根据exchange类型决定使用哪个API
            # 判断是否使用期货API
            if exchange in ['bn_futures', 'binance_futures']:
                market_type = 'futures'
                from src.crypto.binance_data_fetcher import BinanceDataFetcher
                bn_fetcher = BinanceDataFetcher(market_type='futures')
            else:
                market_type = 'spot'
                bn_fetcher = self.bn_fetcher  # 使用默认的现货fetcher
            
            logger.info(f"从币安{market_type}获取 {ticker} {interval} 的最新价格...")
            kline_df = bn_fetcher.get_today_kline(
                symbol=ticker,
                interval=bn_interval,
                include_history=False
            )
            
            if kline_df.empty:
                logger.warning(f"未获取到K线数据: {ticker} {interval}")
                return False
            
            # 获取最新一根K线
            latest_kline = kline_df.iloc[-1]
            current_high = float(latest_kline['high'])
            current_price = float(latest_kline['close'])
            
            logger.info(f"{ticker}: 当前价={current_price:.4f}, 当天最高={current_high:.4f}, 数据库最高={db_high:.4f}")
            
            # [已暂停] 斐波那契回撤检测 - 后续可能需要继续使用
            # 检测斐波那契回撤（使用数据库中的high和low）
            # triggered_levels = self.check_fibonacci_retracement(
            #     ticker=ticker,
            #     exchange=exchange,
            #     interval=interval,
            #     date=date,
            #     high=db_high,
            #     low=db_low,
            #     current_price=current_price
            # )
            # 
            # if triggered_levels:
            #     logger.info(f"📊 {ticker} 触发 {len(triggered_levels)} 个斐波那契回撤位")
            
            # 判断是否需要更新high
            if current_high > db_high:
                # 更新high和current_price
                logger.info(f"✨ {ticker} 突破新高! {db_high:.4f} -> {current_high:.4f}")
                
                # [已暂停] 斐波那契回撤触发记录清除 - 后续可能需要继续使用
                # 清除该监控的回撤触发记录（因为创了新高）
                # monitor_key = (ticker, exchange, interval, date)
                # if monitor_key in self.triggered_levels:
                #     self.triggered_levels[monitor_key].clear()
                #     logger.info(f"🔄 清除 {ticker} 的回撤触发记录（创新高）")
                
                with self.db:
                    self.db.update_monitor_price(
                        ticker=ticker,
                        exchange=exchange,
                        interval=interval,
                        date=date,
                        high=current_high,
                        current_price=current_price
                    )
            else:
                # 只更新current_price
                with self.db:
                    self.db.update_monitor_price(
                        ticker=ticker,
                        exchange=exchange,
                        interval=interval,
                        date=date,
                        current_price=current_price
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"更新 {ticker} 价格失败: {e}")
            return False
    
    def update_all_monitors(self) -> Dict[str, int]:
        """
        更新所有监控记录的价格
        
        Returns:
            统计信息 {'total': 总数, 'success': 成功数, 'failed': 失败数, 'skipped': 跳过数, 'expired': 删除的过期数}
        """
        logger.info("=" * 80)
        logger.info("开始更新所有监控记录的价格")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # 先清理过期数据
        logger.info("\n🗑️  清理过期监控记录...")
        try:
            with self.db:
                expired_count = self.db.delete_expired_monitors(expire_multiplier=4)
            logger.info(f"✓ 清理完成: 删除了 {expired_count} 条过期记录\n")
        except Exception as e:
            logger.error(f"清理过期记录失败: {e}")
            expired_count = 0
        
        stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'expired': expired_count}
        
        try:
            # 获取所有监控记录
            with self.db:
                monitors = self.db.get_all_monitors()
            
            if not monitors:
                logger.warning("数据库中没有监控记录")
                return stats
            
            logger.info(f"共找到 {len(monitors)} 条监控记录")
            
            # 逐条处理
            for monitor in monitors:
                stats['total'] += 1
                ticker = monitor['ticker']
                interval = monitor['interval']
                exchange = monitor['exchange']

                # 跳过不在监控列表中的交易对
                if ticker not in get_monitored_symbols():
                    logger.debug(f"跳过非监控交易对: {exchange} {ticker}")
                    stats['skipped'] += 1
                    continue

                # 跳过非币安交易所（支持现货和合约）
                supported_exchanges = ['bn', 'bn_spot', 'bn_futures', 'binance', 'binance_spot', 'binance_futures']
                if exchange not in supported_exchanges:
                    logger.debug(f"跳过非币安交易所: {exchange} {ticker}")
                    stats['skipped'] += 1
                    continue
                
                logger.info(f"\n处理 [{stats['total']}/{len(monitors)}]: {exchange} {ticker} {interval}")
                
                success = self.update_single_monitor(monitor)
                
                if success:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                
                # 添加短暂延迟，避免API限流
                time.sleep(0.5)
            
            logger.info("\n" + "=" * 80)
            logger.info("价格更新完成")
            logger.info(f"总计: {stats['total']} 条")
            logger.info(f"成功: {stats['success']} 条")
            logger.info(f"失败: {stats['failed']} 条")
            logger.info(f"跳过: {stats['skipped']} 条")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"更新过程出错: {e}", exc_info=True)

        return stats

    def update_all_monitors_dynamic(self) -> Dict[str, int]:
        """
        更新所有动态监控记录的价格（只处理 tokens-config-dynamic.md 中的交易对）

        Returns:
            统计信息 {'total': 总数, 'success': 成功数, 'failed': 失败数, 'skipped': 跳过数, 'expired': 删除的过期数}
        """
        logger.info("=" * 80)
        logger.info("开始更新动态监控记录的价格")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # 先清理过期数据
        logger.info("\n🗑️  清理过期监控记录...")
        try:
            with self.db:
                expired_count = self.db.delete_expired_monitors(expire_multiplier=4)
            logger.info(f"✓ 清理完成: 删除了 {expired_count} 条过期记录\n")
        except Exception as e:
            logger.error(f"清理过期记录失败: {e}")
            expired_count = 0

        stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'expired': expired_count}

        try:
            # 获取所有监控记录
            with self.db:
                monitors = self.db.get_all_monitors()

            if not monitors:
                logger.warning("数据库中没有监控记录")
                return stats

            logger.info(f"共找到 {len(monitors)} 条监控记录")

            # 动态配置的交易对列表
            dynamic_symbols = get_dynamic_symbols()
            logger.info(f"动态配置交易对: {dynamic_symbols}")

            # 逐条处理
            for monitor in monitors:
                stats['total'] += 1
                ticker = monitor['ticker']
                interval = monitor['interval']
                exchange = monitor['exchange']

                # 只处理动态配置列表中的交易对
                if ticker not in dynamic_symbols:
                    logger.debug(f"跳过非动态配置交易对: {exchange} {ticker}")
                    stats['skipped'] += 1
                    continue

                # 跳过非币安交易所（支持现货和合约）
                supported_exchanges = ['bn', 'bn_spot', 'bn_futures', 'binance', 'binance_spot', 'binance_futures']
                if exchange not in supported_exchanges:
                    logger.debug(f"跳过非币安交易所: {exchange} {ticker}")
                    stats['skipped'] += 1
                    continue

                logger.info(f"\n处理 [{stats['total']}/{len(monitors)}]: {exchange} {ticker} {interval}")

                success = self.update_single_monitor(monitor)

                if success:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1

                # 添加短暂延迟，避免API限流
                time.sleep(0.5)

            logger.info("\n" + "=" * 80)
            logger.info("动态配置价格更新完成")
            logger.info(f"总计: {stats['total']} 条")
            logger.info(f"成功: {stats['success']} 条")
            logger.info(f"失败: {stats['failed']} 条")
            logger.info(f"跳过: {stats['skipped']} 条")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"更新过程出错: {e}", exc_info=True)

        return stats
    
    def print_update_summary(self, stats: Dict[str, int]):
        """打印更新摘要"""
        print("\n" + "=" * 80)
        print("价格更新摘要")
        print("=" * 80)
        print(f"总记录数: {stats['total']}")
        print(f"成功更新: {stats['success']}")
        print(f"更新失败: {stats['failed']}")
        print(f"跳过记录: {stats['skipped']}")
        if 'expired' in stats:
            print(f"删除过期: {stats['expired']}")
        if stats['total'] > stats['skipped']:
            success_rate = stats['success'] / (stats['total'] - stats['skipped']) * 100
            print(f"成功率: {success_rate:.2f}%")
        print("=" * 80)


def main():
    """命令行工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description='价格更新工具 - 从币安获取最新价格并更新数据库，支持斐波那契回撤检测')
    parser.add_argument('--once', action='store_true', help='只执行一次然后退出')
    parser.add_argument('--interval', type=int, default=15, help='更新间隔（分钟），默认15分钟')
    parser.add_argument('--wecom-webhook', type=str, help='企业微信webhook地址（可选，也可通过环境变量WECOM_WEBHOOK_URL配置）')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("价格更新工具（含斐波那契回撤检测）")
    print("=" * 80)
    
    # 创建更新器
    updater = PriceUpdater(wecom_webhook_url=args.wecom_webhook)
    
    if args.once:
        # 只执行一次
        stats = updater.update_all_monitors()
        updater.print_update_summary(stats)
    else:
        # 循环执行
        logger.info(f"⏰ 价格更新器已启动，将每 {args.interval} 分钟更新一次")
        logger.info("按 Ctrl+C 停止\n")
        
        try:
            while True:
                stats = updater.update_all_monitors()
                updater.print_update_summary(stats)
                
                logger.info(f"\n等待 {args.interval} 分钟后进行下一次更新...")
                time.sleep(args.interval * 60)
                
        except KeyboardInterrupt:
            logger.info("\n价格更新器已停止")


if __name__ == "__main__":
    main()

