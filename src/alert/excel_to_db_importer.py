#!/usr/bin/env python3
"""
Excel数据导入数据库模块
从 qualified_tokens_multi_period_*.xlsx 文件读取数据并导入到数据库
"""

import os
import sys
import glob
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
import logging

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.db_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExcelToDBImporter:
    """Excel数据导入数据库"""
    
    # 时间周期映射
    INTERVAL_MAPPING = {
        '1日筛选结果': '1D',
        '3日筛选结果': '3D',
        '周筛选结果': '1W',
        '1日K线': '1D',
        '3日K线': '3D',
        '周K线': '1W'
    }
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化导入器
        
        Args:
            db_manager: 数据库管理器实例，如果不提供则创建新的
        """
        self.db = db_manager if db_manager else DatabaseManager()
    
    def get_latest_qualified_tokens_file(self, search_dir: str = None) -> Optional[str]:
        """
        获取最新的 qualified_tokens_multi_period_*.xlsx 文件
        
        Args:
            search_dir: 搜索目录，默认为项目根目录
            
        Returns:
            最新文件的路径，如果没找到返回None
        """
        if search_dir is None:
            # 默认在项目根目录和data目录下搜索
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, '..', '..')
            project_root = os.path.abspath(project_root)
            
            # 搜索多个可能的位置
            search_patterns = [
                os.path.join(project_root, 'qualified_tokens_multi_period_*.xlsx'),
                os.path.join(project_root, 'data', 'qualified_tokens_multi_period_*.xlsx'),
                os.path.join(project_root, 'data', 'qualified_top*_multi_period_*.xlsx'),
            ]
        else:
            search_patterns = [
                os.path.join(search_dir, 'qualified_tokens_multi_period_*.xlsx'),
                os.path.join(search_dir, 'data', 'qualified_tokens_multi_period_*.xlsx'),
            ]
        
        # 收集所有匹配的文件
        all_files = []
        for pattern in search_patterns:
            files = glob.glob(pattern)
            all_files.extend(files)
        
        if not all_files:
            logger.warning("未找到 qualified_tokens_multi_period_*.xlsx 文件")
            return None
        
        # 返回最新的文件（按修改时间）
        latest_file = max(all_files, key=os.path.getmtime)
        logger.info(f"找到最新文件: {latest_file}")
        
        return latest_file
    
    def parse_excel_file(self, excel_path: str) -> Dict[str, pd.DataFrame]:
        """
        解析Excel文件，读取所有sheet
        
        Args:
            excel_path: Excel文件路径
            
        Returns:
            字典，key为sheet名，value为DataFrame
        """
        logger.info(f"开始解析Excel文件: {excel_path}")
        
        try:
            # 读取所有sheet
            excel_data = pd.read_excel(excel_path, sheet_name=None, engine='openpyxl')
            
            logger.info(f"成功读取 {len(excel_data)} 个sheet: {list(excel_data.keys())}")
            
            return excel_data
        
        except Exception as e:
            logger.error(f"解析Excel文件失败: {e}")
            return {}
    
    def calculate_low_high_from_data(self, row: pd.Series) -> tuple:
        """
        从T-2和T-1的数据计算最低点和最高点
        
        Args:
            row: DataFrame的一行数据
            
        Returns:
            (low, high) 元组
        """
        # 收集T-2和T-1的最高价和最低价
        values = []
        
        # T-2的高低点
        if 'T_minus_2_high' in row and pd.notna(row['T_minus_2_high']):
            values.append(row['T_minus_2_high'])
        if 'T_minus_2_low' in row and pd.notna(row['T_minus_2_low']):
            values.append(row['T_minus_2_low'])
        
        # T-1的高低点
        if 'T_minus_1_high' in row and pd.notna(row['T_minus_1_high']):
            values.append(row['T_minus_1_high'])
        if 'T_minus_1_low' in row and pd.notna(row['T_minus_1_low']):
            values.append(row['T_minus_1_low'])
        
        if not values:
            return None, None
        
        # 计算过去三根K线的最低点和最高点
        # 注意：Excel中只有T-2和T-1，所以这里实际计算的是过去两根K线
        low = min(values)
        high = max(values)
        
        return low, high
    
    def import_sheet_to_db(self, sheet_name: str, df: pd.DataFrame, 
                          exchange: str = 'bn', date: str = None) -> int:
        """
        将单个sheet的数据导入数据库
        
        Args:
            sheet_name: sheet名称
            df: DataFrame数据
            exchange: 交易所名称，默认为'bn' (binance)
            date: 日期，默认为当天
            
        Returns:
            成功导入的记录数
        """
        if df.empty:
            logger.warning(f"Sheet '{sheet_name}' 没有数据")
            return 0
        
        # 获取时间粒度
        interval = self.INTERVAL_MAPPING.get(sheet_name, '1D')
        
        # 获取日期
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"开始导入 '{sheet_name}' 到数据库...")
        logger.info(f"  交易所: {exchange}, 日期: {date}, 时间粒度: {interval}")
        
        success_count = 0
        
        with self.db:
            for idx, row in df.iterrows():
                try:
                    # 获取ticker名称
                    ticker = str(row['symbol']).strip()
                    
                    # 计算最低点和最高点
                    low, high = self.calculate_low_high_from_data(row)
                    
                    if low is None or high is None:
                        logger.warning(f"  跳过 {ticker}: 无法计算最高/最低价")
                        continue
                    
                    # current_price 填high的值（按用户要求）
                    current_price = high
                    
                    # 添加到监控表
                    self.db.add_monitor(
                        exchange=exchange,
                        date=date,
                        interval=interval,
                        ticker=ticker,
                        high=float(high),
                        low=float(low),
                        current_price=float(current_price)
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"  导入记录失败 {row.get('symbol', 'Unknown')}: {e}")
                    continue
        
        logger.info(f"  ✓ 成功导入 {success_count} 条记录")
        return success_count
    
    def import_excel_to_db(self, excel_path: str = None, exchange: str = 'bn') -> Dict[str, int]:
        """
        导入Excel文件到数据库
        
        Args:
            excel_path: Excel文件路径，如果不提供则自动查找最新文件
            exchange: 交易所名称，默认为'bn'
            
        Returns:
            每个sheet的导入结果统计
        """
        logger.info("=" * 80)
        logger.info("开始导入Excel数据到数据库")
        logger.info("=" * 80)
        
        # 如果没有提供文件路径，自动查找最新文件
        if excel_path is None:
            excel_path = self.get_latest_qualified_tokens_file()
            if excel_path is None:
                logger.error("无法找到Excel文件")
                return {}
        
        # 检查文件是否存在
        if not os.path.exists(excel_path):
            logger.error(f"文件不存在: {excel_path}")
            return {}
        
        # 解析Excel文件
        excel_data = self.parse_excel_file(excel_path)
        
        if not excel_data:
            logger.error("Excel文件为空或解析失败")
            return {}
        
        # 获取当天日期
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 导入每个sheet
        results = {}
        total_count = 0
        
        for sheet_name, df in excel_data.items():
            count = self.import_sheet_to_db(sheet_name, df, exchange=exchange, date=today)
            results[sheet_name] = count
            total_count += count
        
        # 显示统计信息
        logger.info("\n" + "=" * 80)
        logger.info("导入完成统计")
        logger.info("=" * 80)
        logger.info(f"文件: {os.path.basename(excel_path)}")
        logger.info(f"交易所: {exchange}")
        logger.info(f"日期: {today}")
        logger.info(f"总计导入: {total_count} 条记录")
        logger.info("\n各周期详情:")
        for sheet_name, count in results.items():
            logger.info(f"  {sheet_name}: {count} 条")
        
        # 显示数据库统计
        with self.db:
            stats = self.db.get_monitor_stats()
            logger.info(f"\n数据库当前状态:")
            logger.info(f"  总记录数: {stats['total_monitors']}")
            logger.info(f"  按交易所: {stats['by_exchange']}")
            logger.info(f"  按时间粒度: {stats['by_interval']}")
        
        logger.info("=" * 80)
        
        return results


def main():
    """命令行测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description='导入Excel数据到数据库')
    parser.add_argument('--file', '-f', help='Excel文件路径（可选，不提供则自动查找最新文件）')
    parser.add_argument('--exchange', '-e', default='bn', help='交易所名称，默认为bn')
    
    args = parser.parse_args()
    
    # 创建导入器
    importer = ExcelToDBImporter()
    
    # 执行导入
    results = importer.import_excel_to_db(
        excel_path=args.file,
        exchange=args.exchange
    )
    
    if results:
        print("\n✅ 导入成功！")
    else:
        print("\n❌ 导入失败")


if __name__ == "__main__":
    main()

