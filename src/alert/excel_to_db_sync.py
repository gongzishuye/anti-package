#!/usr/bin/env python3
"""
Excel数据同步到数据库
从 qualified_tokens_multi_period_xxx.xlsx 文件读取数据并写入数据库
"""

import os
import glob
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import logging
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.database.db_manager import DatabaseManager
from src.alert.monitor_config import get_monitored_symbols

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExcelToDBSync:
    """Excel数据同步到数据库"""
    
    # Sheet名称和interval的映射（支持多种格式）
    SHEET_INTERVAL_MAP = {
        '1日筛选结果': '1D',
        '3日筛选结果': '3D',
        '周筛选结果': '1W',
        # 支持简化格式
        '1日': '1D',
        '2日': '2D',
        '3日': '3D',
        '5日': '5D',
        '周': '1W'
    }
    
    def __init__(self, data_dir: str = None, exchange: str = 'bn'):
        """
        初始化同步器
        
        Args:
            data_dir: Excel文件所在目录，默认为项目根目录下的data目录
            exchange: 交易所名称，默认为'bn'（Binance）
        """
        if data_dir is None:
            # 默认为项目根目录下的data目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(project_root, 'data')
        
        self.data_dir = data_dir
        self.exchange = exchange
        self.db = DatabaseManager()
    
    def find_latest_excel(self, pattern: str = None) -> Optional[str]:
        """
        查找最新的Excel文件
        
        Args:
            pattern: 文件名匹配模式，如果不提供则根据exchange自动判断
            
        Returns:
            最新文件的完整路径，如果没有找到则返回None
        """
        # 如果没有提供pattern，根据exchange自动判断
        if pattern is None:
            if self.exchange in ['bn_futures', 'binance_futures']:
                pattern = 'qualified_futures_tokens_multi_period_*.xlsx'
            elif self.exchange in ['bn_spot', 'binance_spot']:
                pattern = 'qualified_tokens_multi_period_*.xlsx'
            elif self.exchange in ['okx_futures']:
                pattern = 'qualified_okx_futures_tokens_multi_period_*.xlsx'
            elif self.exchange in ['okx_spot', 'okx']:
                pattern = 'qualified_okx_tokens_multi_period_*.xlsx'
            else:
                # 默认使用现货
                pattern = 'qualified_tokens_multi_period_*.xlsx'
        
        search_pattern = os.path.join(self.data_dir, pattern)
        files = glob.glob(search_pattern)
        
        if not files:
            logger.warning(f"未找到匹配的文件: {search_pattern}")
            return None
        
        # 按修改时间排序，获取最新的文件
        latest_file = max(files, key=os.path.getmtime)
        logger.info(f"找到最新文件: {latest_file}")
        
        return latest_file
    
    def process_sheet_data(self, df: pd.DataFrame, interval: str, date: str) -> List[Dict]:
        """
        处理单个sheet的数据
        
        Args:
            df: DataFrame数据
            interval: 时间粒度 (如: '1D', '3D', '1W')
            date: 当天日期
            
        Returns:
            处理后的数据列表
        """
        processed_data = []
        
        for idx, row in df.iterrows():
            ticker = row['symbol']

            # 跳过不在监控列表中的交易对
            if ticker not in get_monitored_symbols():
                continue
            
            # 计算过去两根K线（T-2和T-1）的最低点和最高点
            # 注：如果需要包含第三根K线，需要从其他地方获取今天的数据
            low_values = []
            high_values = []
            
            # T_minus_2的数据
            if pd.notna(row.get('T_minus_2_low')):
                low_values.append(float(row['T_minus_2_low']))
            if pd.notna(row.get('T_minus_2_high')):
                high_values.append(float(row['T_minus_2_high']))
            
            # T_minus_1的数据
            if pd.notna(row.get('T_minus_1_low')):
                low_values.append(float(row['T_minus_1_low']))
            if pd.notna(row.get('T_minus_1_high')):
                high_values.append(float(row['T_minus_1_high']))
            
            if not low_values or not high_values:
                logger.warning(f"跳过 {ticker}: 缺少价格数据")
                continue
            
            # 过去三根k线的最低点和最高点
            low = min(low_values)
            high = max(high_values)
            
            # current_price填high的值
            current_price = high
            
            processed_data.append({
                'exchange': self.exchange,
                'date': date,
                'interval': interval,
                'ticker': ticker,
                'low': low,
                'high': high,
                'current_price': current_price
            })
        
        return processed_data
    
    def sync_excel_to_db(self, excel_file: str = None, date: str = None) -> Dict[str, int]:
        """
        将Excel数据同步到数据库
        
        Args:
            excel_file: Excel文件路径，如果为None则自动查找最新文件
            date: 日期字符串（格式：YYYY-MM-DD），如果为None则使用当天日期
            
        Returns:
            同步统计信息 {'total': 总数, 'success': 成功数, 'failed': 失败数}
        """
        # 查找最新的Excel文件
        if excel_file is None:
            excel_file = self.find_latest_excel()
            if excel_file is None:
                logger.error("未找到Excel文件")
                return {'total': 0, 'success': 0, 'failed': 0}
        
        # 使用当天日期
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"开始同步数据: {excel_file}")
        logger.info(f"目标日期: {date}")
        
        stats = {'total': 0, 'success': 0, 'failed': 0}
        
        try:
            # 读取所有sheet
            excel_data = pd.read_excel(excel_file, sheet_name=None)
            
            with self.db:
                # 处理每个sheet
                for sheet_name, df in excel_data.items():
                    # 获取对应的interval
                    interval = self.SHEET_INTERVAL_MAP.get(sheet_name)
                    
                    if interval is None:
                        logger.warning(f"未知的sheet名称: {sheet_name}，跳过")
                        continue
                    
                    logger.info(f"处理 {sheet_name} (interval: {interval}), 共 {len(df)} 条记录")
                    
                    # 处理数据
                    processed_data = self.process_sheet_data(df, interval, date)
                    
                    # 写入数据库
                    for data in processed_data:
                        try:
                            self.db.add_monitor(
                                exchange=data['exchange'],
                                date=data['date'],
                                interval=data['interval'],
                                ticker=data['ticker'],
                                high=data['high'],
                                low=data['low'],
                                current_price=data['current_price']
                            )
                            stats['success'] += 1
                        except Exception as e:
                            logger.error(f"写入失败 {data['ticker']}: {e}")
                            stats['failed'] += 1
                        
                        stats['total'] += 1
            
            logger.info(f"同步完成: 总计 {stats['total']} 条, 成功 {stats['success']} 条, 失败 {stats['failed']} 条")
            
        except Exception as e:
            logger.error(f"同步过程出错: {e}")
            raise
        
        return stats
    
    def print_sync_summary(self, stats: Dict[str, int]):
        """打印同步摘要"""
        print("\n" + "=" * 80)
        print("数据同步摘要")
        print("=" * 80)
        print(f"总记录数: {stats['total']}")
        print(f"成功: {stats['success']}")
        print(f"失败: {stats['failed']}")
        print(f"成功率: {stats['success']/stats['total']*100:.2f}%" if stats['total'] > 0 else "N/A")
        print("=" * 80)


def main():
    """命令行工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Excel数据同步到数据库')
    parser.add_argument('--data-dir', help='Excel文件所在目录')
    parser.add_argument('--excel-file', help='指定Excel文件路径')
    parser.add_argument('--exchange', default='bn', help='交易所名称（默认: bn）')
    parser.add_argument('--date', help='日期（格式: YYYY-MM-DD，默认: 今天）')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Excel数据同步工具")
    print("=" * 80)
    
    # 创建同步器
    syncer = ExcelToDBSync(data_dir=args.data_dir, exchange=args.exchange)
    
    # 执行同步
    stats = syncer.sync_excel_to_db(excel_file=args.excel_file, date=args.date)
    
    # 打印摘要
    syncer.print_sync_summary(stats)
    
    # 显示数据库统计
    print("\n当前数据库统计:")
    with syncer.db:
        monitor_stats = syncer.db.get_monitor_stats()
        print(f"Monitor表总记录数: {monitor_stats['total_monitors']}")
        print(f"按交易所: {monitor_stats['by_exchange']}")
        print(f"按时间粒度: {monitor_stats['by_interval']}")


if __name__ == "__main__":
    main()

