#!/usr/bin/env python3
"""
美股筛选器
提供美股股票的筛选功能，支持多种筛选条件和策略
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
import logging
from dataclasses import dataclass

from .us_stock_fetcher import USStockFetcher
from .us_stock_analyzer import USStockAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ScreeningCriteria:
    """筛选条件数据类"""
    # 基本面条件
    min_market_cap: float = 0  # 最小市值（亿美元）
    max_market_cap: float = float('inf')  # 最大市值
    min_pe_ratio: float = 0  # 最小市盈率
    max_pe_ratio: float = float('inf')  # 最大市盈率
    min_pb_ratio: float = 0  # 最小市净率
    max_pb_ratio: float = float('inf')  # 最大市净率
    min_dividend_yield: float = 0  # 最小股息率
    max_price: float = float('inf')  # 最大股价
    
    # 技术面条件
    min_volume: int = 0  # 最小成交量
    min_price: float = 0  # 最小股价
    rsi_oversold: float = 30  # RSI超卖阈值
    rsi_overbought: float = 70  # RSI超买阈值
    above_sma_20: bool = None  # 是否高于20日均线
    above_sma_50: bool = None  # 是否高于50日均线
    
    # 行业条件
    exclude_sectors: List[str] = None  # 排除行业
    include_sectors: List[str] = None  # 包含行业
    
    # 其他条件
    exclude_etf: bool = False  # 排除ETF
    exclude_warrants: bool = True  # 排除权证
    min_listing_days: int = 0  # 最小上市天数


@dataclass
class ScreeningResult:
    """筛选结果数据类"""
    stocks: pd.DataFrame
    criteria: ScreeningCriteria
    total_stocks: int
    qualified_stocks: int
    screening_time: datetime
    top_gainers: List[Dict]
    top_losers: List[Dict]


class USStockScreener:
    """美股筛选器"""
    
    def __init__(self, fetcher: USStockFetcher = None, analyzer: USStockAnalyzer = None):
        """
        初始化筛选器
        
        Args:
            fetcher: 数据获取器
            analyzer: 数据分析器
        """
        self.fetcher = fetcher or USStockFetcher()
        self.analyzer = analyzer or USStockAnalyzer()
        logger.info("初始化美股筛选器")
    
    def screen_stocks(self, criteria: ScreeningCriteria = None, 
                     include_analysis: bool = True) -> ScreeningResult:
        """
        筛选股票
        
        Args:
            criteria: 筛选条件
            include_analysis: 是否包含技术分析
            
        Returns:
            筛选结果
        """
        if criteria is None:
            criteria = ScreeningCriteria()
        
        start_time = datetime.now()
        logger.info("开始筛选美股...")
        
        try:
            # 1. 获取所有股票数据
            all_stocks = self._fetch_stock_data(criteria)
            if all_stocks.empty:
                logger.warning("未获取到股票数据")
                return ScreeningResult(
                    stocks=pd.DataFrame(),
                    criteria=criteria,
                    total_stocks=0,
                    qualified_stocks=0,
                    screening_time=start_time,
                    top_gainers=[],
                    top_losers=[]
                )
            
            logger.info(f"获取到 {len(all_stocks)} 只股票")
            
            # 2. 应用筛选条件
            filtered_stocks = self._apply_criteria(all_stocks, criteria)
            logger.info(f"筛选后剩余 {len(filtered_stocks)} 只股票")
            
            # 3. 技术分析（可选）
            if include_analysis and not filtered_stocks.empty:
                filtered_stocks = self._add_technical_analysis(filtered_stocks)
            
            # 4. 计算涨跌幅排行
            top_gainers, top_losers = self._calculate_rankings(filtered_stocks)
            
            # 5. 创建结果对象
            result = ScreeningResult(
                stocks=filtered_stocks,
                criteria=criteria,
                total_stocks=len(all_stocks),
                qualified_stocks=len(filtered_stocks),
                screening_time=start_time,
                top_gainers=top_gainers,
                top_losers=top_losers
            )
            
            logger.info(f"筛选完成: {result.qualified_stocks}/{result.total_stocks} 只股票符合条件")
            return result
            
        except Exception as e:
            logger.error(f"筛选股票失败: {e}")
            return ScreeningResult(
                stocks=pd.DataFrame(),
                criteria=criteria,
                total_stocks=0,
                qualified_stocks=0,
                screening_time=start_time,
                top_gainers=[],
                top_losers=[]
            )
    
    def screen_by_strategy(self, strategy: str, **kwargs) -> ScreeningResult:
        """
        按策略筛选
        
        Args:
            strategy: 策略名称
            **kwargs: 策略参数
            
        Returns:
            筛选结果
        """
        strategies = {
            'value': self._value_strategy,
            'growth': self._growth_strategy,
            'dividend': self._dividend_strategy,
            'momentum': self._momentum_strategy,
            'technical': self._technical_strategy,
            'quality': self._quality_strategy
        }
        
        if strategy not in strategies:
            raise ValueError(f"不支持的策略: {strategy}")
        
        logger.info(f"使用 {strategy} 策略筛选股票")
        criteria = strategies[strategy](**kwargs)
        return self.screen_stocks(criteria, include_analysis=True)
    
    def _fetch_stock_data(self, criteria: ScreeningCriteria) -> pd.DataFrame:
        """获取股票数据"""
        try:
            # 获取股票列表
            stocks_df = self.fetcher.get_all_us_stocks(
                include_etf=not criteria.exclude_etf,
                include_warrant=not criteria.exclude_warrants
            )
            
            if stocks_df.empty:
                return pd.DataFrame()
            
            # 获取实时行情
            stock_codes = stocks_df['symbol'].tolist()
            quotes_df = self.fetcher.get_stock_snapshot(stock_codes[:1000])  # 限制数量
            
            if not quotes_df.empty:
                # 合并数据
                merged_df = pd.merge(
                    stocks_df,
                    quotes_df,
                    left_on='symbol',
                    right_on='code',
                    how='inner'
                )
                return merged_df
            else:
                return stocks_df
                
        except Exception as e:
            logger.error(f"获取股票数据失败: {e}")
            return pd.DataFrame()
    
    def _apply_criteria(self, stocks: pd.DataFrame, criteria: ScreeningCriteria) -> pd.DataFrame:
        """应用筛选条件"""
        if stocks.empty:
            return stocks
        
        filtered = stocks.copy()
        
        try:
            # 基本面筛选
            if 'market_val' in filtered.columns:
                filtered = filtered[
                    (filtered['market_val'] >= criteria.min_market_cap * 1e8) &
                    (filtered['market_val'] <= criteria.max_market_cap * 1e8)
                ]
            
            if 'pe_ratio' in filtered.columns:
                filtered = filtered[
                    (filtered['pe_ratio'] >= criteria.min_pe_ratio) &
                    (filtered['pe_ratio'] <= criteria.max_pe_ratio)
                ]
            
            if 'pb_ratio' in filtered.columns:
                filtered = filtered[
                    (filtered['pb_ratio'] >= criteria.min_pb_ratio) &
                    (filtered['pb_ratio'] <= criteria.max_pb_ratio)
                ]
            
            if 'dividend_yield' in filtered.columns:
                filtered = filtered[
                    (filtered['dividend_yield'] >= criteria.min_dividend_yield)
                ]
            
            # 价格筛选
            if 'last_price' in filtered.columns:
                filtered = filtered[
                    (filtered['last_price'] >= criteria.min_price) &
                    (filtered['last_price'] <= criteria.max_price)
                ]
            
            # 成交量筛选
            if 'volume' in filtered.columns:
                filtered = filtered[
                    filtered['volume'] >= criteria.min_volume
                ]
            
            # 股票类型筛选
            if criteria.exclude_etf and 'stock_type' in filtered.columns:
                filtered = filtered[filtered['stock_type'] != 'ETF']
            
            if criteria.exclude_warrants and 'stock_type' in filtered.columns:
                filtered = filtered[filtered['stock_type'] != 'WARRANT']
            
            # 行业筛选
            if criteria.include_sectors and 'sector' in filtered.columns:
                filtered = filtered[filtered['sector'].isin(criteria.include_sectors)]
            
            if criteria.exclude_sectors and 'sector' in filtered.columns:
                filtered = filtered[~filtered['sector'].isin(criteria.exclude_sectors)]
            
            # 上市时间筛选
            if criteria.min_listing_days > 0 and 'listing_date' in filtered.columns:
                today = datetime.now()
                filtered = filtered[
                    (today - pd.to_datetime(filtered['listing_date'])).dt.days >= criteria.min_listing_days
                ]
            
            return filtered
            
        except Exception as e:
            logger.error(f"应用筛选条件失败: {e}")
            return pd.DataFrame()
    
    def _add_technical_analysis(self, stocks: pd.DataFrame) -> pd.DataFrame:
        """添加技术分析"""
        if stocks.empty:
            return stocks
        
        analyzed_stocks = []
        
        for _, stock in stocks.iterrows():
            try:
                symbol = stock['symbol']
                
                # 获取历史数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
                
                kline_data = self.fetcher.get_stock_kline(symbol, start_date, end_date)
                
                if not kline_data.empty:
                    # 技术分析
                    technical = self.analyzer.calculate_technical_indicators(kline_data)
                    trend = self.analyzer.analyze_price_trend(kline_data)
                    volatility = self.analyzer.calculate_volatility(kline_data)
                    
                    # 添加技术指标
                    stock_data = stock.copy()
                    stock_data['rsi'] = technical.rsi
                    stock_data['macd'] = technical.macd
                    stock_data['sma_20'] = technical.sma_20
                    stock_data['sma_50'] = technical.sma_50
                    stock_data['trend'] = trend['trend']
                    stock_data['trend_strength'] = trend['strength']
                    stock_data['volatility'] = volatility['volatility']
                    stock_data['volatility_level'] = volatility['volatility_level']
                    
                    analyzed_stocks.append(stock_data)
                else:
                    analyzed_stocks.append(stock)
                    
            except Exception as e:
                logger.warning(f"分析股票 {stock.get('symbol', 'unknown')} 失败: {e}")
                analyzed_stocks.append(stock)
        
        return pd.DataFrame(analyzed_stocks)
    
    def _calculate_rankings(self, stocks: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """计算涨跌幅排行"""
        if stocks.empty or 'change_rate' not in stocks.columns:
            return [], []
        
        # 过滤有效数据
        valid_stocks = stocks[
            (stocks['change_rate'].notna()) &
            (stocks['volume'] > 0)
        ].copy()
        
        if valid_stocks.empty:
            return [], []
        
        # 涨幅榜
        top_gainers = valid_stocks.nlargest(10, 'change_rate')
        gainers_list = []
        
        for _, stock in top_gainers.iterrows():
            gainers_list.append({
                'symbol': stock.get('symbol', ''),
                'name': stock.get('name', ''),
                'price': stock.get('last_price', 0),
                'change_rate': stock.get('change_rate', 0),
                'volume': stock.get('volume', 0),
                'market_cap': stock.get('market_val', 0)
            })
        
        # 跌幅榜
        top_losers = valid_stocks.nsmallest(10, 'change_rate')
        losers_list = []
        
        for _, stock in top_losers.iterrows():
            losers_list.append({
                'symbol': stock.get('symbol', ''),
                'name': stock.get('name', ''),
                'price': stock.get('last_price', 0),
                'change_rate': stock.get('change_rate', 0),
                'volume': stock.get('volume', 0),
                'market_cap': stock.get('market_val', 0)
            })
        
        return gainers_list, losers_list
    
    def _value_strategy(self, **kwargs) -> ScreeningCriteria:
        """价值投资策略"""
        return ScreeningCriteria(
            min_market_cap=kwargs.get('min_market_cap', 10),
            max_pe_ratio=kwargs.get('max_pe_ratio', 20),
            max_pb_ratio=kwargs.get('max_pb_ratio', 3),
            min_dividend_yield=kwargs.get('min_dividend_yield', 0),
            min_volume=kwargs.get('min_volume', 1000000)
        )
    
    def _growth_strategy(self, **kwargs) -> ScreeningCriteria:
        """成长投资策略"""
        return ScreeningCriteria(
            min_market_cap=kwargs.get('min_market_cap', 5),
            max_pe_ratio=kwargs.get('max_pe_ratio', 50),
            min_price=kwargs.get('min_price', 5),
            min_volume=kwargs.get('min_volume', 500000)
        )
    
    def _dividend_strategy(self, **kwargs) -> ScreeningCriteria:
        """股息投资策略"""
        return ScreeningCriteria(
            min_market_cap=kwargs.get('min_market_cap', 10),
            min_dividend_yield=kwargs.get('min_dividend_yield', 2),
            max_pe_ratio=kwargs.get('max_pe_ratio', 30),
            min_volume=kwargs.get('min_volume', 1000000)
        )
    
    def _momentum_strategy(self, **kwargs) -> ScreeningCriteria:
        """动量投资策略"""
        return ScreeningCriteria(
            min_market_cap=kwargs.get('min_market_cap', 5),
            min_volume=kwargs.get('min_volume', 1000000),
            min_price=kwargs.get('min_price', 10)
        )
    
    def _technical_strategy(self, **kwargs) -> ScreeningCriteria:
        """技术分析策略"""
        return ScreeningCriteria(
            min_market_cap=kwargs.get('min_market_cap', 5),
            min_volume=kwargs.get('min_volume', 500000),
            min_price=kwargs.get('min_price', 5)
        )
    
    def _quality_strategy(self, **kwargs) -> ScreeningCriteria:
        """质量投资策略"""
        return ScreeningCriteria(
            min_market_cap=kwargs.get('min_market_cap', 20),
            max_pe_ratio=kwargs.get('max_pe_ratio', 25),
            max_pb_ratio=kwargs.get('max_pb_ratio', 5),
            min_volume=kwargs.get('min_volume', 1000000)
        )
    
    def save_results(self, result: ScreeningResult, filename: str = None, data_dir: str = 'data'):
        """
        保存筛选结果
        
        Args:
            result: 筛选结果
            filename: 文件名
            data_dir: 数据目录
        """
        if result.stocks.empty:
            logger.warning("筛选结果为空，无法保存")
            return
        
        import os
        
        # 创建数据目录
        os.makedirs(data_dir, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            timestamp = result.screening_time.strftime('%Y%m%d_%H%M%S')
            filename = f'us_stock_screening_{timestamp}.csv'
        
        filepath = os.path.join(data_dir, filename)
        
        try:
            result.stocks.to_csv(filepath, index=False, encoding='utf-8-sig')
            file_size = os.path.getsize(filepath) / 1024  # KB
            logger.info(f"✓ 筛选结果已保存到: {filepath}")
            logger.info(f"  文件大小: {file_size:.2f} KB")
            logger.info(f"  符合条件股票: {result.qualified_stocks} 只")
        except Exception as e:
            logger.error(f"✗ 保存文件失败: {e}")
    
    def get_screening_summary(self, result: ScreeningResult) -> Dict:
        """
        获取筛选结果摘要
        
        Args:
            result: 筛选结果
            
        Returns:
            结果摘要
        """
        if result.stocks.empty:
            return {
                'total_stocks': 0,
                'qualified_stocks': 0,
                'qualification_rate': 0,
                'avg_market_cap': 0,
                'avg_pe_ratio': 0,
                'avg_price': 0,
                'top_gainers_count': 0,
                'top_losers_count': 0
            }
        
        stocks = result.stocks
        
        # 计算统计数据
        summary = {
            'total_stocks': result.total_stocks,
            'qualified_stocks': result.qualified_stocks,
            'qualification_rate': result.qualified_stocks / result.total_stocks * 100,
            'screening_time': result.screening_time.strftime('%Y-%m-%d %H:%M:%S'),
            'top_gainers_count': len(result.top_gainers),
            'top_losers_count': len(result.top_losers)
        }
        
        # 市值统计
        if 'market_val' in stocks.columns:
            summary['avg_market_cap'] = stocks['market_val'].mean() / 1e8  # 转换为亿美元
            summary['median_market_cap'] = stocks['market_val'].median() / 1e8
        
        # 估值统计
        if 'pe_ratio' in stocks.columns:
            summary['avg_pe_ratio'] = stocks['pe_ratio'].mean()
            summary['median_pe_ratio'] = stocks['pe_ratio'].median()
        
        if 'pb_ratio' in stocks.columns:
            summary['avg_pb_ratio'] = stocks['pb_ratio'].mean()
        
        # 价格统计
        if 'last_price' in stocks.columns:
            summary['avg_price'] = stocks['last_price'].mean()
            summary['median_price'] = stocks['last_price'].median()
            summary['min_price'] = stocks['last_price'].min()
            summary['max_price'] = stocks['last_price'].max()
        
        # 行业分布
        if 'sector' in stocks.columns:
            sector_counts = stocks['sector'].value_counts()
            summary['top_sectors'] = sector_counts.head(5).to_dict()
        
        return summary


def main():
    """主函数 - 测试用"""
    print("="*80)
    print("美股筛选器测试")
    print("="*80)
    
    try:
        # 创建筛选器
        screener = USStockScreener()
        
        # 测试价值投资策略
        print("\n1. 测试价值投资策略...")
        value_result = screener.screen_by_strategy('value', max_pe_ratio=15, max_pb_ratio=2)
        print(f"   符合条件股票: {value_result.qualified_stocks} 只")
        
        # 测试成长投资策略
        print("\n2. 测试成长投资策略...")
        growth_result = screener.screen_by_strategy('growth', max_pe_ratio=30)
        print(f"   符合条件股票: {growth_result.qualified_stocks} 只")
        
        # 获取筛选摘要
        if not value_result.stocks.empty:
            print("\n3. 价值投资策略摘要...")
            summary = screener.get_screening_summary(value_result)
            print(f"   平均市值: {summary.get('avg_market_cap', 0):.2f} 亿美元")
            print(f"   平均市盈率: {summary.get('avg_pe_ratio', 0):.2f}")
            print(f"   平均股价: ${summary.get('avg_price', 0):.2f}")
        
        print("\n" + "="*80)
        print("✓ 筛选器测试完成")
        print("="*80)
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
