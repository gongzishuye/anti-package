"""
股票数据获取模块
基于富途API、Polygon.io API和EM API获取美股、港股和A股市场数据
"""

# 使用延迟导入，避免在导入时就加载所有模块
# 这样可以避免某些模块的依赖问题

__all__ = [
    'USStockFetcher',
    'USStockAnalyzer', 
    'USStockScreener',
    'PolygonUSStockFetcher',
    'EMUSStockFetcher',
    'EMHKStockFetcher',
    'EMAStockFetcher',
    'USStockReversalDetector',
    'HKStockReversalDetector',
    'AStockReversalDetector',
]

__version__ = '1.0.0'

# 延迟导入函数
def _lazy_import(name):
    """延迟导入模块"""
    if name == 'USStockFetcher':
        from .us_stock_fetcher import USStockFetcher
        return USStockFetcher
    elif name == 'USStockAnalyzer':
        from .us_stock_analyzer import USStockAnalyzer
        return USStockAnalyzer
    elif name == 'USStockScreener':
        from .us_stock_screener import USStockScreener
        return USStockScreener
    elif name == 'PolygonUSStockFetcher':
        from .polygon_us_stock_fetcher import PolygonUSStockFetcher
        return PolygonUSStockFetcher
    elif name == 'EMUSStockFetcher':
        from .em_us_stock_fetcher import EMUSStockFetcher
        return EMUSStockFetcher
    elif name == 'EMHKStockFetcher':
        from .em_hk_stock_fetcher import EMHKStockFetcher
        return EMHKStockFetcher
    elif name == 'EMAStockFetcher':
        from .em_a_stock_fetcher import EMAStockFetcher
        return EMAStockFetcher
    elif name == 'USStockReversalDetector':
        from .us_stock_reversal_detector import USStockReversalDetector
        return USStockReversalDetector
    elif name == 'HKStockReversalDetector':
        from .hk_stock_reversal_detector import HKStockReversalDetector
        return HKStockReversalDetector
    elif name == 'AStockReversalDetector':
        from .a_stock_reversal_detector import AStockReversalDetector
        return AStockReversalDetector
    else:
        raise ImportError(f"Cannot import {name}")

# 使用 __getattr__ 实现延迟导入
def __getattr__(name):
    if name in __all__:
        return _lazy_import(name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
