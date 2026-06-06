#!/usr/bin/env python3
"""
每日同步脚本 - 简化版
用于crontab或其他定时任务调度器
不依赖schedule库
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alert.excel_to_db_sync import ExcelToDBSync
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """执行每日同步任务"""
    logger.info("=" * 80)
    logger.info("开始执行每日数据同步")
    logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        # 创建同步器
        syncer = ExcelToDBSync(exchange='bn')
        
        # 执行同步
        stats = syncer.sync_excel_to_db()
        
        # 打印结果
        syncer.print_sync_summary(stats)
        
        logger.info("每日同步任务完成")
        
        return 0
        
    except Exception as e:
        logger.error(f"同步任务失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

