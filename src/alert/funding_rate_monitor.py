#!/usr/bin/env python3
"""
资金费率监控器 - 支持按资金费率结算间隔进行报警
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from src.alert.wecom_notifier import WeComNotifier
from src.crypto.binance_data_fetcher import BinanceDataFetcher

logger = logging.getLogger(__name__)


class FundingRateMonitor:
    """资金费率监控器"""

    DATA_FILENAME = "funding_intervals.json"
    DEFAULT_INTERVAL = 8  # 默认资金费率间隔为8小时

    def __init__(self,
                 wecom_webhook_url: Optional[str] = None,
                 threshold: float = 0.002,
                 quote_asset: str = 'USDT'):
        """
        初始化资金费率监控器

        Args:
            wecom_webhook_url: 企业微信webhook
            threshold: 触发报警的资金费率阈值（如0.002表示0.2%）
            quote_asset: 监控的计价货币
        """
        self.threshold = threshold
        self.quote_asset = quote_asset
        self.fetcher = BinanceDataFetcher(market_type='futures')
        self.notifier = WeComNotifier(
            webhook_url=wecom_webhook_url
        ) if wecom_webhook_url else None
        self.futures_only_tokens: Set[str] = set()

        # 数据文件路径
        self.data_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self.intervals_file = os.path.join(self.data_dir, self.DATA_FILENAME)

    # ------------------------------------------------------------------ #
    # 数据文件读写
    # ------------------------------------------------------------------ #
    def _load_intervals(self) -> Dict[str, Dict]:
        """读取资金费率间隔文件"""
        if not os.path.exists(self.intervals_file):
            logger.info("资金费率间隔文件不存在，将在下一次刷新任务中生成")
            return {}

        try:
            with open(self.intervals_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.error(f"读取资金费率间隔文件失败: {e}")
        return {}

    def _save_intervals(self, data: Dict[str, Dict]):
        """保存资金费率间隔信息"""
        try:
            with open(self.intervals_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            logger.info(f"资金费率间隔文件已更新: {self.intervals_file}")
        except Exception as e:
            logger.error(f"写入资金费率间隔文件失败: {e}")

    # ------------------------------------------------------------------ #
    # 文件内容构建
    # ------------------------------------------------------------------ #
    def refresh_funding_intervals(self) -> Dict[str, Dict]:
        """
        刷新资金费率间隔信息，并写入文件
        Returns:
            刷新后的交易对间隔信息
        """
        logger.info("获取仅上线合约的交易对用于刷新资金费率间隔信息...")
        futures_only = set(self.fetcher.get_futures_only_tokens(quote_asset=self.quote_asset))
        if not futures_only:
            logger.warning("未获取到仅上线合约的交易对，将尝试使用全部合约列表")
            futures_only = set(self.fetcher.get_all_tokens(quote_asset=self.quote_asset))
        if not futures_only:
            logger.error("仍未获取到交易对列表，无法刷新资金费率间隔信息")
            return {}
        self.futures_only_tokens = futures_only
        logger.info(f"已记录 {len(self.futures_only_tokens)} 个仅上线合约的交易对")

        adjustments = self.fetcher.get_funding_rate_adjustments()
        logger.info(f"资金费率调整信息: {len(adjustments)} 个交易对有特殊配置")

        now_iso = datetime.now().isoformat()
        intervals: Dict[str, Dict] = {}

        for symbol in futures_only:
            interval = adjustments.get(symbol, {}).get('fundingIntervalHours', self.DEFAULT_INTERVAL)
            try:
                interval = int(interval)
            except (TypeError, ValueError):
                interval = self.DEFAULT_INTERVAL

            if interval <= 0:
                interval = self.DEFAULT_INTERVAL

            intervals[symbol] = {
                'interval': interval,
                'last_update': now_iso
            }

        # 对于调整信息中存在，但缺少于 futures-only 列表的，暂不记录（可能是其他计价货币）
        for symbol, info in adjustments.items():
            if symbol not in intervals:
                continue

        self._save_intervals(intervals)
        return intervals

    # ------------------------------------------------------------------ #
    # 辅助工具
    # ------------------------------------------------------------------ #
    def _format_timestamp(self, ts: Optional[int]) -> str:
        """格式化毫秒时间戳"""
        if not ts:
            return "-"
        try:
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone()
            return dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return "-"

    def _build_alert_message(self, alerts: List[Dict]) -> str:
        """构建企业微信报警消息"""
        alerts.sort(key=lambda x: abs(x['funding_rate']), reverse=True)

        lines = [
            "## 💰 资金费率异常提醒",
            "",
            f"**检测时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**阈值**: ±{self.threshold * 100:.2f}%",
            "",
            "| 交易对 | 当前费率 | 绝对值 | 间隔(h) | 下次结算 | 标记价格 | 指数价格 |",
            "|-------|---------|--------|---------|----------|-----------|-----------|"
        ]

        for item in alerts:
            lines.append(
                f"| {item['symbol']} | {item['funding_rate'] * 100:+.3f}% | "
                f"{abs(item['funding_rate']) * 100:.3f}% | {item['interval']} | "
                f"{self._format_timestamp(item['next_funding_time'])} | "
                f"{item['mark_price']:.4f} | {item['index_price']:.4f} |"
            )

        lines.append("")
        lines.append("> 请关注资金费率波动，谨防异常成本。")

        return "\n".join(lines)

    def _get_due_symbols(self, intervals: Dict[str, Dict], now: Optional[datetime] = None) -> List[str]:
        """根据当前时间和资金费率间隔，筛选需要检测的交易对"""
        now = now or datetime.now().astimezone()
        hour = now.hour

        due_symbols: List[str] = []
        for symbol, info in intervals.items():
            interval = info.get('interval', self.DEFAULT_INTERVAL)
            try:
                interval = int(interval)
            except (TypeError, ValueError):
                interval = self.DEFAULT_INTERVAL

            if interval <= 0:
                interval = self.DEFAULT_INTERVAL

            if hour % interval == 0:
                due_symbols.append(symbol)

        return due_symbols

    # ------------------------------------------------------------------ #
    # 检测主逻辑
    # ------------------------------------------------------------------ #
    def check_and_alert(self) -> List[Dict]:
        """
        检测资金费率并发送报警

        Returns:
            超出阈值的交易对列表
        """
        intervals = self._load_intervals()
        if not intervals:
            logger.info("资金费率间隔信息缺失，尝试刷新后再检测...")
            intervals = self.refresh_funding_intervals()

        if not intervals:
            logger.warning("仍未获取到资金费率间隔信息，终止本次检测")
            return []

        now = datetime.now().astimezone()
        if not self.futures_only_tokens:
            logger.info("futures-only 集合未初始化，尝试从间隔文件加载")
            self.futures_only_tokens = {
                symbol for symbol, info in intervals.items()
                if info.get('note') != 'Symbol not found in current futures list'
            }

        due_symbols = self._get_due_symbols(intervals, now=now)
        due_symbols = [s for s in due_symbols if s in self.futures_only_tokens]
        if not due_symbols:
            logger.info(f"{now.strftime('%Y-%m-%d %H:%M')} 当前小时无需检测资金费率")
            return []

        logger.info(f"本小时需检测 {len(due_symbols)} 个仅上线合约的交易对资金费率")

        funding_data = self.fetcher.get_all_futures_funding_rates()
        if not funding_data:
            logger.warning("未获取到资金费率数据")
            return []

        data_map = {item['symbol']: item for item in funding_data}

        alerts: List[Dict] = []
        missing_symbols: List[str] = []

        for symbol in due_symbols:
            item = data_map.get(symbol)
            if not item:
                missing_symbols.append(symbol)
                continue

            rate = item.get('lastFundingRate')
            if rate is None:
                continue

            if abs(rate) >= self.threshold:
                interval = intervals.get(symbol, {}).get('interval', self.DEFAULT_INTERVAL)
                alerts.append({
                    'symbol': symbol,
                    'funding_rate': float(rate),
                    'mark_price': float(item.get('markPrice', 0) or 0),
                    'index_price': float(item.get('indexPrice', 0) or 0),
                    'next_funding_time': item.get('nextFundingTime'),
                    'interval': interval
                })

        if missing_symbols:
            logger.debug(f"资金费率数据中缺失 {len(missing_symbols)} 个交易对: {', '.join(missing_symbols)}")

        if not alerts:
            logger.info("🎉 本小时内所有待检测交易对资金费率均在安全阈值内")
            return []

        logger.warning(f"⚠️ 本小时共有 {len(alerts)} 个交易对资金费率超出阈值")
        for alert in alerts:
            logger.warning(
                f"  - {alert['symbol']}: {alert['funding_rate'] * 100:+.3f}% "
                f"(间隔 {alert['interval']}h, 阈值 ±{self.threshold * 100:.2f}%)"
            )

        if not self.notifier:
            logger.warning("未配置企业微信webhook，跳过推送")
            return alerts

        content = self._build_alert_message(alerts)
        success = self.notifier.send_markdown_message(content)
        if success:
            logger.info("✅ 资金费率报警推送完成")
        else:
            logger.error("❌ 资金费率报警推送失败")

        return alerts
