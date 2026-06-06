#!/usr/bin/env python3
"""
每日反包数据报警模块
每天早晨8:30读取当日前端BN、OK市场筛选出来的反包数据，并推送报警通知
"""

import os
import sys
import logging
import glob
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.alert.wecom_notifier import WeComNotifier
from src.crypto.binance_data_fetcher import BinanceDataFetcher
from src.crypto.okx_data_fetcher import OKXDataFetcher

# 导入特别关注相关函数
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from src.crypto.flask_auto_server import get_watchlist_webhook_url, get_watchlist_symbols

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyReversalAlert:
    """每日反包数据报警器"""
    
    # Interval映射 (Excel中的sheet名称 -> Binance/OKX格式)
    INTERVAL_MAP = {
        '1日': '1d',
        '2日': '2d',
        '3日': '3d',
        '5日': '5d',
        '周': '1w',
        '月': '1M'
    }
    
    # 交易所映射
    EXCHANGE_MAP = {
        'bn': 'bn',
        'ok': 'ok'
    }
    
    def __init__(self, data_dir: str = None, wecom_webhook_url: str = None):
        """
        初始化每日反包报警器
        
        Args:
            data_dir: Excel文件所在目录，默认为项目根目录下的data目录
            wecom_webhook_url: 企业微信webhook地址
        """
        if data_dir is None:
            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
        self.data_dir = Path(data_dir)
        
        self.bn_fetcher = BinanceDataFetcher(market_type='futures')
        self.okx_fetcher = OKXDataFetcher(market_type='futures')
        
        # 初始化企业微信通知器
        if wecom_webhook_url is None:
            from dotenv import load_dotenv
            load_dotenv()
            wecom_webhook_url = os.getenv('WECOM_WEBHOOK_URL')
        
        self.notifier = WeComNotifier(
            webhook_url=wecom_webhook_url
        ) if wecom_webhook_url else None
        
        # K线图保存目录
        self.chart_dir = self.data_dir / 'charts'
        self.chart_dir.mkdir(parents=True, exist_ok=True)
    
    def find_today_files(self) -> Dict[str, List[Path]]:
        """
        查找当日的BN和OK市场反包数据文件（筛选后的反包数据）
        
        Returns:
            字典，key为'exchange'，value为文件路径列表
        """
        today = datetime.now().strftime('%Y%m%d')
        
        # BN市场文件：qualified_futures_tokens_multi_period_YYYYMMDD_*.xlsx（筛选后的反包数据）
        bn_pattern = str(self.data_dir / f'qualified_futures_tokens_multi_period_{today}*.xlsx')
        bn_files = [Path(f) for f in glob.glob(bn_pattern)]
        
        # OK市场文件：qualified_okx_futures_tokens_multi_period_YYYYMMDD_*.xlsx（筛选后的反包数据）
        ok_pattern = str(self.data_dir / f'qualified_okx_futures_tokens_multi_period_{today}*.xlsx')
        ok_files = [Path(f) for f in glob.glob(ok_pattern)]
        
        # 选择最新的文件
        bn_file = max(bn_files, key=lambda p: p.stat().st_mtime) if bn_files else None
        ok_file = max(ok_files, key=lambda p: p.stat().st_mtime) if ok_files else None
        
        result = {}
        if bn_file:
            result['bn'] = bn_file
        if ok_file:
            result['ok'] = ok_file
        
        logger.info(f"找到当日筛选后的反包数据文件:")
        if bn_file:
            logger.info(f"  BN市场: {bn_file.name}")
        if ok_file:
            logger.info(f"  OK市场: {ok_file.name}")
        
        return result
    
    def read_reversal_data(self, file_path: Path, exchange: str) -> List[Dict]:
        """
        读取反包数据文件（筛选后的反包数据格式）
        
        Args:
            file_path: Excel文件路径
            exchange: 交易所名称（'bn' 或 'ok'）
            
        Returns:
            反包数据列表
        """
        try:
            excel_data = pd.read_excel(file_path, sheet_name=None)
            reversal_data = []
            
            # 从文件名中提取日期（格式：qualified_*_YYYYMMDD_HHMMSS.xlsx）
            import re
            filename = file_path.name
            date_match = re.search(r'(\d{8})', filename)
            file_date = date_match.group(1) if date_match else None
            if file_date:
                # 转换为 YYYY-MM-DD 格式
                file_date_str = f"{file_date[:4]}-{file_date[4:6]}-{file_date[6:8]}"
            else:
                # 如果无法从文件名提取，使用文件修改时间
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                file_date_str = file_mtime.strftime('%Y-%m-%d')
            
            for sheet_name, df in excel_data.items():
                # 跳过空sheet
                if df.empty:
                    continue
                
                # 映射sheet名称到interval
                interval = self.INTERVAL_MAP.get(sheet_name)
                if not interval:
                    logger.warning(f"跳过未知的sheet名称: {sheet_name}")
                    continue
                
                # 处理每一行数据（qualified文件格式：T_minus_1_open, T_minus_1_close等）
                for _, row in df.iterrows():
                    # 提取原始symbol
                    original_symbol = str(row.get('symbol', ''))
                    # 提取T-1（最新一天）的数据用于显示
                    ticker = original_symbol
                    # 移除OKX的-SWAP后缀用于显示
                    if exchange == 'ok' and ticker.endswith('-SWAP'):
                        ticker = ticker.replace('-SWAP', '')
                    
                    reversal = {
                        'ticker': ticker,  # 用于显示（不带-SWAP）
                        'api_symbol': original_symbol,  # 用于API调用（带-SWAP）
                        'exchange': exchange,
                        'interval': interval,
                        'sheet_name': sheet_name,
                        'timestamp': file_date_str,  # 使用文件日期（文件生成日期）
                        'open': float(row.get('T_minus_1_open', 0)),
                        'high': float(row.get('T_minus_1_high', 0)),
                        'low': float(row.get('T_minus_1_low', 0)),
                        'close': float(row.get('T_minus_1_close', 0)),
                        'volume': float(row.get('T_minus_1_volume', 0)),
                        'quote_asset_volume': float(row.get('T_minus_1_quote_asset_volume', 0)),
                        'change_pct': float(row.get('T_minus_1_change_pct', 0)),
                        'volume_increase_pct': float(row.get('volume_growth_rate_pct', 0)),
                        'usdt_volume_growth_rate_pct': float(row.get('usdt_volume_growth_rate_pct', 0)),
                        # T-2数据（用于参考）
                        't2_date': row.get('T_minus_2_date'),
                        't2_open': float(row.get('T_minus_2_open', 0)),
                        't2_close': float(row.get('T_minus_2_close', 0)),
                        't2_change_pct': float(row.get('T_minus_2_change_pct', 0)),
                    }
                    reversal_data.append(reversal)
            
            logger.info(f"从 {file_path.name} 读取到 {len(reversal_data)} 条筛选后的反包数据（文件日期: {file_date_str}）")
            return reversal_data
            
        except Exception as e:
            logger.error(f"读取反包数据文件失败 {file_path}: {e}", exc_info=True)
            return []
    
    def _generate_kline_chart(self, ticker: str, exchange: str, interval: str, bars: int = 50) -> Optional[str]:
        """
        生成K线图并返回图片路径
        
        Args:
            ticker: 交易对
            exchange: 交易所（'bn' 或 'ok'）
            interval: 时间周期（如'1d', '3d', '1w'）
            bars: K线数量
            
        Returns:
            图片路径，如果生成失败返回None
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.patches import Rectangle
        except ImportError:
            logger.error("未安装matplotlib，无法生成K线图")
            return None
        
        try:
            # 根据交易所选择数据获取器并处理ticker格式
            if exchange == 'bn':
                fetcher = self.bn_fetcher
                api_ticker = ticker  # BN格式：ETHUSDT
            elif exchange == 'ok':
                fetcher = self.okx_fetcher
                # OKX格式：如果ticker没有-SWAP后缀，尝试添加-USDT-SWAP
                # 但通常qualified文件中的symbol已经是完整格式（如A-USDT-SWAP）
                # 如果传入的ticker是显示格式（如A-USDT），需要恢复为API格式
                if not ticker.endswith('-SWAP'):
                    # 尝试添加-USDT-SWAP后缀
                    if not ticker.endswith('-USDT'):
                        api_ticker = f"{ticker}-USDT-SWAP"
                    else:
                        api_ticker = f"{ticker}-SWAP"
                else:
                    api_ticker = ticker
            else:
                logger.warning(f"不支持的交易所: {exchange}")
                return None
            
            # 获取K线数据
            df = fetcher.get_klines(
                symbol=api_ticker,
                interval=interval,
                days=bars
            )
            
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
            
            exchange_name = 'BN' if exchange == 'bn' else 'OKX'
            ax.set_title(f"{ticker} {interval} · {exchange_name} · Last {len(df)} Candles", fontsize=12)
            ax.set_ylabel("Price (USDT)")
            ax.grid(True, linestyle='--', alpha=0.3)
            
            # 设置x轴标签
            step = max(1, len(x_values) // 6)
            select_idx = x_values[::step]
            select_labels = [timestamps.iloc[i].strftime('%m-%d %H:%M') for i in select_idx]
            ax.set_xticks(select_idx)
            ax.set_xticklabels(select_labels, rotation=45, ha='right')
            
            fig.tight_layout()
            
            filename = f"{ticker}_{exchange}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            output_path = self.chart_dir / filename
            
            try:
                fig.savefig(output_path, dpi=150)
                logger.info(f"已生成K线图: {output_path}")
            except Exception as exc:
                logger.error(f"保存K线图失败: {exc}")
                plt.close(fig)
                return None
            finally:
                plt.close(fig)
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"生成K线图失败 {ticker} {interval}: {e}", exc_info=True)
            return None
    
    def _build_alert_content(self, reversal: Dict) -> str:
        """
        构建报警消息内容
        
        Args:
            reversal: 反包数据字典
            
        Returns:
            Markdown格式的消息内容
        """
        ticker = reversal['ticker']
        exchange = reversal['exchange'].upper()
        interval = reversal['interval']
        sheet_name = reversal.get('sheet_name', interval)
        
        # 格式化T-1时间（反包检测中最新一天K线的日期）
        t1_date = reversal.get('timestamp')
        if t1_date:
            # 如果是字符串格式，直接使用
            if isinstance(t1_date, str):
                time_str = t1_date
            elif isinstance(t1_date, pd.Timestamp):
                if t1_date.tz is None:
                    t1_date = pd.Timestamp(t1_date, tz='UTC')
                t1_date = t1_date.tz_convert('Asia/Shanghai')
                time_str = t1_date.strftime('%Y-%m-%d')
            else:
                time_str = str(t1_date)
        else:
            time_str = 'N/A'
        
        content = f"""## 📊 每日反包数据预警

**交易对**: {ticker}
**交易所**: {exchange}
**周期**: {sheet_name} ({interval})
**T-1时间**: {time_str}
"""
        return content
    
    def send_alert(self, reversal: Dict) -> bool:
        """
        发送单个反包数据的报警
        
        对于特别关注的标的，使用配置的webhook_url（Core1或Core2）
        对于非特别关注的标的，不发送（仅特别关注标的发送报警）
        
        Args:
            reversal: 反包数据字典
            
        Returns:
            是否发送成功
        """
        ticker = reversal['ticker']
        # 优先使用api_symbol（如果存在），否则使用ticker
        api_symbol = reversal.get('api_symbol', ticker)
        exchange = reversal['exchange']
        interval = reversal['interval']
        
        # 检查是否在特别关注中（仅对股票市场：us, hk, a）
        webhook_url = None
        market_type = None
        
        # 根据exchange判断market_type
        if exchange in ['us', 'hk', 'a']:
            market_type = exchange
            # 检查是否在特别关注中
            watchlist_symbols = get_watchlist_symbols(market_type)
            if ticker in watchlist_symbols:
                # 获取配置的webhook_url
                webhook_url = get_watchlist_webhook_url(market_type, ticker)
                logger.info(f"📤 [特别关注] {ticker} 在特别关注中，使用配置的webhook")
            else:
                # 不在特别关注中，跳过发送（仅特别关注标的发送报警）
                logger.debug(f"📤 {ticker} 不在特别关注中，跳过发送（仅特别关注标的发送报警）")
                return True  # 返回True表示处理完成（跳过发送）
        
        # 检查是否在特别关注中（仅对股票市场：us, hk, a）
        webhook_url = None
        market_type = None
        
        # 根据exchange判断market_type
        if exchange in ['us', 'hk', 'a']:
            market_type = exchange
            # 检查是否在特别关注中
            watchlist_symbols = get_watchlist_symbols(market_type)
            if ticker in watchlist_symbols:
                # 获取配置的webhook_url
                webhook_url = get_watchlist_webhook_url(market_type, ticker)
                logger.info(f"📤 [特别关注] {ticker} 在特别关注中，使用配置的webhook")
            else:
                # 不在特别关注中，跳过发送（仅特别关注标的发送报警）
                logger.debug(f"📤 {ticker} 不在特别关注中，跳过发送（仅特别关注标的发送报警）")
                return True  # 返回True表示处理完成（跳过发送）
        
        # 如果不在股票市场，使用默认notifier（BN和OK市场）
        if webhook_url is None:
            if not self.notifier:
                logger.warning("未配置企业微信webhook，跳过推送")
                return False
            notifier = self.notifier
        else:
            # 创建临时notifier使用配置的webhook_url
            notifier = WeComNotifier(webhook_url=webhook_url)
        
        logger.info(f"📤 [企业微信] 开始发送每日反包报警 - {ticker} ({exchange} {interval})")
        
        # 构建消息内容
        content = self._build_alert_content(reversal)
        
        # 发送Markdown消息
        success = notifier.send_markdown_message(content)
        
        if success:
            logger.info(f"✅ {ticker} 每日反包报警已发送")
            
            # 生成并发送K线图（使用api_symbol以确保API调用正确）
            chart_path = self._generate_kline_chart(api_symbol, exchange, interval)
            if chart_path and hasattr(notifier, "send_image_message"):
                img_success = notifier.send_image_message(image_path=chart_path)
                if img_success:
                    logger.info(f"🖼️ {ticker} K线图已发送")
                else:
                    logger.warning(f"⚠️ {ticker} K线图发送失败")
            else:
                logger.debug(f"{ticker} 无可用K线图或通知器不支持图片发送")
        else:
            logger.error(f"❌ {ticker} 每日反包报警发送失败")
        
        return success
    
    def process_daily_reversals(self) -> Dict[str, int]:
        """
        处理当日的反包数据并发送报警
        
        Returns:
            处理结果统计字典
        """
        logger.info("=" * 80)
        logger.info("📊 开始处理每日反包数据报警")
        logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # 查找当日文件
        files = self.find_today_files()
        
        if not files:
            logger.warning("未找到当日的反包数据文件")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        # 读取所有反包数据
        all_reversals = []
        for exchange, file_path in files.items():
            reversals = self.read_reversal_data(file_path, exchange)
            all_reversals.extend(reversals)
        
        if not all_reversals:
            logger.info("当日无反包数据")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        logger.info(f"共找到 {len(all_reversals)} 条反包数据，开始发送报警...")
        
        # 发送报警
        success_count = 0
        failed_count = 0
        
        for reversal in all_reversals:
            if self.send_alert(reversal):
                success_count += 1
            else:
                failed_count += 1
        
        logger.info("=" * 80)
        logger.info(f"每日反包数据报警处理完成:")
        logger.info(f"  总数: {len(all_reversals)}")
        logger.info(f"  成功: {success_count}")
        logger.info(f"  失败: {failed_count}")
        logger.info("=" * 80)
        
        return {
            'total': len(all_reversals),
            'success': success_count,
            'failed': failed_count
        }


def main():
    """主函数"""
    from dotenv import load_dotenv
    load_dotenv()
    
    alert = DailyReversalAlert()
    result = alert.process_daily_reversals()
    
    print(f"\n处理结果: {result}")


if __name__ == "__main__":
    main()

