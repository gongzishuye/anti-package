#!/usr/bin/env python3
"""
贵金属反包检测器
基于 MetalPriceAPI 数据检测反包形态的贵金属
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from pathlib import Path

# 添加项目路径以支持绝对导入
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from src.metal.metalpriceapi_fetcher import MetalPriceAPIFetcher
else:
    from .metalpriceapi_fetcher import MetalPriceAPIFetcher

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetalReversalDetector:
    """贵金属反包检测器"""
    
    def __init__(self, api_key: str = None, data_dir: str = None):
        """
        初始化反包检测器
        
        Args:
            api_key: MetalPriceAPI API 密钥
            data_dir: 数据存储目录
        """
        self.fetcher = MetalPriceAPIFetcher(api_key=api_key)
        
        # 设置数据目录
        if data_dir is None:
            # 获取当前文件所在目录
            current_dir = Path(__file__).parent
            self.data_dir = current_dir / 'data'
        else:
            self.data_dir = Path(data_dir)
        
        # 创建数据目录
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 历史数据文件路径
        self.history_file = self.data_dir / 'metal_daily_history.xlsx'
        
        # 支持的贵金属列表
        self.supported_metals = ['XAU', 'XAG']  # 黄金、白银
        
        logger.info(f"✓ 贵金属反包检测器初始化成功")
        logger.info(f"  数据目录: {self.data_dir}")
        logger.info(f"  支持的贵金属: {', '.join(self.supported_metals)}")
    
    def get_trading_date(self, days_back: int = 0) -> str:
        """
        获取交易日日期（跳过周末）
        
        Args:
            days_back: 往前推几个交易日，0表示今天
            
        Returns:
            日期字符串 YYYY-MM-DD
        """
        target_date = datetime.now()
        
        # 如果今天是周末，往回找最近的交易日
        while target_date.weekday() >= 5:
            target_date -= timedelta(days=1)
        
        # 再往前推 days_back 个交易日
        for _ in range(days_back):
            target_date -= timedelta(days=1)
            while target_date.weekday() >= 5:
                target_date -= timedelta(days=1)
        
        return target_date.strftime('%Y-%m-%d')
    
    def get_existing_sheets(self) -> List[str]:
        """
        获取历史数据文件中已有的 sheet 名称
        
        Returns:
            sheet 名称列表
        """
        if not self.history_file.exists():
            return []
        
        try:
            with pd.ExcelFile(self.history_file) as xls:
                return xls.sheet_names
        except Exception as e:
            logger.error(f"读取历史文件失败: {e}")
            return []
    
    def cleanup_old_data(self, keep_weeks: int = 3):
        """
        清理旧数据，只保留指定周数的数据
        
        Args:
            keep_weeks: 保留的周数，默认 3 周
        """
        if not self.history_file.exists():
            return
        
        try:
            # 读取现有数据
            with pd.ExcelFile(self.history_file) as xls:
                existing_data = {sheet: pd.read_excel(xls, sheet) for sheet in xls.sheet_names}
            
            if not existing_data:
                return
            
            # 计算截止日期（保留 keep_weeks 周的数据）
            cutoff_date = datetime.now() - timedelta(weeks=keep_weeks)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            
            # 过滤数据，只保留截止日期之后的数据
            filtered_data = {}
            removed_count = 0
            
            for sheet_name, sheet_df in existing_data.items():
                try:
                    # 尝试将 sheet_name 解析为日期
                    sheet_date = datetime.strptime(sheet_name, '%Y-%m-%d')
                    if sheet_date >= cutoff_date:
                        filtered_data[sheet_name] = sheet_df
                    else:
                        removed_count += 1
                        logger.info(f"  删除过期数据: {sheet_name}")
                except ValueError:
                    # 如果不是日期格式，保留（可能是其他类型的 sheet）
                    filtered_data[sheet_name] = sheet_df
            
            if removed_count > 0:
                # 保存清理后的数据
                with pd.ExcelWriter(self.history_file, engine='openpyxl') as writer:
                    for sheet_name, sheet_df in filtered_data.items():
                        sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                logger.info(f"✓ 清理完成，删除了 {removed_count} 个过期 sheet")
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def save_daily_data(self, date: str, df: pd.DataFrame):
        """
        保存每日数据到 Excel
        
        Args:
            date: 日期字符串 YYYY-MM-DD
            df: 数据 DataFrame
        """
        try:
            # 读取现有数据
            existing_data = {}
            if self.history_file.exists():
                with pd.ExcelFile(self.history_file) as xls:
                    for sheet in xls.sheet_names:
                        existing_data[sheet] = pd.read_excel(xls, sheet)
            
            # 确保symbol字段是字符串类型
            if 'symbol' in df.columns:
                df['symbol'] = df['symbol'].astype(str).str.strip()
            
            # 添加日期字段
            if 'date' not in df.columns:
                df['date'] = date
            
            # 过滤掉不需要的列，只保留必要的列
            required_cols = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'date']
            available_cols = [col for col in required_cols if col in df.columns]
            df_filtered = df[available_cols].copy()
            
            # 更新或添加当前日期的数据
            existing_data[date] = df_filtered
            
            # 保存到 Excel（每个日期一个 sheet）
            with pd.ExcelWriter(self.history_file, engine='openpyxl') as writer:
                for sheet_name, sheet_df in existing_data.items():
                    # 确保symbol字段是字符串类型
                    if 'symbol' in sheet_df.columns:
                        sheet_df['symbol'] = sheet_df['symbol'].astype(str).str.strip()
                    
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            file_size = self.history_file.stat().st_size / 1024 / 1024  # MB
            logger.info(f"✓ 日期 {date} 的数据已保存")
            logger.info(f"  文件: {self.history_file}")
            logger.info(f"  文件大小: {file_size:.2f} MB")
            logger.info(f"  sheet 数量: {len(existing_data)}")
            
            # 保存后清理旧数据（保留3周）
            self.cleanup_old_data(keep_weeks=3)
            
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def load_daily_data(self, date: str) -> Optional[pd.DataFrame]:
        """
        从 Excel 文件加载指定日期的数据
        
        Args:
            date: 日期字符串 YYYY-MM-DD
            
        Returns:
            数据 DataFrame，如果不存在则返回 None
        """
        if not self.history_file.exists():
            return None
        
        try:
            df = pd.read_excel(self.history_file, sheet_name=date)
            logger.info(f"✓ 加载日期 {date} 的数据: {len(df)} 条记录")
            return df
        except ValueError:
            # sheet 不存在
            return None
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return None
    
    def ensure_data_available(self, dates: List[str]) -> Dict[str, pd.DataFrame]:
        """
        确保指定日期的数据可用，如果不存在则获取
        
        Args:
            dates: 日期列表
            
        Returns:
            日期到DataFrame的字典
        """
        result = {}
        
        for date in dates:
            # 先尝试从文件加载
            df = self.load_daily_data(date)
            
            if df is None or df.empty:
                # 数据不存在，需要获取
                logger.info(f"日期 {date} 的数据不存在，开始获取...")
                
                # 获取所有贵金属的数据
                all_data = []
                for metal in self.supported_metals:
                    logger.info(f"  获取 {metal}/USD {date} 的数据...")
                    ohlc_data = self.fetcher.get_ohlc(metal, 'USD', date)
                    
                    if ohlc_data:
                        rate = ohlc_data.get('rate', {})
                        timestamp = ohlc_data.get('timestamp', 0)
                        
                        # 将时间戳转换为datetime
                        if timestamp:
                            dt = datetime.fromtimestamp(timestamp)
                        else:
                            dt = datetime.strptime(date, '%Y-%m-%d')
                        
                        all_data.append({
                            'symbol': f'{metal}/USD',
                            'timestamp': dt.replace(hour=0, minute=0, second=0, microsecond=0),
                            'open': float(rate.get('open', 0)),
                            'high': float(rate.get('high', 0)),
                            'low': float(rate.get('low', 0)),
                            'close': float(rate.get('close', 0)),
                            'date': date
                        })
                
                if all_data:
                    df = pd.DataFrame(all_data)
                    # 保存数据
                    self.save_daily_data(date, df)
                    logger.info(f"✓ 日期 {date} 的数据已获取并保存")
                else:
                    logger.warning(f"✗ 日期 {date} 未能获取到数据")
                    continue
            
            result[date] = df
        
        return result
    
    def detect_reversal_pattern(self, df_t2: pd.DataFrame, df_t1: pd.DataFrame) -> pd.DataFrame:
        """
        检测反包形态
        
        反包定义（针对贵金属，由于没有成交量，使用价格变化幅度作为替代指标）:
        1. T-1的价格变化幅度（绝对值）大于T-2的价格变化幅度（绝对值）
        2. T-2是阴线（收盘价低于开盘价）
        3. T-1是阳线（开盘价低于收盘价）且T-1收盘价大于T-2的开盘价
        
        Args:
            df_t2: T-2（前天）的数据
            df_t1: T-1（昨天）的数据
            
        Returns:
            符合反包条件的贵金属 DataFrame
        """
        logger.info("开始检测反包形态...")
        
        # 确保两个数据集都有必要的列
        required_cols = ['symbol', 'open', 'close']
        for col in required_cols:
            if col not in df_t2.columns or col not in df_t1.columns:
                logger.error(f"缺少必要列: {col}")
                return pd.DataFrame()
        
        # 合并T-2和T-1的数据
        merged = pd.merge(
            df_t2[['symbol', 'open', 'high', 'low', 'close']].rename(columns={
                'open': 'open_t2',
                'high': 'high_t2',
                'low': 'low_t2',
                'close': 'close_t2'
            }),
            df_t1[['symbol', 'open', 'high', 'low', 'close']].rename(columns={
                'open': 'open_t1',
                'high': 'high_t1',
                'low': 'low_t1',
                'close': 'close_t1'
            }),
            on='symbol',
            how='inner'
        )
        
        logger.info(f"合并后的贵金属数量: {len(merged)}")
        
        # 计算价格变化幅度（作为成交量的替代指标）
        merged['price_change_t2'] = abs(merged['close_t2'] - merged['open_t2'])
        merged['price_change_t1'] = abs(merged['close_t1'] - merged['open_t1'])
        
        # 应用反包条件
        reversal_metals = merged[
            # 条件 1: T-1的价格变化幅度大于T-2（替代成交量条件）
            (merged['price_change_t1'] > merged['price_change_t2']) &
            
            # 条件 2: T-2是阴线（收盘价低于开盘价）
            (merged['close_t2'] < merged['open_t2']) &
            
            # 条件 3: T-1是阳线（开盘价低于收盘价）
            (merged['open_t1'] < merged['close_t1']) &
            
            # 条件 4: T-1收盘价大于T-2的开盘价
            (merged['close_t1'] > merged['open_t2'])
        ].copy()
        
        if not reversal_metals.empty:
            # 计算额外指标
            reversal_metals['t2_change_pct'] = ((reversal_metals['close_t2'] - reversal_metals['open_t2']) / reversal_metals['open_t2']) * 100
            reversal_metals['t1_change_pct'] = ((reversal_metals['close_t1'] - reversal_metals['open_t1']) / reversal_metals['open_t1']) * 100
            reversal_metals['price_change_increase_pct'] = ((reversal_metals['price_change_t1'] - reversal_metals['price_change_t2']) / reversal_metals['price_change_t2']) * 100
            reversal_metals['reversal_strength'] = reversal_metals['close_t1'] - reversal_metals['open_t2']
            
            # 按反包强度排序（使用价格变化增幅）
            reversal_metals = reversal_metals.sort_values('price_change_increase_pct', ascending=False)
        
        logger.info(f"✓ 检测完成，符合反包条件的贵金属: {len(reversal_metals)} 个")
        
        return reversal_metals
    
    def save_reversal_results(self, date: str, df: pd.DataFrame):
        """
        保存反包检测结果
        
        Args:
            date: 检测日期
            df: 结果 DataFrame
        """
        # 即使结果为空，也保存以更新文件时间戳
        if df.empty:
            logger.info("反包结果为空，保存空结果以更新文件时间戳")
            # 创建一个空的DataFrame，包含必要的列
            df = pd.DataFrame(columns=['symbol', 'open_t2', 'close_t2', 'high_t2', 'low_t2', 
                                       't2_change_pct', 'open_t1', 'close_t1', 
                                       'high_t1', 'low_t1', 't1_change_pct', 
                                       'price_change_increase_pct', 'reversal_strength'])
        
        # 结果文件路径
        result_file = self.data_dir / 'metal_reversal_results.xlsx'
        
        try:
            # 确保symbol字段是字符串类型
            if 'symbol' in df.columns:
                df['symbol'] = df['symbol'].astype(str).str.strip()
            
            # 读取现有结果
            if result_file.exists():
                with pd.ExcelFile(result_file) as xls:
                    existing_results = {}
                    for sheet in xls.sheet_names:
                        sheet_df = pd.read_excel(xls, sheet, dtype={'symbol': str})
                        if 'symbol' in sheet_df.columns:
                            sheet_df['symbol'] = sheet_df['symbol'].astype(str).str.strip()
                        existing_results[sheet] = sheet_df
            else:
                existing_results = {}
            
            # 添加或更新当前日期的结果
            existing_results[date] = df
            
            # 保存到 Excel
            with pd.ExcelWriter(result_file, engine='openpyxl') as writer:
                for sheet_name, sheet_df in existing_results.items():
                    # 确保symbol字段是字符串类型
                    if 'symbol' in sheet_df.columns:
                        sheet_df['symbol'] = sheet_df['symbol'].astype(str).str.strip()
                    
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            file_size = result_file.stat().st_size / 1024 / 1024  # MB
            logger.info(f"✓ 反包结果已保存")
            logger.info(f"  文件: {result_file}")
            logger.info(f"  日期: {date}")
            logger.info(f"  符合条件贵金属: {len(df)} 个")
            logger.info(f"  文件大小: {file_size:.2f} MB")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            import traceback
            traceback.print_exc()
    
    def run_reversal_detection(self) -> pd.DataFrame:
        """
        运行反包检测流程
        
        Returns:
            符合反包条件的贵金属 DataFrame
        """
        logger.info("="*80)
        logger.info("贵金属反包检测流程开始")
        logger.info("="*80)
        
        # 获取日期
        today = self.get_trading_date(0)
        t1_date = self.get_trading_date(1)  # 昨天
        t2_date = self.get_trading_date(2)  # 前天
        
        logger.info(f"\n检测参数:")
        logger.info(f"  今天 (T):   {today}")
        logger.info(f"  昨天 (T-1): {t1_date}")
        logger.info(f"  前天 (T-2): {t2_date}")
        
        # 确保数据可用
        logger.info(f"\n检查并获取数据...")
        data_dict = self.ensure_data_available([t2_date, t1_date])
        
        # 检查是否有足够的历史数据（至少需要2条）
        available_dates = list(data_dict.keys())
        if len(available_dates) < 2:
            logger.warning(f"✗ 历史数据不足，无法判断反包")
            logger.warning(f"  需要至少2条历史数据，当前只有 {len(available_dates)} 条")
            logger.warning(f"  可用日期: {available_dates}")
            return pd.DataFrame()
        
        if t2_date not in data_dict or t1_date not in data_dict:
            logger.error("✗ 缺少必要的日期数据，无法进行检测")
            logger.error(f"  需要: T-2 ({t2_date}), T-1 ({t1_date})")
            logger.error(f"  可用: {available_dates}")
            return pd.DataFrame()
        
        # 检测反包形态
        logger.info(f"\n开始反包检测...")
        reversal_metals = self.detect_reversal_pattern(
            df_t2=data_dict[t2_date],
            df_t1=data_dict[t1_date]
        )
        
        # 保存结果（即使为空也保存，以更新文件时间戳）
        self.save_reversal_results(today, reversal_metals)
        
        if not reversal_metals.empty:
            # 打印摘要
            self.print_reversal_summary(reversal_metals, t2_date, t1_date, today)
        else:
            logger.info("未找到符合反包条件的贵金属")
        
        logger.info("\n" + "="*80)
        logger.info("反包检测流程完成")
        logger.info("="*80)
        
        return reversal_metals
    
    def print_reversal_summary(self, df: pd.DataFrame, t2_date: str, t1_date: str, today: str):
        """
        打印反包检测结果摘要
        
        Args:
            df: 结果 DataFrame
            t2_date: T-2 日期
            t1_date: T-1 日期
            today: 今天日期
        """
        print("\n" + "="*80)
        print("反包检测结果摘要")
        print("="*80)
        
        print(f"\n检测日期: {today}")
        print(f"数据范围: {t2_date} (T-2) → {t1_date} (T-1)")
        print(f"符合条件贵金属数量: {len(df)}")
        
        if len(df) > 0:
            print("\n反包强度详情:")
            print("-"*80)
            
            for idx, row in df.iterrows():
                print(f"\n{row['symbol']}")
                print(f"  T-2: 开盘 ${row['open_t2']:8.2f}, 收盘 ${row['close_t2']:8.2f}, 涨跌 {row['t2_change_pct']:+6.2f}%")
                print(f"  T-1: 开盘 ${row['open_t1']:8.2f}, 收盘 ${row['close_t1']:8.2f}, 涨跌 {row['t1_change_pct']:+6.2f}%")
                print(f"  价格变化增幅: {row['price_change_increase_pct']:+.1f}%")
                print(f"  反包强度: ${row['reversal_strength']:.2f}")
            
            print("\n" + "-"*80)
            
            # 统计信息
            print("\n统计信息:")
            print(f"  平均价格变化增幅: {df['price_change_increase_pct'].mean():.1f}%")
            print(f"  平均 T-1 涨幅: {df['t1_change_pct'].mean():.2f}%")
            print(f"  平均 T-2 跌幅: {df['t2_change_pct'].mean():.2f}%")
        
        print("\n" + "="*80)


def main():
    """主函数 - 测试用"""
    print("\n" + "🚀"*40)
    print("贵金属反包检测器")
    print("🚀"*40)
    
    try:
        # 创建检测器
        detector = MetalReversalDetector()
        
        # 运行反包检测
        results = detector.run_reversal_detection()
        
        if not results.empty:
            print(f"\n✓ 检测完成！找到 {len(results)} 个符合反包条件的贵金属")
            print(f"\n结果已保存到: {detector.data_dir / 'metal_reversal_results.xlsx'}")
        else:
            print("\n未找到符合反包条件的贵金属")
        
        print("\n" + "🎉"*40)
        
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
