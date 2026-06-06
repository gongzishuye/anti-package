#!/usr/bin/env python3
"""
每日A股数据获取和反包检测脚本
每天早晨8点获取昨天的数据，保存到Excel，并执行反包检测
"""

import sys
import os
from datetime import datetime, timedelta
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.equity.a_stock_reversal_detector import AStockReversalDetector

# 设置日志
log_dir = Path(__file__).parent.parent.parent / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / 'equity_a_daily_fetch.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_yesterday_date() -> str:
    """
    获取昨天的日期（跳过周末）
    
    Returns:
        日期字符串 YYYY-MM-DD
    """
    yesterday = datetime.now() - timedelta(days=1)
    
    # 如果昨天是周末，往前找最近的交易日
    while yesterday.weekday() >= 5:
        yesterday -= timedelta(days=1)
    
    return yesterday.strftime('%Y-%m-%d')


def main():
    """主函数"""
    logger.info("="*80)
    logger.info("每日A股数据获取和反包检测任务开始")
    logger.info("="*80)
    
    try:
        # 创建反包检测器
        detector = AStockReversalDetector()
        
        # 获取昨天的日期
        yesterday = get_yesterday_date()
        logger.info(f"\n目标日期: {yesterday}")
        
        # 检查数据是否已存在
        existing_sheets = detector.get_existing_sheets()
        if yesterday in existing_sheets:
            logger.info(f"✓ 日期 {yesterday} 的数据已存在，跳过获取")
        else:
            # 获取昨天的数据
            logger.info(f"\n开始获取 {yesterday} 的A股数据...")
            df = detector.fetcher.get_daily_market_summary(yesterday)
            
            if df.empty:
                logger.warning(f"✗ 日期 {yesterday} 未获取到数据")
                logger.warning("  可能原因：1) API 服务未运行 2) 非交易日 3) 网络问题")
                return
            
            # 保存数据
            logger.info(f"\n保存数据到 Excel...")
            detector.save_daily_data(yesterday, df)
            logger.info(f"✓ 数据保存成功，共 {len(df)} 条记录")
        
        # 执行反包检测
        logger.info(f"\n开始执行反包检测...")
        results = detector.run_reversal_detection()
        
        if not results.empty:
            logger.info(f"✓ 反包检测完成，找到 {len(results)} 只符合条件的股票")
        else:
            logger.info("✓ 反包检测完成，未找到符合条件的股票")
        
        logger.info("\n" + "="*80)
        logger.info("每日任务完成")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"✗ 任务执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()

