#!/usr/bin/env python3
"""
综合定时任务调度器
- Excel数据同步：每天8:30执行
- 价格更新：每15分钟执行
"""

import schedule
import time
from datetime import datetime
import logging
import sys
import os
from functools import partial
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

# 加载.env文件
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alert.price_updater import PriceUpdater
from src.alert.crypto_reversal_detector import CryptoReversalDetector
from src.alert.funding_rate_monitor import FundingRateMonitor
from src.metal.metal_reversal_detector import MetalReversalDetector
from src.alert.monitor_config import MONITORED_INTERVALS, get_dynamic_symbols

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CombinedScheduler:
    """综合定时任务调度器"""

    def __init__(self, data_dir: str = None, exchange: str = 'bn_futures',
                 wecom_webhook_url: str = None, wecom_webhook_url2: str = None):
        """
        初始化调度器

        Args:
            data_dir: Excel文件所在目录
            exchange: 交易所名称
            wecom_webhook_url: 企业微信webhook地址（用于 tokens-config.md）
            wecom_webhook_url2: 企业微信webhook地址2（用于 tokens-config-dynamic.md）
        """
        self.wecom_webhook_url = wecom_webhook_url or os.getenv('WECOM_WEBHOOK_URL')
        self.wecom_webhook_url2 = wecom_webhook_url2 or os.getenv('WECOM_WEBHOOK_URL2')

        self.price_updater = PriceUpdater(wecom_webhook_url=self.wecom_webhook_url)
        self.price_updater_dynamic = PriceUpdater(wecom_webhook_url=self.wecom_webhook_url2)
        self.reversal_detector = CryptoReversalDetector(
            wecom_webhook_url=self.wecom_webhook_url
        )
        self.reversal_detector_dynamic = CryptoReversalDetector(
            wecom_webhook_url=self.wecom_webhook_url2
        )
        self.funding_rate_monitor = FundingRateMonitor(
            wecom_webhook_url=self.wecom_webhook_url,
            threshold=0.002,
            quote_asset='USDT'
        )
        self.metal_reversal_detector = MetalReversalDetector()
        self.last_price_update_time = None
        self.last_reversal_detect_time = None
        self.last_funding_rate_time = None
        self.last_metal_detect_time = None

    def price_update_job(self):
        """价格更新任务（tokens-config.md -> WECOM_WEBHOOK_URL）"""
        logger.info("=" * 80)
        logger.info("💹 开始执行价格更新任务（主配置）")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # 执行更新
            stats = self.price_updater.update_all_monitors()

            # 记录结果
            logger.info(f"更新完成: 成功 {stats['success']}/{stats['total']} 条")

            self.last_price_update_time = datetime.now()

            # 打印摘要
            self.price_updater.print_update_summary(stats)

        except Exception as e:
            logger.error(f"价格更新任务执行失败: {e}", exc_info=True)

    def price_update_job_dynamic(self):
        """价格更新任务（tokens-config-dynamic.md -> WECOM_WEBHOOK_URL2）"""
        logger.info("=" * 80)
        logger.info("💹 开始执行价格更新任务（动态配置）")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # 执行更新（只更新动态配置的交易对）
            stats = self.price_updater_dynamic.update_all_monitors_dynamic()

            # 记录结果
            logger.info(f"更新完成: 成功 {stats['success']}/{stats['total']} 条")

            self.last_price_update_time = datetime.now()

            # 打印摘要
            self.price_updater_dynamic.print_update_summary(stats)

        except Exception as e:
            logger.error(f"价格更新任务（动态配置）执行失败: {e}", exc_info=True)
    
    def reversal_detect_job(self, interval: str = None):
        """
        反包检测任务
        
        Args:
            interval: 指定要检测的周期（如'4H', '8H', '12H', '1D'），对所有监控记录检测该周期。
                     如果为None，则检测所有支持的周期
        """
        interval_name = interval if interval else "所有周期"
        logger.info("=" * 80)
        logger.info(f"🔍 开始执行反包检测任务 ({interval_name})")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        try:
            # 执行反包检测
            reversal_tokens = self.reversal_detector.detect_all_monitors(target_interval=interval)
            
            # 记录结果
            logger.info(f"检测完成: 找到 {len(reversal_tokens)} 个反包token")
            
            self.last_reversal_detect_time = datetime.now()
            
            # 打印结果
            if reversal_tokens:
                logger.info("\n反包token列表:")
                for token in reversal_tokens:
                    logger.info(f"  • {token['ticker']} ({token['exchange']}) {token['interval']} - "
                              f"成交量增幅: {token['volume_increase_pct']:+.1f}%")
            
        except Exception as e:
            logger.error(f"反包检测任务执行失败: {e}", exc_info=True)
    
    def high_frequency_reversal_job(self):
        """
        高频反包检测任务（只处理 2D/5D/1M，避免与 high_priority_reversal_job 重叠）
        - 2D、5D：使用OKX现货数据（UTC+8）
        - 1M：使用币安现货数据（UTC+8）
        - 1D/3D/1W 由 high_priority_reversal_job 使用 bn_futures 数据统一覆盖
        """
        logger.info("=" * 80)
        logger.info("🔍 开始执行高频反包检测任务（2D/5D/1M，现货数据）")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # 只检测 2D/5D/1M（1D/3D/1W 由 high_priority_reversal_job 覆盖）
            reversal_tokens = self.reversal_detector.detect_high_frequency_reversals(
                intervals=['2D', '5D', '1M']
            )
            
            # 记录结果
            logger.info(f"检测完成: 找到 {len(reversal_tokens)} 个反包token")

            self.last_reversal_detect_time = datetime.now()

            # 打印结果（2D/5D/1M）
            if reversal_tokens:
                logger.info("\n高频反包token列表 (2D/5D/1M，现货数据):")
                for token in reversal_tokens:
                    logger.info(f"  • {token['ticker']} ({token['exchange']}) {token['interval']} - "
                              f"成交量增幅: {token['volume_increase_pct']:+.1f}%")
            
        except Exception as e:
            logger.error(f"高频反包检测任务执行失败: {e}", exc_info=True)
    
    def _detect_single_interval(self, interval: str) -> List[Dict]:
        """
        检测单个周期（在独立线程中运行）
        
        Args:
            interval: 周期（如'1H', '2H'）
        
        Returns:
            检测到的反包token列表
        """
        try:
            # 创建新的detector实例（独立数据库连接）
            detector = CryptoReversalDetector(
                wecom_webhook_url=self.wecom_webhook_url
            )
            
            logger.info(f"[{interval}] 🚀 开始检测...")
            start_time = datetime.now()
            
            reversal_tokens = detector.detect_all_monitors(target_interval=interval)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"[{interval}] ✅ 完成，找到 {len(reversal_tokens)} 个反包token，耗时 {duration:.1f}秒")
            
            return reversal_tokens
            
        except Exception as e:
            logger.error(f"[{interval}] ❌ 检测失败: {e}", exc_info=True)
            return []
    
    def reversal_detect_job_parallel(self, intervals: List[str]):
        """
        并行执行多个周期的反包检测
        
        Args:
            intervals: 要检测的周期列表（如['1H', '2H', '4H']）
        """
        logger.info("=" * 80)
        logger.info(f"🚀 并行执行反包检测任务")
        logger.info(f"周期列表: {intervals}")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # 使用ThreadPoolExecutor并行执行
            all_results = {}
            total_tokens = 0
            
            with ThreadPoolExecutor(max_workers=len(intervals)) as executor:
                # 提交所有任务
                future_to_interval = {
                    executor.submit(self._detect_single_interval, interval): interval 
                    for interval in intervals
                }
                
                # 收集结果
                for future in as_completed(future_to_interval):
                    interval = future_to_interval[future]
                    try:
                        result = future.result()
                        all_results[interval] = result
                        total_tokens += len(result)
                    except Exception as e:
                        logger.error(f"[{interval}] ❌ 获取结果失败: {e}")
                        all_results[interval] = []
            
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            # 记录结果
            logger.info("=" * 80)
            logger.info(f"🎉 并行检测完成")
            logger.info(f"总耗时: {total_duration:.1f}秒")
            logger.info(f"总共找到: {total_tokens} 个反包token")
            logger.info("=" * 80)
            
            # 打印每个周期的结果
            for interval, tokens in all_results.items():
                if tokens:
                    logger.info(f"\n[{interval}] 反包token列表:")
                    for token in tokens:
                        logger.info(f"  • {token['ticker']} ({token['exchange']}) - "
                                  f"成交量增幅: {token['volume_increase_pct']:+.1f}%")
            
            self.last_reversal_detect_time = datetime.now()
            
        except Exception as e:
            logger.error(f"并行反包检测任务执行失败: {e}", exc_info=True)
    
    def funding_rate_refresh_job(self):
        """资金费率间隔刷新任务"""
        logger.info("=" * 80)
        logger.info("💰 开始刷新资金费率间隔信息")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            data = self.funding_rate_monitor.refresh_funding_intervals()
            self.last_funding_rate_time = datetime.now()
            logger.info(f"资金费率间隔刷新完成: 共记录 {len(data)} 个交易对")
        except Exception as e:
            logger.error(f"资金费率间隔刷新任务执行失败: {e}", exc_info=True)

    def funding_rate_check_job(self):
        """资金费率检测任务"""
        logger.info("=" * 80)
        logger.info("💰 开始执行资金费率检测任务")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            alerts = self.funding_rate_monitor.check_and_alert()
            logger.info(f"资金费率检测任务完成: 超过阈值 {len(alerts)} 个交易对")
        except Exception as e:
            logger.error(f"资金费率检测任务执行失败: {e}", exc_info=True)

    def metal_daily_job(self):
        """贵金属每日数据获取和反包检测任务"""
        logger.info("=" * 80)
        logger.info("🥇 开始执行贵金属每日数据获取和反包检测任务")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        try:
            from datetime import timedelta
            
            # 获取昨天的日期
            yesterday = datetime.now() - timedelta(days=1)
            while yesterday.weekday() >= 5:  # 跳过周末
                yesterday -= timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y-%m-%d')
            
            logger.info(f"目标日期: {yesterday_str}")
            
            # 检查数据是否已存在
            existing_sheets = self.metal_reversal_detector.get_existing_sheets()
            if yesterday_str in existing_sheets:
                logger.info(f"✓ 日期 {yesterday_str} 的数据已存在，跳过获取")
            else:
                # 获取昨天的数据
                logger.info(f"开始获取 {yesterday_str} 的贵金属数据...")
                
                # 获取所有支持的贵金属数据
                import pandas as pd
                all_data = []
                for metal in self.metal_reversal_detector.supported_metals:
                    logger.info(f"  获取 {metal}/USD {yesterday_str} 的数据...")
                    ohlc_data = self.metal_reversal_detector.fetcher.get_ohlc(metal, 'USD', yesterday_str)
                    
                    if ohlc_data:
                        rate = ohlc_data.get('rate', {})
                        timestamp = ohlc_data.get('timestamp', 0)
                        
                        # 将时间戳转换为datetime
                        if timestamp:
                            dt = datetime.fromtimestamp(timestamp)
                        else:
                            dt = datetime.strptime(yesterday_str, '%Y-%m-%d')
                        
                        all_data.append({
                            'symbol': f'{metal}/USD',
                            'timestamp': dt.replace(hour=0, minute=0, second=0, microsecond=0),
                            'open': float(rate.get('open', 0)),
                            'high': float(rate.get('high', 0)),
                            'low': float(rate.get('low', 0)),
                            'close': float(rate.get('close', 0)),
                            'date': yesterday_str
                        })
                
                if not all_data:
                    logger.warning(f"✗ 日期 {yesterday_str} 未获取到数据")
                    logger.warning("  可能原因：1) API 服务问题 2) 非交易日 3) 网络问题")
                    return
                
                # 转换为DataFrame
                df = pd.DataFrame(all_data)
                
                # 保存数据
                logger.info(f"保存数据到 Excel...")
                self.metal_reversal_detector.save_daily_data(yesterday_str, df)
                logger.info(f"✓ 数据保存成功，共 {len(df)} 条记录")
            
            # 执行反包检测
            logger.info(f"开始执行反包检测...")
            results = self.metal_reversal_detector.run_reversal_detection()
            
            if not results.empty:
                logger.info(f"✓ 反包检测完成，找到 {len(results)} 个符合条件的贵金属")
            else:
                logger.info("✓ 反包检测完成，未找到符合条件的贵金属")
            
            self.last_metal_detect_time = datetime.now()

        except Exception as e:
            logger.error(f"贵金属每日任务执行失败: {e}", exc_info=True)

    def high_frequency_reversal_job_dynamic(self):
        """
        高频反包检测任务（动态配置，2D/5D/1M，现货数据）
        """
        logger.info("=" * 80)
        logger.info("🔍 开始执行高频反包检测任务（动态配置，2D/5D/1M，现货数据）")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # 只检测 2D/5D/1M
            reversal_tokens = self.reversal_detector_dynamic.detect_high_frequency_reversals_dynamic(
                intervals=['2D', '5D', '1M']
            )

            # 记录结果
            logger.info(f"检测完成: 找到 {len(reversal_tokens)} 个反包token")

            self.last_reversal_detect_time = datetime.now()

            # 打印结果
            if reversal_tokens:
                logger.info("\n高频反包token列表 (动态配置，2D/5D/1M，现货数据):")
                for token in reversal_tokens:
                    logger.info(f"  • {token['ticker']} ({token['exchange']}) {token['interval']} - "
                              f"成交量增幅: {token['volume_increase_pct']:+.1f}%")

        except Exception as e:
            logger.error(f"高频反包检测任务（动态配置）执行失败: {e}", exc_info=True)

    def high_priority_reversal_job(self, interval: str):
        """高频反包检测任务（主配置 tokens-config.md -> WECOM_WEBHOOK_URL）"""
        logger.info("=" * 80)
        logger.info(f"⚡ 高频反包检测任务 - 周期 {interval}")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            results = self.reversal_detector.detect_priority_reversals(interval)
            logger.info(f"高频反包检测任务完成: 找到 {len(results)} 个结果 ({interval})")
        except Exception as e:
            logger.error(f"高频反包检测任务执行失败 ({interval}): {e}", exc_info=True)

    def high_priority_reversal_job_dynamic(self, interval: str):
        """高频反包检测任务（动态配置 tokens-config-dynamic.md -> WECOM_WEBHOOK_URL2）"""
        logger.info("=" * 80)
        logger.info(f"⚡ 高频反包检测任务（动态配置） - 周期 {interval}")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            results = self.reversal_detector_dynamic.detect_priority_reversals_dynamic(interval)
            logger.info(f"高频反包检测任务（动态配置）完成: 找到 {len(results)} 个结果 ({interval})")
        except Exception as e:
            logger.error(f"高频反包检测任务（动态配置）执行失败 ({interval}): {e}", exc_info=True)

    # [已禁用] def ma100_touch_job(self, interval: str):
    #     """MA100均线触碰检测任务"""
    #     logger.info(f"📊 MA100检测任务 - 周期 {interval}")
    #     try:
    #         results = self.reversal_detector.detect_ma100_touches(target_interval=interval)
    #         logger.info(f"MA100检测任务完成: 找到 {len(results)} 次触碰 ({interval})")
    #     except Exception as e:
    #         logger.error(f"MA100检测任务执行失败 ({interval}): {e}", exc_info=True)

    def start(self,
              price_update_interval: int = 15,
              run_price_now: bool = False,
              run_reversal_now: bool = False,
              run_funding_now: bool = False,
              run_metal_now: bool = False,
              price_only: bool = False,
              reversal_only: bool = False,
              funding_only: bool = False,
              metal_only: bool = False):
        """
        启动定时任务

        Args:
            price_update_interval: 价格更新间隔（分钟）
            run_price_now: 是否立即执行价格更新
            run_reversal_now: 是否立即执行反包检测
            run_funding_now: 是否立即执行资金费率监控
            price_only: 只运行价格更新任务
            reversal_only: 只运行反包检测任务
            funding_only: 只运行资金费率监控任务
            metal_only: 只运行贵金属每日任务
        """
        logger.info("=" * 80)
        logger.info("综合定时任务调度器启动")
        logger.info("=" * 80)
        
        enable_excel = False  # Excel同步已废弃，统一由反包检测覆盖
        enable_price = not price_only and not reversal_only and not funding_only and not metal_only
        enable_reversal = not price_only and not funding_only and not metal_only
        enable_funding = False  # 暂时停用费率监控
        enable_metal = not price_only and not reversal_only and not funding_only

        # 贵金属每日数据获取和反包检测任务（每天8:02）
        if enable_metal:
            logger.info(f"🥇 贵金属每日任务: 每天 08:02")
            logger.info(f"   数据目录: {self.metal_reversal_detector.data_dir}")
            schedule.every().day.at("08:02").do(self.metal_daily_job)

        if enable_price:
            logger.info(f"🔄 价格更新任务: 每 {price_update_interval} 分钟")
            schedule.every(price_update_interval).minutes.do(self.price_update_job)

            # 动态配置的价格更新任务
            logger.info(f"🔄 价格更新任务（动态配置）: 每 {price_update_interval} 分钟")
            schedule.every(price_update_interval).minutes.do(self.price_update_job_dynamic)

        if enable_reversal:
            logger.info(f"🎯 反包检测任务（8个交易对 x 14个周期）:")
            logger.info(f"   - 15M: 每小时 02/17/32/47 分执行")
            logger.info(f"   - 30M: 每小时 02/32 分执行")
            logger.info(f"   - 1H: 每小时 :02 | 2H: 每2h :02")
            logger.info(f"   - 4H: 00/04/08/12/16/20:02 | 6H: 00/06/12/18:02")
            logger.info(f"   - 8H: 00/08/16:02 | 12H: 00/12:02")
            logger.info(f"   - 1D/3D: 每天 08:02 | 1W: 每周一 08:02")
            logger.info(f"   - 2D/5D/1M: 每天 00:10 (UTC+8)")

            # 15M: 每小时的 02, 17, 32, 47 分执行
            for minute in [2, 17, 32, 47]:
                for hour in range(24):
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        partial(self.high_priority_reversal_job, '15M'))

            # 30M: 每小时的 02, 32 分执行
            for minute in [2, 32]:
                for hour in range(24):
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        partial(self.high_priority_reversal_job, '30M'))

            # 1H: 每小时:02
            for hour in range(24):
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job, '1H'))

            # 2H: 每2小时:02
            for hour in range(0, 24, 2):
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job, '2H'))

            # 4H: 00/04/08/12/16/20:02
            for hour in [0, 4, 8, 12, 16, 20]:
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job, '4H'))

            # 6H: 00/06/12/18:02
            for hour in [0, 6, 12, 18]:
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job, '6H'))

            # 8H: 00/08/16:02
            for hour in [0, 8, 16]:
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job, '8H'))

            # 12H: 00/12:02
            for hour in [0, 12]:
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job, '12H'))

            # 1D/3D: 每天 08:02
            schedule.every().day.at("08:02").do(
                partial(self.high_priority_reversal_job, '1D'))
            schedule.every().day.at("08:02").do(
                partial(self.high_priority_reversal_job, '3D'))

            # 1W: 每周一 08:02
            schedule.every().monday.at("08:02").do(
                partial(self.high_priority_reversal_job, '1W'))

            # 1D/3D/1W 由 high_priority_reversal_job 统一覆盖（bn_futures）
            # 2D/5D/1M 使用 OKX/BN 现货数据，每个周期检测8个交易对
            schedule.every().day.at("00:10").do(self.high_frequency_reversal_job)

            # 动态配置的反包检测（使用 tokens-config-dynamic.md）
            logger.info(f"   - 动态配置: 同步主配置的所有周期")

            # 5M: 每5分钟检测一次 (每小时的 00/05/10/15/20/25/30/35/40/45/50/55)
            for minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
                for hour in range(24):
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        partial(self.high_priority_reversal_job_dynamic, '5M'))

            # 10M: 每10分钟检测一次 (每小时的 00/10/20/30/40/50)
            for minute in [0, 10, 20, 30, 40, 50]:
                for hour in range(24):
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        partial(self.high_priority_reversal_job_dynamic, '10M'))

            # 15M: 每小时 02/17/32/47 分执行
            for minute in [2, 17, 32, 47]:
                for hour in range(24):
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        partial(self.high_priority_reversal_job_dynamic, '15M'))
            for minute in [2, 32]:
                for hour in range(24):
                    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
                        partial(self.high_priority_reversal_job_dynamic, '30M'))
            for hour in range(24):
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job_dynamic, '1H'))
            for hour in range(0, 24, 2):
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job_dynamic, '2H'))
            for hour in [0, 4, 8, 12, 16, 20]:
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job_dynamic, '4H'))
            for hour in [0, 6, 12, 18]:
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job_dynamic, '6H'))
            for hour in [0, 8, 16]:
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job_dynamic, '8H'))
            for hour in [0, 12]:
                schedule.every().day.at(f"{hour:02d}:02").do(
                    partial(self.high_priority_reversal_job_dynamic, '12H'))
            schedule.every().day.at("08:02").do(
                partial(self.high_priority_reversal_job_dynamic, '1D'))
            schedule.every().day.at("08:02").do(
                partial(self.high_priority_reversal_job_dynamic, '3D'))
            schedule.every().monday.at("08:02").do(
                partial(self.high_priority_reversal_job_dynamic, '1W'))
            schedule.every().day.at("00:10").do(self.high_frequency_reversal_job_dynamic)

            # [已禁用] MA100均线触碰检测（每个整点前2分钟执行，覆盖1H/2H/4H/6H/8H/12H/1D）
            # logger.info("📊 MA100均线触碰检测任务:")
            # # 1H/2H: 每小时:02
            # for hour in range(24):
            #     schedule.every().day.at(f"{hour:02d}:02").do(
            #         partial(self.ma100_touch_job, '1H'))
            #     schedule.every().day.at(f"{hour:02d}:02").do(
            #         partial(self.ma100_touch_job, '2H'))
            # # 4H: 00/04/08/12/16/20:02
            # for hour in [0, 4, 8, 12, 16, 20]:
            #     schedule.every().day.at(f"{hour:02d}:02").do(
            #         partial(self.ma100_touch_job, '4H'))
            # # 6H: 00/06/12/18:02
            # for hour in [0, 6, 12, 18]:
            #     schedule.every().day.at(f"{hour:02d}:02").do(
            #         partial(self.ma100_touch_job, '6H'))
            # # 8H: 00/08/16:02
            # for hour in [0, 8, 16]:
            #     schedule.every().day.at(f"{hour:02d}:02").do(
            #         partial(self.ma100_touch_job, '8H'))
            # # 12H: 00/12:02
            # for hour in [0, 12]:
            #     schedule.every().day.at(f"{hour:02d}:02").do(
            #         partial(self.ma100_touch_job, '12H'))
            # # 1D: 每天 08:02
            # schedule.every().day.at("08:02").do(
            #     partial(self.ma100_touch_job, '1D'))
            # logger.info("   - 周期: 1H/2H/4H/6H/8H/12H/1D")
            # logger.info("   - 标的: BTC/ETH/SOL/BNB/XAU/XAG/CL/USO")
            # logger.info("   - 报警目标: CORE2 (WECOM_WEBHOOK_URL)")

        if enable_funding:
            logger.info(f"💰 资金费率监控任务:")
            logger.info(f"   - 间隔刷新: 每4小时 (00:05 / 04:05 / 08:05 ...)")
            logger.info(f"   - 阈值检测: 每小时 (00:10 / 01:10 / 02:10 ...)")
            for hour in range(0, 24, 4):
                time_str = f"{hour:02d}:05"
                schedule.every().day.at(time_str).do(self.funding_rate_refresh_job)
            for hour in range(0, 24):
                time_str = f"{hour:02d}:10"
                schedule.every().day.at(time_str).do(self.funding_rate_check_job)
            logger.info(f"   - 报警阈值: ±{self.funding_rate_monitor.threshold * 100:.2f}%")
            logger.info(f"   - 数据来源: Funding Rate Info & Premium Index")

        logger.info(f"🏢 交易所: bn_futures")

        # 立即执行任务（如果需要）
        if run_price_now and enable_price:
            logger.info("\n立即执行价格更新...")
            self.price_update_job()

        if run_reversal_now and enable_reversal:
            logger.info("\n立即执行反包检测（所有周期）...")
            self.high_frequency_reversal_job()

        if run_funding_now and enable_funding:
            logger.info("\n立即执行资金费率刷新+检测...")
            self.funding_rate_refresh_job()
            self.funding_rate_check_job()

        if run_metal_now and enable_metal:
            logger.info("\n立即执行贵金属每日任务...")
            self.metal_daily_job()
        
        logger.info("\n⏰ 定时任务已启动")
        logger.info("按 Ctrl+C 停止\n")
        
        # 持续运行
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("\n定时任务已停止")


def main():
    """命令行工具"""
    import argparse

    parser = argparse.ArgumentParser(
        description='综合定时任务调度器 - 简化版（8个交易对 x 14个周期）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 启动所有任务（价格更新每15分钟，反包检测所有周期）
  python3 combined_scheduler.py

  # 自定义价格更新间隔为5分钟
  python3 combined_scheduler.py --price-interval 5

  # 启动时立即执行反包检测
  python3 combined_scheduler.py --run-reversal-now

  # 只运行价格更新任务
  python3 combined_scheduler.py --price-only

  # 只运行反包检测任务
  python3 combined_scheduler.py --reversal-only
        """
    )

    parser.add_argument('--price-interval', type=int, default=15,
                       help='价格更新间隔（分钟，默认: 15）')
    parser.add_argument('--wecom-webhook', type=str,
                       help='企业微信webhook地址（用于 tokens-config.md，可选，也可通过.env配置WECOM_WEBHOOK_URL）')
    parser.add_argument('--wecom-webhook2', type=str,
                       help='企业微信webhook地址2（用于 tokens-config-dynamic.md，可选，也可通过.env配置WECOM_WEBHOOK_URL2）')
    parser.add_argument('--run-price-now', action='store_true',
                       help='启动时立即执行价格更新')
    parser.add_argument('--run-reversal-now', action='store_true',
                       help='启动时立即执行反包检测')
    parser.add_argument('--run-metal-now', action='store_true',
                       help='启动时立即执行贵金属每日任务')
    parser.add_argument('--price-only', action='store_true',
                       help='只运行价格更新任务')
    parser.add_argument('--reversal-only', action='store_true',
                       help='只运行反包检测任务')
    parser.add_argument('--metal-only', action='store_true',
                       help='只运行贵金属每日任务')

    args = parser.parse_args()

    # 创建调度器
    scheduler = CombinedScheduler(
        wecom_webhook_url=args.wecom_webhook,
        wecom_webhook_url2=args.wecom_webhook2
    )

    # 启动任务
    scheduler.start(
        price_update_interval=args.price_interval,
        run_price_now=args.run_price_now,
        run_reversal_now=args.run_reversal_now,
        run_metal_now=args.run_metal_now,
        price_only=args.price_only,
        reversal_only=args.reversal_only,
        metal_only=args.metal_only
    )


if __name__ == "__main__":
    main()

