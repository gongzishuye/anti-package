#!/usr/bin/env python3
"""
定时任务调度器
每天早上8:30自动同步Excel数据到数据库
"""

import schedule
import time
from datetime import datetime
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alert.excel_to_db_sync import ExcelToDBSync

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyScheduler:
    """每日定时任务调度器"""
    
    def __init__(self, data_dir: str = None, exchange: str = 'bn'):
        """
        初始化调度器
        
        Args:
            data_dir: Excel文件所在目录
            exchange: 交易所名称
        """
        self.syncer = ExcelToDBSync(data_dir=data_dir, exchange=exchange)
        self.last_run_time = None
    
    def sync_job(self):
        """定时同步任务"""
        logger.info("=" * 80)
        logger.info("开始执行定时同步任务")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        try:
            # 执行同步
            stats = self.syncer.sync_excel_to_db()
            
            # 记录结果
            logger.info(f"同步完成: 成功 {stats['success']}/{stats['total']} 条")
            
            self.last_run_time = datetime.now()
            
            # 打印摘要
            self.syncer.print_sync_summary(stats)
            
        except Exception as e:
            logger.error(f"同步任务执行失败: {e}", exc_info=True)
    
    def run_once(self):
        """立即运行一次（用于测试）"""
        logger.info("手动触发同步任务")
        self.sync_job()
    
    def start(self, time_str: str = "08:30", run_immediately: bool = False):
        """
        启动定时任务
        
        Args:
            time_str: 每天执行的时间（格式：HH:MM）
            run_immediately: 是否立即执行一次
        """
        logger.info("=" * 80)
        logger.info("定时任务调度器启动")
        logger.info("=" * 80)
        logger.info(f"计划执行时间: 每天 {time_str}")
        logger.info(f"数据目录: {self.syncer.data_dir}")
        logger.info(f"交易所: {self.syncer.exchange}")
        
        # 设置定时任务
        schedule.every().day.at(time_str).do(self.sync_job)
        
        # 如果需要，立即执行一次
        if run_immediately:
            logger.info("立即执行一次同步...")
            self.run_once()
        
        logger.info(f"\n⏰ 定时任务已启动，将在每天 {time_str} 执行")
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
    
    parser = argparse.ArgumentParser(description='定时任务调度器 - 每天同步Excel数据到数据库')
    parser.add_argument('--time', default='08:30', help='执行时间（格式: HH:MM，默认: 08:30）')
    parser.add_argument('--data-dir', help='Excel文件所在目录')
    parser.add_argument('--exchange', default='bn', help='交易所名称（默认: bn）')
    parser.add_argument('--run-now', action='store_true', help='立即执行一次')
    parser.add_argument('--once', action='store_true', help='只执行一次然后退出')
    
    args = parser.parse_args()
    
    # 创建调度器
    scheduler = DailyScheduler(data_dir=args.data_dir, exchange=args.exchange)
    
    if args.once:
        # 只执行一次
        scheduler.run_once()
    else:
        # 启动定时任务
        scheduler.start(time_str=args.time, run_immediately=args.run_now)


if __name__ == "__main__":
    main()
