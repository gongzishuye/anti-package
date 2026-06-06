#!/usr/bin/env python3
"""
美股数据分析器
提供美股数据的分析功能，包括技术指标、财务分析、风险评估等
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TechnicalIndicators:
    """技术指标数据类"""
    sma_5: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_lower: float = 0.0
    volume_sma: float = 0.0


@dataclass
class FundamentalMetrics:
    """基本面指标数据类"""
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    dividend_yield: float = 0.0
    market_cap: float = 0.0
    debt_to_equity: float = 0.0
    roe: float = 0.0
    roa: float = 0.0
    current_ratio: float = 0.0


class USStockAnalyzer:
    """美股数据分析器"""
    
    def __init__(self):
        """初始化分析器"""
        logger.info("初始化美股数据分析器")
    
    def calculate_technical_indicators(self, price_data: pd.DataFrame) -> TechnicalIndicators:
        """
        计算技术指标
        
        Args:
            price_data: 包含OHLCV数据的DataFrame
            
        Returns:
            技术指标对象
        """
        if price_data.empty or len(price_data) < 50:
            logger.warning("数据不足，无法计算完整技术指标")
            return TechnicalIndicators()
        
        try:
            close_prices = price_data['close'].values
            volumes = price_data['volume'].values
            
            # 移动平均线
            sma_5 = self._calculate_sma(close_prices, 5)
            sma_20 = self._calculate_sma(close_prices, 20)
            sma_50 = self._calculate_sma(close_prices, 50)
            
            # 指数移动平均线
            ema_12 = self._calculate_ema(close_prices, 12)
            ema_26 = self._calculate_ema(close_prices, 26)
            
            # RSI
            rsi = self._calculate_rsi(close_prices, 14)
            
            # MACD
            macd_line = ema_12 - ema_26
            macd_signal = self._calculate_ema(macd_line, 9)
            macd = macd_line[-1] - macd_signal[-1] if len(macd_signal) > 0 else 0
            
            # 布林带
            bollinger_upper, bollinger_lower = self._calculate_bollinger_bands(close_prices, 20, 2)
            
            # 成交量移动平均
            volume_sma = self._calculate_sma(volumes, 20)
            
            return TechnicalIndicators(
                sma_5=sma_5,
                sma_20=sma_20,
                sma_50=sma_50,
                ema_12=ema_12,
                ema_26=ema_26,
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal[-1] if len(macd_signal) > 0 else 0,
                bollinger_upper=bollinger_upper,
                bollinger_lower=bollinger_lower,
                volume_sma=volume_sma
            )
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return TechnicalIndicators()
    
    def analyze_price_trend(self, price_data: pd.DataFrame, short_period: int = 20, long_period: int = 50) -> Dict:
        """
        分析价格趋势
        
        Args:
            price_data: 价格数据
            short_period: 短期周期
            long_period: 长期周期
            
        Returns:
            趋势分析结果
        """
        if price_data.empty or len(price_data) < long_period:
            return {"trend": "unknown", "strength": 0, "signal": "neutral"}
        
        try:
            close_prices = price_data['close'].values
            
            # 计算移动平均线
            short_ma = self._calculate_sma(close_prices, short_period)
            long_ma = self._calculate_sma(close_prices, long_period)
            
            current_price = close_prices[-1]
            
            # 趋势判断
            if short_ma > long_ma:
                if current_price > short_ma:
                    trend = "bullish"
                    strength = min((short_ma - long_ma) / long_ma * 100, 10)
                    signal = "buy" if strength > 2 else "hold"
                else:
                    trend = "bullish_weak"
                    strength = min((short_ma - long_ma) / long_ma * 100, 5)
                    signal = "hold"
            elif short_ma < long_ma:
                if current_price < short_ma:
                    trend = "bearish"
                    strength = min((long_ma - short_ma) / long_ma * 100, 10)
                    signal = "sell" if strength > 2 else "hold"
                else:
                    trend = "bearish_weak"
                    strength = min((long_ma - short_ma) / long_ma * 100, 5)
                    signal = "hold"
            else:
                trend = "sideways"
                strength = 0
                signal = "hold"
            
            # 计算价格动量
            momentum = (current_price - close_prices[-5]) / close_prices[-5] * 100 if len(close_prices) >= 5 else 0
            
            return {
                "trend": trend,
                "strength": round(strength, 2),
                "signal": signal,
                "momentum": round(momentum, 2),
                "current_price": current_price,
                "short_ma": short_ma,
                "long_ma": long_ma
            }
            
        except Exception as e:
            logger.error(f"分析价格趋势失败: {e}")
            return {"trend": "error", "strength": 0, "signal": "neutral"}
    
    def calculate_volatility(self, price_data: pd.DataFrame, period: int = 20) -> Dict:
        """
        计算波动率
        
        Args:
            price_data: 价格数据
            period: 计算周期
            
        Returns:
            波动率分析结果
        """
        if price_data.empty or len(price_data) < period:
            return {"volatility": 0, "volatility_level": "low"}
        
        try:
            close_prices = price_data['close'].values
            
            # 计算日收益率
            returns = np.diff(close_prices) / close_prices[:-1]
            
            # 计算波动率（标准差）
            volatility = np.std(returns[-period:]) * np.sqrt(252) * 100  # 年化波动率
            
            # 波动率等级
            if volatility < 15:
                volatility_level = "low"
            elif volatility < 30:
                volatility_level = "medium"
            else:
                volatility_level = "high"
            
            # 计算最大回撤
            cumulative_returns = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max * 100
            max_drawdown = np.min(drawdown)
            
            return {
                "volatility": round(volatility, 2),
                "volatility_level": volatility_level,
                "max_drawdown": round(max_drawdown, 2),
                "avg_daily_return": round(np.mean(returns) * 100, 4),
                "positive_days": np.sum(returns > 0),
                "negative_days": np.sum(returns < 0),
                "total_days": len(returns)
            }
            
        except Exception as e:
            logger.error(f"计算波动率失败: {e}")
            return {"volatility": 0, "volatility_level": "error"}
    
    def analyze_volume(self, price_data: pd.DataFrame) -> Dict:
        """
        分析成交量
        
        Args:
            price_data: 包含成交量数据的DataFrame
            
        Returns:
            成交量分析结果
        """
        if price_data.empty or 'volume' not in price_data.columns:
            return {"volume_trend": "unknown", "volume_ratio": 0}
        
        try:
            volumes = price_data['volume'].values
            current_volume = volumes[-1]
            
            # 成交量移动平均
            volume_sma = self._calculate_sma(volumes, 20)
            volume_sma_5 = self._calculate_sma(volumes, 5)
            
            # 成交量比率
            volume_ratio = current_volume / volume_sma if volume_sma > 0 else 1
            
            # 成交量趋势
            if volume_sma_5 > volume_sma:
                volume_trend = "increasing"
            elif volume_sma_5 < volume_sma:
                volume_trend = "decreasing"
            else:
                volume_trend = "stable"
            
            # 成交量价格关系
            close_prices = price_data['close'].values
            price_change = (close_prices[-1] - close_prices[-2]) / close_prices[-2] if len(close_prices) >= 2 else 0
            
            # 价量关系分析
            if price_change > 0 and volume_ratio > 1.2:
                price_volume_relation = "bullish_confirm"
            elif price_change < 0 and volume_ratio > 1.2:
                price_volume_relation = "bearish_confirm"
            elif price_change > 0 and volume_ratio < 0.8:
                price_volume_relation = "bullish_weak"
            elif price_change < 0 and volume_ratio < 0.8:
                price_volume_relation = "bearish_weak"
            else:
                price_volume_relation = "neutral"
            
            return {
                "volume_trend": volume_trend,
                "volume_ratio": round(volume_ratio, 2),
                "current_volume": current_volume,
                "volume_sma_20": volume_sma,
                "volume_sma_5": volume_sma_5,
                "price_volume_relation": price_volume_relation
            }
            
        except Exception as e:
            logger.error(f"分析成交量失败: {e}")
            return {"volume_trend": "error", "volume_ratio": 0}
    
    def calculate_support_resistance(self, price_data: pd.DataFrame, lookback: int = 50) -> Dict:
        """
        计算支撑阻力位
        
        Args:
            price_data: 价格数据
            lookback: 回看周期
            
        Returns:
            支撑阻力位分析结果
        """
        if price_data.empty or len(price_data) < lookback:
            return {"support": 0, "resistance": 0, "strength": "weak"}
        
        try:
            close_prices = price_data['close'].values
            high_prices = price_data['high'].values
            low_prices = price_data['low'].values
            
            recent_data = price_data.tail(lookback)
            
            # 找局部高点和低点
            highs = []
            lows = []
            
            for i in range(1, len(recent_data) - 1):
                if (recent_data.iloc[i]['high'] > recent_data.iloc[i-1]['high'] and 
                    recent_data.iloc[i]['high'] > recent_data.iloc[i+1]['high']):
                    highs.append(recent_data.iloc[i]['high'])
                
                if (recent_data.iloc[i]['low'] < recent_data.iloc[i-1]['low'] and 
                    recent_data.iloc[i]['low'] < recent_data.iloc[i+1]['low']):
                    lows.append(recent_data.iloc[i]['low'])
            
            # 计算阻力位（主要高点）
            resistance = np.percentile(highs, 70) if highs else high_prices.max()
            
            # 计算支撑位（主要低点）
            support = np.percentile(lows, 30) if lows else low_prices.min()
            
            # 当前价格
            current_price = close_prices[-1]
            
            # 强度评估
            resistance_distance = (resistance - current_price) / current_price * 100
            support_distance = (current_price - support) / current_price * 100
            
            if resistance_distance < 2 and support_distance < 2:
                strength = "tight_range"
            elif resistance_distance > 10 and support_distance > 10:
                strength = "wide_range"
            else:
                strength = "normal"
            
            return {
                "support": round(support, 2),
                "resistance": round(resistance, 2),
                "current_price": current_price,
                "strength": strength,
                "resistance_distance": round(resistance_distance, 2),
                "support_distance": round(support_distance, 2),
                "high_points": len(highs),
                "low_points": len(lows)
            }
            
        except Exception as e:
            logger.error(f"计算支撑阻力位失败: {e}")
            return {"support": 0, "resistance": 0, "strength": "error"}
    
    def generate_trading_signals(self, price_data: pd.DataFrame) -> Dict:
        """
        生成交易信号
        
        Args:
            price_data: 价格数据
            
        Returns:
            交易信号分析结果
        """
        try:
            # 计算各种指标
            technical = self.calculate_technical_indicators(price_data)
            trend = self.analyze_price_trend(price_data)
            volatility = self.calculate_volatility(price_data)
            volume = self.analyze_volume(price_data)
            sr = self.calculate_support_resistance(price_data)
            
            # 信号权重
            signals = {
                "trend_signal": self._get_trend_signal(trend),
                "ma_signal": self._get_ma_signal(technical),
                "rsi_signal": self._get_rsi_signal(technical.rsi),
                "macd_signal": self._get_macd_signal(technical.macd, technical.macd_signal),
                "volume_signal": self._get_volume_signal(volume),
                "volatility_signal": self._get_volatility_signal(volatility)
            }
            
            # 计算综合信号
            signal_scores = {
                "strong_buy": 0,
                "buy": 0,
                "hold": 0,
                "sell": 0,
                "strong_sell": 0
            }
            
            for signal_type, signal in signals.items():
                weight = self._get_signal_weight(signal_type)
                signal_scores[signal] += weight
            
            # 确定最终信号
            final_signal = max(signal_scores, key=signal_scores.get)
            confidence = max(signal_scores.values()) / sum(signal_scores.values()) * 100
            
            return {
                "final_signal": final_signal,
                "confidence": round(confidence, 1),
                "signals": signals,
                "technical": technical,
                "trend": trend,
                "volatility": volatility,
                "volume": volume,
                "support_resistance": sr
            }
            
        except Exception as e:
            logger.error(f"生成交易信号失败: {e}")
            return {"final_signal": "error", "confidence": 0}
    
    def _calculate_sma(self, prices: np.ndarray, period: int) -> float:
        """计算简单移动平均线"""
        if len(prices) < period:
            return 0.0
        return np.mean(prices[-period:])
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均线"""
        if len(prices) < period:
            return np.array([prices[-1]])
        
        multiplier = 2 / (period + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]
        
        for i in range(1, len(prices)):
            ema[i] = (prices[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2) -> Tuple[float, float]:
        """计算布林带"""
        if len(prices) < period:
            return prices[-1], prices[-1]
        
        sma = self._calculate_sma(prices, period)
        std = np.std(prices[-period:])
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, lower_band
    
    def _get_trend_signal(self, trend: Dict) -> str:
        """获取趋势信号"""
        if trend.get("signal") == "buy":
            return "buy"
        elif trend.get("signal") == "sell":
            return "sell"
        else:
            return "hold"
    
    def _get_ma_signal(self, technical: TechnicalIndicators) -> str:
        """获取移动平均线信号"""
        if technical.sma_5 > technical.sma_20 > technical.sma_50:
            return "buy"
        elif technical.sma_5 < technical.sma_20 < technical.sma_50:
            return "sell"
        else:
            return "hold"
    
    def _get_rsi_signal(self, rsi: float) -> str:
        """获取RSI信号"""
        if rsi < 30:
            return "buy"
        elif rsi > 70:
            return "sell"
        else:
            return "hold"
    
    def _get_macd_signal(self, macd: float, macd_signal: float) -> str:
        """获取MACD信号"""
        if macd > 0 and macd > macd_signal:
            return "buy"
        elif macd < 0 and macd < macd_signal:
            return "sell"
        else:
            return "hold"
    
    def _get_volume_signal(self, volume: Dict) -> str:
        """获取成交量信号"""
        if volume.get("price_volume_relation") == "bullish_confirm":
            return "buy"
        elif volume.get("price_volume_relation") == "bearish_confirm":
            return "sell"
        else:
            return "hold"
    
    def _get_volatility_signal(self, volatility: Dict) -> str:
        """获取波动率信号"""
        level = volatility.get("volatility_level", "medium")
        if level == "low":
            return "hold"  # 低波动率，观望
        elif level == "high":
            return "hold"  # 高波动率，谨慎
        else:
            return "hold"  # 中等波动率，正常
    
    def _get_signal_weight(self, signal_type: str) -> int:
        """获取信号权重"""
        weights = {
            "trend_signal": 3,
            "ma_signal": 2,
            "rsi_signal": 2,
            "macd_signal": 2,
            "volume_signal": 1,
            "volatility_signal": 1
        }
        return weights.get(signal_type, 1)


def main():
    """主函数 - 测试用"""
    print("="*80)
    print("美股数据分析器测试")
    print("="*80)
    
    # 创建测试数据
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    n_days = len(dates)
    
    # 模拟价格数据
    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, n_days)
    prices = base_price * np.cumprod(1 + returns)
    
    # 创建OHLCV数据
    test_data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.normal(0, 0.005, n_days)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, n_days))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, n_days))),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n_days)
    })
    
    # 创建分析器
    analyzer = USStockAnalyzer()
    
    # 测试各项分析功能
    print("\n1. 计算技术指标...")
    technical = analyzer.calculate_technical_indicators(test_data)
    print(f"   SMA(20): {technical.sma_20:.2f}")
    print(f"   RSI: {technical.rsi:.2f}")
    print(f"   MACD: {technical.macd:.4f}")
    
    print("\n2. 分析价格趋势...")
    trend = analyzer.analyze_price_trend(test_data)
    print(f"   趋势: {trend['trend']}")
    print(f"   强度: {trend['strength']}")
    print(f"   信号: {trend['signal']}")
    
    print("\n3. 计算波动率...")
    volatility = analyzer.calculate_volatility(test_data)
    print(f"   年化波动率: {volatility['volatility']:.2f}%")
    print(f"   波动率等级: {volatility['volatility_level']}")
    print(f"   最大回撤: {volatility['max_drawdown']:.2f}%")
    
    print("\n4. 分析成交量...")
    volume = analyzer.analyze_volume(test_data)
    print(f"   成交量趋势: {volume['volume_trend']}")
    print(f"   成交量比率: {volume['volume_ratio']}")
    
    print("\n5. 计算支撑阻力位...")
    sr = analyzer.calculate_support_resistance(test_data)
    print(f"   支撑位: {sr['support']:.2f}")
    print(f"   阻力位: {sr['resistance']:.2f}")
    
    print("\n6. 生成交易信号...")
    signals = analyzer.generate_trading_signals(test_data)
    print(f"   最终信号: {signals['final_signal']}")
    print(f"   信心度: {signals['confidence']:.1f}%")
    
    print("\n" + "="*80)
    print("✓ 分析器测试完成")
    print("="*80)


if __name__ == "__main__":
    main()
