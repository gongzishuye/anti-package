#!/usr/bin/env python3
"""
美股反包检测器
基于 Polygon.io 数据检测反包形态的股票
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path

# 添加项目路径以支持绝对导入
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from src.equity.polygon_us_stock_fetcher import PolygonUSStockFetcher
    from src.equity.em_us_stock_fetcher import EMUSStockFetcher
else:
    from .polygon_us_stock_fetcher import PolygonUSStockFetcher
    from .em_us_stock_fetcher import EMUSStockFetcher

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class USStockReversalDetector:
    """美股反包检测器"""
    
    def __init__(self, api_key: str = None, data_dir: str = None, use_em_api: bool = True, em_api_url: str = None):
        """
        初始化反包检测器
        
        Args:
            api_key: Polygon.io API 密钥（当 use_em_api=False 时使用）
            data_dir: 数据存储目录
            use_em_api: 是否使用 EM API，默认 True
            em_api_url: EM API 地址，默认 http://127.0.0.1:8080/api/public/stock_us_spot_em
        """
        # 选择数据获取器
        if use_em_api:
            self.fetcher = EMUSStockFetcher(api_url=em_api_url)
            logger.info("使用 EM API 数据源")
        else:
            self.fetcher = PolygonUSStockFetcher(api_key=api_key)
            logger.info("使用 Polygon.io API 数据源")
        
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
        self.history_file = self.data_dir / 'us_stock_daily_history.xlsx'
        
        logger.info(f"✓ 反包检测器初始化成功")
        logger.info(f"  数据目录: {self.data_dir}")
    
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
                
                logger.info(f"✓ 数据清理完成，删除了 {removed_count} 个过期 sheet，保留 {len(filtered_data)} 个 sheet")
            else:
                logger.info(f"✓ 数据清理完成，无需删除数据（所有数据都在 {keep_weeks} 周内）")
            
        except Exception as e:
            logger.error(f"清理数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def save_daily_data(self, date: str, df: pd.DataFrame):
        """
        保存每日数据到 Excel 文件的指定 sheet
        
        注意：只保留成交额大于1000万的标的
        
        Args:
            date: 日期字符串 YYYY-MM-DD
            df: 数据 DataFrame
        """
        if df.empty:
            logger.warning(f"日期 {date} 的数据为空，跳过保存")
            return
        
        try:
            # 过滤成交额小于1000万的标的
            min_turnover = 10000000  # 1000万
            original_count = len(df)
            
            # 计算或获取成交额
            if 'turnover' in df.columns:
                # 使用数据中的成交额字段
                df_filtered = df[df['turnover'] >= min_turnover].copy()
            elif 'vwap' in df.columns and 'volume' in df.columns:
                # 计算成交额：vwap * volume
                df['turnover'] = df['vwap'] * df['volume']
                df_filtered = df[df['turnover'] >= min_turnover].copy()
            elif 'close' in df.columns and 'volume' in df.columns:
                # 使用收盘价 * 成交量作为近似值
                df['turnover'] = df['close'] * df['volume']
                df_filtered = df[df['turnover'] >= min_turnover].copy()
            else:
                logger.warning(f"日期 {date} 的数据无法计算成交额，跳过过滤")
                df_filtered = df.copy()
            
            filtered_count = len(df_filtered)
            removed_count = original_count - filtered_count
            
            if removed_count > 0:
                logger.info(f"✓ 成交额过滤: {original_count} → {filtered_count} 只股票 (成交额 >= {min_turnover/1e6:.0f}万，已过滤 {removed_count} 只)")
            
            # 读取现有数据
            if self.history_file.exists():
                with pd.ExcelFile(self.history_file) as xls:
                    existing_data = {sheet: pd.read_excel(xls, sheet) for sheet in xls.sheet_names}
            else:
                existing_data = {}
            
            # 添加或更新当前日期的数据（使用过滤后的数据）
            existing_data[date] = df_filtered
            
            # 保存到 Excel（每个日期一个 sheet）
            with pd.ExcelWriter(self.history_file, engine='openpyxl') as writer:
                for sheet_name, sheet_df in existing_data.items():
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
        
        注意：API只能获取昨天的数据，所以如果T-2数据不存在，无法通过API获取
        
        Args:
            dates: 日期列表（通常包含T-2和T-1）
            
        Returns:
            日期到 DataFrame 的字典
        """
        result = {}
        existing_sheets = self.get_existing_sheets()
        
        # 计算昨天的日期（API只能获取这个日期的数据）
        yesterday = self.get_trading_date(1)
        
        for date in dates:
            if date in existing_sheets:
                # 数据已存在，直接加载
                df = self.load_daily_data(date)
                if df is not None:
                    result[date] = df
                    logger.info(f"✓ 日期 {date} 的数据已存在")
                else:
                    # 加载失败，尝试重新获取
                    logger.warning(f"日期 {date} 数据加载失败，尝试重新获取...")
                    # 只有昨天的数据可以通过API获取
                    if date == yesterday:
                        df = self.fetcher.get_daily_market_summary(date)
                        if not df.empty:
                            self.save_daily_data(date, df)
                            result[date] = df
                        else:
                            logger.warning(f"✗ 日期 {date} 未获取到数据（可能是非交易日）")
                    else:
                        logger.error(f"✗ 日期 {date} 的数据不存在，且无法通过API获取（API只能获取昨天({yesterday})的数据）")
            else:
                # 数据不存在，尝试获取
                logger.info(f"日期 {date} 的数据不存在，开始获取...")
                # 只有昨天的数据可以通过API获取
                if date == yesterday:
                    df = self.fetcher.get_daily_market_summary(date)
                    if not df.empty:
                        self.save_daily_data(date, df)
                        result[date] = df
                        logger.info(f"✓ 日期 {date} 的数据已获取并保存")
                    else:
                        logger.warning(f"✗ 日期 {date} 未获取到数据（可能是非交易日）")
                else:
                    logger.error(f"✗ 日期 {date} 的数据不存在，且无法通过API获取（API只能获取昨天({yesterday})的数据）")
                    logger.error(f"  请确保历史数据已正确保存到Excel文件中")
        
        return result
    
    def detect_reversal_pattern(self, df_t2: pd.DataFrame, df_t1: pd.DataFrame, 
                                min_turnover: float = 10000000, 
                                fetch_market_cap: bool = True,
                                min_market_cap: float = 0) -> pd.DataFrame:
        """
        检测反包形态
        
        反包定义:
        1. T-1的成交额大于T-2（使用成交额而不是成交量）
        2. T-2是阴线（收盘价低于开盘价）
        3. T-1是阳线（开盘价低于收盘价）且T-1收盘价大于T-2的开盘价
        4. T-1的交易额 >= min_turnover (默认1000万)
        5. 市值 >= min_market_cap (可选，默认不限制)
        
        Args:
            df_t2: T-2（前天）的数据
            df_t1: T-1（昨天）的数据
            min_turnover: T-1 最小交易额，默认 10000000 (1000万)
            fetch_market_cap: 是否获取市值数据，默认 True
            min_market_cap: 最小市值，默认 0 (不限制)。例如: 1000000000 (10亿美金)
            
        Returns:
            符合反包条件的股票 DataFrame
        """
        logger.info("开始检测反包形态...")
        
        # 确保两个数据集都有必要的列
        required_cols = ['symbol', 'open', 'close', 'volume']
        for col in required_cols:
            if col not in df_t2.columns or col not in df_t1.columns:
                logger.error(f"缺少必要列: {col}")
                return pd.DataFrame()
        
        # 检查是否有 vwap 和 turnover 列
        t2_cols = ['symbol', 'open', 'close', 'volume', 'high', 'low']
        t1_cols = ['symbol', 'open', 'close', 'volume', 'high', 'low']
        
        if 'vwap' in df_t2.columns:
            t2_cols.append('vwap')
        if 'vwap' in df_t1.columns:
            t1_cols.append('vwap')
        
        # 优先使用数据中的成交额字段
        if 'turnover' in df_t2.columns:
            t2_cols.append('turnover')
        if 'turnover' in df_t1.columns:
            t1_cols.append('turnover')
        
        # 添加市值字段（如果存在）
        if 'market_cap' in df_t2.columns:
            t2_cols.append('market_cap')
        if 'market_cap' in df_t1.columns:
            t1_cols.append('market_cap')
        
        # 添加名称字段（如果存在）
        if 'name' in df_t2.columns:
            t2_cols.append('name')
        if 'name' in df_t1.columns:
            t1_cols.append('name')
        
        # 合并数据（按 symbol）
        merged = pd.merge(
            df_t2[t2_cols],
            df_t1[t1_cols],
            on='symbol',
            suffixes=('_t2', '_t1')
        )
        
        logger.info(f"合并后的股票数量: {len(merged)}")
        
        # 计算 T-2 和 T-1 的交易额（优先使用数据中的成交额，否则计算）
        if 'turnover_t2' in merged.columns:
            # 使用数据中的成交额
            pass
        elif 'vwap_t2' in merged.columns:
            merged['turnover_t2'] = merged['vwap_t2'] * merged['volume_t2']
        else:
            # 如果没有 vwap，使用收盘价作为近似值
            logger.warning("未找到 vwap 列，使用收盘价计算 T-2 交易额")
            merged['turnover_t2'] = merged['close_t2'] * merged['volume_t2']
        
        if 'turnover_t1' in merged.columns:
            # 使用数据中的成交额
            pass
        elif 'vwap_t1' in merged.columns:
            merged['turnover_t1'] = merged['vwap_t1'] * merged['volume_t1']
        else:
            # 如果没有 vwap，使用收盘价作为近似值
            logger.warning("未找到 vwap 列，使用收盘价计算 T-1 交易额")
            merged['turnover_t1'] = merged['close_t1'] * merged['volume_t1']
        
        # 应用反包条件
        reversal_stocks = merged[
            # 条件 1: T-1的成交额大于T-2（使用成交额而不是成交量）
            (merged['turnover_t1'] > merged['turnover_t2']) &
            
            # 条件 2: T-2是阴线（收盘价低于开盘价）
            (merged['close_t2'] < merged['open_t2']) &
            
            # 条件 3: T-1是阳线（开盘价低于收盘价）
            (merged['open_t1'] < merged['close_t1']) &
            
            # 条件 4: T-1收盘价大于T-2的开盘价
            (merged['close_t1'] > merged['open_t2']) &
            
            # 条件 5: T-1交易额大于等于最小交易额 (默认1000万)
            (merged['turnover_t1'] >= min_turnover)
        ].copy()
        
        if not reversal_stocks.empty:
            # 计算额外指标
            reversal_stocks['t2_change_pct'] = ((reversal_stocks['close_t2'] - reversal_stocks['open_t2']) / reversal_stocks['open_t2']) * 100
            reversal_stocks['t1_change_pct'] = ((reversal_stocks['close_t1'] - reversal_stocks['open_t1']) / reversal_stocks['open_t1']) * 100
            # 使用成交额增幅而不是成交量增幅
            reversal_stocks['turnover_increase_pct'] = ((reversal_stocks['turnover_t1'] - reversal_stocks['turnover_t2']) / reversal_stocks['turnover_t2']) * 100
            reversal_stocks['reversal_strength'] = reversal_stocks['close_t1'] - reversal_stocks['open_t2']
            
            # 获取市值数据（如果需要）
            if fetch_market_cap or min_market_cap > 0:
                # 检查数据中是否已有市值字段（合并后可能是 market_cap_t1 或 market_cap_t2）
                if 'market_cap_t1' in reversal_stocks.columns:
                    # 使用 T-1 的市值（更准确）
                    reversal_stocks['market_cap'] = reversal_stocks['market_cap_t1']
                    logger.info("使用数据中已有的市值字段 (market_cap_t1)")
                elif 'market_cap_t2' in reversal_stocks.columns:
                    # 使用 T-2 的市值作为备选
                    reversal_stocks['market_cap'] = reversal_stocks['market_cap_t2']
                    logger.info("使用数据中已有的市值字段 (market_cap_t2)")
                elif 'market_cap' in reversal_stocks.columns:
                    logger.info("使用数据中已有的市值字段")
                elif hasattr(self.fetcher, 'get_multiple_ticker_details'):
                    logger.info("正在获取股票市值数据...")
                    symbols = reversal_stocks['symbol'].tolist()
                    market_cap_df = self.fetcher.get_multiple_ticker_details(symbols, delay=0.25)
                    
                    if not market_cap_df.empty:
                        # 合并市值数据
                        reversal_stocks = pd.merge(
                            reversal_stocks,
                            market_cap_df[['symbol', 'market_cap', 'name', 'weighted_shares_outstanding']],
                            on='symbol',
                            how='left'
                        )
                        logger.info(f"✓ 成功获取 {len(market_cap_df)} 只股票的市值数据")
                    else:
                        logger.warning("未获取到市值数据")
                        reversal_stocks['market_cap'] = 0
                        reversal_stocks['name'] = ''
                else:
                    logger.warning("数据获取器不支持获取市值详情，使用默认值")
                    reversal_stocks['market_cap'] = 0
                    if 'name' not in reversal_stocks.columns:
                        reversal_stocks['name'] = ''
                
                # 确保市值字段不为空
                reversal_stocks['market_cap'] = reversal_stocks['market_cap'].fillna(0)
                
                # 处理名称字段
                if 'name_t1' in reversal_stocks.columns:
                    reversal_stocks['name'] = reversal_stocks['name_t1']
                elif 'name_t2' in reversal_stocks.columns:
                    reversal_stocks['name'] = reversal_stocks['name_t2']
                elif 'name' not in reversal_stocks.columns:
                    reversal_stocks['name'] = ''
                reversal_stocks['name'] = reversal_stocks['name'].fillna('')
                
                # 应用市值过滤条件
                if min_market_cap > 0:
                    before_filter = len(reversal_stocks)
                    reversal_stocks = reversal_stocks[
                        (reversal_stocks['market_cap'].notna()) & 
                        (reversal_stocks['market_cap'] >= min_market_cap)
                    ].copy()
                    logger.info(f"✓ 市值过滤: {before_filter} → {len(reversal_stocks)} 只 (市值 >= ${min_market_cap/1e9:.1f}B)")
            
            # 按反包强度排序（使用成交额增幅）
            reversal_stocks = reversal_stocks.sort_values('turnover_increase_pct', ascending=False)
        
        logger.info(f"✓ 检测完成，符合反包条件的股票: {len(reversal_stocks)} 只")
        logger.info(f"  (交易额过滤条件: >= ${min_turnover:,.0f})")
        
        return reversal_stocks
    
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
                                       'volume_t2', 't2_change_pct', 'open_t1', 'close_t1', 
                                       'high_t1', 'low_t1', 'volume_t1', 't1_change_pct', 
                                       'volume_increase_pct', 'reversal_strength', 'turnover_t1',
                                       'market_cap', 'name'])
        
        # 结果文件路径
        result_file = self.data_dir / 'us_stock_reversal_results.xlsx'
        
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
                    
                    # 设置symbol列为文本格式
                    if 'symbol' in sheet_df.columns:
                        worksheet = writer.sheets[sheet_name]
                        symbol_col_idx = list(sheet_df.columns).index('symbol') + 1
                        symbol_col_letter = worksheet.cell(row=1, column=symbol_col_idx).column_letter
                        for row in range(2, len(sheet_df) + 2):
                            cell = worksheet[f'{symbol_col_letter}{row}']
                            cell.number_format = '@'  # @表示文本格式
            
            file_size = result_file.stat().st_size / 1024 / 1024  # MB
            logger.info(f"✓ 反包结果已保存")
            logger.info(f"  文件: {result_file}")
            logger.info(f"  日期: {date}")
            logger.info(f"  符合条件股票: {len(df)} 只")
            logger.info(f"  文件大小: {file_size:.2f} MB")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            import traceback
            traceback.print_exc()
    
    def run_reversal_detection(self, min_market_cap: float = 1000000000) -> pd.DataFrame:
        """
        运行反包检测流程
        
        Args:
            min_market_cap: 最小市值（美元），默认10亿美元
        
        Returns:
            符合反包条件的股票 DataFrame
        """
        logger.info("="*80)
        logger.info("美股反包检测流程开始")
        logger.info("="*80)
        
        # 检查今天是否是周日或周一（美股周末休市，无法计算反包）
        today_weekday = datetime.now().weekday()  # 0=周一, 6=周日
        if today_weekday == 6:  # 周日
            logger.warning("✗ 今天是周日，美股休市，无法计算反包")
            return pd.DataFrame()
        elif today_weekday == 0:  # 周一
            logger.warning("✗ 今天是周一，T-1可能是周末，无法计算反包")
            return pd.DataFrame()
        
        # 获取日期
        today = self.get_trading_date(0)
        t1_date = self.get_trading_date(1)  # 昨天
        t2_date = self.get_trading_date(2)  # 前天
        
        logger.info(f"\n检测参数:")
        logger.info(f"  今天 (T):   {today}")
        logger.info(f"  昨天 (T-1): {t1_date}")
        logger.info(f"  前天 (T-2): {t2_date}")
        logger.info(f"  最小市值: ${min_market_cap/1e9:.1f}B")
        
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
        
        # 检测反包形态（添加市值过滤）
        logger.info(f"\n开始反包检测...")
        reversal_stocks = self.detect_reversal_pattern(
            df_t2=data_dict[t2_date],
            df_t1=data_dict[t1_date],
            min_market_cap=min_market_cap
        )
        
        # 保存结果（即使为空也保存，以更新文件时间戳）
        self.save_reversal_results(today, reversal_stocks)
        
        if not reversal_stocks.empty:
            # 打印摘要
            self.print_reversal_summary(reversal_stocks, t2_date, t1_date, today)
        else:
            logger.warning("未找到符合反包条件的股票")
        
        logger.info("\n" + "="*80)
        logger.info("反包检测流程完成")
        logger.info("="*80)
        
        return reversal_stocks
    
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
        print(f"符合条件股票数量: {len(df)}")
        
        if len(df) > 0:
            print("\n反包强度 TOP 10:")
            print("-"*80)
            
            top_10 = df.head(10)
            
            for idx, row in top_10.iterrows():
                print(f"\n{row['symbol']:6s}")
                print(f"  T-2: 开盘 ${row['open_t2']:8.2f}, 收盘 ${row['close_t2']:8.2f}, 涨跌 {row['t2_change_pct']:+6.2f}%, 成交量 {row['volume_t2']:,.0f}")
                print(f"  T-1: 开盘 ${row['open_t1']:8.2f}, 收盘 ${row['close_t1']:8.2f}, 涨跌 {row['t1_change_pct']:+6.2f}%, 成交量 {row['volume_t1']:,.0f}")
                print(f"  成交额增幅: {row['turnover_increase_pct']:+.1f}%")
                print(f"  反包强度: ${row['reversal_strength']:.2f}")
            
            print("\n" + "-"*80)
            
            # 统计信息
            print("\n统计信息:")
            print(f"  平均成交额增幅: {df['turnover_increase_pct'].mean():.1f}%")
            print(f"  平均 T-1 涨幅: {df['t1_change_pct'].mean():.2f}%")
            print(f"  平均 T-2 跌幅: {df['t2_change_pct'].mean():.2f}%")
        
        print("\n" + "="*80)


def main():
    """主函数 - 测试用"""
    print("\n" + "🚀"*40)
    print("美股反包检测器")
    print("🚀"*40)
    
    try:
        # 创建检测器
        detector = USStockReversalDetector()
        
        # 运行反包检测
        results = detector.run_reversal_detection()
        
        if not results.empty:
            print(f"\n✓ 检测完成！找到 {len(results)} 只符合反包条件的股票")
            print(f"\n结果已保存到: {detector.data_dir / 'us_stock_reversal_results.xlsx'}")
        else:
            print("\n未找到符合反包条件的股票")
        
        print("\n" + "🎉"*40)
        
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

