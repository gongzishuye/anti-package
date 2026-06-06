#!/usr/bin/env python3
"""
监控配置中心
所有 symbol、interval 配置的唯一来源
交易对从 tokens-config.md 动态读取，每10分钟自动reload
"""

import os
import time
from threading import Lock

# 配置文件路径
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
TOKENS_CONFIG_FILE = os.path.join(CONFIG_DIR, 'tokens-config.md')
TOKENS_CONFIG_DYNAMIC_FILE = os.path.join(CONFIG_DIR, 'tokens-config-dynamic.md')

# [已禁用] 需要额外MA52/EMA144检测的交易对
# PRECIOUS_METALS = ['XAUUSDT', 'XAGUSDT']

# 监控的所有周期（5M及以上）
MONITORED_INTERVALS = [
    '5M', '10M', '15M', '30M', '1H', '2H', '4H', '6H', '8H', '12H',
    '1D', '2D', '3D', '5D', '1W', '1M'
]

# Interval映射（数据库格式 -> Binance格式）
INTERVAL_MAP = {
    '5M': '5m',
    '10M': '10m',
    '15M': '15m',
    '30M': '30m',
    '1H': '1h',
    '2H': '2h',
    '4H': '4h',
    '6H': '6h',
    '8H': '8h',
    '12H': '12h',
    '1D': '1d',
    '2D': '2d',
    '3D': '3d',
    '5D': '5d',
    '1W': '1w',
    '1M': '1M',
}

# ─────────────────────────────────────────────────────────
# 动态配置加载器（文件变化时立即reload）
# ─────────────────────────────────────────────────────────

_tokens_cache = None
_tokens_last_mtime = None  # 上次加载时的文件修改时间
_tokens_lock = Lock()

# 动态配置
_tokens_dynamic_cache = None
_tokens_dynamic_last_mtime = None
_tokens_dynamic_lock = Lock()


def _load_tokens_config():
    """从 tokens-config.md 解析交易对列表，文件变化时立即reload"""
    global _tokens_cache, _tokens_last_mtime

    with _tokens_lock:
        if not os.path.exists(TOKENS_CONFIG_FILE):
            import logging
            logging.warning(f"tokens-config.md 不存在: {TOKENS_CONFIG_FILE}")
            return _tokens_cache if _tokens_cache is not None else []

        current_mtime = os.path.getmtime(TOKENS_CONFIG_FILE)

        # 文件未变化，直接返回缓存
        if _tokens_last_mtime is not None and current_mtime == _tokens_last_mtime:
            return _tokens_cache

        # 文件变化，重新加载
        tokens = []
        with open(TOKENS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                symbol = line.split('#')[0].strip()
                if symbol:
                    tokens.append(symbol)

        import logging
        if _tokens_last_mtime is not None:
            logging.info(f"[monitor_config] 检测到 tokens-config.md 变化，已重新加载: {tokens}")
        else:
            logging.info(f"[monitor_config] tokens-config.md 首次加载: {tokens}")

        _tokens_cache = tokens
        _tokens_last_mtime = current_mtime
        return tokens


def _load_tokens_config_dynamic():
    """从 tokens-config-dynamic.md 解析交易对列表，文件变化时立即reload"""
    global _tokens_dynamic_cache, _tokens_dynamic_last_mtime

    with _tokens_dynamic_lock:
        if not os.path.exists(TOKENS_CONFIG_DYNAMIC_FILE):
            import logging
            logging.warning(f"tokens-config-dynamic.md 不存在: {TOKENS_CONFIG_DYNAMIC_FILE}")
            return _tokens_dynamic_cache if _tokens_dynamic_cache is not None else []

        current_mtime = os.path.getmtime(TOKENS_CONFIG_DYNAMIC_FILE)

        # 文件未变化，直接返回缓存
        if _tokens_dynamic_last_mtime is not None and current_mtime == _tokens_dynamic_last_mtime:
            return _tokens_dynamic_cache

        # 文件变化，重新加载
        tokens = []
        with open(TOKENS_CONFIG_DYNAMIC_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                symbol = line.split('#')[0].strip()
                if symbol:
                    tokens.append(symbol)

        import logging
        if _tokens_dynamic_last_mtime is not None:
            logging.info(f"[monitor_config] 检测到 tokens-config-dynamic.md 变化，已重新加载: {tokens}")
        else:
            logging.info(f"[monitor_config] tokens-config-dynamic.md 首次加载: {tokens}")

        _tokens_dynamic_cache = tokens
        _tokens_dynamic_last_mtime = current_mtime
        return tokens


def get_monitored_symbols():
    """获取当前监控的交易对列表（每次调用自动检测文件变化）"""
    return _load_tokens_config()


def get_dynamic_symbols():
    """获取动态监控的交易对列表（从 tokens-config-dynamic.md，每次调用自动检测文件变化）"""
    return _load_tokens_config_dynamic()


# 首次加载
_load_tokens_config()