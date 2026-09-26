#!/usr/bin/env python3
"""
综合调度器（精简版）
- 仅处理动态配置通道的反包检测任务
- 使用 APScheduler 替代原 `schedule` 库
- 进程内后台线程运行，可与 Flask 共存
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Dict
from functools import partial

from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# 加载 .env 文件
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alert.crypto_reversal_detector import CryptoReversalDetector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CombinedScheduler:
    """综合调度器（精简版）"""

    def __init__(self, wecom_webhook_url2: str = None):
        """
        初始化调度器

        Args:
            wecom_webhook_url2: 动态配置通道的企业微信 webhook 地址
        """
        self.wecom_webhook_url2 = wecom_webhook_url2 or os.getenv('WECOM_WEBHOOK_URL2')

        # 动态配置反包检测器
        self.reversal_detector_dynamic = CryptoReversalDetector(
            wecom_webhook_url=self.wecom_webhook_url2
        )

        self.scheduler = BackgroundScheduler()
        self.last_reversal_detect_time = None

    def reversal_detect_job_dynamic(self, interval: str):
        """动态配置反包检测任务（按 interval 周期）"""
        logger.info("=" * 80)
        logger.info(f"⚡ 开始动态反包检测 ({interval})")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            results = self.reversal_detector_dynamic.detect_priority_reversals_dynamic(interval)
            logger.info(f"⚡ {interval} 检测完成: 找到 {len(results)} 个反包 token")
            self.last_reversal_detect_time = datetime.now()
        except Exception as e:
            logger.error(f"反包检测任务执行失败: {e}", exc_info=True)

    def reversal_detect_high_freq_job_dynamic(self, intervals: List[str]):
        """动态配置高频反包检测任务（处理 2D/5D/1M）"""
        logger.info("=" * 80)
        logger.info(f"⚡ 开始动态高频反包检测 {intervals}")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            results = self.reversal_detector_dynamic.detect_high_frequency_reversals_dynamic(intervals)
            logger.info(f"⚡ 高频检测完成: 找到 {len(results)} 个反包 token")
            self.last_reversal_detect_time = datetime.now()
        except Exception as e:
            logger.error(f"高频反包检测任务执行失败: {e}", exc_info=True)

    def start(self):
        """启动调度器"""
        logger.info("=" * 80)
        logger.info("综合调度器启动（动态配置通道）")
        logger.info("=" * 80)
        logger.info(f"Webhook: {self.wecom_webhook_url2[:60] if self.wecom_webhook_url2 else 'NOT CONFIGURED'}")

        # 短周期：5M/10M/15M/30M — 每整点 minute=2
        for interval in ['5M', '10M', '15M', '30M']:
            self.scheduler.add_job(
                self.reversal_detect_job_dynamic,
                'cron', hour='*', minute='2',
                args=[interval], id=f'reversal_{interval}'
            )
            logger.info(f"  - {interval}: 每整点 minute=2")

        # 1H/2H — 每偶数整点 minute=2
        for interval in ['1H', '2H']:
            self.scheduler.add_job(
                self.reversal_detect_job_dynamic,
                'cron', hour='*/2', minute='2',
                args=[interval], id=f'reversal_{interval}'
            )
            logger.info(f"  - {interval}: 每偶数整点 minute=2")

        # 4H/6H/8H/12H — 每 12 小时整点 minute=2
        for interval in ['4H', '6H', '8H', '12H']:
            self.scheduler.add_job(
                self.reversal_detect_job_dynamic,
                'cron', hour='*/12', minute='2',
                args=[interval], id=f'reversal_{interval}'
            )
            logger.info(f"  - {interval}: 每 12 小时整点 minute=2")

        # 1D/3D — 每天 08:02
        for interval in ['1D', '3D']:
            self.scheduler.add_job(
                self.reversal_detect_job_dynamic,
                'cron', hour='8', minute='2',
                args=[interval], id=f'reversal_{interval}'
            )
            logger.info(f"  - {interval}: 每天 08:02")

        # 1W — 每周一 08:02
        self.scheduler.add_job(
            self.reversal_detect_job_dynamic,
            'cron', day_of_week='mon', hour='8', minute='2',
            args=['1W'], id='reversal_1W'
        )
        logger.info("  - 1W: 每周一 08:02")

        # 2D/5D/1M 高频 — 每天 00:10
        self.scheduler.add_job(
            self.reversal_detect_high_freq_job_dynamic,
            'cron', hour='0', minute='10',
            args=[['2D', '5D', '1M']], id='reversal_high_freq'
        )
        logger.info("  - 2D/5D/1M: 每天 00:10（高频）")

        self.scheduler.start()
        logger.info("\n⏰ 定时任务已启动（动态配置通道）")
        logger.info(f"   已注册 {len(self.scheduler.get_jobs())} 个任务")