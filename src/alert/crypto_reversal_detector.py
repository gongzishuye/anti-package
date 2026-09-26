#!/usr/bin/env python3
"""
加密货币反包检测器
基于monitor表中的数据检测反包形态
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.database.db_manager import DatabaseManager
from src.crypto.binance_data_fetcher import BinanceDataFetcher
from src.alert.wecom_notifier import WeComNotifier
from src.alert.monitor_config import (
    get_dynamic_symbols,
    get_dynamic_symbols_for_interval,
    MONITORED_INTERVALS,
    INTERVAL_MAP as CONFIG_INTERVAL_MAP
)
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CryptoReversalDetector:
    """加密货币反包检测器"""

    # Interval映射（从中央配置导入 + 补充Binance短周期格式）
    # CONFIG_INTERVAL_MAP 的值已经是 Binance 格式（如 '1h', '1d', '1M'）
    # 内部使用短格式作为 key（如 '1H', '1D', '1M'）来保持与数据库格式一致
    BN_INTERVAL_SUFFIX = {
        '5M': '5m', '10M': '10m',
        '15M': '15m', '30M': '30m', '1H': '1h', '2H': '2h',
        '4H': '4h', '6H': '6h', '8H': '8h', '12H': '12h',
        '1D': '1d', '2D': '2d', '3D': '3d', '5D': '5d', '1W': '1w', '1M': '1M'
    }

    # 支持的检测interval（支持所有监控周期）
    SUPPORTED_INTERVALS = MONITORED_INTERVALS

    # 高优先级检测交易对（在运行时从配置文件动态读取）

    # 高频检测周期（从中央配置导入）
    PRIORITY_INTERVALS = MONITORED_INTERVALS

    # [已禁用] MA100均线触碰检测标的
    # MA100_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT',
    #                  'XAUUSDT', 'XAGUSDT', 'CLUSDT', 'USOUSDT']
    # [已禁用] MA100均线触碰检测周期
    # MA100_INTERVALS = ['1H', '2H', '4H', '6H', '8H', '12H', '1D']

    def __init__(self, wecom_webhook_url: str = None):
        """
        初始化反包检测器
        
        Args:
            wecom_webhook_url: 企业微信webhook地址
        """
        self.db = DatabaseManager()
        self.bn_fetcher = BinanceDataFetcher()
        self.futures_fetcher = BinanceDataFetcher(market_type='futures')

        # 初始化企业微信通知器（默认消费 WECOM_WEBHOOK_URL2，动态配置通道）
        if wecom_webhook_url is None:
            wecom_webhook_url = os.getenv('WECOM_WEBHOOK_URL2')

        self.notifier = WeComNotifier(
            webhook_url=wecom_webhook_url
        ) if wecom_webhook_url else None
        
        self.chart_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'charts')
        )
        os.makedirs(self.chart_dir, exist_ok=True)

        self.FUTURES_EXCHANGES = {'bn_futures', 'binance_futures'}
    
    def get_kline_data(self, ticker: str, interval: str, exchange: str, klines_count: int = 10) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            ticker: 交易对
            interval: 时间周期 (如 '1H', '1D', '2H', '4H', '8H', '12H')
            exchange: 交易所名称
            klines_count: 需要获取的K线数量，默认10根
            
        Returns:
            K线数据
        """
        try:
            # 转换为币安格式
            bn_interval = self.BN_INTERVAL_SUFFIX.get(interval)
            if not bn_interval:
                logger.error(f"不支持的interval: {interval}")
                return pd.DataFrame()

            # 根据exchange类型决定使用哪个API
            if exchange in ['bn_futures', 'binance_futures']:
                bn_fetcher = self.futures_fetcher
            else:
                bn_fetcher = self.bn_fetcher  # 使用默认的现货fetcher

            df = bn_fetcher.get_klines(
                symbol=ticker,
                interval=bn_interval,
                days=klines_count  # 这里传的是K线数量
            )
            return df
        except Exception as e:
            logger.error(f"获取{ticker}K线数据失败: {e}")
            return pd.DataFrame()
    
    def _format_datetime(self, ts: Optional[pd.Timestamp]) -> str:
        """格式化时间戳为字符串（转换为北京时间）"""
        if ts is None:
            return "-"
        if isinstance(ts, pd.Timestamp):
            if ts.tz is None:
                ts = ts.tz_localize('UTC')
            return ts.tz_convert('Asia/Shanghai').strftime('%Y-%m-%d %H:%M')
        try:
            return pd.Timestamp(ts, tz='UTC').tz_convert('Asia/Shanghai').strftime('%Y-%m-%d %H:%M')
        except Exception:
            return str(ts)
    
    def _build_priority_alert_content(self, reversal: Dict) -> str:
        """构建高优先级反包报警内容（支持向上/向下反包）"""
        ticker = reversal['ticker']
        interval = reversal.get('interval', '')
        interval_display = interval.replace('M', 'm')
        t1_time = self._format_datetime(reversal.get('t1_date'))
        direction = reversal.get('direction', 'bullish')
        direction_text = '向下反包（阴包阳）' if direction == 'bearish' else '向上反包（阳包阴）'
        
        content = f"""## ⚡ 高频反包检测

**交易对**: {ticker}
**类型**: {direction_text}
**周期**: {interval_display}
**T-1时间**: {t1_time}
"""

        return content
    
    def _generate_futures_kline_chart(self,
                                      ticker: str,
                                      interval: str,
                                      bars: int = 50) -> Optional[str]:
        """生成期货K线图并返回图片路径"""
        if interval not in self.BN_INTERVAL_SUFFIX:
            logger.warning(f"无法生成K线图，未找到interval映射: {interval}")
            return None

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.patches import Rectangle
        except ImportError:
            logger.error("未安装matplotlib，无法生成K线图")
            return None

        try:
            df = self.futures_fetcher.get_klines(
                symbol=ticker,
                interval=self.BN_INTERVAL_SUFFIX[interval],
                days=bars
            )
        except Exception as exc:
            logger.error(f"获取期货K线数据失败: {exc}")
            return None

        if df.empty:
            logger.warning(f"{ticker} {interval}: 未获取到K线数据，无法生成图表")
            return None

        df = df.sort_values('timestamp').tail(bars).copy()

        required_cols = {'open', 'high', 'low', 'close'}
        if not required_cols.issubset(df.columns):
            logger.warning(f"{ticker} {interval}: K线数据缺少必要列 {required_cols}")
            return None

        # 处理时间列
        timestamps = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
        if timestamps.isnull().all():
            logger.warning(f"{ticker} {interval}: 时间列解析失败")
            return None
        timestamps = timestamps.dt.tz_convert('Asia/Shanghai')

        opens = df['open'].astype(float).tolist()
        highs = df['high'].astype(float).tolist()
        lows = df['low'].astype(float).tolist()
        closes = df['close'].astype(float).tolist()

        fig, ax = plt.subplots(figsize=(10, 5))
        x_values = list(range(len(df)))
        candle_width = 0.6

        for idx, (x, o, h, l, c) in enumerate(zip(x_values, opens, highs, lows, closes)):
            color = '#22c55e' if c >= o else '#ef4444'
            ax.plot([x, x], [l, h], color=color, linewidth=1)
            lower = min(o, c)
            height = abs(c - o)
            height = height if height > 1e-8 else 1e-8
            rect = Rectangle(
                (x - candle_width / 2, lower),
                candle_width,
                height,
                facecolor=color,
                edgecolor=color,
                linewidth=1,
            )
            ax.add_patch(rect)

        ax.set_title(f"{ticker} {interval} · Last {len(df)} Candles", fontsize=12)
        ax.set_ylabel("Price (USDT)")
        ax.grid(True, linestyle='--', alpha=0.3)

        # 设置x轴标签
        step = max(1, len(x_values) // 6)
        select_idx = x_values[::step]
        select_labels = [timestamps.iloc[i].strftime('%m-%d %H:%M') for i in select_idx]
        ax.set_xticks(select_idx)
        ax.set_xticklabels(select_labels, rotation=45, ha='right')

        fig.tight_layout()

        filename = f"{ticker}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_path = os.path.join(self.chart_dir, filename)

        try:
            fig.savefig(output_path, dpi=150)
            logger.info(f"已生成K线图: {output_path}")
        except Exception as exc:
            logger.error(f"保存K线图失败: {exc}")
            plt.close(fig)
            return None
        finally:
            plt.close(fig)

        return output_path

    def _send_priority_alert(self, reversal: Dict) -> bool:
        """发送高优先级反包报警（仅发送到主webhook）"""
        if not self.notifier:
            logger.warning("未配置企业微信webhook，跳过高优先级反包推送")
            return False
        
        content = self._build_priority_alert_content(reversal)
        success = self.notifier.send_markdown_message(content)
        if success:
            logger.info(f"✅ 高频反包报警已发送: {reversal['ticker']} ({reversal.get('interval')})")
            chart_path = self._generate_futures_kline_chart(
                reversal['ticker'],
                reversal.get('interval', ''),
                bars=50
            )
            if chart_path and hasattr(self.notifier, "send_image_message"):
                img_success = self.notifier.send_image_message(
                    image_path=chart_path
                )
                if img_success:
                    logger.info(f"🖼️ 高频反包K线图已发送: {reversal['ticker']}")
                else:
                    logger.warning(f"⚠️ 高频反包K线图发送失败: {reversal['ticker']}")
            else:
                logger.debug("高频反包图表未生成或通知器不支持图片发送")
        else:
            logger.error(f"❌ 高频反包报警发送失败: {reversal['ticker']} ({reversal.get('interval')})")
        return success

    def _check_precious_metal_ma_ema(self, ticker: str, interval: str) -> Optional[Dict]:
        """
        检测贵金属的MA52/EMA144跌破（仅用于XAUUSDT/XAGUSDT）

        Args:
            ticker: 交易对
            interval: 周期

        Returns:
            如果跌破，返回详细信息字典；否则返回None
        """
        bn_interval = self.BN_INTERVAL_SUFFIX.get(interval)
        if not bn_interval:
            return None

        try:
            # 获取150根K线用于计算MA52和EMA144
            df = self.futures_fetcher.get_klines(
                symbol=ticker,
                interval=bn_interval,
                days=150 if bn_interval in ['1h'] else 300
            )

            if df.empty or len(df) < 144:
                logger.debug(f"{ticker} {interval}: K线数据不足，跳过MA/EMA检测")
                return None

            df = df.sort_values('timestamp').tail(150).copy()

            # 计算MA52和EMA144
            df['ma52'] = df['close'].rolling(window=52, min_periods=1).mean()
            df['ema144'] = df['close'].ewm(span=144, adjust=False).mean()

            latest = df.iloc[-1]
            latest_low = float(latest['low'])
            latest_close = float(latest['close'])
            latest_timestamp = str(latest['timestamp'])

            # 检查MA52跌破
            ma52_value = float(latest['ma52'])
            if latest_low < ma52_value:
                logger.info(f"✨ {ticker} {interval} 检测到MA52跌破: low=${latest_low:.4f} < MA52=${ma52_value:.4f}")
                result = {
                    'ticker': ticker,
                    'exchange': 'bn_futures',
                    'interval': interval,
                    'direction': 'ma52_breakdown',
                    't1_date': pd.Timestamp(latest_timestamp, tz='UTC'),
                    't1_low': latest_low,
                    't1_close': latest_close,
                    'ma52': ma52_value,
                    'breakdown_pct': ((latest_low - ma52_value) / ma52_value * 100) if ma52_value > 0 else 0
                }
                self._send_precious_metal_alert(result, indicator='MA52')
                return result

            # 检查EMA144跌破
            ema144_value = float(latest['ema144'])
            if latest_low < ema144_value:
                logger.info(f"✨ {ticker} {interval} 检测到EMA144跌破: low=${latest_low:.4f} < EMA144=${ema144_value:.4f}")
                result = {
                    'ticker': ticker,
                    'exchange': 'bn_futures',
                    'interval': interval,
                    'direction': 'ema144_breakdown',
                    't1_date': pd.Timestamp(latest_timestamp, tz='UTC'),
                    't1_low': latest_low,
                    't1_close': latest_close,
                    'ema144': ema144_value,
                    'breakdown_pct': ((latest_low - ema144_value) / ema144_value * 100) if ema144_value > 0 else 0
                }
                self._send_precious_metal_alert(result, indicator='EMA144')
                return result

            return None

        except Exception as e:
            logger.error(f"检测 {ticker} {interval} MA/EMA 失败: {e}", exc_info=True)
            return None

    def _send_precious_metal_alert(self, result: Dict, indicator: str = 'MA52') -> bool:
        """发送贵金属MA/EMA跌破报警"""
        if not self.notifier:
            logger.warning("未配置企业微信webhook，跳过贵金属报警")
            return False

        ticker = result['ticker']
        interval = result['interval']
        metal_name = '白银(XAG)' if ticker == 'XAGUSDT' else '黄金(XAU)'
        indicator_value = result.get('ma52') or result.get('ema144')
        indicator_label = f'{indicator}={indicator_value:.4f}'

        content = f"""## 📉 {metal_name} {interval} {indicator} 跌破报警

**交易对**: {ticker}
**周期**: {interval}
**指标**: {indicator}

---

**最新K线信息**
- 时间: {result['t1_date']}
- 最低价: <font color="warning">${result['t1_low']:.4f}</font>
- 收盘价: ${result['t1_close']:.4f}
- {indicator}: ${indicator_value:.4f}

---

**跌破情况**
- 跌破幅度: <font color="warning">{result['breakdown_pct']:.2f}%</font>
- 距离{indicator}: ${result['t1_low'] - indicator_value:.4f}

---

**报警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

> ⚠️ {metal_name} {interval} K线最低价跌破{indicator}，请关注!
"""
        return self.notifier.send_markdown_message(content)

    # [已禁用] def _check_ma100_touch(self, ticker: str, interval: str) -> Optional[Dict]:
        """
        检测指定交易对/周期最后一根K线是否触碰MA100均线。

        触碰定义：K线的上下影线与MA100有交叉
        - t1_high >= ma100 AND t1_low <= ma100

        Args:
            ticker: 交易对，如 'BTCUSDT'
            interval: 周期，如 '1H', '4H', '1D'

        Returns:
            触碰详情字典；未触碰则返回 None
        """
        # [已禁用] bn_interval = self.BN_INTERVAL_SUFFIX.get(interval)
        # [已禁用] if not bn_interval:
        # [已禁用]     return None
        # [已禁用]
        # [已禁用] # 获取150根K线（足够计算MA100）
        # [已禁用] df = self.futures_fetcher.get_klines(
        # [已禁用]     symbol=ticker,
        # [已禁用]     interval=bn_interval,
        # [已禁用]     days=150
        # [已禁用] )
        # [已禁用] if df.empty or len(df) < 100:
        # [已禁用]     return None
        # [已禁用]
        # [已禁用] df['ma100'] = df['close'].rolling(window=100, min_periods=100).mean()
        # [已禁用] latest = df.iloc[-1]
        # [已禁用] ma100 = latest['ma100']
        # [已禁用] if pd.isna(ma100):
        # [已禁用]     return None
        # [已禁用]
        # [已禁用] t1_high = float(latest['high'])
        # [已禁用] t1_low = float(latest['low'])
        # [已禁用] t1_close = float(latest['close'])
        # [已禁用] t1_open = float(latest['open'])
        # [已禁用] t1_date = latest.get('open_time', latest.get('time', pd.Timestamp.now()))
        # [已禁用]
        # [已禁用] # 触碰条件：K线范围与MA100有交叉
        # [已禁用] if t1_high >= ma100 and t1_low <= ma100:
        # [已禁用]     # 判断触碰类型
        # [已禁用]     if t1_close >= ma100:
        # [已禁用]         touch_type = '上穿/支撑'   # 收盘在均线上方
        # [已禁用]     else:
        # [已禁用]         touch_type = '下穿/阻力'   # 收盘在均线下方
        # [已禁用]
        # [已禁用]     return {
        # [已禁用]         'ticker': ticker,
        # [已禁用]         'interval': interval,
        # [已禁用]         'ma100': float(ma100),
        # [已禁用]         't1_high': t1_high,
        # [已禁用]         't1_low': t1_low,
        # [已禁用]         't1_open': t1_open,
        # [已禁用]         't1_close': t1_close,
        # [已禁用]         't1_date': t1_date,
        # [已禁用]         'touch_type': touch_type,
        # [已禁用]     }
        # [已禁用] return None

    # [已禁用] def _send_ma100_alert(self, result: Dict) -> bool:
    # [已禁用]     """发送MA100均线触碰报警"""
    # [已禁用]     notifier = WeComNotifier(webhook_url=os.getenv('WECOM_WEBHOOK_URL'))
    # [已禁用]     if not notifier:
    # [已禁用]         logger.warning("未配置企业微信webhook，跳过MA100报警")
    # [已禁用]         return False
    # [已禁用]
    # [已禁用]     ticker = result['ticker']
    # [已禁用]     interval = result['interval']
    # [已禁用]     ma100 = result['ma100']
    # [已禁用]     t1_high = result['t1_high']
    # [已禁用]     t1_low = result['t1_low']
    # [已禁用]     t1_close = result['t1_close']
    # [已禁用]     t1_date = result['t1_date']
    # [已禁用]
    # [已禁用]     if isinstance(t1_date, pd.Timestamp):
    # [已禁用]         t1_date_str = t1_date.strftime('%Y-%m-%d %H:%M')
    # [已禁用]     else:
    # [已禁用]         t1_date_str = str(t1_date)
    # [已禁用]
    # [已禁用]     # 标的名映射
    # [已禁用]     symbol_names = {
    # [已禁用]         'BTCUSDT': 'BTC',
    # [已禁用]         'ETHUSDT': 'ETH',
    # [已禁用]         'SOLUSDT': 'SOL',
    # [已禁用]         'BNBUSDT': 'BNB',
    # [已禁用]         'XAUUSDT': '黄金(XAU)',
    # [已禁用]         'XAGUSDT': '白银(XAG)',
    # [已禁用]         'CLUSDT': '原油(CL)',
    # [已禁用]         'USOUSDT': '原油(USO)',
    # [已禁用]     }
    # [已禁用]     name = symbol_names.get(ticker, ticker)
    # [已禁用]
    # [已禁用]     content = f"""## 📊 {name} {interval} MA100 均线触碰
    # [已禁用]
    # [已禁用]**交易对**: {ticker}
    # [已禁用]**周期**: {interval}
    # [已禁用]
    # [已禁用]---
    # [已禁用]
    # [已禁用]**均线信息**
    # [已禁用]- MA100: ${ma100:.4f}
    # [已禁用]
    # [已禁用]---
    # [已禁用]
    # [已禁用]**最新K线**
    # [已禁用]- 时间: {t1_date_str}
    # [已禁用]- 开盘: ${result['t1_open']:.4f}
    # [已禁用]- 最高: ${t1_high:.4f}
    # [已禁用]- 最低: ${t1_low:.4f}
    # [已禁用]- 收盘: <font color="warning">${t1_close:.4f}</font>
    # [已禁用]
    # [已禁用]---
    # [已禁用]
    # [已禁用]**触碰情况**
    # [已禁用]- 触碰类型: {result['touch_type']}
    # [已禁用]- K线范围: ${t1_low:.4f} ~ ${t1_high:.4f}
    # [已禁用]- 距MA100: ${abs(t1_close - ma100):.4f}
    # [已禁用]
    # [已禁用]---
    # [已禁用]
    # [已禁用]**报警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    # [已禁用]"""
    # [已禁用]     return notifier.send_markdown_message(content)

    # [已禁用] def detect_ma100_touches(self, target_interval: str = None) -> List[Dict]:
    # [已禁用]     """
    # [已禁用]     检测MA100均线触碰。
    # [已禁用]
    # [已禁用]     Args:
    # [已禁用]         target_interval: 指定周期；为None则检测所有配置的周期。
    # [已禁用]
    # [已禁用]     Returns:
    # [已禁用]         触碰结果列表。
    # [已禁用]     """
    # [已禁用]     intervals = [target_interval.upper()] if target_interval else self.MA100_INTERVALS
    # [已禁用]
    # [已禁用]     results = []
    # [已禁用]     for interval in intervals:
    # [已禁用]         if interval not in self.MA100_INTERVALS:
    # [已禁用]             continue
    # [已禁用]         for ticker in self.MA100_SYMBOLS:
    # [已禁用]             touch = self._check_ma100_touch(ticker, interval)
    # [已禁用]             if touch:
    # [已禁用]                 results.append(touch)
    # [已禁用]                 self._send_ma100_alert(touch)
    # [已禁用]                 logger.info(f"📊 {ticker} {interval} 触碰MA100: {touch['touch_type']}")
    # [已禁用]
    # [已禁用]     if results:
    # [已禁用]         logger.info(f"MA100检测完成: 找到 {len(results)} 次触碰")
    # [已禁用]     else:
    # [已禁用]         logger.info(f"MA100检测完成: 无触碰信号")
    # [已禁用]     return results

    def check_reversal_pattern(self, ticker: str, exchange: str, interval: str, force: bool = False) -> Optional[Dict]:
        """
        检测反包形态

        K线定义说明：
        - T = 当前正在进行的K线（例如：04:00:00开盘时，T就是04:00-08:00的K线）
        - T-1 = T之前最近一根已收盘的K线（例如：04:00:00开盘时，T-1应该是00:00-04:00的K线）
        - T-2 = T-1之前最近一根已收盘的K线（例如：04:00:00开盘时，T-2应该是20:00-00:00的K线）

        反包定义（需要同时满足以下3个条件）:
        1. T-2是阴线（收盘价 < 开盘价）
        2. T-1是阳线（收盘价 > 开盘价）
        3. T-1收盘价 > T-2开盘价
        
        Args:
            ticker: 交易对
            exchange: 交易所
            interval: 时间周期 (如 '1H', '1D', '2H', '4H', '8H', '12H')
            
        Returns:
            如果符合反包，返回详细信息字典；否则返回None
        """
        # 只处理币安的数据
        supported_exchanges = ['bn', 'bn_spot', 'bn_futures', 'binance', 'binance_spot', 'binance_futures']
        if exchange not in supported_exchanges:
            return None
        
        # 只检测支持的interval
        if not force and interval not in self.SUPPORTED_INTERVALS:
            logger.debug(f"跳过不支持的interval: {interval} (ticker={ticker})")
            return None
        
        # 获取最近K线数据（默认10根，确保数据充足）
        df = self.get_kline_data(ticker, interval=interval, exchange=exchange, klines_count=10)
        
        if df.empty or len(df) < 2:
            logger.warning(f"{ticker}: K线数据不足（需要至少2根K线）")
            return None
        
        # 检查最新K线是否已收盘，如果未收盘则跳过它
        # 使用UTC时区统一处理时间，避免时区不一致问题
        now = pd.Timestamp.now(tz='UTC')
        df = df.sort_values('timestamp')
        
        # 确保K线数据的时间戳有统一的时区处理（如果K线数据是naive，视为UTC）
        if 'timestamp' in df.columns and len(df) > 0:
            # 检查第一个元素是否有时区信息
            if isinstance(df['timestamp'].iloc[0], pd.Timestamp):
                if df['timestamp'].iloc[0].tz is None:
                    # 如果timestamp是naive，将其视为UTC
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                elif df['timestamp'].iloc[0].tz != now.tz:
                    df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')
            else:
                # 如果不是Timestamp类型，尝试转换
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        if 'close_time' in df.columns and len(df) > 0:
            # 检查第一个元素是否有时区信息
            if isinstance(df['close_time'].iloc[0], pd.Timestamp):
                if df['close_time'].iloc[0].tz is None:
                    # 如果close_time是naive，将其视为UTC
                    df['close_time'] = pd.to_datetime(df['close_time'], utc=True)
                elif df['close_time'].iloc[0].tz != now.tz:
                    df['close_time'] = df['close_time'].dt.tz_convert('UTC')
            else:
                # 如果不是Timestamp类型，尝试转换
                df['close_time'] = pd.to_datetime(df['close_time'], utc=True)
        
        # K线定义逻辑：
        # - T = 当前正在进行的K线（例如：04:00:00开盘时，T就是04:00-08:00的K线）
        # - T-1 = T之前最近一根已收盘的K线（例如：04:00:00开盘时，T-1应该是00:00-04:00的K线）
        # - T-2 = T-1之前最近一根已收盘的K线（例如：04:00:00开盘时，T-2应该是20:00-00:00的K线）
        #
        # 找到当前正在进行的K线（T）
        # T是当前时间所在的K线（close_time >= now的第一根K线）
        current_kline = df[df['close_time'] >= now]
        
        if len(current_kline) == 0:
            # 如果所有K线都已收盘，则使用最后一根K线作为T
            # 这种情况下：
            # - T = 最后一根K线
            # - T-1 = 倒数第二根K线
            # - T-2 = 倒数第三根K线
            if len(df) < 3:
                logger.debug(f"{ticker} {interval}: K线总数不足3根，跳过检测")
                return None
            t = df.iloc[-1]  # 最后一根K线作为T
            t1 = df.iloc[-2]  # T-1
            t2 = df.iloc[-3]  # T-2
        else:
            # 找到当前正在进行的K线（T）
            t = current_kline.iloc[0]
            
            # T-1是T之前最近一根已收盘的K线
            # T-2是T-1之前最近一根已收盘的K线
            # 例如：04:00开盘时，T是04:00-08:00，T-1是00:00-04:00，T-2是20:00-00:00
            completed_df = df[(df['close_time'] < now) & (df['timestamp'] < t['timestamp'])]
            
            if len(completed_df) < 2:
                logger.debug(f"{ticker} {interval}: T之前已收盘的K线不足2根，跳过检测")
                return None
            
            # 获取T之前的最后两根已收盘的K线
            completed_df = completed_df.tail(2)
            t2 = completed_df.iloc[0]  # T-2（倒数第二根已收盘的K线）
            t1 = completed_df.iloc[1]  # T-1（最后一根已收盘的K线）
        
        # 优化检测时机：确保T-1的收盘时间已经过去（增加1分钟缓冲时间，避免在K线刚收盘时检测）
        # 这样可以确保K线数据已经完全更新
        buffer_time = timedelta(minutes=1)
        t1_close_time = t1['close_time']
        
        # 确保close_time也是UTC时区（由于上面已经统一处理了df的时区，这里应该已经是UTC）
        if t1_close_time >= (now - buffer_time):
            logger.debug(f"{ticker} {interval}: T-1 ({t1['timestamp']}) 收盘时间未超过缓冲期，跳过检测")
            return None
        
        # 检查反包条件（已移除成交量条件）
        conditions = {
            't2_bearish': t2['close'] < t2['open'],                            # 1. T-2阴线
            't1_bullish': t1['close'] > t1['open'],                            # 2. T-1阳线
            'reversal': t1['close'] > t2['open']                               # 3. T-1收盘 > T-2开盘
        }
        
        # 所有条件都满足才是反包
        is_reversal = all(conditions.values())
        
        # 调试日志：记录检测详情
        logger.debug(f"{ticker} {interval}: T-2={t2['timestamp']} ({'阴线' if t2['close'] < t2['open'] else '阳线'}), "
                    f"T-1={t1['timestamp']} ({'阳线' if t1['close'] > t1['open'] else '阴线'}), "
                    f"条件={conditions}, 反包={is_reversal}")
        
        if is_reversal:
            # 计算指标
            volume_increase_pct = ((t1['volume'] - t2['volume']) / t2['volume']) * 100
            t2_change_pct = ((t2['close'] - t2['open']) / t2['open']) * 100
            t1_change_pct = ((t1['close'] - t1['open']) / t1['open']) * 100
            reversal_strength = t1['close'] - t2['open']
            
            result = {
                'ticker': ticker,
                'exchange': exchange,
                'interval': interval,
                'direction': 'bullish',  # 向上反包（阳包阴）
                # T-2数据
                't2_date': t2['timestamp'],  # 保存timestamp对象，后续格式化
                't2_open': float(t2['open']),
                't2_high': float(t2['high']),
                't2_low': float(t2['low']),
                't2_close': float(t2['close']),
                't2_volume': float(t2['volume']),
                't2_change_pct': t2_change_pct,
                # T-1数据
                't1_date': t1['timestamp'],  # 保存timestamp对象，后续格式化
                't1_open': float(t1['open']),
                't1_high': float(t1['high']),
                't1_low': float(t1['low']),
                't1_close': float(t1['close']),
                't1_volume': float(t1['volume']),
                't1_change_pct': t1_change_pct,
                # 计算指标
                'volume_increase_pct': volume_increase_pct,
                'reversal_strength': reversal_strength,
                'conditions': conditions
            }
            
            logger.info(f"✨ {ticker} 检测到反包形态!")
            logger.info(f"  T-2: ${t2['open']:.4f} → ${t2['close']:.4f} ({t2_change_pct:+.2f}%) 📉")
            logger.info(f"  T-1: ${t1['open']:.4f} → ${t1['close']:.4f} ({t1_change_pct:+.2f}%) 📈")
            logger.info(f"  成交量增幅: {volume_increase_pct:+.1f}%")
            
            return result
        else:
            return None
    
    def check_bearish_reversal_pattern(self, ticker: str, exchange: str, interval: str, force: bool = False) -> Optional[Dict]:
        """
        检测向下反包形态（阴包阳）

        K线定义说明：与向上反包相同
        - T = 当前正在进行的K线
        - T-1 = T之前最近一根已收盘的K线
        - T-2 = T-1之前最近一根已收盘的K线

        向下反包定义（阴包阳，需要同时满足以下3个条件）:
        1. T-2是阳线（收盘价 > 开盘价）
        2. T-1是阴线（收盘价 < 开盘价）
        3. T-1收盘价 < T-2开盘价
        
        Args:
            ticker: 交易对
            exchange: 交易所
            interval: 时间周期 (如 '1H', '1D', '2H', '4H', '8H', '12H')
            force: 是否强制检测（跳过interval校验）
            
        Returns:
            如果符合向下反包，返回详细信息字典；否则返回None
        """
        supported_exchanges = ['bn', 'bn_spot', 'bn_futures', 'binance', 'binance_spot', 'binance_futures']
        if exchange not in supported_exchanges:
            return None
        
        if not force and interval not in self.SUPPORTED_INTERVALS:
            logger.debug(f"跳过不支持的interval: {interval} (ticker={ticker}, bearish)")
            return None
        
        df = self.get_kline_data(ticker, interval=interval, exchange=exchange, klines_count=10)
        
        if df.empty or len(df) < 2:
            logger.warning(f"{ticker}: K线数据不足（需要至少2根K线）")
            return None
        
        now = pd.Timestamp.now(tz='UTC')
        df = df.sort_values('timestamp')
        
        if 'timestamp' in df.columns and len(df) > 0:
            if isinstance(df['timestamp'].iloc[0], pd.Timestamp):
                if df['timestamp'].iloc[0].tz is None:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                elif df['timestamp'].iloc[0].tz != now.tz:
                    df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')
            else:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        if 'close_time' in df.columns and len(df) > 0:
            if isinstance(df['close_time'].iloc[0], pd.Timestamp):
                if df['close_time'].iloc[0].tz is None:
                    df['close_time'] = pd.to_datetime(df['close_time'], utc=True)
                elif df['close_time'].iloc[0].tz != now.tz:
                    df['close_time'] = df['close_time'].dt.tz_convert('UTC')
            else:
                df['close_time'] = pd.to_datetime(df['close_time'], utc=True)
        
        current_kline = df[df['close_time'] >= now]
        
        if len(current_kline) == 0:
            if len(df) < 3:
                logger.debug(f"{ticker} {interval}: K线总数不足3根，跳过向下反包检测")
                return None
            t = df.iloc[-1]
            t1 = df.iloc[-2]
            t2 = df.iloc[-3]
        else:
            t = current_kline.iloc[0]
            completed_df = df[(df['close_time'] < now) & (df['timestamp'] < t['timestamp'])]
            if len(completed_df) < 2:
                logger.debug(f"{ticker} {interval}: T之前已收盘的K线不足2根，跳过向下反包检测")
                return None
            completed_df = completed_df.tail(2)
            t2 = completed_df.iloc[0]
            t1 = completed_df.iloc[1]
        
        buffer_time = timedelta(minutes=1)
        t1_close_time = t1['close_time']
        if t1_close_time >= (now - buffer_time):
            logger.debug(f"{ticker} {interval}: T-1 收盘时间未超过缓冲期，跳过向下反包检测")
            return None
        
        # 向下反包条件（阴包阳，已移除成交量条件）
        conditions = {
            't2_bullish': t2['close'] > t2['open'],                             # 1. T-2阳线
            't1_bearish': t1['close'] < t1['open'],                             # 2. T-1阴线
            'reversal': t1['close'] < t2['open']                                # 3. T-1收盘 < T-2开盘
        }
        
        is_bearish_reversal = all(conditions.values())
        
        logger.debug(f"{ticker} {interval} 向下反包: T-2={'阳线' if t2['close'] > t2['open'] else '阴线'}, "
                     f"T-1={'阴线' if t1['close'] < t1['open'] else '阳线'}, "
                     f"条件={conditions}, 向下反包={is_bearish_reversal}")
        
        if is_bearish_reversal:
            volume_increase_pct = ((t1['volume'] - t2['volume']) / t2['volume']) * 100
            t2_change_pct = ((t2['close'] - t2['open']) / t2['open']) * 100
            t1_change_pct = ((t1['close'] - t1['open']) / t1['open']) * 100
            reversal_strength = t2['open'] - t1['close']  # 向下反包强度：T-2开盘 - T-1收盘
            
            result = {
                'ticker': ticker,
                'exchange': exchange,
                'interval': interval,
                'direction': 'bearish',  # 向下反包
                't2_date': t2['timestamp'],
                't2_open': float(t2['open']),
                't2_high': float(t2['high']),
                't2_low': float(t2['low']),
                't2_close': float(t2['close']),
                't2_volume': float(t2['volume']),
                't2_change_pct': t2_change_pct,
                't1_date': t1['timestamp'],
                't1_open': float(t1['open']),
                't1_high': float(t1['high']),
                't1_low': float(t1['low']),
                't1_close': float(t1['close']),
                't1_volume': float(t1['volume']),
                't1_change_pct': t1_change_pct,
                'volume_increase_pct': volume_increase_pct,
                'reversal_strength': reversal_strength,
                'conditions': conditions
            }
            
            logger.info(f"✨ {ticker} 检测到向下反包形态（阴包阳）!")
            logger.info(f"  T-2: ${t2['open']:.4f} → ${t2['close']:.4f} ({t2_change_pct:+.2f}%) 📈")
            logger.info(f"  T-1: ${t1['open']:.4f} → ${t1['close']:.4f} ({t1_change_pct:+.2f}%) 📉")
            logger.info(f"  成交量增幅: {volume_increase_pct:+.1f}%")
            
            return result
        else:
            return None
    
    def detect_all_monitors(self, target_interval: str = None) -> List[Dict]:
        """
        检测monitor表中所有代币的反包形态
        
        Args:
            target_interval: 指定要检测的周期（如'1H', '2H', '4H', '8H', '12H', '1D'），对所有监控记录检测该周期。
                           如果为None，则检测所有支持的周期（1H, 2H, 4H, 8H, 12H, 1D）
        
        Returns:
            符合反包条件的列表
        """
        logger.info("=" * 80)
        logger.info("🔍 开始检测加密货币反包形态")
        
        # 确定要检测的周期列表
        if target_interval:
            if target_interval not in self.SUPPORTED_INTERVALS:
                logger.warning(f"不支持的周期: {target_interval}，跳过检测")
                return []
            intervals_to_check = [target_interval]
            logger.info(f"检测周期: {target_interval}（对所有监控记录检测该周期）")
        else:
            intervals_to_check = self.SUPPORTED_INTERVALS
            logger.info(f"检测周期: 所有支持的周期 {intervals_to_check}（对所有监控记录检测所有周期）")
        
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # 获取所有监控记录
        with self.db:
            monitors = self.db.get_all_monitors()
        
        if not monitors:
            logger.warning("数据库中没有监控记录")
            return []
        
        logger.info(f"共找到 {len(monitors)} 条监控记录")
        
        # 对监控记录进行去重（根据ticker, exchange）
        # 同一交易对可能有多条不同interval的记录，但反包检测都要检测所有周期
        seen = set()
        unique_monitors = []
        for monitor in monitors:
            key = (monitor['ticker'], monitor['exchange'])
            if key not in seen:
                seen.add(key)
                unique_monitors.append(monitor)
        
        if len(monitors) != len(unique_monitors):
            logger.info(f"去重后: {len(unique_monitors)} 个交易对（去除了 {len(monitors) - len(unique_monitors)} 条重复记录）")
        
        reversal_tokens = []
        
        # 对每个交易对，检测指定的周期（或多个周期）
        for i, monitor in enumerate(unique_monitors, 1):
            ticker = monitor['ticker']
            exchange = monitor['exchange']
            monitor_interval = monitor['interval']  # monitor表中的interval（用于其他用途，不用于反包检测）
            
            logger.info(f"\n[{i}/{len(unique_monitors)}] 检测 {exchange} {ticker} (monitor周期: {monitor_interval})")
            
            # 检测指定的周期（或多个周期）
            for interval in intervals_to_check:
                logger.info(f"  检测 {interval} 周期反包...")
                
                result = self.check_reversal_pattern(ticker, exchange, interval)
                
                if result:
                    # 检查是否已存在相同的报警记录（去重机制）
                    # 通过检查数据库中是否已有相同(ticker, exchange, interval)和T-1时间戳的报警记录
                    t1_timestamp_str = result['t1_date'].strftime('%Y-%m-%d %H:%M:%S')
                    is_duplicate = False
                    
                    try:
                        with self.db:
                            # 查询最近24小时内相同ticker、exchange、interval的报警记录
                            recent_alerts = self.db.get_alerts(
                                ticker=ticker,
                                exchange=exchange,
                                interval=interval,
                                limit=10
                            )
                            
                            # 检查trigger_signal中是否包含T-1的时间信息
                            # trigger_signal格式: "🔄 反包报警(4H)：成交量增幅+0.6%，价格从$4.797000回涨至$4.979000"
                            # 我们通过检查T-1收盘价是否相同来判断是否重复
                            t1_close_str = f"${result['t1_close']:.6f}"
                            for alert in recent_alerts:
                                # 检查trigger_signal是否包含相同的T-1收盘价和周期
                                trigger_signal = alert.get('trigger_signal', '')
                                if f"反包报警({interval})" in trigger_signal and t1_close_str in trigger_signal:
                                    # 进一步检查时间是否接近（同一根K线）
                                    alert_time = alert.get('update_time', '')
                                    # 如果报警时间在T-1收盘时间之后，且间隔不超过2小时，认为是重复
                                    try:
                                        alert_datetime = datetime.strptime(alert_time, '%Y-%m-%d %H:%M:%S')
                                        t1_datetime = result['t1_date'].to_pydatetime()
                                        time_diff = abs((alert_datetime - t1_datetime).total_seconds() / 3600)
                                        if time_diff < 2:  # 2小时内认为是同一根K线的重复报警
                                            is_duplicate = True
                                            logger.info(f"⚠️ {ticker} {interval} 检测到重复报警（T-1时间: {t1_timestamp_str}），跳过发送")
                                            break
                                    except Exception as e:
                                        logger.debug(f"解析报警时间失败: {e}")
                    except Exception as e:
                        logger.warning(f"检查重复报警失败: {e}，继续发送报警")
                    
                    if is_duplicate:
                        continue  # 跳过重复报警
                    
                    reversal_tokens.append(result)
                    
                    # 先记录报警到数据库，再发送报警（确保数据一致性）
                    db_record_success = False
                    try:
                        # 从monitor表获取交易对信息（使用第一条匹配的记录）
                        with self.db:
                            monitor_records = self.db.get_monitor(
                                ticker=ticker,
                                exchange=exchange
                            )
                            if monitor_records:
                                monitor_record = monitor_records[0]
                                # 记录反包报警，使用检测到的周期interval，而不是monitor的interval
                                # 在trigger_signal中包含T-1的时间戳，便于后续去重检查
                                trigger_signal = f"🔄 反包报警({interval}) T-1[{t1_timestamp_str}]：成交量增幅{result['volume_increase_pct']:+.1f}%，价格从${result['t2_close']:.4f}回涨至${result['t1_close']:.6f}"
                                self.db.add_alert(
                                    exchange=exchange,
                                    date=monitor_record['date'],
                                    interval=interval,  # 使用检测到的周期
                                    ticker=ticker,
                                    trigger_signal=trigger_signal,
                                    high=result['t1_high'],
                                    low=result['t1_low'],
                                    current_price=result['t1_close']
                                )
                                db_record_success = True
                                logger.info(f"📝 {ticker} {interval} 反包报警已记录到数据库")
                            else:
                                logger.warning(f"未找到监控记录: {ticker} {exchange}，跳过数据库记录")
                    except Exception as e:
                        logger.error(f"记录反包报警到数据库失败: {e}，跳过发送报警（避免数据不一致）")
                        continue  # 数据库记录失败，不发送报警
                    
                    # 数据库记录成功后再发送企业微信通知
                    if db_record_success:
                        self.send_reversal_alert(result)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"反包检测完成: 找到 {len(reversal_tokens)} 个反包token")
        logger.info("=" * 80)
        
        return reversal_tokens
    
    def send_reversal_alert(self, reversal: Dict, max_retries: int = 3) -> bool:
        """
        发送反包检测报警（带重试机制）
        
        根据周期决定发送到哪些webhook：
        - 1H: 只发送到主webhook
        - 其他周期: 发送到所有webhook
        
        Args:
            reversal: 反包信息字典
            max_retries: 最大重试次数，默认3次
        
        Returns:
            是否发送成功
        """
        if not self.notifier:
            logger.warning("未配置企业微信webhook，跳过推送")
            return False
        
        ticker = reversal['ticker']
        exchange = reversal['exchange']
        interval = reversal['interval']
        
        logger.info(f"📤 [企业微信] 开始发送反包检测报警 - {ticker} ({interval})")
        
        # 格式化时间戳（转换为UTC+8时区）
        def format_timestamp(ts, interval):
            """根据interval格式化时间戳，转换为UTC+8时区（北京时间）"""
            # 确保时间戳有时区信息
            if isinstance(ts, pd.Timestamp):
                if ts.tz is None:
                    ts = pd.Timestamp(ts, tz='UTC')
                # 转换为UTC+8
                ts_utc8 = ts.tz_convert('Asia/Shanghai')  # UTC+8
            else:
                # 如果不是Timestamp类型，尝试转换
                ts_utc8 = pd.Timestamp(ts, tz='UTC').tz_convert('Asia/Shanghai')
            
            if interval == '1D':
                return ts_utc8.strftime('%Y-%m-%d')
            else:
                return ts_utc8.strftime('%Y-%m-%d %H:%M')
        
        t1_time = format_timestamp(reversal['t1_date'], interval=reversal['interval'])
        
        # 构建Markdown消息（简化格式，只保留交易对、周期和T-1时间）
        content = f"""## 🎯 加密货币反包检测预警

**交易对**: {ticker}
**周期**: {reversal['interval']}
**T-1时间**: {t1_time}
"""
        
        # 重试机制：最多重试max_retries次
        import time
        for attempt in range(1, max_retries + 1):
            try:
                success = self.notifier.send_markdown_message(content)
                if success:
                    logger.info(f"✅ {ticker} 反包报警已发送（尝试 {attempt}/{max_retries}）")
                    
                    if exchange in self.FUTURES_EXCHANGES:
                        chart_path = self._generate_futures_kline_chart(ticker, interval)
                        if chart_path and hasattr(self.notifier, "send_image_message"):
                            image_sent = self.notifier.send_image_message(
                                image_path=chart_path
                            )
                            if image_sent:
                                logger.info(f"🖼️ {ticker} K线图已发送")
                            else:
                                logger.warning(f"⚠️ {ticker} K线图发送失败")
                        else:
                            logger.debug(f"{ticker} 无可用K线图或企业微信不支持图片发送")
                    
                    return True
                else:
                    if attempt < max_retries:
                        wait_time = attempt * 2  # 递增等待时间：2秒、4秒、6秒
                        logger.warning(f"⚠️ {ticker} 反包报警发送失败（尝试 {attempt}/{max_retries}），{wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ {ticker} 反包报警发送失败（已重试 {max_retries} 次）")
            except Exception as e:
                if attempt < max_retries:
                    wait_time = attempt * 2
                    logger.warning(f"⚠️ {ticker} 反包报警发送异常（尝试 {attempt}/{max_retries}）: {e}，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ {ticker} 反包报警发送异常（已重试 {max_retries} 次）: {e}")
        
        return False
    
    def detect_priority_reversals(self, target_interval: str) -> List[Dict]:
        """
        检测高优先级交易对的反包形态（仅使用币安合约数据）
        同时检测：正向反包（阳包阴）和反向反包（阴包阳），任一检测到即报警。
        
        Args:
            target_interval: 周期，如 '15M', '30M', '1H', '2H', '4H', '6H', '8H', '12H', '1D', '3D', '1W'
        
        Returns:
            检测到的反包结果列表（含向上/向下反包）
        """
        interval = target_interval.upper()
        if interval not in MONITORED_INTERVALS:
            logger.warning(f"不支持的高优先级检测周期: {target_interval}")
            return []
        
        logger.info("=" * 80)
        symbols = get_monitored_symbols()
        logger.info(f"⚡ 高频反包检测 ({interval}) - 目标交易对: {', '.join(symbols)}")

        results = []
        for ticker in symbols:
            # 正向反包（阳包阴）
            reversal = self.check_reversal_pattern(
                ticker=ticker,
                exchange='bn_futures',
                interval=interval,
                force=True
            )
            if reversal:
                results.append(reversal)
                self._send_priority_alert(reversal)
            # 反向反包（阴包阳）
            bearish = self.check_bearish_reversal_pattern(
                ticker=ticker,
                exchange='bn_futures',
                interval=interval,
                force=True
            )
            if bearish:
                results.append(bearish)
                self._send_priority_alert(bearish)

            # [已禁用] 贵金属额外检测：MA52/EMA144跌破
            # [已禁用] if ticker in PRECIOUS_METALS:
            # [已禁用]     metal_result = self._check_precious_metal_ma_ema(ticker, interval)
            # [已禁用]     if metal_result:
            # [已禁用]         results.append(metal_result)
        
        if results:
            logger.info(f"⚡ 高频反包检测 ({interval}) 找到 {len(results)} 个结果（含向上/向下反包）")
        else:
            logger.info(f"⚡ 高频反包检测 ({interval}) 无反包信号")

        return results

    def detect_priority_reversals_dynamic(self, target_interval: str) -> List[Dict]:
        """
        检测动态配置交易对的反包形态（仅使用币安合约数据，从 tokens-config-dynamic.md 读取）
        同时检测：正向反包（阳包阴）和反向反包（阴包阳），任一检测到即报警。

        Args:
            target_interval: 周期，如 '15M', '30M', '1H', '2H', '4H', '6H', '8H', '12H', '1D', '3D', '1W'

        Returns:
            检测到的反包结果列表（含向上/向下反包）
        """
        interval = target_interval.upper()
        if interval not in MONITORED_INTERVALS:
            logger.warning(f"不支持的高优先级检测周期: {target_interval}")
            return []

        logger.info("=" * 80)
        symbols = get_dynamic_symbols_for_interval(interval)
        logger.info(f"⚡ 高频反包检测（动态配置，{interval}） - 目标交易对: {', '.join(symbols)}")

        results = []
        for ticker in symbols:
            # 正向反包（阳包阴）
            reversal = self.check_reversal_pattern(
                ticker=ticker,
                exchange='bn_futures',
                interval=interval,
                force=True
            )
            if reversal:
                results.append(reversal)
                self._send_priority_alert(reversal)
            # 反向反包（阴包阳）
            bearish = self.check_bearish_reversal_pattern(
                ticker=ticker,
                exchange='bn_futures',
                interval=interval,
                force=True
            )
            if bearish:
                results.append(bearish)
                self._send_priority_alert(bearish)

        if results:
            logger.info(f"⚡ 高频反包检测（动态配置，{interval}）找到 {len(results)} 个结果（含向上/向下反包）")
        else:
            logger.info(f"⚡ 高频反包检测（动态配置，{interval}）无反包信号")

        return results
    
    def check_reversal_pattern_utf8(self, ticker: str, interval: str) -> Optional[Dict]:
        """
        使用get_klines_utf8检测反包形态（针对1D、3D、周线、月线）
        
        注意：此方法使用UTC+8时区的K线数据，专门用于日线及以上周期的反包检测
        
        Args:
            ticker: 交易对
            interval: 时间周期 ('1D', '3D', '1W', '1M')
            
        Returns:
            如果符合反包，返回详细信息字典；否则返回None
        """
        # 支持的周期
        supported_intervals = ['1D', '3D', '1W', '1M']
        if interval not in supported_intervals:
            logger.warning(f"不支持的interval: {interval}，支持的周期: {supported_intervals}")
            return None
        
        # 映射到币安API格式（使用BN_INTERVAL_SUFFIX）
        bn_interval = self.BN_INTERVAL_SUFFIX.get(interval)
        if not bn_interval:
            logger.warning(f"不支持的interval: {interval}")
            return None
        
        try:
            # 使用get_klines_utf8获取K线数据（需要足够的历史数据）
            days_needed = {
                '1d': 10,   # 10天数据
                '3d': 30,   # 30天数据（约10根3日K线）
                '1w': 70,   # 70天数据（约10根周K线）
                '1M': 300   # 300天数据（约10根月K线）
            }
            days = days_needed.get(bn_interval, 10)
            
            df = self.bn_fetcher.get_klines_utf8(
                symbol=ticker,
                days=days,
                interval=bn_interval
            )
            
            if df.empty or len(df) < 3:
                logger.warning(f"{ticker} {interval}: K线数据不足（需要至少3根K线）")
                return None
            
            # 按时间排序
            df = df.sort_values('timestamp')
            
            # 对于日线及以上周期，我们检测最后两根已收盘的K线
            # 由于get_klines_utf8返回的数据中，最后一条可能是今天正在进行的K线
            # 我们需要找到最后两根已收盘的K线作为T-1和T-2
            
            # 获取当前时间（UTC+8）
            from datetime import timezone, timedelta
            utc8_offset = timezone(timedelta(hours=8))
            now_utc8 = pd.Timestamp.now(tz=utc8_offset)
            
            # 确保时间戳有时区信息
            if 'timestamp' in df.columns:
                if df['timestamp'].iloc[0].tz is None:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                df['timestamp'] = df['timestamp'].dt.tz_convert(utc8_offset)
            
            if 'close_time' in df.columns:
                if df['close_time'].iloc[0].tz is None:
                    df['close_time'] = pd.to_datetime(df['close_time'], utc=True)
                df['close_time'] = df['close_time'].dt.tz_convert(utc8_offset)
            
            # 找到已收盘的K线（收盘时间 < 当前时间）
            completed_df = df[df['close_time'] < now_utc8]
            
            if len(completed_df) < 2:
                logger.debug(f"{ticker} {interval}: 已收盘的K线不足2根，跳过检测")
                return None
            
            # 获取最后两根已收盘的K线
            t2 = completed_df.iloc[-2]  # T-2
            t1 = completed_df.iloc[-1]   # T-1
            
            # 检查反包条件
            conditions = {
                'volume_increase': t1['volume'] > t2['volume'],                     # 1. 成交量增加
                't2_bearish': t2['close'] < t2['open'],                            # 2. T-2阴线
                't1_bullish': t1['close'] > t1['open'],                             # 3. T-1阳线
                'reversal': t1['close'] > t2['open']                                # 4. T-1收盘 > T-2开盘
            }
            
            # 所有条件都满足才是反包
            is_reversal = all(conditions.values())
            
            logger.debug(f"{ticker} {interval}: T-2={t2['timestamp']} ({'阴线' if t2['close'] < t2['open'] else '阳线'}), "
                        f"T-1={t1['timestamp']} ({'阳线' if t1['close'] > t1['open'] else '阴线'}), "
                        f"条件={conditions}, 反包={is_reversal}")
            
            if is_reversal:
                # 计算指标
                volume_increase_pct = ((t1['volume'] - t2['volume']) / t2['volume']) * 100 if t2['volume'] > 0 else 0
                t2_change_pct = ((t2['close'] - t2['open']) / t2['open']) * 100 if t2['open'] > 0 else 0
                t1_change_pct = ((t1['close'] - t1['open']) / t1['open']) * 100 if t1['open'] > 0 else 0
                reversal_strength = t1['close'] - t2['open']
                
                # 获取 quote_asset_volume（如果存在）
                t2_quote_asset_volume = float(t2.get('quote_asset_volume', 0))
                t1_quote_asset_volume = float(t1.get('quote_asset_volume', 0))
                usdt_volume_growth_rate_pct = ((t1_quote_asset_volume - t2_quote_asset_volume) / t2_quote_asset_volume * 100) if t2_quote_asset_volume > 0 else 0
                
                result = {
                    'ticker': ticker,
                    'exchange': 'bn_spot',  # 使用现货数据
                    'interval': interval,
                    # T-2数据
                    't2_date': t2['timestamp'],
                    't2_open': float(t2['open']),
                    't2_high': float(t2['high']),
                    't2_low': float(t2['low']),
                    't2_close': float(t2['close']),
                    't2_volume': float(t2['volume']),
                    't2_quote_asset_volume': t2_quote_asset_volume,
                    't2_change_pct': t2_change_pct,
                    # T-1数据
                    't1_date': t1['timestamp'],
                    't1_open': float(t1['open']),
                    't1_high': float(t1['high']),
                    't1_low': float(t1['low']),
                    't1_close': float(t1['close']),
                    't1_volume': float(t1['volume']),
                    't1_quote_asset_volume': t1_quote_asset_volume,
                    't1_change_pct': t1_change_pct,
                    # 计算指标
                    'volume_increase_pct': volume_increase_pct,
                    'usdt_volume_growth_rate_pct': usdt_volume_growth_rate_pct,
                    'reversal_strength': reversal_strength,
                    'conditions': conditions
                }
                
                logger.info(f"✨ {ticker} {interval} 检测到反包形态!")
                logger.info(f"  T-2: ${t2['open']:.4f} → ${t2['close']:.4f} ({t2_change_pct:+.2f}%) 📉")
                logger.info(f"  T-1: ${t1['open']:.4f} → ${t1['close']:.4f} ({t1_change_pct:+.2f}%) 📈")
                logger.info(f"  成交量增幅: {volume_increase_pct:+.1f}%")
                
                return result
            else:
                return None
                
        except Exception as e:
            logger.error(f"检测{ticker} {interval}反包形态失败: {e}", exc_info=True)
            return None
    
    def _convert_ticker_to_okx_format(self, ticker: str) -> str:
        """
        将币安格式的交易对转换为OKX格式
        BTCUSDT -> BTC-USDT
        """
        if len(ticker) > 4 and ticker.endswith('USDT'):
            base = ticker[:-4]
            return f"{base}-USDT"
        return ticker
    
    def check_reversal_pattern_okx_utf8(self, ticker: str, interval: str) -> Optional[Dict]:
        """
        使用OKX数据检测反包形态（针对2D、5D周期）
        
        注意：此方法使用OKX现货数据，UTC+8时区的K线数据
        
        Args:
            ticker: 交易对（币安格式，如BTCUSDT）
            interval: 时间周期 ('2D', '5D')
            
        Returns:
            如果符合反包，返回详细信息字典；否则返回None
        """
        # 支持的周期
        supported_intervals = ['2D', '5D']
        if interval not in supported_intervals:
            logger.warning(f"不支持的interval: {interval}，支持的周期: {supported_intervals}")
            return None
        
        # 映射到OKX API格式
        okx_interval_map = {
            '2D': '2d',
            '5D': '5d'
        }
        okx_interval = okx_interval_map[interval]
        
        # 转换交易对格式：BTCUSDT -> BTC-USDT
        okx_ticker = self._convert_ticker_to_okx_format(ticker)
        
        try:
            # 使用get_klines获取K线数据（需要足够的历史数据，use_utc0=False表示使用UTC+8）
            days_needed = {
                '2d': 20,   # 20天数据（约10根2日K线）
                '5d': 50    # 50天数据（约10根5日K线）
            }
            days = days_needed.get(okx_interval, 20)
            
            df = self.okx_fetcher.get_klines(
                symbol=okx_ticker,
                days=days,
                interval=okx_interval,
                use_utc0=False  # 使用UTC+8时区
            )
            
            if df.empty or len(df) < 3:
                logger.warning(f"{ticker} {interval}: OKX K线数据不足（需要至少3根K线）")
                return None
            
            # 按时间排序
            df = df.sort_values('timestamp')
            
            # 对于日线及以上周期，我们检测最后两根已收盘的K线
            # 获取当前时间（UTC+8）
            from datetime import timezone, timedelta
            utc8_offset = timezone(timedelta(hours=8))
            now_utc8 = pd.Timestamp.now(tz=utc8_offset)
            
            # 确保时间戳有时区信息
            if 'timestamp' in df.columns:
                if df['timestamp'].iloc[0].tz is None:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                df['timestamp'] = df['timestamp'].dt.tz_convert(utc8_offset)
            
            if 'close_time' in df.columns:
                if df['close_time'].iloc[0].tz is None:
                    df['close_time'] = pd.to_datetime(df['close_time'], utc=True)
                df['close_time'] = df['close_time'].dt.tz_convert(utc8_offset)
            
            # 找到已收盘的K线（收盘时间 < 当前时间）
            completed_df = df[df['close_time'] < now_utc8]
            
            if len(completed_df) < 2:
                logger.debug(f"{ticker} {interval}: 已收盘的K线不足2根，跳过检测")
                return None
            
            # 获取最后两根已收盘的K线
            t2 = completed_df.iloc[-2]  # T-2
            t1 = completed_df.iloc[-1]   # T-1
            
            # 检查反包条件
            conditions = {
                'volume_increase': t1['volume'] > t2['volume'],                     # 1. 成交量增加
                't2_bearish': t2['close'] < t2['open'],                            # 2. T-2阴线
                't1_bullish': t1['close'] > t1['open'],                             # 3. T-1阳线
                'reversal': t1['close'] > t2['open']                                # 4. T-1收盘 > T-2开盘
            }
            
            # 所有条件都满足才是反包
            is_reversal = all(conditions.values())
            
            logger.debug(f"{ticker} {interval}: T-2={t2['timestamp']} ({'阴线' if t2['close'] < t2['open'] else '阳线'}), "
                        f"T-1={t1['timestamp']} ({'阳线' if t1['close'] > t1['open'] else '阴线'}), "
                        f"条件={conditions}, 反包={is_reversal}")
            
            if is_reversal:
                # 计算指标
                volume_increase_pct = ((t1['volume'] - t2['volume']) / t2['volume']) * 100 if t2['volume'] > 0 else 0
                t2_change_pct = ((t2['close'] - t2['open']) / t2['open']) * 100 if t2['open'] > 0 else 0
                t1_change_pct = ((t1['close'] - t1['open']) / t1['open']) * 100 if t1['open'] > 0 else 0
                reversal_strength = t1['close'] - t2['open']
                
                # 获取 quote_asset_volume（如果存在）
                t2_quote_asset_volume = float(t2.get('quote_asset_volume', 0))
                t1_quote_asset_volume = float(t1.get('quote_asset_volume', 0))
                usdt_volume_growth_rate_pct = ((t1_quote_asset_volume - t2_quote_asset_volume) / t2_quote_asset_volume * 100) if t2_quote_asset_volume > 0 else 0
                
                result = {
                    'ticker': ticker,  # 保持币安格式
                    'exchange': 'ok_spot',  # 使用OKX现货数据
                    'interval': interval,
                    # T-2数据
                    't2_date': t2['timestamp'],
                    't2_open': float(t2['open']),
                    't2_high': float(t2['high']),
                    't2_low': float(t2['low']),
                    't2_close': float(t2['close']),
                    't2_volume': float(t2['volume']),
                    't2_quote_asset_volume': t2_quote_asset_volume,
                    't2_change_pct': t2_change_pct,
                    # T-1数据
                    't1_date': t1['timestamp'],
                    't1_open': float(t1['open']),
                    't1_high': float(t1['high']),
                    't1_low': float(t1['low']),
                    't1_close': float(t1['close']),
                    't1_volume': float(t1['volume']),
                    't1_quote_asset_volume': t1_quote_asset_volume,
                    't1_change_pct': t1_change_pct,
                    # 计算指标
                    'volume_increase_pct': volume_increase_pct,
                    'usdt_volume_growth_rate_pct': usdt_volume_growth_rate_pct,
                    'reversal_strength': reversal_strength,
                    'conditions': conditions
                }
                
                logger.info(f"✨ {ticker} {interval} (OKX) 检测到反包形态!")
                logger.info(f"  T-2: ${t2['open']:.4f} → ${t2['close']:.4f} ({t2_change_pct:+.2f}%) 📉")
                logger.info(f"  T-1: ${t1['open']:.4f} → ${t1['close']:.4f} ({t1_change_pct:+.2f}%) 📈")
                logger.info(f"  成交量增幅: {volume_increase_pct:+.1f}%")
                
                return result
            else:
                return None
                
        except Exception as e:
            logger.error(f"检测{ticker} {interval} (OKX) 反包形态失败: {e}", exc_info=True)
            return None
    
    def detect_high_frequency_reversals(self, intervals: List[str] = None) -> List[Dict]:
        """
        高频反包检测（长周期，现货数据）
        - 2D、5D：使用OKX现货数据（UTC+8）
        - 1D、3D、1W、1M：使用币安现货数据（UTC+8）
        注意：1D/3D/1W 由 high_priority_reversal_job 使用 bn_futures 数据覆盖，
              此方法主要处理 2D/5D（OKX特有）以及 1M 的现货验证。

        Args:
            intervals: 要检测的周期列表，调用方应传入 ['2D', '5D', '1M']
        
        Returns:
            符合反包条件的列表
        """
        if intervals is None:
            intervals = ['2D', '5D', '1M']
        
        logger.info("=" * 80)
        logger.info("🔍 开始高频反包检测（2D/5D/1M，现货数据）")
        logger.info(f"检测周期: {intervals}")
        logger.info(f"目标交易对: {', '.join(symbols)}")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        reversal_tokens = []
        symbols = get_monitored_symbols()

        # 对每个高频交易对，检测指定的周期
        for i, ticker in enumerate(symbols, 1):
            logger.info(f"\n[{i}/{len(symbols)}] 检测 {ticker}")
            
            # 检测指定的周期
            for interval in intervals:
                # 根据周期选择数据源
                if interval in ['2D', '5D']:
                    # 2D和5D使用OKX现货数据
                    logger.info(f"  检测 {interval} 周期反包 (OKX现货)...")
                    result = self.check_reversal_pattern_okx_utf8(ticker, interval)
                    exchange = 'ok_spot'  # OKX现货
                else:
                    # 1D、3D、1W、1M使用币安现货数据
                    logger.info(f"  检测 {interval} 周期反包 (BN现货)...")
                    result = self.check_reversal_pattern_utf8(ticker, interval)
                    exchange = 'bn_spot'  # 币安现货
                
                if result:
                    # 检查是否已存在相同的报警记录（去重机制）
                    t1_timestamp_str = result['t1_date'].strftime('%Y-%m-%d %H:%M:%S')
                    is_duplicate = False
                    
                    # 使用result中的exchange（可能是ok_spot或bn_spot）
                    alert_exchange = result.get('exchange', exchange)
                    
                    try:
                        with self.db:
                            # 查询最近24小时内相同ticker、exchange、interval的报警记录
                            recent_alerts = self.db.get_alerts(
                                ticker=ticker,
                                exchange=alert_exchange,
                                interval=interval,
                                limit=10
                            )
                            
                            # 检查trigger_signal中是否包含相同的T-1收盘价和周期
                            t1_close_str = f"${result['t1_close']:.6f}"
                            for alert in recent_alerts:
                                trigger_signal = alert.get('trigger_signal', '')
                                if f"反包报警({interval})" in trigger_signal and t1_close_str in trigger_signal:
                                    # 进一步检查时间是否接近（同一根K线）
                                    alert_time = alert.get('update_time', '')
                                    try:
                                        alert_datetime = datetime.strptime(alert_time, '%Y-%m-%d %H:%M:%S')
                                        t1_datetime = result['t1_date'].to_pydatetime()
                                        time_diff = abs((alert_datetime - t1_datetime).total_seconds() / 3600)
                                        if time_diff < 24:  # 24小时内认为是同一根K线的重复报警
                                            is_duplicate = True
                                            logger.info(f"⚠️ {ticker} {interval} 检测到重复报警（T-1时间: {t1_timestamp_str}），跳过发送")
                                            break
                                    except Exception as e:
                                        logger.debug(f"解析报警时间失败: {e}")
                    except Exception as e:
                        logger.warning(f"检查重复报警失败: {e}，继续发送报警")
                    
                    if is_duplicate:
                        continue  # 跳过重复报警
                    
                    reversal_tokens.append(result)
                    
                    # 先记录报警到数据库，再发送报警
                    db_record_success = False
                    try:
                        with self.db:
                            # 使用result中的exchange（可能是ok_spot或bn_spot）
                            alert_exchange = result.get('exchange', exchange)
                            # 尝试获取监控记录，如果没有则使用当前日期
                            monitor_records = self.db.get_monitor(
                                ticker=ticker,
                                exchange=alert_exchange
                            )
                            if monitor_records:
                                monitor_record = monitor_records[0]
                                monitor_date = monitor_record['date']
                            else:
                                # 如果没有监控记录，使用当前日期
                                monitor_date = datetime.now().strftime('%Y-%m-%d')
                                logger.debug(f"未找到监控记录: {ticker} {alert_exchange}，使用当前日期: {monitor_date}")
                            
                            trigger_signal = f"🔄 高频反包报警({interval}) T-1[{t1_timestamp_str}]：成交量增幅{result['volume_increase_pct']:+.1f}%，价格从${result['t2_close']:.4f}回涨至${result['t1_close']:.6f}"
                            self.db.add_alert(
                                exchange=alert_exchange,
                                date=monitor_date,
                                interval=interval,
                                ticker=ticker,
                                trigger_signal=trigger_signal,
                                high=result['t1_high'],
                                low=result['t1_low'],
                                current_price=result['t1_close']
                            )
                            db_record_success = True
                            logger.info(f"📝 {ticker} {interval} 高频反包报警已记录到数据库")
                    except Exception as e:
                        logger.error(f"记录高频反包报警到数据库失败: {e}，跳过发送报警")
                        continue
                    
                    # 数据库记录成功后再发送企业微信通知
                    if db_record_success:
                        self.send_reversal_alert(result)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"高频反包检测完成: 找到 {len(reversal_tokens)} 个反包token")
        logger.info("=" * 80)
        
        # 如果有检测结果，保存到 Excel
        if reversal_tokens:
            try:
                self.save_high_frequency_reversals_to_excel(reversal_tokens)
            except Exception as e:
                logger.error(f"保存高频反包检测结果到 Excel 失败: {e}", exc_info=True)

        return reversal_tokens

    def detect_high_frequency_reversals_dynamic(self, intervals: List[str] = None) -> List[Dict]:
        """
        高频反包检测（动态配置，长周期，现货数据）
        - 2D、5D：使用OKX现货数据（UTC+8）
        - 1M：使用币安现货数据（UTC+8）
        从 tokens-config-dynamic.md 读取交易对列表

        Args:
            intervals: 要检测的周期列表，调用方应传入 ['2D', '5D', '1M']

        Returns:
            符合反包条件的列表
        """
        if intervals is None:
            intervals = ['2D', '5D', '1M']

        logger.info("=" * 80)
        logger.info("🔍 开始高频反包检测（动态配置，2D/5D/1M，现货数据）")
        logger.info(f"检测周期: {intervals}")

        reversal_tokens = []
        # 按 level 过滤：每个 ticker 只跑它 level 兼容的 intervals
        from src.alert.monitor_config import get_dynamic_symbols_with_levels, LEVEL_INTERVAL_MAP
        all_with_levels = get_dynamic_symbols_with_levels()
        eligible_intervals_per_symbol = {
            s: [iv for iv in intervals if iv in LEVEL_INTERVAL_MAP.get(lvl, set())]
            for s, lvl in all_with_levels
        }
        symbols = list(eligible_intervals_per_symbol.keys())
        logger.info(f"目标交易对: {', '.join(symbols)}")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # 对每个高频交易对，检测指定的周期
        for i, ticker in enumerate(symbols, 1):
            logger.info(f"\n[{i}/{len(symbols)}] 检测 {ticker}")

            # 只跑该 ticker 的 level 兼容的 intervals
            eligible_for_ticker = eligible_intervals_per_symbol.get(ticker, [])
            for interval in eligible_for_ticker:
                # 根据周期选择数据源
                if interval in ['2D', '5D']:
                    # 2D和5D使用OKX现货数据
                    logger.info(f"  检测 {interval} 周期反包 (OKX现货)...")
                    result = self.check_reversal_pattern_okx_utf8(ticker, interval)
                    exchange = 'ok_spot'  # OKX现货
                else:
                    # 1M使用币安现货数据
                    logger.info(f"  检测 {interval} 周期反包 (BN现货)...")
                    result = self.check_reversal_pattern_utf8(ticker, interval)
                    exchange = 'bn_spot'  # 币安现货

                if result:
                    # 检查是否已存在相同的报警记录（去重机制）
                    t1_timestamp_str = result['t1_date'].strftime('%Y-%m-%d %H:%M:%S')
                    is_duplicate = False

                    # 使用result中的exchange（可能是ok_spot或bn_spot）
                    alert_exchange = result.get('exchange', exchange)

                    try:
                        with self.db:
                            # 查询最近24小时内相同ticker、exchange、interval的报警记录
                            recent_alerts = self.db.get_alerts(
                                ticker=ticker,
                                exchange=alert_exchange,
                                interval=interval,
                                limit=10
                            )

                            # 检查trigger_signal中是否包含相同的T-1收盘价和周期
                            t1_close_str = f"${result['t1_close']:.6f}"
                            for alert in recent_alerts:
                                trigger_signal = alert.get('trigger_signal', '')
                                if f"反包报警({interval})" in trigger_signal and t1_close_str in trigger_signal:
                                    # 进一步检查时间是否接近（同一根K线）
                                    alert_time = alert.get('update_time', '')
                                    try:
                                        alert_datetime = datetime.strptime(alert_time, '%Y-%m-%d %H:%M:%S')
                                        t1_datetime = result['t1_date'].to_pydatetime()
                                        time_diff = abs((alert_datetime - t1_datetime).total_seconds() / 3600)
                                        if time_diff < 24:  # 24小时内认为是同一根K线的重复报警
                                            is_duplicate = True
                                            logger.info(f"⚠️ {ticker} {interval} 检测到重复报警（T-1时间: {t1_timestamp_str}），跳过发送")
                                            break
                                    except Exception as e:
                                        logger.debug(f"解析报警时间失败: {e}")
                    except Exception as e:
                        logger.warning(f"检查重复报警失败: {e}，继续发送报警")

                    if is_duplicate:
                        continue  # 跳过重复报警

                    reversal_tokens.append(result)

                    # 先记录报警到数据库，再发送报警
                    db_record_success = False
                    try:
                        with self.db:
                            # 使用result中的exchange（可能是ok_spot或bn_spot）
                            alert_exchange = result.get('exchange', exchange)
                            # 尝试获取监控记录，如果没有则使用当前日期
                            monitor_records = self.db.get_monitor(
                                ticker=ticker,
                                exchange=alert_exchange
                            )
                            if monitor_records:
                                monitor_record = monitor_records[0]
                                monitor_date = monitor_record['date']
                            else:
                                # 如果没有监控记录，使用当前日期
                                monitor_date = datetime.now().strftime('%Y-%m-%d')
                                logger.debug(f"未找到监控记录: {ticker} {alert_exchange}，使用当前日期: {monitor_date}")

                            trigger_signal = f"🔄 高频反包报警({interval}) T-1[{t1_timestamp_str}]：成交量增幅{result['volume_increase_pct']:+.1f}%，价格从${result['t2_close']:.4f}回涨至${result['t1_close']:.6f}"
                            self.db.add_alert(
                                exchange=alert_exchange,
                                date=monitor_date,
                                interval=interval,
                                ticker=ticker,
                                trigger_signal=trigger_signal,
                                high=result['t1_high'],
                                low=result['t1_low'],
                                current_price=result['t1_close']
                            )
                            db_record_success = True
                            logger.info(f"📝 {ticker} {interval} 高频反包报警已记录到数据库")
                    except Exception as e:
                        logger.error(f"记录高频反包报警到数据库失败: {e}，跳过发送报警")
                        continue

                    # 数据库记录成功后再发送企业微信通知
                    if db_record_success:
                        self.send_reversal_alert(result)

        logger.info("\n" + "=" * 80)
        logger.info(f"高频反包检测（动态配置）完成: 找到 {len(reversal_tokens)} 个反包token")
        logger.info("=" * 80)

        # 如果有检测结果，保存到 Excel
        if reversal_tokens:
            try:
                self.save_high_frequency_reversals_to_excel(reversal_tokens)
            except Exception as e:
                logger.error(f"保存高频反包检测结果到 Excel 失败: {e}", exc_info=True)

        return reversal_tokens

    def save_high_frequency_reversals_to_excel(self, reversal_tokens: List[Dict]):
        """
        将高频反包检测结果保存到 Excel 文件
        
        Args:
            reversal_tokens: 反包检测结果列表
        """
        if not reversal_tokens:
            logger.warning("没有反包检测结果，跳过保存")
            return
        
        # 创建保存目录
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # 生成文件名（带时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'high_frequency_reversals_{timestamp}.xlsx'
        filepath = os.path.join(data_dir, filename)
        
        # 周期到中文 Sheet 名称的映射
        interval_sheet_map = {
            '1D': '1日',
            '2D': '2日',
            '3D': '3日',
            '5D': '5日',
            '1W': '周',
            '1M': '月'
        }
        
        # 按周期分组
        grouped_by_interval = {}
        for token in reversal_tokens:
            interval = token.get('interval', '1D')
            if interval not in grouped_by_interval:
                grouped_by_interval[interval] = []
            grouped_by_interval[interval].append(token)
        
        # 创建 Excel writer
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            for interval, tokens in grouped_by_interval.items():
                # 获取 Sheet 名称
                sheet_name = interval_sheet_map.get(interval, interval)
                
                # 构建 DataFrame
                rows = []
                for token in tokens:
                    # 格式化日期
                    t2_date = token['t2_date']
                    t1_date = token['t1_date']
                    if isinstance(t2_date, pd.Timestamp):
                        t2_date_str = t2_date.strftime('%Y-%m-%d')
                    else:
                        t2_date_str = str(t2_date)
                    
                    if isinstance(t1_date, pd.Timestamp):
                        t1_date_str = t1_date.strftime('%Y-%m-%d')
                    else:
                        t1_date_str = str(t1_date)
                    
                    row = {
                        'symbol': token['ticker'],
                        'T_minus_2_date': t2_date_str,
                        'T_minus_2_open': token['t2_open'],
                        'T_minus_2_high': token['t2_high'],
                        'T_minus_2_low': token['t2_low'],
                        'T_minus_2_close': token['t2_close'],
                        'T_minus_2_volume': token['t2_volume'],
                        'T_minus_2_quote_asset_volume': token.get('t2_quote_asset_volume', 0),
                        'T_minus_2_change_pct': token['t2_change_pct'],
                        'T_minus_1_date': t1_date_str,
                        'T_minus_1_open': token['t1_open'],
                        'T_minus_1_high': token['t1_high'],
                        'T_minus_1_low': token['t1_low'],
                        'T_minus_1_close': token['t1_close'],
                        'T_minus_1_volume': token['t1_volume'],
                        'T_minus_1_quote_asset_volume': token.get('t1_quote_asset_volume', 0),
                        'T_minus_1_change_pct': token['t1_change_pct'],
                        'volume_growth_rate_pct': token['volume_increase_pct'],
                        'usdt_volume_growth_rate_pct': token.get('usdt_volume_growth_rate_pct', 0)
                    }
                    rows.append(row)
                
                # 创建 DataFrame
                df = pd.DataFrame(rows)
                
                # 写入 Excel
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                logger.info(f"✓ 已保存 {len(tokens)} 条 {interval} 周期反包数据到 Sheet '{sheet_name}'")
        
        logger.info(f"✓ 高频反包检测结果已保存到: {filepath}")


def main():
    """测试函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='加密货币反包检测工具')
    parser.add_argument('--wecom-webhook', type=str, 
                       help='企业微信webhook地址（可选，也可通过.env配置）')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🔍 加密货币反包检测工具")
    print("=" * 80)
    print()
    
    # 创建检测器
    detector = CryptoReversalDetector(wecom_webhook_url=args.wecom_webhook)
    
    # 执行检测
    reversal_tokens = detector.detect_all_monitors()
    
    # 显示结果
    print("\n" + "=" * 80)
    print("📊 检测结果摘要")
    print("=" * 80)
    print(f"检测代币数: {len(reversal_tokens)}")
    
    if reversal_tokens:
        print(f"\n找到 {len(reversal_tokens)} 个反包token:\n")
        
        for i, token in enumerate(reversal_tokens, 1):
            print(f"{i}. {token['ticker']} ({token['exchange']})")
            print(f"   T-2: ${token['t2_open']:.4f} → ${token['t2_close']:.4f} ({token['t2_change_pct']:+.2f}%)")
            print(f"   T-1: ${token['t1_open']:.4f} → ${token['t1_close']:.4f} ({token['t1_change_pct']:+.2f}%)")
            print(f"   成交量增幅: {token['volume_increase_pct']:+.1f}%")
            print()
    else:
        print("\n未找到符合反包条件的token")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

