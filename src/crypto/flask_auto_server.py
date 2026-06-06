#!/usr/bin/env python3
"""
多周期Token筛选结果Flask自动化服务
集成定时任务：每天早上8点自动获取数据、筛选、更新展示
"""

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pandas as pd
import os
import sys
import glob
import logging
import subprocess
import traceback
import json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/flask_auto_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# 导入数据处理模块
try:
    from fetch_multi_period_data import fetch_all_periods_data, save_to_excel
    from token_filter_multi_period import MultiPeriodTokenFilter
    logger.info("✓ 成功导入数据处理模块")
except Exception as e:
    logger.error(f"✗ 导入模块失败: {e}")

# 全局配置
CONFIG = {
    'top_n': 100,  # 默认获取Top100，可通过环境变量配置
    'kline_records': 200,  # 默认每个Token获取200条K线数据
}

# 黑名单文件路径
BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'symbol_blacklist.json')
# 特别关注文件路径
WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), '..', 'equity', 'watchlist.json')
# Core1和Core2企业微信webhook地址
CORE1_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=ea7b1192-2e52-4886-8b4f-859207cf8516"
CORE2_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=37f7e3c5-cec7-4fce-8a0d-ab67faa7c412"

# 全局变量存储任务状态
task_status = {
    'last_run': None,
    'next_run': None,
    'status': '未运行',
    'message': '等待首次运行',
    'data_file': None,
    'filter_file': None
}


def merge_spot_futures_data(spot_data, futures_data):
    """合并现货和合约数据"""
    merged_data = {}
    
    # 获取所有周期
    all_periods = set()
    if spot_data.get('success') and spot_data.get('sheets'):
        all_periods.update(spot_data['sheets'].keys())
    if futures_data.get('success') and futures_data.get('sheets'):
        all_periods.update(futures_data['sheets'].keys())
    
    for period in all_periods:
        spot_tokens = spot_data.get('sheets', {}).get(period, []) if spot_data.get('success') else []
        futures_tokens = futures_data.get('sheets', {}).get(period, []) if futures_data.get('success') else []
        
        # 创建交易对映射，处理OKX合约格式差异
        spot_map = {token['symbol']: token for token in spot_tokens}
        futures_map = {}
        
        # 为合约数据创建映射，处理-SWAP后缀
        for token in futures_tokens:
            symbol = token['symbol']
            # 去掉OKX合约的-SWAP后缀进行匹配
            normalized_symbol = symbol.replace('-SWAP', '') if symbol.endswith('-SWAP') else symbol
            futures_map[normalized_symbol] = token
        
        # 合并逻辑
        merged_tokens = []
        all_symbols = set(spot_map.keys()) | set(futures_map.keys())
        
        for symbol in all_symbols:
            has_spot = symbol in spot_map
            has_futures = symbol in futures_map
            
            if has_spot and has_futures:
                # 两者都有，使用现货数据，标记为both
                token = spot_map[symbol].copy()
                token['market_type'] = 'both'
                merged_tokens.append(token)
            elif has_spot:
                # 只有现货
                token = spot_map[symbol].copy()
                token['market_type'] = 'spot'
                merged_tokens.append(token)
            else:
                # 只有合约
                token = futures_map[symbol].copy()
                # 去掉合约交易对的-SWAP后缀显示
                if token['symbol'].endswith('-SWAP'):
                    token['symbol'] = token['symbol'].replace('-SWAP', '')
                token['market_type'] = 'perp'
                merged_tokens.append(token)
        
        merged_data[period] = merged_tokens
    
    return {
        'success': True,
        'sheets': merged_data,
        'update_time': max(
            spot_data.get('update_time', ''),
            futures_data.get('update_time', '')
        )
    }

def get_latest_qualified_tokens_file(market_type='bn_spot'):
    """获取最新的筛选结果Excel文件"""
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    data_dir = os.path.abspath(data_dir)
    
    if market_type == 'bn_spot':
        # BN现货数据文件 - 匹配两种格式：qualified_top* 和 qualified_tokens
        files1 = glob.glob(os.path.join(data_dir, 'qualified_top*_multi_period_*.xlsx'))
        files2 = glob.glob(os.path.join(data_dir, 'qualified_tokens_multi_period_*.xlsx'))
        files = files1 + files2
    elif market_type == 'bn_futures':
        # BN合约数据文件 - 匹配两种格式：qualified_futures_top* 和 qualified_futures_tokens
        files1 = glob.glob(os.path.join(data_dir, 'qualified_futures_top*_multi_period_*.xlsx'))
        files2 = glob.glob(os.path.join(data_dir, 'qualified_futures_tokens_multi_period_*.xlsx'))
        files = files1 + files2
    elif market_type == 'ok_spot':
        # OK现货数据文件 - 匹配两种格式：qualified_okx_top* 和 qualified_okx_tokens
        files1 = glob.glob(os.path.join(data_dir, 'qualified_okx_top*_multi_period_*.xlsx'))
        files2 = glob.glob(os.path.join(data_dir, 'qualified_okx_tokens_multi_period_*.xlsx'))
        files = files1 + files2
    elif market_type == 'ok_futures':
        # OK合约数据文件 - 匹配两种格式：qualified_okx_futures_top* 和 qualified_okx_futures_tokens
        files1 = glob.glob(os.path.join(data_dir, 'qualified_okx_futures_top*_multi_period_*.xlsx'))
        files2 = glob.glob(os.path.join(data_dir, 'qualified_okx_futures_tokens_multi_period_*.xlsx'))
        files = files1 + files2
    elif market_type == 'us_stock':
        # 美股反包数据文件 - 在 src/equity/data 目录下
        equity_data_dir = os.path.join(os.path.dirname(__file__), '..', 'equity', 'data')
        equity_data_dir = os.path.abspath(equity_data_dir)
        files = glob.glob(os.path.join(equity_data_dir, 'us_stock_reversal_results.xlsx'))
    elif market_type == 'hk_stock':
        # 港股反包数据文件 - 在 src/equity/data 目录下
        equity_data_dir = os.path.join(os.path.dirname(__file__), '..', 'equity', 'data')
        equity_data_dir = os.path.abspath(equity_data_dir)
        files = glob.glob(os.path.join(equity_data_dir, 'hk_stock_reversal_results.xlsx'))
    elif market_type == 'a_stock':
        # A股反包数据文件 - 在 src/equity/data 目录下
        equity_data_dir = os.path.join(os.path.dirname(__file__), '..', 'equity', 'data')
        equity_data_dir = os.path.abspath(equity_data_dir)
        files = glob.glob(os.path.join(equity_data_dir, 'a_stock_reversal_results.xlsx'))
    elif market_type == 'metal':
        # 贵金属反包数据文件 - 在 src/metal/data 目录下
        metal_data_dir = os.path.join(os.path.dirname(__file__), '..', 'metal', 'data')
        metal_data_dir = os.path.abspath(metal_data_dir)
        files = glob.glob(os.path.join(metal_data_dir, 'metal_reversal_results.xlsx'))
    else:
        # 默认BN现货数据文件
        files1 = glob.glob(os.path.join(data_dir, 'qualified_top*_multi_period_*.xlsx'))
        files2 = glob.glob(os.path.join(data_dir, 'qualified_tokens_multi_period_*.xlsx'))
        files = files1 + files2
    
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def read_excel_all_sheets(excel_file):
    """读取Excel文件的所有sheet"""
    try:
        excel = pd.ExcelFile(excel_file)
        file_time = datetime.fromtimestamp(os.path.getmtime(excel_file))
        
        results = {
            'success': True,
            'file': excel_file,
            'update_time': file_time.strftime('%Y-%m-%d %H:%M:%S'),
            'sheets': {}
        }
        
        # Sheet名称映射：将不同的sheet名称映射到前端期望的格式
        sheet_name_mapping = {
            '1日': '1日',
            '2日': '2日',
            '3日': '3日',
            '5日': '5日',
            '周': '周',
            '1日筛选结果': '1日',
            '2日筛选结果': '2日',
            '3日筛选结果': '3日',
            '5日筛选结果': '5日',
            '周筛选结果': '周'
        }
        
        for sheet_name in excel.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            tokens = []
            for _, row in df.iterrows():
                token = {
                    'symbol': row['symbol'],
                    'T_minus_2_date': row['T_minus_2_date'],
                    'T_minus_2_open': float(row['T_minus_2_open']),
                    'T_minus_2_high': float(row['T_minus_2_high']),
                    'T_minus_2_low': float(row['T_minus_2_low']),
                    'T_minus_2_close': float(row['T_minus_2_close']),
                    'T_minus_2_volume': float(row['T_minus_2_volume']),
                    'T_minus_2_quote_asset_volume': float(row['T_minus_2_quote_asset_volume']),
                    'T_minus_2_change_pct': float(row['T_minus_2_change_pct']),
                    'T_minus_1_date': row['T_minus_1_date'],
                    'T_minus_1_open': float(row['T_minus_1_open']),
                    'T_minus_1_high': float(row['T_minus_1_high']),
                    'T_minus_1_low': float(row['T_minus_1_low']),
                    'T_minus_1_close': float(row['T_minus_1_close']),
                    'T_minus_1_volume': float(row['T_minus_1_volume']),
                    'T_minus_1_quote_asset_volume': float(row['T_minus_1_quote_asset_volume']),
                    'T_minus_1_change_pct': float(row['T_minus_1_change_pct']),
                    'volume_growth_rate_pct': float(row['volume_growth_rate_pct']),
                    'usdt_volume_growth_rate_pct': float(row.get('usdt_volume_growth_rate_pct', 0)),
                }
                tokens.append(token)
            
            # 使用映射后的名称作为key
            mapped_name = sheet_name_mapping.get(sheet_name, sheet_name)
            results['sheets'][mapped_name] = tokens
        
        return results
        
    except Exception as e:
        logger.error(f"读取Excel失败: {e}")
        return {
            'success': False,
            'message': f'读取Excel失败: {str(e)}',
            'sheets': {}
        }


def read_us_stock_reversal_excel(excel_file):
    """读取美股反包Excel文件（最新数据）"""
    try:
        excel = pd.ExcelFile(excel_file)
        file_time = datetime.fromtimestamp(os.path.getmtime(excel_file))
        
        results = {
            'success': True,
            'file': excel_file,
            'update_time': file_time.strftime('%Y-%m-%d %H:%M:%S'),
            'sheets': {}
        }
        
        # 获取今天的日期作为sheet名称
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 如果今天的sheet不存在，使用最新的sheet
        if today in excel.sheet_names:
            target_sheet = today
            use_today_data = True
        elif len(excel.sheet_names) > 0:
            # 使用最新的sheet（按日期排序）
            target_sheet = sorted(excel.sheet_names)[-1]
            use_today_data = False
            logger.warning(f"⚠️ 今天({today})的数据不存在，使用最新的sheet: {target_sheet}")
        else:
            logger.warning(f"Excel文件中没有任何sheet")
            results['message'] = 'Excel文件中没有数据'
            return results
        
        # 读取Excel时指定symbol为字符串类型，保留前导0
        df = pd.read_excel(excel_file, sheet_name=target_sheet, dtype={'symbol': str})
        # 确保symbol字段是字符串类型
        if 'symbol' in df.columns:
            df['symbol'] = df['symbol'].astype(str).str.strip()
        
        stocks = []
        
        for _, row in df.iterrows():
            # 计算交易额 (turnover_t1)
            turnover_t1 = 0
            if 'turnover_t1' in row:
                turnover_t1 = float(row['turnover_t1'])
            elif 'vwap_t1' in row and 'volume_t1' in row:
                turnover_t1 = float(row['vwap_t1']) * float(row['volume_t1'])
            elif 'close_t1' in row and 'volume_t1' in row:
                turnover_t1 = float(row['close_t1']) * float(row['volume_t1'])
            
            stock = {
                'symbol': str(row['symbol']).strip(),  # 确保symbol是字符串类型
                'open_t2': float(row.get('open_t2', 0)),
                'close_t2': float(row.get('close_t2', 0)),
                'high_t2': float(row.get('high_t2', 0)),
                'low_t2': float(row.get('low_t2', 0)),
                'volume_t2': float(row.get('volume_t2', 0)),
                't2_change_pct': float(row.get('t2_change_pct', 0)),
                'open_t1': float(row.get('open_t1', 0)),
                'close_t1': float(row.get('close_t1', 0)),
                'high_t1': float(row.get('high_t1', 0)),
                'low_t1': float(row.get('low_t1', 0)),
                'volume_t1': float(row.get('volume_t1', 0)),
                't1_change_pct': float(row.get('t1_change_pct', 0)),
                'volume_increase_pct': float(row.get('volume_increase_pct', 0)),
                'reversal_strength': float(row.get('reversal_strength', 0)),
                'turnover_t1': turnover_t1,  # 添加交易额字段
                'data_date': target_sheet,  # 添加数据日期
                'market_cap': float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else 0,  # 添加市值字段
                'name': str(row.get('name', '')) if pd.notna(row.get('name')) else '',  # 添加公司名称
            }
            stocks.append(stock)
        
        # 如果使用的不是今天的数据，使用数据日期+默认时间作为update_time
        if not use_today_data:
            # 使用数据日期 + 默认时间（08:00:00）作为update_time
            try:
                data_date_obj = datetime.strptime(target_sheet, '%Y-%m-%d')
                results['update_time'] = data_date_obj.strftime('%Y-%m-%d 08:00:00')
            except:
                # 如果解析失败，使用文件修改时间
                pass
        
        # 使用today作为key保持一致性
        results['sheets']['today'] = stocks
        results['data_date'] = target_sheet  # 标记实际数据日期
        logger.info(f"✓ 读取美股反包数据成功: {len(stocks)} 只股票 (数据日期: {target_sheet}, 更新时间: {results['update_time']})")
        
        return results
        
    except Exception as e:
        logger.error(f"读取美股Excel失败: {e}")
        return {
            'success': False,
            'message': f'读取美股Excel失败: {str(e)}',
            'sheets': {}
        }


def read_hk_stock_reversal_excel(excel_file):
    """读取港股反包Excel文件（最新数据）"""
    try:
        excel = pd.ExcelFile(excel_file)
        file_time = datetime.fromtimestamp(os.path.getmtime(excel_file))
        
        results = {
            'success': True,
            'file': excel_file,
            'update_time': file_time.strftime('%Y-%m-%d %H:%M:%S'),
            'sheets': {}
        }
        
        # 获取今天的日期作为sheet名称
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 如果今天的sheet不存在，使用最新的sheet
        if today in excel.sheet_names:
            target_sheet = today
            use_today_data = True
        elif len(excel.sheet_names) > 0:
            # 使用最新的sheet（按日期排序）
            target_sheet = sorted(excel.sheet_names)[-1]
            use_today_data = False
            logger.warning(f"⚠️ 今天({today})的数据不存在，使用最新的sheet: {target_sheet}")
        else:
            logger.warning(f"Excel文件中没有任何sheet")
            results['message'] = 'Excel文件中没有数据'
            return results
        
        # 读取Excel时指定symbol为字符串类型，保留前导0
        df = pd.read_excel(excel_file, sheet_name=target_sheet, dtype={'symbol': str})
        # 确保symbol字段是字符串类型
        if 'symbol' in df.columns:
            df['symbol'] = df['symbol'].astype(str).str.strip()
        
        stocks = []
        
        for _, row in df.iterrows():
            # 计算交易额 (turnover_t1)
            turnover_t1 = 0
            if 'turnover_t1' in row:
                turnover_t1 = float(row['turnover_t1'])
            elif 'vwap_t1' in row and 'volume_t1' in row:
                turnover_t1 = float(row['vwap_t1']) * float(row['volume_t1'])
            elif 'close_t1' in row and 'volume_t1' in row:
                turnover_t1 = float(row['close_t1']) * float(row['volume_t1'])
            
            stock = {
                'symbol': str(row['symbol']).strip(),  # 确保symbol是字符串类型
                'open_t2': float(row.get('open_t2', 0)),
                'close_t2': float(row.get('close_t2', 0)),
                'high_t2': float(row.get('high_t2', 0)),
                'low_t2': float(row.get('low_t2', 0)),
                'volume_t2': float(row.get('volume_t2', 0)),
                't2_change_pct': float(row.get('t2_change_pct', 0)),
                'open_t1': float(row.get('open_t1', 0)),
                'close_t1': float(row.get('close_t1', 0)),
                'high_t1': float(row.get('high_t1', 0)),
                'low_t1': float(row.get('low_t1', 0)),
                'volume_t1': float(row.get('volume_t1', 0)),
                't1_change_pct': float(row.get('t1_change_pct', 0)),
                'volume_increase_pct': float(row.get('volume_increase_pct', 0)),
                'reversal_strength': float(row.get('reversal_strength', 0)),
                'turnover_t1': turnover_t1,  # 添加交易额字段
                'data_date': target_sheet,  # 添加数据日期
                'market_cap': float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else 0,  # 添加市值字段
                'name': str(row.get('name', '')) if pd.notna(row.get('name')) else '',  # 添加公司名称
            }
            stocks.append(stock)
        
        # 如果使用的不是今天的数据，使用数据日期+默认时间作为update_time
        if not use_today_data:
            # 使用数据日期 + 默认时间（08:00:00）作为update_time
            try:
                data_date_obj = datetime.strptime(target_sheet, '%Y-%m-%d')
                results['update_time'] = data_date_obj.strftime('%Y-%m-%d 08:00:00')
            except:
                # 如果解析失败，使用文件修改时间
                pass
        
        # 使用today作为key保持一致性
        results['sheets']['today'] = stocks
        results['data_date'] = target_sheet  # 标记实际数据日期
        logger.info(f"✓ 读取港股反包数据成功: {len(stocks)} 只股票 (数据日期: {target_sheet}, 更新时间: {results['update_time']})")
        
        return results
        
    except Exception as e:
        logger.error(f"读取港股Excel失败: {e}")
        return {
            'success': False,
            'message': f'读取港股Excel失败: {str(e)}',
            'sheets': {}
        }


def read_a_stock_reversal_excel(excel_file):
    """读取A股反包Excel文件（最新数据）"""
    try:
        excel = pd.ExcelFile(excel_file)
        file_time = datetime.fromtimestamp(os.path.getmtime(excel_file))
        
        results = {
            'success': True,
            'file': excel_file,
            'update_time': file_time.strftime('%Y-%m-%d %H:%M:%S'),
            'sheets': {}
        }
        
        # 获取今天的日期作为sheet名称
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 如果今天的sheet不存在，使用最新的sheet
        if today in excel.sheet_names:
            target_sheet = today
        elif len(excel.sheet_names) > 0:
            # 使用最新的sheet（按日期排序）
            target_sheet = sorted(excel.sheet_names)[-1]
            logger.info(f"今天({today})的数据不存在，使用最新的sheet: {target_sheet}")
        else:
            logger.warning(f"Excel文件中没有任何sheet")
            results['message'] = 'Excel文件中没有数据'
            return results
        
        # 读取Excel时指定symbol为字符串类型，保留前导0
        df = pd.read_excel(excel_file, sheet_name=target_sheet, dtype={'symbol': str})
        # 确保symbol字段是字符串类型
        if 'symbol' in df.columns:
            df['symbol'] = df['symbol'].astype(str).str.strip()
        
        stocks = []
        
        for _, row in df.iterrows():
            # 计算交易额 (turnover_t1)
            turnover_t1 = 0
            if 'turnover_t1' in row:
                turnover_t1 = float(row['turnover_t1'])
            elif 'vwap_t1' in row and 'volume_t1' in row:
                turnover_t1 = float(row['vwap_t1']) * float(row['volume_t1'])
            elif 'close_t1' in row and 'volume_t1' in row:
                turnover_t1 = float(row['close_t1']) * float(row['volume_t1'])
            
            stock = {
                'symbol': str(row['symbol']).strip(),  # 确保symbol是字符串类型
                'open_t2': float(row.get('open_t2', 0)),
                'close_t2': float(row.get('close_t2', 0)),
                'high_t2': float(row.get('high_t2', 0)),
                'low_t2': float(row.get('low_t2', 0)),
                'volume_t2': float(row.get('volume_t2', 0)),
                't2_change_pct': float(row.get('t2_change_pct', 0)),
                'open_t1': float(row.get('open_t1', 0)),
                'close_t1': float(row.get('close_t1', 0)),
                'high_t1': float(row.get('high_t1', 0)),
                'low_t1': float(row.get('low_t1', 0)),
                'volume_t1': float(row.get('volume_t1', 0)),
                't1_change_pct': float(row.get('t1_change_pct', 0)),
                'volume_increase_pct': float(row.get('volume_increase_pct', 0)),
                'reversal_strength': float(row.get('reversal_strength', 0)),
                'turnover_t1': turnover_t1,  # 添加交易额字段
                'data_date': target_sheet,  # 添加数据日期
                'market_cap': float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else 0,  # 添加市值字段
                'name': str(row.get('name', '')) if pd.notna(row.get('name')) else '',  # 添加公司名称
            }
            stocks.append(stock)
        
        # 使用today作为key保持一致性
        results['sheets']['today'] = stocks
        results['data_date'] = target_sheet  # 标记实际数据日期
        logger.info(f"✓ 读取A股反包数据成功: {len(stocks)} 只股票 (数据日期: {target_sheet})")
        
        return results
        
    except Exception as e:
        logger.error(f"读取A股Excel失败: {e}")
        return {
            'success': False,
            'message': f'读取A股Excel失败: {str(e)}',
            'sheets': {}
        }


def read_metal_reversal_excel(excel_file):
    """读取贵金属反包Excel文件（最新数据）"""
    try:
        excel = pd.ExcelFile(excel_file)
        file_time = datetime.fromtimestamp(os.path.getmtime(excel_file))
        
        results = {
            'success': True,
            'file': excel_file,
            'update_time': file_time.strftime('%Y-%m-%d %H:%M:%S'),
            'sheets': {}
        }
        
        # 获取今天的日期作为sheet名称
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 如果今天的sheet不存在，使用最新的sheet
        if today in excel.sheet_names:
            target_sheet = today
            use_today_data = True
        elif len(excel.sheet_names) > 0:
            # 使用最新的sheet（按日期排序）
            target_sheet = sorted(excel.sheet_names)[-1]
            use_today_data = False
            logger.warning(f"⚠️ 今天({today})的数据不存在，使用最新的sheet: {target_sheet}")
        else:
            logger.warning(f"Excel文件中没有任何sheet")
            results['message'] = 'Excel文件中没有数据'
            return results
        
        # 读取Excel时指定symbol为字符串类型
        df = pd.read_excel(excel_file, sheet_name=target_sheet, dtype={'symbol': str})
        # 确保symbol字段是字符串类型
        if 'symbol' in df.columns:
            df['symbol'] = df['symbol'].astype(str).str.strip()
        
        metals = []
        
        for _, row in df.iterrows():
            # 贵金属没有成交量/交易额，使用价格变化幅度作为替代指标
            price_change_increase_pct = float(row.get('price_change_increase_pct', 0))
            
            metal = {
                'symbol': str(row['symbol']).strip(),  # 确保symbol是字符串类型
                'open_t2': float(row.get('open_t2', 0)),
                'close_t2': float(row.get('close_t2', 0)),
                'high_t2': float(row.get('high_t2', 0)),
                'low_t2': float(row.get('low_t2', 0)),
                't2_change_pct': float(row.get('t2_change_pct', 0)),
                'open_t1': float(row.get('open_t1', 0)),
                'close_t1': float(row.get('close_t1', 0)),
                'high_t1': float(row.get('high_t1', 0)),
                'low_t1': float(row.get('low_t1', 0)),
                't1_change_pct': float(row.get('t1_change_pct', 0)),
                'price_change_increase_pct': price_change_increase_pct,  # 价格变化增幅（替代成交量增幅）
                'reversal_strength': float(row.get('reversal_strength', 0)),
                'data_date': target_sheet,  # 添加数据日期
            }
            metals.append(metal)
        
        # 如果使用的不是今天的数据，使用数据日期+默认时间作为update_time
        if not use_today_data:
            # 使用数据日期 + 默认时间（08:02:00）作为update_time
            try:
                data_date_obj = datetime.strptime(target_sheet, '%Y-%m-%d')
                results['update_time'] = data_date_obj.strftime('%Y-%m-%d 08:02:00')
            except:
                # 如果解析失败，使用文件修改时间
                pass
        
        # 使用today作为key保持一致性
        results['sheets']['today'] = metals
        results['data_date'] = target_sheet  # 标记实际数据日期
        logger.info(f"✓ 读取贵金属反包数据成功: {len(metals)} 个贵金属 (数据日期: {target_sheet}, 更新时间: {results['update_time']})")
        
        return results
        
    except Exception as e:
        logger.error(f"读取贵金属Excel失败: {e}")
        return {
            'success': False,
            'message': f'读取贵金属Excel失败: {str(e)}',
            'sheets': {}
        }


def fetch_and_filter_market(market_type):
    """获取指定市场类型的数据并筛选"""
    if market_type == 'bn_spot':
        market_name = "BN现货"
    elif market_type == 'bn_futures':
        market_name = "BN合约"
    elif market_type == 'ok_spot':
        market_name = "OK现货"
    elif market_type == 'ok_futures':
        market_name = "OK合约"
    else:
        market_name = "未知市场"
    
    logger.info(f"开始处理{market_name}数据...")
    
    try:
        # 步骤1: 获取K线数据
        logger.info(f"步骤1: 获取{market_name}Top{CONFIG['top_n']}多周期K线数据...")
        
        # 根据市场类型选择数据获取器
        if market_type.startswith('bn_'):
            # Binance数据获取器
            from binance_data_fetcher import BinanceDataFetcher
            from fetch_multi_period_data import save_to_excel
            
            # 创建数据获取器
            bn_market_type = 'futures' if market_type == 'bn_futures' else 'spot'
            fetcher = BinanceDataFetcher(market_type=bn_market_type)
        elif market_type.startswith('ok_'):
            # OKX数据获取器
            from okx_data_fetcher import OKXDataFetcher
            from okx_fetch_multi_period_data import save_to_excel
            
            # 创建数据获取器
            ok_market_type = 'futures' if market_type == 'ok_futures' else 'spot'
            fetcher = OKXDataFetcher(market_type=ok_market_type)
        else:
            raise Exception(f"不支持的市场类型: {market_type}")
        
        # 预筛选机制：先获取周K线数据，筛选出数据充足的token
        # 使用用户设置的kline_records作为预筛选阈值
        min_data_threshold = CONFIG['kline_records']
        logger.info(f"步骤1.1: 预筛选{market_name}Token（基于周K线数据量，要求>={min_data_threshold}条）...")
        
        # 先获取周K线数据进行预筛选
        # 对于周K线，需要足够长的历史数据来满足kline_records的要求
        # 添加一些缓冲天数，确保能获取到足够的周K线数据
        week_days = CONFIG['kline_records']
        week_df = fetcher.fetch_top_n_daily_data(
            days=week_days,
            interval='1w',
            top_n=CONFIG['top_n'],
            delay=0.1
        )
        
        if week_df.empty:
            logger.warning(f"✗ {market_name}周K线数据获取失败，跳过预筛选")
            valid_symbols = None
        else:
            # 统计每个token的周K线数据量
            symbol_counts = week_df['symbol'].value_counts()
            # 使用用户设置的kline_records作为预筛选阈值
            valid_symbols = symbol_counts[symbol_counts >= min_data_threshold].index.tolist()
            logger.info(f"✓ {market_name}预筛选完成: {len(valid_symbols)}/{len(symbol_counts)} 个token数据充足（>={min_data_threshold}条周K线）")
            
            if len(valid_symbols) == 0:
                logger.warning(f"✗ {market_name}没有token满足数据量要求，跳过后续获取")
                raise Exception(f"{market_name}没有token满足数据量要求（>={min_data_threshold}条周K线）")
        
        # 获取多周期数据 - 根据市场类型配置不同的周期
        if market_type.startswith('bn_'):
            # Binance数据获取器：使用用户设置的kline_records
            periods = [
                {'interval': '1d', 'days': CONFIG['kline_records'], 'name': '1日'},
                {'interval': '3d', 'days': CONFIG['kline_records'], 'name': '3日'},
                {'interval': '1w', 'days': CONFIG['kline_records'], 'name': '周'}
            ]
        elif market_type.startswith('ok_'):
            # OKX数据获取器：增加2日、5日周期，使用用户设置的kline_records
            periods = [
                {'interval': '1d', 'days': CONFIG['kline_records'], 'name': '1日'},
                {'interval': '2d', 'days': CONFIG['kline_records'], 'name': '2日'},
                {'interval': '3d', 'days': CONFIG['kline_records'], 'name': '3日'},
                {'interval': '5d', 'days': CONFIG['kline_records'], 'name': '5日'},
                {'interval': '1w', 'days': CONFIG['kline_records'], 'name': '周'}
            ]
        else:
            # 默认配置
            periods = [
                {'interval': '1d', 'days': 16, 'name': '1日'},
                {'interval': '3d', 'days': 16, 'name': '3日'},
                {'interval': '1w', 'days': 16, 'name': '周'}
            ]
        
        all_periods_data = {}
        
        # 如果有预筛选结果，只获取有效token的数据
        if valid_symbols:
            logger.info(f"步骤1.2: 获取{market_name}有效Token的多周期K线数据...")
            
            # 为每个周期获取数据，但限制为有效token
            for period in periods:
                # 所有周期都需要重新获取，确保获取正确的K线数量
                logger.info(f"获取{market_name}{period['name']}K线数据（限制为{len(valid_symbols)}个有效token）...")
                
                # 创建一个临时的fetcher，限制token数量
                limited_fetcher = fetcher.__class__(market_type=fetcher.market_type)
                
                # 获取有效token的数据
                df = limited_fetcher.fetch_top_n_daily_data(
                    days=period['days'],
                    interval=period['interval'],
                    top_n=len(valid_symbols),  # 限制为有效token数量
                    delay=0.1
                )
                
                # 进一步过滤，只保留有效token
                if not df.empty:
                    filtered_df = df[df['symbol'].isin(valid_symbols)]
                    all_periods_data[period['name']] = filtered_df
                    logger.info(f"✓ {market_name}{period['name']}K线数据（预筛选后）: {len(filtered_df)}条记录")
                else:
                    logger.warning(f"✗ {market_name}{period['name']}K线数据获取失败")
        else:
            # 没有预筛选结果，按原逻辑获取所有数据
            logger.info(f"步骤1.2: 获取{market_name}所有Token的多周期K线数据...")
            for period in periods:
                logger.info(f"获取{market_name}{period['name']}K线数据...")
                df = fetcher.fetch_top_n_daily_data(
                    days=period['days'],
                    interval=period['interval'],
                    top_n=CONFIG['top_n'],
                    delay=0.1
                )
                if not df.empty:
                    all_periods_data[period['name']] = df
                    logger.info(f"✓ {market_name}{period['name']}K线数据获取完成: {len(df)}条记录")
                else:
                    logger.warning(f"✗ {market_name}{period['name']}K线数据获取失败")
        
        if not all_periods_data:
            raise Exception(f"未获取到任何{market_name}K线数据")
        
        # 保存数据到Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 根据市场类型生成文件名前缀
        if market_type == 'bn_spot':
            prefix = f"top{CONFIG['top_n']}_multi_period"
        elif market_type == 'bn_futures':
            prefix = f"futures_top{CONFIG['top_n']}_multi_period"
        elif market_type == 'ok_spot':
            prefix = f"okx_top{CONFIG['top_n']}_multi_period"
        elif market_type == 'ok_futures':
            prefix = f"okx_futures_top{CONFIG['top_n']}_multi_period"
        else:
            prefix = f"{market_type}_top{CONFIG['top_n']}_multi_period"
        
        # 确保保存到正确的data目录
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        data_dir = os.path.abspath(data_dir)
        os.makedirs(data_dir, exist_ok=True)
        filename = os.path.join(data_dir, f"{prefix}_{timestamp}.xlsx")
        
        # 直接保存到指定路径，处理时区信息
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, df in all_periods_data.items():
                # 处理时区信息：去掉时间戳列的时区信息
                df_copy = df.copy()
                
                # 检查并处理时间戳列
                timestamp_columns = ['timestamp', 'close_time', 'T_minus_2_date', 'T_minus_1_date']
                for col in timestamp_columns:
                    if col in df_copy.columns:
                        # 如果列包含时区信息，去掉时区
                        if df_copy[col].dtype.name.startswith('datetime64'):
                            df_copy[col] = df_copy[col].dt.tz_localize(None)
                        elif hasattr(df_copy[col].iloc[0], 'tz') and df_copy[col].iloc[0].tz is not None:
                            df_copy[col] = df_copy[col].dt.tz_localize(None)
                
                df_copy.to_excel(writer, sheet_name=sheet_name, index=False)
        
        excel_file = filename
        logger.info(f"✓ {market_name}K线数据已保存: {excel_file}")
        
        # 步骤2: 筛选Token
        logger.info(f"步骤2: 筛选{market_name}Token...")
        
        from token_filter_multi_period import MultiPeriodTokenFilter
        
        filter_obj = MultiPeriodTokenFilter(excel_file)
        results = filter_obj.filter_all_periods()
        
        # 保存筛选结果
        # 根据市场类型生成输出文件名前缀
        if market_type == 'bn_spot':
            output_prefix = "qualified_tokens_multi_period"
        elif market_type == 'bn_futures':
            output_prefix = "qualified_futures_tokens_multi_period"
        elif market_type == 'ok_spot':
            output_prefix = "qualified_okx_tokens_multi_period"
        elif market_type == 'ok_futures':
            output_prefix = "qualified_okx_futures_tokens_multi_period"
        else:
            output_prefix = f"qualified_{market_type}_tokens_multi_period"
        
        output_filename = f"{output_prefix}_{timestamp}.xlsx"
        output_file = filter_obj.save_results_to_excel(results, output_filename)
        
        if output_file:
            logger.info(f"✓ {market_name}Token筛选完成: {output_file}")
            return output_file
        else:
            raise Exception(f"{market_name}Token筛选失败")
            
    except Exception as e:
        logger.error(f"{market_name}数据处理失败: {str(e)}")
        raise


def process_us_stock_reversal():
    """处理US股票反包检测"""
    try:
        logger.info("开始处理US股票反包检测...")
        
        # 导入US股票反包检测器
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from equity.us_stock_reversal_detector import USStockReversalDetector
        
        # 创建检测器
        detector = USStockReversalDetector()
        
        # 运行反包检测
        results = detector.run_reversal_detection()
        
        if not results.empty:
            logger.info(f"✓ US股票反包检测完成: 找到 {len(results)} 只符合条件的股票")
            return True
        else:
            logger.warning("US股票反包检测完成: 未找到符合条件的股票")
            return True
            
    except Exception as e:
        logger.error(f"US股票反包检测失败: {e}")
        logger.error(traceback.format_exc())
        return False


def process_hk_stock_reversal():
    """处理港股反包检测"""
    try:
        logger.info("开始处理港股反包检测...")
        
        # 导入港股反包检测器
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from equity.hk_stock_reversal_detector import HKStockReversalDetector
        
        # 创建检测器
        detector = HKStockReversalDetector()
        
        # 运行反包检测
        results = detector.run_reversal_detection()
        
        if not results.empty:
            logger.info(f"✓ 港股反包检测完成: 找到 {len(results)} 只符合条件的股票")
            return True
        else:
            logger.warning("港股反包检测完成: 未找到符合条件的股票")
            return True
            
    except Exception as e:
        logger.error(f"港股反包检测失败: {e}")
        logger.error(traceback.format_exc())
        return False


def process_a_stock_reversal():
    """处理A股反包检测"""
    try:
        logger.info("开始处理A股反包检测...")
        
        # 导入A股反包检测器
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from equity.a_stock_reversal_detector import AStockReversalDetector
        
        # 创建检测器
        detector = AStockReversalDetector()
        
        # 运行反包检测
        results = detector.run_reversal_detection()
        
        if not results.empty:
            logger.info(f"✓ A股反包检测完成: 找到 {len(results)} 只符合条件的股票")
            return True
        else:
            logger.warning("A股反包检测完成: 未找到符合条件的股票")
            return True
            
    except Exception as e:
        logger.error(f"A股反包检测失败: {e}")
        logger.error(traceback.format_exc())
        return False


def auto_fetch_and_filter():
    """自动获取数据并筛选的任务（BN合约+OK合约+US股票+港股+A股）"""
    logger.info("="*80)
    logger.info("开始执行自动化任务（BN合约+OK合约+US股票+港股+A股）")
    logger.info(f"配置: Top{CONFIG['top_n']} 代币")
    logger.info("="*80)
    
    try:
        task_status['status'] = '运行中'
        task_status['message'] = f"正在获取Top{CONFIG['top_n']}代币数据（BN合约+OK合约+US股票+港股+A股）..."
        task_status['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 并发处理五个市场数据
        import threading
        import time
        
        bn_futures_result = {'file': None, 'error': None}
        ok_futures_result = {'file': None, 'error': None}
        us_stock_result = {'success': False, 'error': None}
        hk_stock_result = {'success': False, 'error': None}
        a_stock_result = {'success': False, 'error': None}
        
        def process_bn_futures():
            try:
                bn_futures_result['file'] = fetch_and_filter_market('bn_futures')
            except Exception as e:
                bn_futures_result['error'] = str(e)
        
        def process_ok_futures():
            try:
                ok_futures_result['file'] = fetch_and_filter_market('ok_futures')
            except Exception as e:
                ok_futures_result['error'] = str(e)
        
        def process_us_stock():
            try:
                us_stock_result['success'] = process_us_stock_reversal()
            except Exception as e:
                us_stock_result['error'] = str(e)
        
        def process_hk_stock():
            try:
                hk_stock_result['success'] = process_hk_stock_reversal()
            except Exception as e:
                hk_stock_result['error'] = str(e)
        
        def process_a_stock():
            try:
                a_stock_result['success'] = process_a_stock_reversal()
            except Exception as e:
                a_stock_result['error'] = str(e)
        
        # 启动五个线程
        bn_futures_thread = threading.Thread(target=process_bn_futures)
        ok_futures_thread = threading.Thread(target=process_ok_futures)
        us_stock_thread = threading.Thread(target=process_us_stock)
        hk_stock_thread = threading.Thread(target=process_hk_stock)
        a_stock_thread = threading.Thread(target=process_a_stock)
        
        bn_futures_thread.start()
        ok_futures_thread.start()
        us_stock_thread.start()
        hk_stock_thread.start()
        a_stock_thread.start()
        
        # 等待五个线程完成
        bn_futures_thread.join()
        ok_futures_thread.join()
        us_stock_thread.join()
        hk_stock_thread.join()
        a_stock_thread.join()
        
        # 检查结果
        errors = []
        if bn_futures_result['error']:
            errors.append(f"BN合约处理失败: {bn_futures_result['error']}")
        if ok_futures_result['error']:
            errors.append(f"OK合约处理失败: {ok_futures_result['error']}")
        if us_stock_result['error']:
            errors.append(f"US股票处理失败: {us_stock_result['error']}")
        if hk_stock_result['error']:
            errors.append(f"港股处理失败: {hk_stock_result['error']}")
        if a_stock_result['error']:
            errors.append(f"A股处理失败: {a_stock_result['error']}")
        
        # 不因为单个市场失败而导致整体失败
        success_markets = []
        if not bn_futures_result['error']:
            success_markets.append('BN合约')
        if not ok_futures_result['error']:
            success_markets.append('OK合约')
        if not us_stock_result['error']:
            success_markets.append('US股票')
        if not hk_stock_result['error']:
            success_markets.append('港股')
        if not a_stock_result['error']:
            success_markets.append('A股')
        
        # 更新状态
        if success_markets:
            task_status['status'] = '成功'
            task_status['message'] = f'自动化任务完成 ({", ".join(success_markets)})'
            if errors:
                task_status['message'] += f' | 部分失败: {"; ".join(errors)}'
        else:
            task_status['status'] = '失败'
            task_status['message'] = f'所有市场处理失败: {"; ".join(errors)}'
        
        task_status['filter_file'] = {
            'bn_futures': bn_futures_result['file'],
            'ok_futures': ok_futures_result['file'],
            'us_stock': us_stock_result['success'],
            'hk_stock': hk_stock_result['success'],
            'a_stock': a_stock_result['success']
        }
        
        logger.info("="*80)
        if success_markets:
            logger.info(f"✓ 自动化任务执行成功 ({', '.join(success_markets)})")
            logger.info(f"  BN合约筛选结果: {bn_futures_result['file']}")
            logger.info(f"  OK合约筛选结果: {ok_futures_result['file']}")
            logger.info(f"  US股票反包检测: {'成功' if us_stock_result['success'] else '失败'}")
            logger.info(f"  港股反包检测: {'成功' if hk_stock_result['success'] else '失败'}")
            logger.info(f"  A股反包检测: {'成功' if a_stock_result['success'] else '失败'}")
            if errors:
                logger.warning(f"  部分失败: {'; '.join(errors)}")
        else:
            logger.error("✗ 自动化任务执行失败")
            logger.error(f"  错误: {'; '.join(errors)}")
        logger.info("="*80)
        
    except Exception as e:
        error_msg = f"自动化任务失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        task_status['status'] = '失败'
        task_status['message'] = error_msg


# ==================== 黑名单管理函数 ====================

def load_blacklist():
    """加载黑名单"""
    try:
        if os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                blacklist = json.load(f)
                # 确保所有市场都存在
                default_markets = {'bn': [], 'ok': [], 'us': [], 'hk': [], 'a': [], 'metal': []}
                for market in default_markets:
                    if market not in blacklist:
                        blacklist[market] = []
                return blacklist
        return {'bn': [], 'ok': [], 'us': [], 'hk': [], 'a': [], 'metal': []}
    except Exception as e:
        logger.error(f"加载黑名单失败: {e}")
        return {'bn': [], 'ok': [], 'us': [], 'hk': [], 'a': [], 'metal': []}


def save_blacklist(blacklist):
    """保存黑名单"""
    try:
        os.makedirs(os.path.dirname(BLACKLIST_FILE), exist_ok=True)
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存黑名单失败: {e}")
        return False


def add_to_blacklist(market, symbol):
    """添加到黑名单"""
    blacklist = load_blacklist()
    if market not in blacklist:
        blacklist[market] = []
    if symbol not in blacklist[market]:
        blacklist[market].append(symbol)
        save_blacklist(blacklist)
        logger.info(f"已将 {symbol} 加入 {market} 黑名单")
        return True
    return False


def remove_from_blacklist(market, symbol):
    """从黑名单移除"""
    blacklist = load_blacklist()
    if market in blacklist and symbol in blacklist[market]:
        blacklist[market].remove(symbol)
        save_blacklist(blacklist)
        logger.info(f"已将 {symbol} 从 {market} 黑名单移除")
        return True
    return False


def filter_blacklist(tokens, market_type):
    """过滤黑名单中的标的"""
    blacklist = load_blacklist()
    market_blacklist = blacklist.get(market_type, [])
    if not market_blacklist:
        return tokens
    
    filtered = [t for t in tokens if t.get('symbol') not in market_blacklist]
    removed_count = len(tokens) - len(filtered)
    if removed_count > 0:
        logger.info(f"已过滤 {market_type} 市场黑名单标的: {removed_count} 只")
    return filtered


# ==================== Flask路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template_string(get_html_template())


@app.route('/monitor')
def monitor_page():
    """监控Token列表页面"""
    return render_template_string(get_monitor_html_template())


@app.route('/open-interest')
def open_interest_page():
    """合约持仓量监控页面"""
    return render_template_string(get_open_interest_html_template())


def calculate_and_save_open_interest():
    """计算并保存合约持仓量数据到JSON文件"""
    try:
        from src.crypto.binance_data_fetcher import BinanceDataFetcher
        
        logger.info("开始计算合约持仓量数据...")
        calculation_start_time = datetime.now()
        
        # 获取仅上线合约的交易对
        futures_fetcher = BinanceDataFetcher(market_type='futures')
        futures_only_tokens = futures_fetcher.get_futures_only_tokens()
        
        # 获取当前持仓量数据
        result_data = []
        for symbol in futures_only_tokens:
            try:
                # 获取当前持仓量
                oi_data = futures_fetcher.get_open_interest(symbol)
                if not oi_data:
                    continue
                
                current_oi = float(oi_data.get('openInterest', 0))
                
                # 获取1小时前持仓量（使用历史持仓量API）
                try:
                    # 优先使用5分钟数据，对比12条前（1小时前）
                    hist_df = futures_fetcher.get_open_interest_hist(symbol, period='5m', limit=24)
                    if not hist_df.empty and len(hist_df) >= 12:
                        # 使用历史数据的最新记录作为当前，倒数第13条作为1小时前
                        latest_hist_oi = float(hist_df.iloc[-1]['sumOpenInterest'])
                        previous_oi = float(hist_df.iloc[-13]['sumOpenInterest'])  # 12条前，即1小时前
                        # 用历史最新的覆盖实时数据，更准确
                        current_oi = latest_hist_oi
                    else:
                        # 如果5分钟数据不足，使用1小时数据
                        hist_hour = futures_fetcher.get_open_interest_hist(symbol, period='1h', limit=2)
                        if not hist_hour.empty and len(hist_hour) >= 2:
                            previous_oi = float(hist_hour.iloc[-2]['sumOpenInterest'])
                        else:
                            previous_oi = current_oi
                except:
                    previous_oi = current_oi
                
                # 计算增长率
                growth_rate = 0
                if previous_oi > 0:
                    growth_rate = ((current_oi - previous_oi) / previous_oi) * 100
                
                # 计算增长金额（需要获取当前价格）
                try:
                    from binance.client import Client
                    client = Client()
                    ticker = client.futures_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price']) if ticker else 0
                    growth_amount_usdt = (current_oi - previous_oi) * current_price if current_price > 0 else 0
                except:
                    growth_amount_usdt = 0
                
                # 筛选条件：增长率 > 20% 或 增长金额 > 100万USDT
                if growth_rate > 20 or growth_amount_usdt > 1000000:
                    result_data.append({
                        'symbol': symbol,
                        'current_oi': current_oi,
                        'previous_oi': previous_oi,
                        'growth_rate': growth_rate,
                        'growth_amount_usdt': growth_amount_usdt,
                        'update_time': datetime.fromtimestamp(oi_data.get('time', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    })
                
            except Exception as e:
                logger.error(f"获取 {symbol} 持仓量失败: {e}")
                continue
        
        # 按增长率排序
        result_data.sort(key=lambda x: x['growth_rate'], reverse=True)
        
        calculation_end_time = datetime.now()
        
        # 准备保存的数据
        save_data = {
            'update_time': calculation_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'calculation_time': calculation_end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'data': result_data
        }
        
        # 确保data目录存在
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        data_dir = os.path.abspath(data_dir)
        os.makedirs(data_dir, exist_ok=True)
        
        # 保存到JSON文件
        json_file_path = os.path.join(data_dir, 'open_interest_data.json')
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 合约持仓量数据计算完成，共 {len(result_data)} 条记录，已保存到 {json_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"计算合约持仓量数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False


@app.route('/api/open-interest')
def get_open_interest_data():
    """获取合约持仓量数据（从JSON文件读取）"""
    try:
        # 获取data目录路径
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        data_dir = os.path.abspath(data_dir)
        json_file_path = os.path.join(data_dir, 'open_interest_data.json')
        
        # 检查文件是否存在
        if not os.path.exists(json_file_path):
            logger.warning(f"持仓量数据文件不存在: {json_file_path}")
            return jsonify({
                'success': False,
                'message': '数据文件不存在，等待定时任务生成数据',
                'data': [],
                'update_time': '',
                'calculation_time': ''
            })
        
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
        
        # 返回数据，保持原有格式
        return jsonify({
            'success': True,
            'data': file_data.get('data', []),
            'update_time': file_data.get('update_time', ''),
            'calculation_time': file_data.get('calculation_time', '')
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"读取持仓量数据文件JSON格式错误: {e}")
        return jsonify({
            'success': False,
            'message': f'数据文件格式错误: {str(e)}',
            'data': [],
            'update_time': '',
            'calculation_time': ''
        })
    except Exception as e:
        logger.error(f"获取合约持仓量数据失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e),
            'data': [],
            'update_time': '',
            'calculation_time': ''
        })


# =====================================================
# Token配置管理（tokens-config-dynamic.md）
# =====================================================

@app.route('/token-config')
def token_config_page():
    """Token配置管理页面"""
    return render_template_string(get_token_config_html_template())


@app.route('/api/token-config')
def get_token_config():
    """获取Token配置文件内容"""
    try:
        # 获取alert目录下的tokens-config-dynamic.md文件
        alert_dir = os.path.join(os.path.dirname(__file__), '..', 'alert')
        alert_dir = os.path.abspath(alert_dir)
        config_file = os.path.join(alert_dir, 'tokens-config-dynamic.md')

        if not os.path.exists(config_file):
            return jsonify({
                'success': False,
                'message': f'配置文件不存在: {config_file}',
                'content': '',
                'last_modified': ''
            })

        # 读取文件内容
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 获取文件修改时间
        mtime = os.path.getmtime(config_file)
        last_modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            'success': True,
            'content': content,
            'last_modified': last_modified,
            'file_path': config_file
        })

    except Exception as e:
        logger.error(f"获取Token配置失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'content': '',
            'last_modified': ''
        })


@app.route('/api/token-config/save', methods=['POST'])
def save_token_config():
    """保存Token配置文件"""
    try:
        data = request.get_json()
        content = data.get('content', '')

        if not content:
            return jsonify({
                'success': False,
                'message': '配置文件内容不能为空'
            })

        # 获取alert目录下的tokens-config-dynamic.md文件
        alert_dir = os.path.join(os.path.dirname(__file__), '..', 'alert')
        alert_dir = os.path.abspath(alert_dir)
        config_file = os.path.join(alert_dir, 'tokens-config-dynamic.md')

        # 保存文件
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # 解析保存后的交易对列表
        tokens = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            symbol = line.split('#')[0].strip()
            if symbol:
                tokens.append(symbol)

        logger.info(f"✓ Token配置已保存，共 {len(tokens)} 个交易对: {tokens}")

        return jsonify({
            'success': True,
            'message': f'配置已保存，共 {len(tokens)} 个交易对',
            'tokens': tokens,
            'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        logger.error(f"保存Token配置失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


def get_token_config_html_template():
    """Token配置管理HTML模板"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Token配置管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        .content {
            padding: 30px;
        }
        .info-box {
            background: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            margin-bottom: 20px;
            border-radius: 0 8px 8px 0;
        }
        .info-box h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 16px;
        }
        .info-box p {
            color: #4a5568;
            font-size: 14px;
            line-height: 1.6;
        }
        .info-box code {
            background: #e2e8f0;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 10px;
            color: #2d3748;
            font-weight: 600;
        }
        textarea {
            width: 100%;
            min-height: 400px;
            padding: 15px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
            line-height: 1.6;
            resize: vertical;
            transition: border-color 0.3s;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5a67d8;
            transform: translateY(-2px);
        }
        .btn-secondary {
            background: #e2e8f0;
            color: #4a5568;
        }
        .btn-secondary:hover {
            background: #cbd5e0;
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            display: none;
        }
        .status.success {
            background: #c6f6d5;
            color: #276749;
        }
        .status.error {
            background: #fed7d7;
            color: #c53030;
        }
        .status.info {
            background: #bee3f8;
            color: #2b6cb0;
        }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .back-link:hover {
            text-decoration: underline;
        }
        .last-modified {
            color: #718096;
            font-size: 12px;
            margin-top: 10px;
        }
        .token-preview {
            margin-top: 20px;
            padding: 15px;
            background: #f7fafc;
            border-radius: 8px;
            display: none;
        }
        .token-preview h4 {
            color: #2d3748;
            margin-bottom: 10px;
        }
        .token-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .token-tag {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .loading {
            text-align: center;
            padding: 50px;
            color: #718096;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ Token配置管理</h1>
            <p>编辑 tokens-config-dynamic.md 文件内容，修改后点击保存即可生效</p>
        </div>
        <div class="content">
            <div class="info-box">
                <h3>📋 使用说明</h3>
                <p>
                    • 每行填写一个交易对，如 <code>BTCUSDT</code><br>
                    • 支持 <code>#</code> 注释，如 <code>BTCUSDT  # 比特币</code><br>
                    • 保存后系统会自动重新加载配置<br>
                    • 此配置用于 <strong>动态监控任务</strong>，报警发送到第二个企业微信群
                </p>
            </div>

            <div id="loading" class="loading">加载中...</div>

            <div id="editor" style="display: none;">
                <div class="form-group">
                    <label>配置文件内容 (tokens-config-dynamic.md)：</label>
                    <textarea id="configContent" placeholder="每行一个交易对，如：BTCUSDT  # 比特币"></textarea>
                    <div class="last-modified" id="lastModified"></div>
                </div>

                <div class="btn-group">
                    <button class="btn btn-primary" onclick="saveConfig()">💾 保存配置</button>
                    <button class="btn btn-secondary" onclick="reloadConfig()">🔄 重新加载</button>
                </div>

                <div id="status" class="status"></div>

                <div id="tokenPreview" class="token-preview">
                    <h4>📊 当前配置的交易对：</h4>
                    <div class="token-list" id="tokenList"></div>
                </div>

                <a href="/" class="back-link">← 返回首页</a>
            </div>
        </div>
    </div>

    <script>
        let originalContent = '';

        function loadConfig() {
            fetch('/api/token-config')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    if (data.success) {
                        document.getElementById('editor').style.display = 'block';
                        document.getElementById('configContent').value = data.content;
                        originalContent = data.content;
                        document.getElementById('lastModified').textContent = '最后修改: ' + data.last_modified;
                        parseAndShowTokens(data.content);
                    } else {
                        showStatus(data.message, 'error');
                    }
                })
                .catch(error => {
                    document.getElementById('loading').style.display = 'none';
                    showStatus('加载失败: ' + error, 'error');
                });
        }

        function parseAndShowTokens(content) {
            const tokens = [];
            const lines = content.split('\\n');
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || trimmed.startsWith('#')) continue;
                const symbol = trimmed.split('#')[0].trim();
                if (symbol) tokens.push(symbol);
            }

            const preview = document.getElementById('tokenPreview');
            const list = document.getElementById('tokenList');

            if (tokens.length > 0) {
                preview.style.display = 'block';
                list.innerHTML = tokens.map(t => `<span class="token-tag">${t}</span>`).join('');
            } else {
                preview.style.display = 'none';
            }
        }

        function saveConfig() {
            const content = document.getElementById('configContent').value;
            const originalHasChanged = content !== originalContent;

            if (!originalHasChanged) {
                showStatus('内容没有变化，无需保存', 'info');
                return;
            }

            if (!content.trim()) {
                showStatus('配置文件内容不能为空', 'error');
                return;
            }

            fetch('/api/token-config/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: content })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    originalContent = content;
                    showStatus(data.message, 'success');
                    parseAndShowTokens(content);
                } else {
                    showStatus(data.message, 'error');
                }
            })
            .catch(error => {
                showStatus('保存失败: ' + error, 'error');
            });
        }

        function reloadConfig() {
            loadConfig();
            showStatus('已重新加载', 'info');
        }

        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
            setTimeout(() => {
                status.style.display = 'none';
            }, 3000);
        }

        // 页面加载时自动读取配置
        window.addEventListener('load', loadConfig);

        // 监听内容变化，实时预览交易对
        document.getElementById('configContent').addEventListener('input', function() {
            parseAndShowTokens(this.value);
        });
    </script>
</body>
</html>
    """


@app.route('/api/monitor')
def get_monitor_data():
    """获取监控Token数据"""
    try:
        # 添加项目根目录到路径
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        with db:
            monitors = db.get_all_monitors()
        
        # 格式化数据
        result = {
            'success': True,
            'tokens': [],
            'total': len(monitors)
        }
        
        for m in monitors:
            token_data = {
                'id': m['id'],
                'ticker': m['ticker'],
                'exchange': m['exchange'],
                'interval': m['interval'],
                'date': m['date'],
                'high': float(m['high']) if m['high'] else 0,
                'low': float(m['low']) if m['low'] else 0,
                'current_price': float(m['current_price']) if m['current_price'] else 0,
                'update_time': m.get('update_time', ''),
                'price_range': float(m['high']) - float(m['low']) if m['high'] and m['low'] else 0,
                'source': m.get('source', 'auto')
            }
            result['tokens'].append(token_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取监控数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取监控数据失败: {str(e)}'
        })


@app.route('/api/monitor/add', methods=['POST'])
def add_monitor_token():
    """添加监控Token（人工/高频导入）"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').strip().upper()
        interval = data.get('interval', '1D')
        source = data.get('source', 'manual')
        source = source.strip().lower() if isinstance(source, str) else 'manual'
        allowed_sources = {'manual', 'auto', 'highfreq'}
        
        if source not in allowed_sources:
            return jsonify({
                'success': False,
                'message': f'来源类型不支持: {source}'
            })
        
        if not ticker:
            return jsonify({
                'success': False,
                'message': '请填写交易对名称'
            })
        
        # 添加项目根目录到路径
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        
        # 设置默认值
        exchange = 'bn_futures'
        date = datetime.now().strftime('%Y-%m-%d')
        
        # 如果没有提供价格，设置为0（后续从交易所获取）
        high = data.get('high', 0)
        low = data.get('low', 0)
        current_price = data.get('current_price', 0)
        
        # 插入数据库
        with db:
            monitor_id = db.add_monitor(
                exchange=exchange,
                date=date,
                interval=interval,
                ticker=ticker,
                high=high,
                low=low,
                current_price=current_price,
                source=source
            )
        
        source_label_map = {
            'manual': '人工',
            'auto': '自动',
            'highfreq': '高频'
        }
        source_label = source_label_map.get(source, source)
        logger.info(f"{source_label}导入监控: {exchange} {ticker} {interval} (ID: {monitor_id}, source={source})")
        
        return jsonify({
            'success': True,
            'message': f'成功添加监控: {ticker}',
            'id': monitor_id
        })
        
    except Exception as e:
        logger.error(f"添加监控失败: {e}")
        return jsonify({
            'success': False,
            'message': f'添加监控失败: {str(e)}'
        }), 400


@app.route('/api/monitor/remove', methods=['POST'])
def remove_monitor_token():
    """删除监控Token（仅限人工或高频导入）"""
    try:
        data = request.get_json()
        monitor_id = data.get('id')
        
        if not monitor_id:
            return jsonify({
                'success': False,
                'message': '缺少监控ID参数'
            })
        
        # 添加项目根目录到路径
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from src.database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        
        # 先查询该监控记录，确认是否为人工导入
        with db:
            monitors = db.get_all_monitors()
            target_monitor = None
            for m in monitors:
                if m['id'] == monitor_id:
                    target_monitor = m
                    break
            
            if not target_monitor:
                return jsonify({
                    'success': False,
                    'message': '未找到该监控记录'
                })
            
            # 只允许删除人工或高频导入的记录
            if target_monitor.get('source') not in ('manual', 'highfreq'):
                return jsonify({
                    'success': False,
                    'message': '只能删除人工或高频来源的监控记录'
                })
            
            # 删除记录
            success = db.delete_monitor(
                ticker=target_monitor['ticker'],
                exchange=target_monitor['exchange'],
                interval=target_monitor['interval'],
                date=target_monitor['date']
            )
        
        if success:
            logger.info(f"删除监控: {target_monitor['exchange']} {target_monitor['ticker']} {target_monitor['interval']} (ID: {monitor_id})")
            return jsonify({
                'success': True,
                'message': f'成功删除监控: {target_monitor["ticker"]}'
            })
        else:
            return jsonify({
                'success': False,
                'message': '删除失败，未找到该监控记录'
            })
        
    except Exception as e:
        logger.error(f"删除监控失败: {e}")
        return jsonify({
            'success': False,
            'message': f'删除监控失败: {str(e)}'
        }), 400


@app.route('/api/data')
def get_data():
    """获取筛选结果数据（BN合约+OK合约+US股票+港股+A股）"""
    # 获取BN合约数据
    bn_futures_file = get_latest_qualified_tokens_file('bn_futures')
    # 获取OK合约数据
    ok_futures_file = get_latest_qualified_tokens_file('ok_futures')
    # 获取美股反包数据
    us_stock_file = get_latest_qualified_tokens_file('us_stock')
    # 获取港股反包数据
    hk_stock_file = get_latest_qualified_tokens_file('hk_stock')
    # 获取A股反包数据
    a_stock_file = get_latest_qualified_tokens_file('a_stock')
    # 获取贵金属反包数据
    metal_file = get_latest_qualified_tokens_file('metal')
    
    result = {
        'success': True,
        'bn': {'success': False, 'message': '', 'sheets': {}},
        'ok': {'success': False, 'message': '', 'sheets': {}},
        'us': {'success': False, 'message': '', 'sheets': {}},
        'hk': {'success': False, 'message': '', 'sheets': {}},
        'a': {'success': False, 'message': '', 'sheets': {}},
        'metal': {'success': False, 'message': '', 'sheets': {}}
    }
    
    # 读取BN合约数据
    if bn_futures_file:
        bn_futures_result = read_excel_all_sheets(bn_futures_file)
        if bn_futures_result['success']:
            # 为合约数据添加market_type标记，并过滤黑名单
            for period, tokens in bn_futures_result['sheets'].items():
                for token in tokens:
                    token['market_type'] = 'perp'
                # 过滤黑名单
                bn_futures_result['sheets'][period] = filter_blacklist(tokens, 'bn')
            result['bn'] = bn_futures_result
        else:
            result['bn'] = bn_futures_result
    else:
        result['bn']['message'] = '未找到BN合约数据文件'
    
    # 读取OK合约数据
    if ok_futures_file:
        ok_futures_result = read_excel_all_sheets(ok_futures_file)
        if ok_futures_result['success']:
            # 为合约数据添加market_type标记，处理OKX合约的-SWAP后缀，并过滤黑名单
            for period, tokens in ok_futures_result['sheets'].items():
                for token in tokens:
                    token['market_type'] = 'perp'
                    # 去掉OKX合约的-SWAP后缀显示
                    if token['symbol'].endswith('-SWAP'):
                        token['symbol'] = token['symbol'].replace('-SWAP', '')
                # 过滤黑名单
                ok_futures_result['sheets'][period] = filter_blacklist(tokens, 'ok')
            result['ok'] = ok_futures_result
        else:
            result['ok'] = ok_futures_result
    else:
        result['ok']['message'] = '未找到OK合约数据文件'
    
    # 读取美股反包数据
    if us_stock_file:
        us_stock_result = read_us_stock_reversal_excel(us_stock_file)
        if us_stock_result['success']:
            # 获取特别关注列表
            us_watchlist = get_watchlist_symbols('us')
            
            # 为美股数据添加market_type标记，过滤黑名单，并置顶特别关注
            for period, stocks in us_stock_result['sheets'].items():
                for stock in stocks:
                    stock['market_type'] = 'stock'
                    # 标记是否为特别关注
                    stock['is_watched'] = stock['symbol'] in us_watchlist
                
                # 过滤黑名单
                stocks = filter_blacklist(stocks, 'us')
                
                # 置顶特别关注的标的
                watched_stocks = [s for s in stocks if s.get('is_watched', False)]
                other_stocks = [s for s in stocks if not s.get('is_watched', False)]
                us_stock_result['sheets'][period] = watched_stocks + other_stocks
            result['us'] = us_stock_result
        else:
            result['us'] = us_stock_result
    else:
        result['us']['message'] = '未找到美股反包数据文件'
    
    # 读取港股反包数据
    if hk_stock_file:
        hk_stock_result = read_hk_stock_reversal_excel(hk_stock_file)
        if hk_stock_result['success']:
            # 获取特别关注列表
            hk_watchlist = get_watchlist_symbols('hk')
            
            # 为港股数据添加market_type标记，过滤黑名单，并置顶特别关注
            for period, stocks in hk_stock_result['sheets'].items():
                for stock in stocks:
                    stock['market_type'] = 'stock'
                    # 标记是否为特别关注
                    stock['is_watched'] = stock['symbol'] in hk_watchlist
                
                # 过滤黑名单
                stocks = filter_blacklist(stocks, 'hk')
                
                # 置顶特别关注的标的
                watched_stocks = [s for s in stocks if s.get('is_watched', False)]
                other_stocks = [s for s in stocks if not s.get('is_watched', False)]
                hk_stock_result['sheets'][period] = watched_stocks + other_stocks
            result['hk'] = hk_stock_result
        else:
            result['hk'] = hk_stock_result
    else:
        result['hk']['message'] = '未找到港股反包数据文件'
    
    # 读取A股反包数据
    if a_stock_file:
        a_stock_result = read_a_stock_reversal_excel(a_stock_file)
        if a_stock_result['success']:
            # 获取特别关注列表
            a_watchlist = get_watchlist_symbols('a')
            
            # 为A股数据添加market_type标记，过滤黑名单，并置顶特别关注
            for period, stocks in a_stock_result['sheets'].items():
                for stock in stocks:
                    stock['market_type'] = 'stock'
                    # 标记是否为特别关注
                    stock['is_watched'] = stock['symbol'] in a_watchlist
                
                # 过滤黑名单
                stocks = filter_blacklist(stocks, 'a')
                
                # 置顶特别关注的标的
                watched_stocks = [s for s in stocks if s.get('is_watched', False)]
                other_stocks = [s for s in stocks if not s.get('is_watched', False)]
                a_stock_result['sheets'][period] = watched_stocks + other_stocks
            result['a'] = a_stock_result
        else:
            result['a'] = a_stock_result
    else:
        result['a']['message'] = '未找到A股反包数据文件'
    
    # 读取贵金属反包数据
    if metal_file:
        metal_result = read_metal_reversal_excel(metal_file)
        if metal_result['success']:
            # 为贵金属数据添加market_type标记，并过滤黑名单
            for period, metals in metal_result['sheets'].items():
                for metal in metals:
                    metal['market_type'] = 'metal'
                # 过滤黑名单
                metal_result['sheets'][period] = filter_blacklist(metals, 'metal')
            result['metal'] = metal_result
        else:
            result['metal'] = metal_result
    else:
        result['metal']['message'] = '未找到贵金属反包数据文件'
    
    # 读取零点反包数据（从 src/alert/data 目录）
    result['zero_reversal'] = get_zero_reversal_data()
    
    # 如果都没有数据，返回失败
    if not bn_futures_file and not ok_futures_file and not us_stock_file and not hk_stock_file and not a_stock_file and not metal_file:
        result['success'] = False
        result['message'] = '未找到任何筛选结果文件，正在等待首次数据获取...'
    
    return jsonify(result)


@app.route('/api/status')
def get_status():
    """获取任务状态"""
    status_with_config = task_status.copy()
    status_with_config['config'] = CONFIG
    return jsonify(status_with_config)


@app.route('/api/trigger', methods=['GET', 'POST'])
def trigger_task():
    """手动触发任务"""
    logger.info("收到手动触发请求")
    
    # 在后台执行任务
    import threading
    thread = threading.Thread(target=auto_fetch_and_filter)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': '任务已启动，正在后台执行...'
    })


@app.route('/api/blacklist', methods=['GET'])
def get_blacklist():
    """获取黑名单"""
    try:
        blacklist = load_blacklist()
        return jsonify({
            'success': True,
            'blacklist': blacklist
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/blacklist/add', methods=['POST'])
def add_blacklist():
    """添加到黑名单"""
    try:
        from flask import request
        data = request.get_json()
        market = data.get('market')
        symbol = data.get('symbol')
        
        if not market or not symbol:
            return jsonify({
                'success': False,
                'message': '缺少market或symbol参数'
            })
        
        success = add_to_blacklist(market, symbol)
        return jsonify({
            'success': success,
            'message': f'已将 {symbol} 加入 {market} 黑名单' if success else f'{symbol} 已在黑名单中'
        })
    except Exception as e:
        logger.error(f"添加黑名单失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/blacklist/remove', methods=['POST'])
def remove_blacklist():
    """从黑名单移除"""
    try:
        from flask import request
        data = request.get_json()
        market = data.get('market')
        symbol = data.get('symbol')
        
        if not market or not symbol:
            return jsonify({
                'success': False,
                'message': '缺少market或symbol参数'
            })
        
        success = remove_from_blacklist(market, symbol)
        return jsonify({
            'success': success,
            'message': f'已将 {symbol} 从 {market} 黑名单移除' if success else f'{symbol} 不在黑名单中'
        })
    except Exception as e:
        logger.error(f"移除黑名单失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


# ==================== 特别关注管理函数 ====================

def load_watchlist():
    """加载特别关注列表，支持新旧格式兼容"""
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容旧格式：如果是数组，转换为新格式
                for market in ['us', 'hk', 'a']:
                    if market in data:
                        if isinstance(data[market], list) and len(data[market]) > 0:
                            # 检查第一个元素是否是字符串（旧格式）
                            if isinstance(data[market][0], str):
                                # 转换为新格式：默认使用Core2
                                data[market] = [
                                    {'symbol': symbol, 'webhook_url': 'core2'}
                                    for symbol in data[market]
                                ]
                return data
        return {'us': [], 'hk': [], 'a': []}
    except Exception as e:
        logger.error(f"加载特别关注列表失败: {e}")
        return {'us': [], 'hk': [], 'a': []}


def get_watchlist_symbols(market):
    """获取特别关注列表中的symbol列表（兼容新旧格式）"""
    watchlist = load_watchlist()
    market_list = watchlist.get(market, [])
    if not market_list:
        return []
    # 如果是新格式（对象数组），提取symbol
    if isinstance(market_list[0], dict):
        return [item['symbol'] for item in market_list]
    # 如果是旧格式（字符串数组），直接返回
    return market_list


def get_watchlist_webhook_url(market, symbol):
    """获取特别关注标的的webhook_url，如果未配置则返回Core2（默认）"""
    watchlist = load_watchlist()
    market_list = watchlist.get(market, [])
    if not market_list:
        return CORE2_WEBHOOK_URL  # 默认Core2
    
    # 查找对应的标的
    for item in market_list:
        if isinstance(item, dict):
            if item.get('symbol') == symbol:
                webhook_url = item.get('webhook_url', 'core2')
                if webhook_url == 'core1':
                    return CORE1_WEBHOOK_URL
                elif webhook_url == 'core2':
                    return CORE2_WEBHOOK_URL
                else:
                    # 如果直接是URL，直接返回
                    return webhook_url
        elif isinstance(item, str) and item == symbol:
            # 旧格式，默认Core2
            return CORE2_WEBHOOK_URL
    
    return CORE2_WEBHOOK_URL  # 默认Core2


def save_watchlist(watchlist):
    """保存特别关注列表"""
    try:
        os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
        with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存特别关注列表失败: {e}")
        return False


def add_to_watchlist(market, symbol, webhook_url='core2'):
    """添加到特别关注
    
    Args:
        market: 市场类型（us/hk/a）
        symbol: 标的代码
        webhook_url: webhook配置（'core1'/'core2'或完整URL），默认'core2'
    """
    watchlist = load_watchlist()
    if market not in watchlist:
        watchlist[market] = []
    
    # 检查是否已存在
    market_list = watchlist[market]
    existing_index = None
    for i, item in enumerate(market_list):
        if isinstance(item, dict):
            if item.get('symbol') == symbol:
                existing_index = i
                break
        elif isinstance(item, str) and item == symbol:
            existing_index = i
            break
    
    if existing_index is not None:
        # 更新现有项
        watchlist[market][existing_index] = {'symbol': symbol, 'webhook_url': webhook_url}
    else:
        # 添加新项
        watchlist[market].append({'symbol': symbol, 'webhook_url': webhook_url})
    
    save_watchlist(watchlist)
    logger.info(f"已将 {symbol} 加入 {market} 特别关注，webhook: {webhook_url}")
    return True


def remove_from_watchlist(market, symbol):
    """从特别关注移除"""
    watchlist = load_watchlist()
    if market not in watchlist:
        return False
    
    market_list = watchlist[market]
    for i, item in enumerate(market_list):
        if isinstance(item, dict):
            if item.get('symbol') == symbol:
                watchlist[market].pop(i)
                save_watchlist(watchlist)
                logger.info(f"已将 {symbol} 从 {market} 特别关注移除")
                return True
        elif isinstance(item, str) and item == symbol:
            watchlist[market].pop(i)
            save_watchlist(watchlist)
            logger.info(f"已将 {symbol} 从 {market} 特别关注移除")
            return True
    
    return False


def get_latest_daily_history(market):
    """获取最新一天的daily_history数据"""
    try:
        equity_data_dir = os.path.join(os.path.dirname(__file__), '..', 'equity', 'data')
        equity_data_dir = os.path.abspath(equity_data_dir)
        
        if market == 'us':
            history_file = os.path.join(equity_data_dir, 'us_stock_daily_history.xlsx')
        elif market == 'hk':
            history_file = os.path.join(equity_data_dir, 'hk_stock_daily_history.xlsx')
        elif market == 'a':
            history_file = os.path.join(equity_data_dir, 'a_stock_daily_history.xlsx')
        else:
            return pd.DataFrame()
        
        if not os.path.exists(history_file):
            return pd.DataFrame()
        
        excel = pd.ExcelFile(history_file)
        if len(excel.sheet_names) == 0:
            return pd.DataFrame()
        
        # 获取最新的sheet（按日期排序）
        latest_sheet = sorted(excel.sheet_names)[-1]
        # 确保symbol字段以字符串类型读取，保留前导0
        df = pd.read_excel(history_file, sheet_name=latest_sheet, dtype={'symbol': str})
        # 确保symbol字段是字符串类型
        if 'symbol' in df.columns:
            df['symbol'] = df['symbol'].astype(str).str.strip()
        return df
    except Exception as e:
        logger.error(f"获取{market}最新历史数据失败: {e}")
        return pd.DataFrame()


def get_zero_reversal_data():
    """
    读取 src/alert/data 目录下当天的反包数据
    
    Returns:
        包含零点反包数据的字典
    """
    try:
        from datetime import datetime
        import glob
        
        # 获取当天日期（格式：YYYYMMDD）
        today = datetime.now().strftime('%Y%m%d')
        
        # 查找 src/alert/data 目录下当天的反包数据文件
        alert_data_dir = os.path.join(os.path.dirname(__file__), '..', 'alert', 'data')
        pattern = os.path.join(alert_data_dir, f'high_frequency_reversals_{today}*.xlsx')
        files = glob.glob(pattern)
        
        if not files:
            return {
                'success': False,
                'message': f'未找到今天的零点反包数据文件（日期: {today}）',
                'sheets': {}
            }
        
        # 获取最新的文件
        latest_file = max(files, key=os.path.getmtime)
        
        # 读取Excel文件
        excel_data = pd.read_excel(latest_file, sheet_name=None)
        
        # 转换数据格式
        result = {
            'success': True,
            'message': f'成功读取零点反包数据（文件: {os.path.basename(latest_file)}）',
            'update_time': datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S'),
            'sheets': {}
        }
        
        # 处理每个sheet
        for sheet_name, df in excel_data.items():
            stocks = []
            for _, row in df.iterrows():
                stock = {
                    'symbol': str(row.get('symbol', '')),
                    'market_type': 'crypto',
                    'interval': sheet_name,  # 1日、2日、3日、5日、周、月
                    't2_date': str(row.get('T_minus_2_date', '')),
                    't2_open': float(row.get('T_minus_2_open', 0)),
                    't2_high': float(row.get('T_minus_2_high', 0)),
                    't2_low': float(row.get('T_minus_2_low', 0)),
                    't2_close': float(row.get('T_minus_2_close', 0)),
                    't2_volume': float(row.get('T_minus_2_volume', 0)),
                    't2_quote_asset_volume': float(row.get('T_minus_2_quote_asset_volume', 0)),
                    't2_change_pct': float(row.get('T_minus_2_change_pct', 0)),
                    't1_date': str(row.get('T_minus_1_date', '')),
                    't1_open': float(row.get('T_minus_1_open', 0)),
                    't1_high': float(row.get('T_minus_1_high', 0)),
                    't1_low': float(row.get('T_minus_1_low', 0)),
                    't1_close': float(row.get('T_minus_1_close', 0)),
                    't1_volume': float(row.get('T_minus_1_volume', 0)),
                    't1_quote_asset_volume': float(row.get('T_minus_1_quote_asset_volume', 0)),
                    't1_change_pct': float(row.get('T_minus_1_change_pct', 0)),
                    'volume_growth_rate_pct': float(row.get('volume_growth_rate_pct', 0)),
                    'usdt_volume_growth_rate_pct': float(row.get('usdt_volume_growth_rate_pct', 0))
                }
                stocks.append(stock)
            
            result['sheets'][sheet_name] = stocks
        
        logger.info(f"✓ 读取零点反包数据成功: {len(result['sheets'])} 个周期")
        return result
        
    except Exception as e:
        logger.error(f"读取零点反包数据失败: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'读取零点反包数据失败: {str(e)}',
            'sheets': {}
        }


@app.route('/api/watchlist/search', methods=['GET'])
def search_stocks():
    """搜索股票（从daily_history获取最新数据）"""
    try:
        market = request.args.get('market', 'us')
        query = request.args.get('q', '').strip().upper()
        
        if not query:
            return jsonify({
                'success': False,
                'message': '请输入搜索关键词',
                'results': []
            })
        
        # 获取最新一天的daily_history数据
        df = get_latest_daily_history(market)
        
        if df.empty:
            return jsonify({
                'success': False,
                'message': '未找到历史数据',
                'results': []
            })
        
        # 搜索symbol字段
        if 'symbol' not in df.columns:
            return jsonify({
                'success': False,
                'message': '数据格式错误：缺少symbol字段',
                'results': []
            })
        
        # 过滤匹配的股票
        matched = df[df['symbol'].str.upper().str.contains(query, na=False)]
        
        # 返回结果（最多50条）
        results = []
        for _, row in matched.head(50).iterrows():
            result = {
                'symbol': str(row['symbol']),
                'name': str(row.get('name', '')) if 'name' in row else ''
            }
            # 添加价格信息（如果有）
            if 'close' in row:
                result['price'] = float(row['close'])
            results.append(result)
        
        return jsonify({
            'success': True,
            'message': f'找到 {len(results)} 条结果',
            'results': results
        })
    except Exception as e:
        logger.error(f"搜索股票失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'results': []
        })


@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """获取特别关注列表"""
    try:
        watchlist = load_watchlist()
        return jsonify({
            'success': True,
            'watchlist': watchlist
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/watchlist/add', methods=['POST'])
def add_watchlist():
    """添加到特别关注"""
    try:
        data = request.get_json()
        market = data.get('market')
        symbol = data.get('symbol')
        webhook_url = data.get('webhook_url', 'core2')  # 默认core2
        
        if not market or not symbol:
            return jsonify({
                'success': False,
                'message': '缺少market或symbol参数'
            })
        
        # 验证webhook_url
        if webhook_url not in ['core1', 'core2']:
            webhook_url = 'core2'  # 默认core2
        
        success = add_to_watchlist(market, symbol, webhook_url)
        return jsonify({
            'success': success,
            'message': f'已将 {symbol} 加入 {market} 特别关注（{webhook_url}）' if success else f'{symbol} 已在特别关注中'
        })
    except Exception as e:
        logger.error(f"添加特别关注失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/watchlist/remove', methods=['POST'])
def remove_watchlist():
    """从特别关注移除"""
    try:
        data = request.get_json()
        market = data.get('market')
        symbol = data.get('symbol')
        
        if not market or not symbol:
            return jsonify({
                'success': False,
                'message': '缺少market或symbol参数'
            })
        
        success = remove_from_watchlist(market, symbol)
        return jsonify({
            'success': success,
            'message': f'已将 {symbol} 从 {market} 特别关注移除' if success else f'{symbol} 不在特别关注中'
        })
    except Exception as e:
        logger.error(f"移除特别关注失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


def get_html_template():
    """获取HTML模板"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>多周期Token筛选 - 自动化版</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header h1 { color: #2d3748; font-size: 32px; margin-bottom: 10px; }
        .header p { color: #718096; font-size: 14px; }
        
        /* 任务状态卡片 */
        .task-status {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .status-label { font-weight: 600; color: #4a5568; }
        .status-value { color: #2d3748; }
        .status-running { color: #f59e0b; }
        .status-success { color: #10b981; }
        .status-error { color: #ef4444; }
        .trigger-btn {
            background: #10b981;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .trigger-btn:hover { background: #059669; }
        .trigger-btn:disabled { background: #9ca3af; cursor: not-allowed; }
        
        /* 市场类型选项卡 */
        .market-tabs {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        /* 周期选项卡 */
        .period-tabs {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .tab-btn {
            padding: 12px 24px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            background: white;
            color: #4a5568;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .tab-btn:hover { border-color: #667eea; color: #667eea; }
        .tab-btn.active { background: #667eea; border-color: #667eea; color: white; }
        
        /* 今日反包下拉菜单样式 */
        #todayReversalMenu button:hover {
            background: #f7fafc !important;
        }
        
        /* 数据标识样式 */
        .data-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-left: 8px;
            background: #e2e8f0;
            transition: all 0.3s ease;
        }
        .data-indicator.has-today {
            background: #10b981;
            box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.3);
        }
        .data-indicator.no-data {
            background: #ef4444;
            box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.3);
        }
        
        
        
        .controls {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .btn:hover { background: #5a67d8; }
        .search-box { flex: 1; min-width: 250px; }
        .search-box input {
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
        }
        
        .table-container {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #f7fafc;
            color: #2d3748;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            border-bottom: 2px solid #e2e8f0;
            position: relative;
        }
        .sort-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
            margin-left: 5px;
            padding: 2px 5px;
            border-radius: 3px;
            transition: all 0.2s ease;
        }
        .sort-btn:hover {
            background: #e2e8f0;
        }
        .sort-btn.asc::after {
            content: " ↑";
            color: #10b981;
        }
        .sort-btn.desc::after {
            content: " ↓";
            color: #ef4444;
        }
        
        /* 新鲜数据标识样式 */
        .fresh-indicator {
            margin-left: 5px;
            font-size: 12px;
            animation: pulse 2s infinite;
        }
        
        .tab-btn.fresh-data {
            border: 2px solid #10b981;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
        }
        
        .tab-btn.recent-data {
            border: 2px solid #f59e0b;
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            box-shadow: 0 0 10px rgba(245, 158, 11, 0.3);
        }
        
        .tab-btn.old-data {
            border: 2px solid #ef4444;
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        td {
            padding: 15px;
            border-bottom: 1px solid #e2e8f0;
            color: #4a5568;
        }
        tr:hover { background: #f7fafc; }
        .token-symbol { 
            font-weight: 600; 
            color: #667eea; 
            cursor: pointer;
            text-decoration: none;
        }
        .token-symbol:hover { color: #5a67d8; text-decoration: underline; }
        .positive-change { color: #48bb78; font-weight: 600; }
        .loading { text-align: center; padding: 50px; }
        .no-data { text-align: center; padding: 50px; color: #718096; }
        
        /* 拉黑按钮样式 */
        .blacklist-btn {
            background: #ef4444;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .blacklist-btn:hover {
            background: #dc2626;
            transform: scale(1.05);
        }
        .blacklist-btn:active {
            transform: scale(0.95);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 多周期Token筛选 - 全市场版</h1>
            <p id="updateTime">加载中...</p>
            <div style="margin-top: 15px;">
                <a href="/monitor" style="color: #667eea; text-decoration: none; font-weight: 600; padding: 8px 16px; background: #f0f4ff; border-radius: 8px; transition: all 0.3s ease; margin-right: 10px;">
                    📊 监控Token列表
                </a>
                <a href="/open-interest" style="color: #667eea; text-decoration: none; font-weight: 600; padding: 8px 16px; background: #f0f4ff; border-radius: 8px; transition: all 0.3s ease; margin-right: 10px;">
                    📈 合约持仓量
                </a>
                <a href="/token-config" style="color: #667eea; text-decoration: none; font-weight: 600; padding: 8px 16px; background: #f0f4ff; border-radius: 8px; transition: all 0.3s ease;">
                    ⚙️ 修改Token监控
                </a>
            </div>
        </div>
        
        <!-- 市场类型选项卡 -->
        <div class="market-tabs">
            <button class="tab-btn active" data-market="bn">📈 BN市场</button>
            <button class="tab-btn" data-market="ok">🟠 OK市场</button>
            <button class="tab-btn" data-market="us">🇺🇸 US股票</button>
            <button class="tab-btn" data-market="hk">🇭🇰 港股股票</button>
            <button class="tab-btn" data-market="a">🇨🇳 A股股票</button>
            <button class="tab-btn" data-market="metal">🥇 贵金属</button>
            <button class="tab-btn" data-market="zero_reversal">🕛 零点反包</button>
        </div>
        
        <!-- 任务状态 -->
        <div class="task-status">
            <h3 style="margin-bottom: 15px; color: #2d3748;">⏰ 自动化任务状态</h3>
            <div class="status-row">
                <span class="status-label">配置:</span>
                <span class="status-value" id="configTopN">Top100</span>
            </div>
            <div class="status-row">
                <span class="status-label">状态:</span>
                <span class="status-value" id="taskStatus">检查中...</span>
            </div>
            <div class="status-row">
                <span class="status-label">消息:</span>
                <span class="status-value" id="taskMessage">-</span>
            </div>
            <div class="status-row">
                <span class="status-label">上次运行:</span>
                <span class="status-value" id="lastRun">-</span>
            </div>
            <div class="status-row">
                <span class="status-label">下次运行:</span>
                <span class="status-value" id="nextRun">每天 08:00</span>
            </div>
            <div class="status-row">
                <span class="status-label">操作:</span>
                <button class="trigger-btn" onclick="triggerTask()" id="triggerBtn">
                    🔄 手动触发任务
                </button>
            </div>
        </div>
        
        <!-- 周期选项卡 -->
        <div class="period-tabs">
            <!-- 今日反包（股票市场，最左侧） -->
            <div class="us-only" data-period="today" data-market="us" style="display:none; position:relative;">
                <button class="tab-btn" onclick="loadTodayReversalData(); toggleTodayReversalMenu(event);" style="margin:0;">今日反包<span class="data-indicator" id="indicator-today-us"></span></button>
                <div id="todayReversalMenu" style="display:none; position:absolute; top:100%; left:0; margin-top:5px; background:white; border:2px solid #e2e8f0; border-radius:8px; box-shadow:0 4px 6px rgba(0,0,0,0.1); z-index:1000; min-width:200px;">
                    <button onclick="showWatchlistManager(); closeTodayReversalMenu();" style="width:100%; padding:12px 20px; border:none; background:white; text-align:left; cursor:pointer; font-weight:600; color:#2d3748; border-bottom:1px solid #e2e8f0; border-radius:8px 8px 0 0;" onmouseover="this.style.background='#f7fafc'" onmouseout="this.style.background='white'">⭐ 特别关注管理</button>
                    <button onclick="showBlacklistManager(); closeTodayReversalMenu();" style="width:100%; padding:12px 20px; border:none; background:white; text-align:left; cursor:pointer; font-weight:600; color:#2d3748; border-radius:0 0 8px 8px;" onmouseover="this.style.background='#f7fafc'" onmouseout="this.style.background='white'">🚫 黑名单管理</button>
                </div>
            </div>
            <!-- BN和OK市场的周期按钮 -->
            <button class="tab-btn active bn-only ok-only" data-period="1日">1日K线<span class="data-indicator" id="indicator-1日"></span></button>
            <button class="tab-btn bn-only" data-period="3日" data-market="bn">3日K线<span class="data-indicator" id="indicator-3日-bn"></span></button>
            <button class="tab-btn bn-only" data-period="周" data-market="bn">周K线<span class="data-indicator" id="indicator-周-bn"></span></button>
            <button class="tab-btn ok-only" data-period="2日" data-market="ok" style="display:none;">2日K线<span class="data-indicator" id="indicator-2日-ok"></span></button>
            <button class="tab-btn ok-only" data-period="3日" data-market="ok" style="display:none;">3日K线<span class="data-indicator" id="indicator-3日-ok"></span></button>
            <button class="tab-btn ok-only" data-period="5日" data-market="ok" style="display:none;">5日K线<span class="data-indicator" id="indicator-5日-ok"></span></button>
            <button class="tab-btn ok-only" data-period="周" data-market="ok" style="display:none;">周K线<span class="data-indicator" id="indicator-周-ok"></span></button>
            <!-- 特别关注和黑名单管理（最右侧） -->
            <button class="tab-btn" onclick="showWatchlistManager()" style="background: #10b981; margin-left: auto;">⭐ 特别关注</button>
            <button class="tab-btn" onclick="showBlacklistManager()" style="background: #ef4444;">🚫 黑名单管理</button>
        </div>
        
        
        <div class="controls">
            <div class="search-box" style="position: relative; display: flex; gap: 8px;">
                <div style="flex: 1; position: relative;">
                    <input type="text" id="searchInput" placeholder="🔍 搜索标的（输入代码搜索并添加到特别关注）..." autocomplete="off" style="width: 100%;">
                    <div id="searchResults" style="display:none; position:absolute; top:100%; left:0; right:0; background:white; border:2px solid #e2e8f0; border-radius:8px; margin-top:5px; max-height:300px; overflow-y:auto; z-index:1000; box-shadow:0 4px 6px rgba(0,0,0,0.1);"></div>
                </div>
                <select id="webhookSelect" style="padding: 8px 12px; border: 2px solid #e2e8f0; border-radius: 8px; cursor: pointer; font-size: 14px; background: white; margin-right: 10px;">
                    <option value="core2">Core2 (默认)</option>
                    <option value="core1">Core1</option>
                </select>
                <button id="addButton" onclick="addSymbolDirectly()" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; white-space: nowrap;" onmouseover="this.style.background='#5568d3'" onmouseout="this.style.background='#667eea'">添加</button>
            </div>
        </div>
        
        <!-- 特别关注管理模态框 -->
        <div id="watchlistModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000; justify-content:center; align-items:center;">
            <div style="background:white; border-radius:15px; padding:30px; max-width:800px; max-height:80vh; overflow-y:auto; box-shadow:0 20px 60px rgba(0,0,0,0.3);">
                <h2 style="margin-bottom:20px; color:#2d3748;">⭐ 特别关注管理</h2>
                
                <div style="margin-bottom:20px;">
                    <div style="display:flex; gap:10px; margin-bottom:15px;">
                        <button class="tab-btn active" onclick="switchWatchlistMarket('us')" data-wl-market="us">US股票</button>
                        <button class="tab-btn" onclick="switchWatchlistMarket('hk')" data-wl-market="hk">港股</button>
                        <button class="tab-btn" onclick="switchWatchlistMarket('a')" data-wl-market="a">A股</button>
                    </div>
                    
                    <div id="watchlistContent"></div>
                </div>
                
                <div style="text-align:right;">
                    <button class="btn" onclick="closeWatchlistManager()" style="background:#718096;">关闭</button>
                </div>
            </div>
        </div>
        
        <!-- 黑名单管理模态框 -->
        <div id="blacklistModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000; justify-content:center; align-items:center;">
            <div style="background:white; border-radius:15px; padding:30px; max-width:800px; max-height:80vh; overflow-y:auto; box-shadow:0 20px 60px rgba(0,0,0,0.3);">
                <h2 style="margin-bottom:20px; color:#2d3748;">🚫 黑名单管理</h2>
                
                <div style="margin-bottom:20px;">
                    <div style="display:flex; gap:10px; margin-bottom:15px;">
                        <button class="tab-btn active" onclick="switchBlacklistMarket('bn')" data-bl-market="bn">BN市场</button>
                        <button class="tab-btn" onclick="switchBlacklistMarket('ok')" data-bl-market="ok">OK市场</button>
                        <button class="tab-btn" onclick="switchBlacklistMarket('us')" data-bl-market="us">US股票</button>
                        <button class="tab-btn" onclick="switchBlacklistMarket('hk')" data-bl-market="hk">港股</button>
                        <button class="tab-btn" onclick="switchBlacklistMarket('a')" data-bl-market="a">A股</button>
                        <button class="tab-btn" onclick="switchBlacklistMarket('metal')" data-bl-market="metal">贵金属</button>
                    </div>
                    
                    <div id="blacklistContent"></div>
                </div>
                
                <div style="text-align:right;">
                    <button class="btn" onclick="closeBlacklistManager()" style="background:#718096;">关闭</button>
                </div>
            </div>
        </div>
        
        <div class="table-container">
            <div id="loading" class="loading">正在加载数据...</div>
            <div id="noData" class="no-data" style="display:none;">暂无数据</div>
            <table id="dataTable" style="display:none;">
                <thead id="tableHead">
                    <tr>
                        <th>排名</th><th>Symbol</th><th>T-1日期</th><th>T-2价格</th><th>T-1价格</th>
                        <th>成交量增长 <button class="sort-btn desc" onclick="sortTable('volume_growth_rate_pct')" title="点击排序">↕️</button></th>
                        <th>涨幅 <button class="sort-btn" onclick="sortTable('change_pct')" title="点击排序">↕️</button></th>
                        <th id="turnoverColumn" style="display:none;">交易额 <button class="sort-btn" onclick="sortTable('turnover_t1')" title="点击排序">↕️</button></th>
                        <th id="marketCapColumn" style="display:none;">市值 <button class="sort-btn" onclick="sortTable('market_cap')" title="点击排序">↕️</button></th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        let allData = {
            bn: {},
            ok: {},
            us: {},
            hk: {},
            a: {},
            zero_reversal: {}
        };
        let currentMarket = 'bn';
        let currentPeriod = '1日';
        let currentSortField = 'volume_growth_rate_pct'; // 默认按成交量增长排序
        let currentSortOrder = 'desc'; // 'asc' 或 'desc'
        
        // 加载任务状态
        async function loadTaskStatus() {
            try {
                const response = await fetch('/api/status');
                const status = await response.json();
                
                // 更新配置信息
                if (status.config && status.config.top_n) {
                    document.getElementById('configTopN').textContent = `Top${status.config.top_n} 代币`;
                }
                
                document.getElementById('taskStatus').textContent = status.status;
                document.getElementById('taskStatus').className = 'status-value status-' + status.status.toLowerCase();
                document.getElementById('taskMessage').textContent = status.message;
                document.getElementById('lastRun').textContent = status.last_run || '未运行';
                
                // 如果正在运行，禁用触发按钮
                const triggerBtn = document.getElementById('triggerBtn');
                triggerBtn.disabled = status.status === '运行中';
            } catch (error) {
                console.error('加载状态失败:', error);
            }
        }
        
        // 手动触发任务
        async function triggerTask() {
            if (!confirm('确定要手动触发数据更新任务吗？\\n这将获取最新BN市场、OK市场K线数据并重新筛选，以及US股票、港股、A股反包检测。\\n\\n预计耗时：30-40分钟')) {
                return;
            }
            
            try {
                const response = await fetch('/api/trigger');
                const result = await response.json();
                alert(result.message);
                loadTaskStatus();
            } catch (error) {
                alert('触发失败: ' + error.message);
            }
        }
        

        // 加载数据
        async function loadData() {
            try {
                const dataResponse = await fetch('/api/data');
                const result = await dataResponse.json();
                
                if (result.success) {
                    // 更新BN数据（合并现货和合约）
                    if (result.bn && result.bn.success) {
                        allData.bn = result.bn.sheets;
                        console.log('BN数据加载成功:', Object.keys(allData.bn));
                    }
                    
                    // 更新OK数据（合并现货和合约）
                    if (result.ok && result.ok.success) {
                        allData.ok = result.ok.sheets;
                        console.log('OK数据加载成功:', Object.keys(allData.ok));
                    }
                    
                    // 更新US数据（美股反包）
                    if (result.us && result.us.success) {
                        allData.us = result.us.sheets;
                        console.log('US数据加载成功:', Object.keys(allData.us));
                    }
                    
                    // 更新HK数据（港股反包）
                    if (result.hk && result.hk.success) {
                        allData.hk = result.hk.sheets;
                        console.log('HK数据加载成功:', Object.keys(allData.hk));
                    }
                    
                    // 更新A股数据（A股反包）
                    if (result.a && result.a.success) {
                        allData.a = result.a.sheets;
                        console.log('A股数据加载成功:', Object.keys(allData.a));
                    }
                    
                    // 更新贵金属数据（贵金属反包）
                    if (result.metal && result.metal.success) {
                        allData.metal = result.metal.sheets;
                        console.log('贵金属数据加载成功:', Object.keys(allData.metal));
                    }
                    
                    // 更新零点反包数据
                    if (result.zero_reversal && result.zero_reversal.success) {
                        allData.zero_reversal = result.zero_reversal.sheets;
                        console.log('零点反包数据加载成功:', Object.keys(allData.zero_reversal));
                    }
                    
                    // 更新显示时间（六个市场）
                    const bnTime = result.bn && result.bn.update_time ? result.bn.update_time : '';
                    const okTime = result.ok && result.ok.update_time ? result.ok.update_time : '';
                    const usTime = result.us && result.us.update_time ? result.us.update_time : '';
                    const hkTime = result.hk && result.hk.update_time ? result.hk.update_time : '';
                    const aTime = result.a && result.a.update_time ? result.a.update_time : '';
                    const zeroTime = result.zero_reversal && result.zero_reversal.update_time ? result.zero_reversal.update_time : '';
                    
                    let updateTimeText = '';
                    const times = [];
                    if (bnTime) times.push(`BN市场: ${bnTime}`);
                    if (okTime) times.push(`OK市场: ${okTime}`);
                    if (usTime) times.push(`US股票: ${usTime}`);
                    if (hkTime) times.push(`港股股票: ${hkTime}`);
                    if (aTime) times.push(`A股股票: ${aTime}`);
                    if (zeroTime) times.push(`零点反包: ${zeroTime}`);
                    
                    if (times.length > 0) {
                        updateTimeText = times.join(' | ');
                    } else {
                        updateTimeText = '数据加载中...';
                    }
                    
                    document.getElementById('updateTime').textContent = updateTimeText;
                    
                    // 加载当前市场和周期数据
                    if (currentMarket === 'zero_reversal') {
                        // 零点反包市场：更新周期选项卡后再加载数据
                        updatePeriodTabs(currentMarket);
                        // updatePeriodTabs 中已经调用了 loadMarketData，这里不需要再调用
                    } else {
                        loadPeriodData(currentPeriod);
                    }
                    updateDataIndicators(); // 更新数据标识
                } else {
                    document.getElementById('loading').innerHTML = 
                        `<p style="color: red;">❌ ${result.message}</p>`;
                }
            } catch (error) {
                document.getElementById('loading').innerHTML = 
                    `<p style="color: red;">❌ 加载失败: ${error.message}</p>`;
            }
        }
        
        function loadPeriodData(period) {
            currentPeriod = period;
            console.log('加载周期数据:', period, '市场:', currentMarket);
            
            // 如果是零点反包市场，从 zero_reversal 数据中加载指定周期的数据
            if (currentMarket === 'zero_reversal') {
                const tokens = allData.zero_reversal && allData.zero_reversal[period] ? allData.zero_reversal[period] : [];
                console.log(`零点反包 ${period} 数据数量:`, tokens.length);
                displayTokens(tokens);
                return;
            }
            
            const tokens = allData[currentMarket][period] || [];
            console.log('获取到Token数量:', tokens.length);
            displayTokens(tokens);
        }
        
        // 加载零点反包数据
        function loadZeroReversalData() {
            currentPeriod = 'zero_reversal';
            
            // 合并所有周期的零点反包数据
            const allZeroReversalTokens = [];
            if (allData.zero_reversal) {
                for (const [sheetName, tokens] of Object.entries(allData.zero_reversal)) {
                    tokens.forEach(token => {
                        token.interval = sheetName; // 添加周期信息
                        allZeroReversalTokens.push(token);
                    });
                }
            }
            
            console.log('零点反包数据数量:', allZeroReversalTokens.length);
            displayTokens(allZeroReversalTokens);
        }
        

        function updatePeriodTabs(market) {
            // 隐藏所有周期选项卡（包括容器）
            document.querySelectorAll('.period-tabs .bn-only').forEach(btn => {
                btn.style.display = 'none';
            });
            document.querySelectorAll('.period-tabs .ok-only').forEach(btn => {
                btn.style.display = 'none';
            });
            document.querySelectorAll('.period-tabs .us-only').forEach(btn => {
                btn.style.display = 'none';
            });
            
            // 移除所有按钮的active状态（除了特别关注和黑名单管理按钮）
            document.querySelectorAll('.period-tabs .tab-btn').forEach(btn => {
                // 跳过特别关注和黑名单管理按钮
                if (btn.onclick && (btn.onclick.toString().includes('showWatchlistManager') || btn.onclick.toString().includes('showBlacklistManager'))) {
                    return;
                }
                btn.classList.remove('active');
            });
            
            // 根据市场类型显示相应的周期选项卡
            if (market === 'bn') {
                // BN市场：显示1日、3日、周
                document.querySelectorAll('.period-tabs .bn-only').forEach(btn => {
                    btn.style.display = 'block';
                });
                // 1日选项卡始终显示
                const day1Btn = document.querySelector('[data-period="1日"]');
                if (day1Btn) {
                    day1Btn.style.display = 'block';
                    day1Btn.classList.add('active');
                }
                currentPeriod = '1日';
            } else if (market === 'ok') {
                // OKX市场：显示1日、2日、3日、5日、周
                document.querySelectorAll('.period-tabs .ok-only').forEach(btn => {
                    btn.style.display = 'block';
                });
                // 1日选项卡始终显示
                const day1Btn = document.querySelector('[data-period="1日"]');
                if (day1Btn) {
                    day1Btn.style.display = 'block';
                    day1Btn.classList.add('active');
                }
                currentPeriod = '1日';
            } else if (market === 'us') {
                // US股票市场：只显示今日反包（不显示1日K线）
                document.querySelectorAll('.period-tabs .us-only').forEach(btn => {
                    btn.style.display = 'block';
                });
                // 确保1日K线按钮隐藏
                const day1Btn = document.querySelector('[data-period="1日"]');
                if (day1Btn) {
                    day1Btn.style.display = 'none';
                }
                const todayBtn = document.querySelector('[data-period="today"] button');
                if (todayBtn) {
                    todayBtn.classList.add('active');
                }
                currentPeriod = 'today';
            } else if (market === 'hk' || market === 'a') {
                // 港股/A股市场：只显示今日反包（不显示1日K线）
                document.querySelectorAll('.period-tabs .us-only').forEach(btn => {
                    btn.style.display = 'block';
                });
                // 确保1日K线按钮隐藏
                const day1Btn = document.querySelector('[data-period="1日"]');
                if (day1Btn) {
                    day1Btn.style.display = 'none';
                }
                const todayBtn = document.querySelector('[data-period="today"] button');
                if (todayBtn) {
                    todayBtn.classList.add('active');
                }
                currentPeriod = 'today';
            } else if (market === 'zero_reversal') {
                // 零点反包市场：显示所有周期选项卡（1日、2日、3日、5日、周、月）
                // 隐藏BN和OK市场的周期按钮
                document.querySelectorAll('.period-tabs .bn-only, .period-tabs .ok-only, .period-tabs .us-only').forEach(btn => {
                    btn.style.display = 'none';
                });
                
                // 显示零点反包的周期按钮
                const zeroPeriods = ['1日', '2日', '3日', '5日', '周', '月'];
                zeroPeriods.forEach(period => {
                    // 检查是否有该周期的数据
                    if (allData.zero_reversal && allData.zero_reversal[period] && allData.zero_reversal[period].length > 0) {
                        // 创建或显示周期按钮
                        let periodBtn = document.querySelector(`[data-period="${period}"][data-market="zero_reversal"]`);
                        if (!periodBtn) {
                            // 如果按钮不存在，创建一个
                            periodBtn = document.createElement('button');
                            periodBtn.className = 'tab-btn';
                            periodBtn.setAttribute('data-period', period);
                            periodBtn.setAttribute('data-market', 'zero_reversal');
                            const periodText = period === '周' ? '周K线' : period === '月' ? '月K线' : period + 'K线';
                            periodBtn.innerHTML = `${periodText}<span class="data-indicator" id="indicator-${period}-zero"></span>`;
                            
                            // 添加点击事件
                            periodBtn.addEventListener('click', (e) => {
                                e.stopPropagation();
                                document.querySelectorAll('.period-tabs .tab-btn').forEach(b => b.classList.remove('active'));
                                periodBtn.classList.add('active');
                                loadPeriodData(period);
                                document.getElementById('searchInput').value = '';
                            });
                            
                            // 插入到周期选项卡中（在特别关注按钮之前）
                            const watchlistBtn = document.querySelector('.period-tabs .tab-btn[onclick*="showWatchlistManager"]');
                            if (watchlistBtn) {
                                watchlistBtn.parentNode.insertBefore(periodBtn, watchlistBtn);
                            } else {
                                document.querySelector('.period-tabs').appendChild(periodBtn);
                            }
                        }
                        periodBtn.style.display = 'block';
                    }
                });
                
                // 默认激活第一个有数据的周期
                const firstPeriod = zeroPeriods.find(p => allData.zero_reversal && allData.zero_reversal[p] && allData.zero_reversal[p].length > 0);
                if (firstPeriod) {
                    const firstBtn = document.querySelector(`[data-period="${firstPeriod}"][data-market="zero_reversal"]`);
                    if (firstBtn) {
                        firstBtn.classList.add('active');
                    }
                    currentPeriod = firstPeriod;
                } else {
                    // 如果没有数据，直接加载所有数据
                    loadZeroReversalData();
                    return;
                }
            } else if (market === 'bn-gainers') {
                // BN涨幅榜：隐藏所有周期选项卡
                const day1Btn = document.querySelector('[data-period="1日"]');
                if (day1Btn) {
                    day1Btn.style.display = 'none';
                }
            }
        }
        
        function loadMarketData(market) {
            currentMarket = market;
            if (market === 'zero_reversal') {
                loadZeroReversalData();
            } else {
                loadPeriodData(currentPeriod);
            }
            updateDataIndicators(); // 更新数据标识
        }
        
        // 排序功能
        function sortTable(field) {
            // 如果点击的是同一个字段,切换排序顺序
            if (currentSortField === field) {
                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortField = field;
                currentSortOrder = 'desc'; // 默认降序
            }
            
            // 更新按钮状态
            updateSortButtons();
            
            // 重新显示数据
            loadPeriodData(currentPeriod);
        }
        
        function updateSortButtons() {
            // 清除所有按钮的排序状态
            document.querySelectorAll('.sort-btn').forEach(btn => {
                btn.classList.remove('asc', 'desc');
            });
            
            // 设置当前排序按钮的状态
            if (currentSortField) {
                const buttons = document.querySelectorAll('.sort-btn');
                buttons.forEach(btn => {
                    if (btn.onclick.toString().includes(currentSortField)) {
                        btn.classList.add(currentSortOrder);
                    }
                });
            }
        }
        
        // 更新数据新鲜度标识 - 随机Token采样验证
        function updateDataIndicators() {
            console.log('=== 开始更新数据新鲜度标识（随机采样版） ===');
            
            // 清除所有tab的新鲜数据标识
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('fresh-data');
                const existingIndicator = btn.querySelector('.fresh-indicator');
                if (existingIndicator) {
                    existingIndicator.remove();
                }
            });
            
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            console.log('今天:', today.toDateString());
            
            const currentMarketData = allData[currentMarket];
            if (!currentMarketData) {
                console.log(`${currentMarket} 市场没有数据`);
                return;
            }
            
            // 简化的周期配置
            let periods = [];
            if (currentMarket === 'bn') {
                periods = ['1日', '3日', '周'];
            } else if (currentMarket === 'ok') {
                periods = ['1日', '2日', '3日', '5日', '周'];
            } else if (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a' || currentMarket === 'metal') {
                periods = ['today'];
            }
            const periodDaysMap = {'1日': 1, '2日': 2, '3日': 3, '5日': 5, '周': 7};
            
            // 为每个周期计算并应用标识 - 随机选择Token进行验证
            periods.forEach(period => {
                const periodData = currentMarketData[period];
                if (!periodData || periodData.length === 0) {
                    console.log(`${currentMarket} ${period} 没有数据`);
                    return;
                }
                
                // 随机选择一个Token进行验证
                const randomIndex = Math.floor(Math.random() * periodData.length);
                const randomToken = periodData[randomIndex];
                
                if (!randomToken || !randomToken.T_minus_1_date) {
                    console.log(`${currentMarket} ${period} 随机选择的Token没有T_minus_1_date`);
                    return;
                }
                
                // 使用随机选择的Token的T-1日期
                const tMinus1Date = new Date(randomToken.T_minus_1_date);
                tMinus1Date.setHours(0, 0, 0, 0);
                
                const periodDays = periodDaysMap[period];
                const calculatedTDate = new Date(tMinus1Date);
                calculatedTDate.setDate(calculatedTDate.getDate() + periodDays);
                calculatedTDate.setHours(0, 0, 0, 0);
                
                // 判断是否等于今天
                const isToday = calculatedTDate.getTime() === today.getTime();
                
                // 只显示绿色或白色
                const indicatorType = isToday ? 'fresh-data' : '';
                const indicatorText = isToday ? '🟢' : '';
                
                const tMinus1DateStr = tMinus1Date.toISOString().split('T')[0];
                const tDateStr = calculatedTDate.toISOString().split('T')[0];
                const todayStr = today.toISOString().split('T')[0];
                console.log(`${currentMarket} ${period}: 随机Token=${randomToken.symbol}, T-1=${tMinus1DateStr}, +${periodDays}天=${tDateStr}, 今天=${todayStr}, 是否今天=${isToday}, 颜色=${indicatorText}`);
                
                // 应用标识 - 使用更精确的选择器
                let tabBtn;
                if (period === '1日') {
                    // 1日K线没有data-market属性，直接选择
                    tabBtn = document.querySelector(`[data-period="${period}"]`);
                } else {
                    // 其他周期使用data-market属性
                    tabBtn = document.querySelector(`[data-period="${period}"][data-market="${currentMarket}"]`);
                }
                
                if (tabBtn && tabBtn.style.display !== 'none') {
                    if (isToday) {
                        tabBtn.classList.add(indicatorType);
                        
                        const indicatorElement = document.createElement('span');
                        indicatorElement.className = 'fresh-indicator';
                        indicatorElement.textContent = indicatorText;
                        indicatorElement.title = `${currentMarket.toUpperCase()}${period}: 随机Token=${randomToken.symbol}, T=${tDateStr} (今天)`;
                        tabBtn.appendChild(indicatorElement);
                    }
                    
                    console.log(`✅ 应用标识到 ${period} tab: ${indicatorText} (${currentMarket}, 随机Token: ${randomToken.symbol})`);
                } else {
                    console.log(`⏭️ 跳过隐藏的${period} tab按钮 (${currentMarket})`);
                }
            });
            
            console.log('=== 数据新鲜度标识更新完成（随机采样版） ===');
        }
        
        
        function displayTokens(tokens) {
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            document.getElementById('loading').style.display = 'none';
            
            // 显示/隐藏交易额列和市值列（US、港股、A股市场显示，贵金属不显示）
            const turnoverColumn = document.getElementById('turnoverColumn');
            const marketCapColumn = document.getElementById('marketCapColumn');
            if (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a') {
                turnoverColumn.style.display = 'table-cell';
                marketCapColumn.style.display = 'table-cell';
            } else {
                turnoverColumn.style.display = 'none';
                marketCapColumn.style.display = 'none';
            }
            
            if (tokens.length === 0) {
                document.getElementById('noData').style.display = 'block';
                document.getElementById('dataTable').style.display = 'none';
                return;
            }
            
            document.getElementById('noData').style.display = 'none';
            document.getElementById('dataTable').style.display = 'table';
            
            // 根据当前排序设置排序数据
            let sorted;
            if (currentSortField) {
                sorted = [...tokens].sort((a, b) => {
                    // 字段名映射：处理US市场和其他市场的字段名差异
                    let actualFieldA = currentSortField;
                    let actualFieldB = currentSortField;
                    
                    if (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a') {
                        // US、港股、A股市场字段名映射
                        const fieldMapping = {
                            'volume_growth_rate_pct': 'volume_increase_pct',  // 成交量增长
                            'change_pct': 't1_change_pct'  // 涨幅
                        };
                        actualFieldA = fieldMapping[currentSortField] || currentSortField;
                        actualFieldB = fieldMapping[currentSortField] || currentSortField;
                    } else if (currentMarket === 'metal') {
                        // 贵金属市场字段名映射
                        const fieldMapping = {
                            'volume_growth_rate_pct': 'price_change_increase_pct',  // 价格变化增幅（替代成交量增长）
                            'change_pct': 't1_change_pct'  // 涨幅
                        };
                        actualFieldA = fieldMapping[currentSortField] || currentSortField;
                        actualFieldB = fieldMapping[currentSortField] || currentSortField;
                    }
                    
                    const aValue = a[actualFieldA];
                    const bValue = b[actualFieldB];
                    const comparison = aValue - bValue;
                    return currentSortOrder === 'asc' ? comparison : -comparison;
                });
            } else if (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a') {
                // US、港股、A股市场默认按交易额倒序排列
                sorted = [...tokens].sort((a, b) => b.turnover_t1 - a.turnover_t1);
            } else if (currentMarket === 'metal') {
                // 贵金属市场默认按价格变化增幅倒序排列
                sorted = [...tokens].sort((a, b) => (b.price_change_increase_pct || 0) - (a.price_change_increase_pct || 0));
            } else {
                // 默认按成交量排序（降序）
                sorted = [...tokens].sort((a, b) => 
                    b.T_minus_1_quote_asset_volume - a.T_minus_1_quote_asset_volume
                );
            }
            
            sorted.forEach((token, index) => {
                const row = tbody.insertRow();
                row.insertCell().innerHTML = `<strong>${index + 1}</strong>`;
                
                const symbolCell = row.insertCell();
                // 根据市场类型设置链接
                let linkUrl = '';
                if (currentMarket === 'us') {
                    linkUrl = `https://www.google.com/finance/quote/${token.symbol}:NASDAQ`;
                } else if (currentMarket === 'hk') {
                    linkUrl = `https://www.google.com/finance/quote/${token.symbol}:HKG`;
                } else if (currentMarket === 'a') {
                    linkUrl = `https://www.google.com/finance/quote/${token.symbol}:SHA`;
                } else if (currentMarket === 'metal') {
                    // 贵金属链接到Google Finance（去掉/USD后缀）
                    const symbol = token.symbol.replace('/USD', '');
                    linkUrl = `https://www.google.com/finance/quote/${symbol}-USD`;
                } else {
                    linkUrl = `https://www.binance.com/zh-CN/trade/${token.symbol}`;
                }
                // 如果是特别关注，添加标记和背景色
                const isWatched = token.is_watched || false;
                const watchedMark = isWatched ? '<span style="color:#f59e0b; margin-left:5px;">⭐</span>' : '';
                const rowStyle = isWatched ? 'background: #fef3c7;' : '';
                if (rowStyle) {
                    row.style.cssText = rowStyle;
                }
                symbolCell.innerHTML = `<a href="${linkUrl}" target="_blank" class="token-symbol">${token.symbol}${watchedMark}</a>`;
                
                // T-1日期
                const t1Date = (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a' || currentMarket === 'metal') ? 
                    (token.data_date || 'N/A') : 
                    (token.T_minus_1_date ? token.T_minus_1_date.split(' ')[0] : 'N/A');
                const dateCell = row.insertCell();
                dateCell.textContent = t1Date;
                dateCell.style.fontSize = '12px';
                dateCell.style.color = '#718096';
                
                // T-2价格
                const t2Price = (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a' || currentMarket === 'metal') ? token.close_t2 : token.T_minus_2_close;
                row.insertCell().textContent = `$${t2Price.toFixed(4)}`;
                
                // T-1价格
                const t1Price = (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a' || currentMarket === 'metal') ? token.close_t1 : token.T_minus_1_close;
                row.insertCell().textContent = `$${t1Price.toFixed(4)}`;
                
                // 成交量增长（贵金属显示价格变化增幅）
                let volGrowth;
                if (currentMarket === 'metal') {
                    volGrowth = token.price_change_increase_pct || 0;
                } else if (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a') {
                    volGrowth = token.volume_increase_pct;
                } else {
                    volGrowth = token.volume_growth_rate_pct;
                }
                const volCell = row.insertCell();
                volCell.innerHTML = `<span class="positive-change">+${volGrowth.toFixed(1)}%</span>`;
                if (currentMarket === 'metal') {
                    volCell.title = '价格变化增幅（替代成交量增幅）';
                }
                
                // 涨幅
                const changePercent = (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a' || currentMarket === 'metal') ? token.t1_change_pct : token.T_minus_1_change_pct;
                const priceCell = row.insertCell();
                priceCell.innerHTML = `<span class="positive-change">+${changePercent.toFixed(2)}%</span>`;
                
                // 交易额和市值（US、港股、A股市场，贵金属不显示）
                if (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a') {
                    row.insertCell().textContent = formatNumber(token.turnover_t1);
                    
                    // 市值
                    const marketCapCell = row.insertCell();
                    if (token.market_cap && token.market_cap > 0) {
                        marketCapCell.textContent = formatNumber(token.market_cap);
                        marketCapCell.title = token.name || token.symbol;  // 鼠标悬停显示公司名称
                    } else {
                        marketCapCell.textContent = 'N/A';
                        marketCapCell.style.color = '#cbd5e0';
                    }
                }
                
                // 操作按钮（拉黑）
                const actionCell = row.insertCell();
                const blacklistBtn = document.createElement('button');
                blacklistBtn.className = 'blacklist-btn';
                blacklistBtn.textContent = '🚫 拉黑';
                blacklistBtn.title = `将 ${token.symbol} 加入黑名单`;
                blacklistBtn.onclick = () => blacklistSymbol(token.symbol);
                actionCell.appendChild(blacklistBtn);
            });
        }
        
        function formatNumber(num) {
            if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
            if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
            if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
            return num.toFixed(2);
        }
        
        function refreshData() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('dataTable').style.display = 'none';
            loadData();
            loadTaskStatus();
        }
        
        // 拉黑标的
        async function blacklistSymbol(symbol) {
            if (!confirm(`确定要将 ${symbol} 加入${currentMarket.toUpperCase()}市场黑名单吗？\\n\\n加入后将不再显示该标的。`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/blacklist/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        market: currentMarket,
                        symbol: symbol
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`✓ ${result.message}\\n\\n刷新页面后生效。`);
                    // 刷新数据
                    refreshData();
                } else {
                    alert(`✗ 拉黑失败: ${result.message}`);
                }
            } catch (error) {
                alert(`✗ 拉黑失败: ${error.message}`);
            }
        }
        
        // 显示黑名单管理器
        async function showBlacklistManager() {
            const modal = document.getElementById('blacklistModal');
            modal.style.display = 'flex';
            
            // 重置tab样式，设置当前市场为active（如果当前市场支持黑名单）
            document.querySelectorAll('[data-bl-market]').forEach(btn => {
                btn.classList.remove('active');
            });
            // 根据当前市场设置active，如果当前市场不支持黑名单，默认显示第一个
            const supportedMarkets = ['bn', 'ok', 'us', 'hk', 'a', 'metal'];
            const defaultMarket = supportedMarkets.includes(currentMarket) ? currentMarket : 'bn';
            const activeBtn = document.querySelector(`[data-bl-market="${defaultMarket}"]`);
            if (activeBtn) {
                activeBtn.classList.add('active');
                await loadBlacklistData(defaultMarket);
            }
        }
        
        // 关闭黑名单管理器
        function closeBlacklistManager() {
            document.getElementById('blacklistModal').style.display = 'none';
        }
        
        // 切换黑名单市场
        async function switchBlacklistMarket(market) {
            // 更新tab样式
            document.querySelectorAll('[data-bl-market]').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelector(`[data-bl-market="${market}"]`).classList.add('active');
            
            // 加载该市场的黑名单
            await loadBlacklistData(market);
        }
        
        // 加载黑名单数据
        async function loadBlacklistData(market) {
            try {
                const response = await fetch('/api/blacklist');
                const result = await response.json();
                
                if (result.success) {
                    const blacklist = result.blacklist[market] || [];
                    const content = document.getElementById('blacklistContent');
                    
                    if (blacklist.length === 0) {
                        content.innerHTML = '<p style="color:#718096; text-align:center; padding:20px;">该市场暂无黑名单标的</p>';
                    } else {
                        let html = '<div style="display:grid; gap:10px;">';
                        blacklist.forEach(symbol => {
                            html += `
                                <div style="display:flex; justify-content:space-between; align-items:center; padding:10px; background:#f7fafc; border-radius:8px;">
                                    <span style="font-weight:600; color:#2d3748;">${symbol}</span>
                                    <button onclick="removeFromBlacklist('${market}', '${symbol}')" style="background:#10b981; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px;">
                                        ✓ 解除拉黑
                                    </button>
                                </div>
                            `;
                        });
                        html += '</div>';
                        content.innerHTML = html;
                    }
                } else {
                    alert(`✗ 加载黑名单失败: ${result.message}`);
                }
            } catch (error) {
                alert(`✗ 加载黑名单失败: ${error.message}`);
            }
        }
        
        // 从黑名单移除
        async function removeFromBlacklist(market, symbol) {
            if (!confirm(`确定要将 ${symbol} 从${market.toUpperCase()}市场黑名单中移除吗？`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/blacklist/remove', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        market: market,
                        symbol: symbol
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`✓ ${result.message}`);
                    // 重新加载黑名单
                    await loadBlacklistData(market);
                    // 如果是当前市场，刷新数据
                    if (market === currentMarket) {
                        refreshData();
                    }
                } else {
                    alert(`✗ 移除失败: ${result.message}`);
                }
            } catch (error) {
                alert(`✗ 移除失败: ${error.message}`);
            }
        }
        
        // 搜索功能（仅对股票市场：us, hk, a）
        let searchTimeout = null;
        document.getElementById('searchInput').addEventListener('input', async (e) => {
            const term = e.target.value.trim();
            const searchResults = document.getElementById('searchResults');
            
            // 清除之前的定时器
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            
            // 如果是股票市场，显示搜索下拉框
            if ((currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a') && term.length >= 1) {
                // 延迟搜索，避免频繁请求
                searchTimeout = setTimeout(async () => {
                    try {
                        const response = await fetch(`/api/watchlist/search?market=${currentMarket}&q=${encodeURIComponent(term)}`);
                        const result = await response.json();
                        
                        if (result.success && result.results.length > 0) {
                            let html = '<div style="padding:10px;">';
                            result.results.forEach(item => {
                                html += `
                                    <div style="display:flex; justify-content:space-between; align-items:center; padding:8px; border-bottom:1px solid #e2e8f0; cursor:pointer; hover:background:#f7fafc;" 
                                         onmouseover="this.style.background='#f7fafc'" 
                                         onmouseout="this.style.background='white'"
                                         onclick="addToWatchlistFromSearch('${currentMarket}', '${item.symbol}')">
                                        <div>
                                            <strong style="color:#667eea;">${item.symbol}</strong>
                                            ${item.name ? `<span style="color:#718096; margin-left:10px;">${item.name}</span>` : ''}
                                        </div>
                                        <span style="color:#10b981; font-size:12px;">点击添加 ⭐ (使用当前选择的Webhook)</span>
                                    </div>
                                `;
                            });
                            html += '</div>';
                            searchResults.innerHTML = html;
                            searchResults.style.display = 'block';
                        } else {
                            searchResults.innerHTML = '<div style="padding:10px; color:#718096; text-align:center;">未找到匹配的标的</div>';
                            searchResults.style.display = 'block';
                        }
                    } catch (error) {
                        console.error('搜索失败:', error);
                        searchResults.style.display = 'none';
                    }
                }, 300);
            } else {
                // 非股票市场或搜索词为空，隐藏下拉框，使用本地过滤
                searchResults.style.display = 'none';
                if (term) {
            const tokens = allData[currentMarket][currentPeriod] || [];
                    const filtered = tokens.filter(t => t.symbol.toLowerCase().includes(term.toLowerCase()));
            displayTokens(filtered);
                } else {
                    displayTokens(allData[currentMarket][currentPeriod] || []);
                }
            }
        });
        
        // 点击外部关闭搜索下拉框
        document.addEventListener('click', (e) => {
            const searchInput = document.getElementById('searchInput');
            const searchResults = document.getElementById('searchResults');
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.style.display = 'none';
            }
        });
        
        // 从搜索结果添加到特别关注
        async function addToWatchlistFromSearch(market, symbol) {
            const webhookSelect = document.getElementById('webhookSelect');
            const webhookUrl = webhookSelect ? webhookSelect.value : 'core2';
            
            try {
                const response = await fetch('/api/watchlist/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        market: market,
                        symbol: symbol,
                        webhook_url: webhookUrl
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`✓ ${result.message}`);
                    // 清空搜索框
                    document.getElementById('searchInput').value = '';
                    document.getElementById('searchResults').style.display = 'none';
                    // 刷新数据
                    loadData();
                } else {
                    alert(`✗ 添加失败: ${result.message}`);
                }
            } catch (error) {
                alert(`✗ 添加失败: ${error.message}`);
            }
        }
        
        // 直接添加标的到特别关注（不进行搜索匹配）
        async function addSymbolDirectly() {
            // 只对股票市场（us, hk, a）有效
            if (currentMarket !== 'us' && currentMarket !== 'hk' && currentMarket !== 'a') {
                alert('✗ 此功能仅适用于股票市场（US、港股、A股）');
                return;
            }
            
            const searchInput = document.getElementById('searchInput');
            const webhookSelect = document.getElementById('webhookSelect');
            let symbol = searchInput.value.trim().toUpperCase();
            const webhookUrl = webhookSelect ? webhookSelect.value : 'core2';
            
            if (!symbol) {
                alert('✗ 请输入标的代码');
                return;
            }
            
            try {
                const response = await fetch('/api/watchlist/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        market: currentMarket,
                        symbol: symbol,
                        webhook_url: webhookUrl
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`✓ ${result.message}`);
                    // 清空搜索框
                    searchInput.value = '';
                    document.getElementById('searchResults').style.display = 'none';
                    // 刷新数据
                    loadData();
                } else {
                    alert(`✗ 添加失败: ${result.message}`);
                }
            } catch (error) {
                alert(`✗ 添加失败: ${error.message}`);
            }
        }
        
        // 显示特别关注管理器
        async function showWatchlistManager() {
            const modal = document.getElementById('watchlistModal');
            modal.style.display = 'flex';
            
            // 重置tab样式，设置当前市场为active
            document.querySelectorAll('[data-wl-market]').forEach(btn => {
                btn.classList.remove('active');
            });
            // 根据当前市场设置active
            const currentWatchlistMarket = (currentMarket === 'us' || currentMarket === 'hk' || currentMarket === 'a') ? currentMarket : 'us';
            document.querySelector(`[data-wl-market="${currentWatchlistMarket}"]`).classList.add('active');
            
            // 加载当前市场的特别关注
            await loadWatchlistData(currentWatchlistMarket);
        }
        
        // 关闭特别关注管理器
        function closeWatchlistManager() {
            document.getElementById('watchlistModal').style.display = 'none';
        }
        
        // 切换特别关注市场
        async function switchWatchlistMarket(market) {
            // 更新tab样式
            document.querySelectorAll('[data-wl-market]').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelector(`[data-wl-market="${market}"]`).classList.add('active');
            
            // 加载该市场的特别关注
            await loadWatchlistData(market);
        }
        
        // 加载特别关注数据
        async function loadWatchlistData(market) {
            try {
                const response = await fetch('/api/watchlist');
                const result = await response.json();
                
                if (result.success) {
                    const watchlist = result.watchlist[market] || [];
                    const content = document.getElementById('watchlistContent');
                    
                    if (watchlist.length === 0) {
                        content.innerHTML = '<p style="color:#718096; text-align:center; padding:20px;">该市场暂无特别关注的标的</p>';
                    } else {
                        let html = '<div style="display:grid; gap:10px;">';
                        watchlist.forEach(item => {
                            const symbol = typeof item === 'string' ? item : item.symbol;
                            const webhookUrl = typeof item === 'object' ? (item.webhook_url || 'core2') : 'core2';
                            const webhookLabel = webhookUrl === 'core1' ? 'Core1' : 'Core2';
                            html += `
                                <div style="display:flex; justify-content:space-between; align-items:center; padding:10px; background:#f7fafc; border-radius:8px;">
                                    <div style="display:flex; align-items:center; gap:10px;">
                                        <span style="font-weight:600; color:#2d3748;">⭐ ${symbol}</span>
                                        <span style="font-size:12px; color:#718096; background:#e2e8f0; padding:2px 8px; border-radius:4px;">${webhookLabel}</span>
                                    </div>
                                    <button onclick="removeFromWatchlist('${market}', '${symbol}')" style="background:#ef4444; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px;">
                                        ✗ 移除
                                    </button>
                                </div>
                            `;
                        });
                        html += '</div>';
                        content.innerHTML = html;
                    }
                } else {
                    alert(`✗ 加载特别关注失败: ${result.message}`);
                }
            } catch (error) {
                alert(`✗ 加载特别关注失败: ${error.message}`);
            }
        }
        
        // 从特别关注移除
        async function removeFromWatchlist(market, symbol) {
            if (!confirm(`确定要将 ${symbol} 从${market.toUpperCase()}市场特别关注中移除吗？`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/watchlist/remove', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        market: market,
                        symbol: symbol
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(`✓ ${result.message}`);
                    // 重新加载特别关注
                    await loadWatchlistData(market);
                    // 如果是当前市场，刷新数据
                    if (market === currentMarket) {
                        loadData();
                    }
                } else {
                    alert(`✗ 移除失败: ${result.message}`);
                }
            } catch (error) {
                alert(`✗ 移除失败: ${error.message}`);
            }
        }
        
        // 市场切换
        document.querySelectorAll('.market-tabs .tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.market-tabs .tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMarket = btn.dataset.market;
                updatePeriodTabs(currentMarket);
                loadMarketData(currentMarket);
                document.getElementById('searchInput').value = '';
            });
        });
        
        // 加载今日反包数据
        function loadTodayReversalData() {
            // 设置当前周期为today
            currentPeriod = 'today';
            // 移除其他按钮的active状态
            document.querySelectorAll('.period-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            // 设置今日反包按钮为active
            const todayBtn = document.querySelector('[data-period="today"] button');
            if (todayBtn) {
                todayBtn.classList.add('active');
            }
            // 加载数据
            loadPeriodData('today');
        }
        
        // 切换今日反包下拉菜单
        function toggleTodayReversalMenu(event) {
            if (event) {
                event.stopPropagation();
            }
            const menu = document.getElementById('todayReversalMenu');
            if (menu.style.display === 'none' || !menu.style.display) {
                menu.style.display = 'block';
                // 点击外部关闭菜单
                setTimeout(() => {
                    document.addEventListener('click', closeTodayReversalMenuOnClick);
                }, 100);
            } else {
                menu.style.display = 'none';
                document.removeEventListener('click', closeTodayReversalMenuOnClick);
            }
        }
        
        function closeTodayReversalMenu() {
            document.getElementById('todayReversalMenu').style.display = 'none';
            document.removeEventListener('click', closeTodayReversalMenuOnClick);
        }
        
        function closeTodayReversalMenuOnClick(e) {
            const menu = document.getElementById('todayReversalMenu');
            const todayBtnContainer = document.querySelector('[data-period="today"]');
            if (menu && todayBtnContainer && !menu.contains(e.target) && !todayBtnContainer.contains(e.target)) {
                closeTodayReversalMenu();
            }
        }
        
        // 周期切换
        document.querySelectorAll('.period-tabs .tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // 如果点击的是今日反包下拉菜单，不处理
                if (e.target.closest('#todayReversalMenu')) {
                    return;
                }
                // 如果点击的是今日反包按钮，不在这里处理（由按钮的onclick处理）
                if (btn.closest('[data-period="today"]')) {
                    return;
                }
                document.querySelectorAll('.period-tabs .tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (btn.dataset.period) {
                loadPeriodData(btn.dataset.period);
                }
                document.getElementById('searchInput').value = '';
                // 关闭今日反包下拉菜单
                closeTodayReversalMenu();
            });
        });
        
        // 初始加载
        window.addEventListener('load', () => {
            updatePeriodTabs(currentMarket); // 初始化周期选项卡
            updateSortButtons(); // 初始化排序按钮状态
            loadData();
            loadTaskStatus();
            // 每30秒更新一次状态
            setInterval(loadTaskStatus, 30000);
            // 每60秒更新一次数据标识
            setInterval(updateDataIndicators, 60000);
        });
    </script>
</body>
</html>'''


def get_monitor_html_template():
    """获取监控Token列表HTML模板"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>监控Token列表</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header h1 { color: #2d3748; font-size: 32px; margin-bottom: 10px; }
        .header p { color: #718096; font-size: 14px; }
        
        .nav-link {
            display: inline-block;
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            padding: 8px 16px;
            background: #f0f4ff;
            border-radius: 8px;
            transition: all 0.3s ease;
            margin-top: 15px;
        }
        .nav-link:hover {
            background: #667eea;
            color: white;
        }
        
        .controls {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .btn:hover { background: #5a67d8; }
        .search-box { flex: 1; min-width: 250px; }
        .search-box input {
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
        }
        
        .table-container {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #f7fafc;
            color: #2d3748;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            border-bottom: 2px solid #e2e8f0;
            position: relative;
        }
        .sort-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
            margin-left: 5px;
            padding: 2px 5px;
            border-radius: 3px;
            transition: all 0.2s ease;
            color: #718096;
        }
        .sort-btn:hover {
            background: #e2e8f0;
        }
        .sort-btn.asc::after {
            content: " ↑";
            color: #10b981;
        }
        .sort-btn.desc::after {
            content: " ↓";
            color: #ef4444;
        }
        td {
            padding: 15px;
            border-bottom: 1px solid #e2e8f0;
            color: #4a5568;
        }
        tr:hover { background: #f7fafc; }
        .token-symbol { 
            font-weight: 600; 
            color: #667eea; 
        }
        .positive-change { color: #48bb78; font-weight: 600; }
        .negative-change { color: #ef4444; font-weight: 600; }
        .loading { text-align: center; padding: 50px; }
        .no-data { text-align: center; padding: 50px; color: #718096; }
        
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-exchange { background: #e0e7ff; color: #4338ca; }
        .badge-interval { background: #dbeafe; color: #1e40af; }
        .badge-active { background: #d1fae5; color: #065f46; }
        .badge-inactive { background: #fee2e2; color: #991b1b; }
        .badge-highfreq { background: #fef3c7; color: #b45309; }
        
        /* 移除按钮样式 */
        .remove-btn {
            background: #ef4444;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .remove-btn:hover {
            background: #dc2626;
            transform: scale(1.05);
        }
        .remove-btn:active {
            transform: scale(0.95);
        }
        
        /* 来源标签页样式 */
        .source-tabs {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .source-tab-btn {
            padding: 12px 24px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            background: white;
            color: #4a5568;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .source-tab-btn:hover { border-color: #667eea; color: #667eea; }
        .source-tab-btn.active { background: #667eea; border-color: #667eea; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 监控Token列表</h1>
            <p id="updateTime">加载中...</p>
            <a href="/" class="nav-link">← 返回主页</a>
        </div>
        
        <!-- 来源标签页 -->
        <div class="source-tabs">
            <button class="source-tab-btn active" data-source="manual" onclick="switchSource('manual')">人工</button>
            <button class="source-tab-btn" data-source="highfreq" onclick="switchSource('highfreq')">高频</button>
            <button class="source-tab-btn" data-source="auto" onclick="switchSource('auto')">自动</button>
        </div>
        
        <div class="controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 搜索Token...">
            </div>
            <button class="btn" onclick="refreshData()">🔄 刷新数据</button>
            <button class="btn" id="addMonitorBtn" onclick="showAddMonitorModal()" style="background: #10b981;">➕ 添加人工监控</button>
        </div>
        
        <!-- 添加监控对话框 -->
        <div id="addMonitorModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:1000; justify-content:center; align-items:center;">
            <div style="background:white; border-radius:15px; padding:30px; max-width:500px; box-shadow:0 20px 60px rgba(0,0,0,0.3);">
                <h2 style="margin-bottom:20px; color:#2d3748;">➕ 添加监控Token</h2>
                
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:600; color:#4a5568;">交易对 <span style="color:red;">*</span></label>
                    <input type="text" id="addTickerInput" placeholder="例如: BTCUSDT" 
                           style="width:100%; padding:12px; border:2px solid #e2e8f0; border-radius:8px;">
                </div>
                
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:600; color:#4a5568;">时间周期</label>
                    <select id="addIntervalSelect" style="width:100%; padding:12px; border:2px solid #e2e8f0; border-radius:8px;">
                        <option value="1D">1日</option>
                        <option value="3D">3日</option>
                        <option value="1W">周</option>
                    </select>
                </div>
                
                <div style="margin-bottom:20px; padding:15px; background:#f0f9ff; border-radius:8px;">
                    <p id="addModalInfo" style="margin:0; font-size:13px; color:#0369a1;">
                        ℹ️ 默认为 bn_futures 交易所，监控日期为今天，标识为人工导入
                    </p>
                </div>
                
                <div style="display:flex; gap:10px; justify-content:flex-end;">
                    <button class="btn" onclick="closeAddMonitorModal()" style="background:#718096;">取消</button>
                    <button class="btn" onclick="submitAddMonitor()" style="background:#10b981;">确认添加</button>
                </div>
            </div>
        </div>
        
        <div class="table-container">
            <div id="loading" class="loading">正在加载数据...</div>
            <div id="noData" class="no-data" style="display:none;">暂无数据</div>
            <table id="dataTable" style="display:none;">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>交易对</th>
                        <th>交易所</th>
                        <th>周期</th>
                        <th>监控日期 <button class="sort-btn" onclick="sortTable('date')" title="点击排序">↕️</button></th>
                        <th>来源 <button class="sort-btn" onclick="sortTable('source')" title="点击排序">↕️</button></th>
                        <th>最高价</th>
                        <th>最低价</th>
                        <th>当前价</th>
                        <th>价格区间</th>
                        <th>更新时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        let allTokens = [];
        let displayTokens = [];
        let currentSortField = null;
        let currentSortOrder = 'asc'; // 'asc' 或 'desc'
        let currentSource = 'manual'; // 'manual', 'auto' - 默认显示人工
        
        // 加载数据
        async function loadData() {
            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('noData').style.display = 'none';
                document.getElementById('dataTable').style.display = 'none';
                
                const response = await fetch('/api/monitor');
                const result = await response.json();
                
                if (result.success) {
                    allTokens = result.tokens;
                    filterBySource(); // 根据当前来源过滤
                    
                    document.getElementById('updateTime').textContent = 
                        `共找到 ${result.total} 个监控Token`;
                    
                    // 更新来源统计
                    updateSourceStats();
                    updateAddButtonState();
                    
                    renderTable();
                } else {
                    document.getElementById('loading').innerHTML = 
                        `<p style="color: red;">❌ ${result.message}</p>`;
                }
            } catch (error) {
                document.getElementById('loading').innerHTML = 
                    `<p style="color: red;">❌ 加载失败: ${error.message}</p>`;
            }
        }
        
        // 切换来源标签
        function switchSource(source) {
            currentSource = source;
            
            // 更新标签按钮状态
            document.querySelectorAll('.source-tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelector(`[data-source="${source}"]`).classList.add('active');
            
            // 过滤数据
            filterBySource();
            
            // 重新渲染表格
            renderTable();
            
            // 更新统计信息
            updateSourceStats();
            updateAddButtonState();
        }
        
        // 根据来源过滤数据
        function filterBySource() {
            if (currentSource === 'manual') {
                displayTokens = allTokens.filter(t => t.source === 'manual');
            } else if (currentSource === 'highfreq') {
                displayTokens = allTokens.filter(t => t.source === 'highfreq');
            } else if (currentSource === 'auto') {
                displayTokens = allTokens.filter(t => t.source === 'auto' || !t.source);
            } else {
                displayTokens = [...allTokens];
            }
            
            // 应用搜索过滤（如果存在）
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            if (searchTerm) {
                displayTokens = displayTokens.filter(t => 
                    t.ticker.toLowerCase().includes(searchTerm) ||
                    t.exchange.toLowerCase().includes(searchTerm) ||
                    t.interval.toLowerCase().includes(searchTerm)
                );
            }
            
            // 应用排序（如果存在）
            if (currentSortField) {
                applySort();
            }
        }
        
        // 更新来源统计信息
        function updateSourceStats() {
            const manualCount = allTokens.filter(t => t.source === 'manual').length;
            const highfreqCount = allTokens.filter(t => t.source === 'highfreq').length;
            const autoCount = allTokens.filter(t => t.source === 'auto' || !t.source).length;
            
            // 更新标签按钮文本显示数量
            const manualBtn = document.querySelector('[data-source="manual"]');
            const highfreqBtn = document.querySelector('[data-source="highfreq"]');
            const autoBtn = document.querySelector('[data-source="auto"]');
            
            if (manualBtn) manualBtn.textContent = `人工 (${manualCount})`;
            if (highfreqBtn) highfreqBtn.textContent = `高频 (${highfreqCount})`;
            if (autoBtn) autoBtn.textContent = `自动 (${autoCount})`;
        }
        
        // 根据来源更新添加按钮状态
        function updateAddButtonState() {
            const addBtn = document.getElementById('addMonitorBtn');
            if (!addBtn) return;
            
            const disableStyle = () => {
                addBtn.disabled = true;
                addBtn.style.opacity = '0.6';
                addBtn.style.cursor = 'not-allowed';
            };
            
            const enableStyle = (bgColor, text) => {
                addBtn.disabled = false;
                addBtn.style.opacity = '1';
                addBtn.style.cursor = 'pointer';
                addBtn.style.background = bgColor;
                addBtn.textContent = text;
            };
            
            if (currentSource === 'manual') {
                enableStyle('#10b981', '➕ 添加人工监控');
            } else if (currentSource === 'highfreq') {
                enableStyle('#f59e0b', '➕ 添加高频监控');
            } else if (currentSource === 'auto') {
                disableStyle();
                addBtn.style.background = '#a0aec0';
                addBtn.textContent = '➕ 自动列表不可添加';
            } else {
                enableStyle('#10b981', '➕ 添加监控');
            }
        }
        
        // 渲染表格
        function renderTable() {
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            if (displayTokens.length === 0) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('noData').style.display = 'block';
                return;
            }
            
            displayTokens.forEach(token => {
                const row = document.createElement('tr');
                
                // 计算价格位置百分比
                let positionText = '-';
                let positionClass = '';
                if (token.current_price > 0 && token.price_range > 0) {
                    const fromHigh = ((token.high - token.current_price) / token.price_range) * 100;
                    positionText = `${fromHigh.toFixed(1)}%`;
                    if (fromHigh > 50) positionClass = 'positive-change';
                    else positionClass = 'negative-change';
                }
                
                let sourceBadge = '<span class="badge badge-inactive">自动</span>';
                if (token.source === 'manual') {
                    sourceBadge = '<span class="badge badge-active">人工</span>';
                } else if (token.source === 'highfreq') {
                    sourceBadge = '<span class="badge badge-highfreq">高频</span>';
                }
                
                // 仅人工或高频来源的Token显示移除按钮
                const removableSources = ['manual', 'highfreq'];
                const removeButton = removableSources.includes(token.source) 
                    ? `<button class="remove-btn" onclick="removeToken(${token.id}, '${token.ticker}')">移除</button>`
                    : '-';
                
                row.innerHTML = `
                    <td>${token.id}</td>
                    <td class="token-symbol">${token.ticker}</td>
                    <td><span class="badge badge-exchange">${token.exchange}</span></td>
                    <td><span class="badge badge-interval">${token.interval}</span></td>
                    <td>${token.date}</td>
                    <td>${sourceBadge}</td>
                    <td>${token.high > 0 ? '$' + token.high.toFixed(6) : '-'}</td>
                    <td>${token.low > 0 ? '$' + token.low.toFixed(6) : '-'}</td>
                    <td>${token.current_price > 0 ? '$' + token.current_price.toFixed(6) : '-'}</td>
                    <td>${token.price_range > 0 ? '$' + token.price_range.toFixed(6) : '-'}</td>
                    <td>${token.update_time || '-'}</td>
                    <td>${removeButton}</td>
                `;
                tbody.appendChild(row);
            });
            
            document.getElementById('loading').style.display = 'none';
            document.getElementById('noData').style.display = 'none';
            document.getElementById('dataTable').style.display = 'table';
        }
        
        // 刷新数据
        function refreshData() {
            loadData();
        }
        
        // 应用排序
        function applySort() {
            displayTokens.sort((a, b) => {
                let valueA = a[currentSortField];
                let valueB = b[currentSortField];
                
                // 处理日期排序
                if (currentSortField === 'date') {
                    valueA = new Date(valueA);
                    valueB = new Date(valueB);
                }
                
                // 处理source排序，不同来源有固定顺序
                if (currentSortField === 'source') {
                    const orderMap = { manual: 1, highfreq: 2, auto: 3 };
                    valueA = orderMap[valueA] || 99;
                    valueB = orderMap[valueB] || 99;
                }
                
                // 比较
                if (valueA < valueB) return currentSortOrder === 'asc' ? -1 : 1;
                if (valueA > valueB) return currentSortOrder === 'asc' ? 1 : -1;
                return 0;
            });
        }
        
        // 排序功能
        function sortTable(field) {
            // 切换排序方向
            if (currentSortField === field) {
                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortField = field;
                currentSortOrder = 'asc';
            }
            
            // 执行排序
            applySort();
            
            // 更新按钮状态
            updateSortButtons();
            
            // 重新渲染表格
            renderTable();
        }
        
        // 更新排序按钮状态
        function updateSortButtons() {
            // 清除所有排序按钮的状态
            document.querySelectorAll('.sort-btn').forEach(btn => {
                btn.classList.remove('asc', 'desc');
            });
            
            // 设置当前排序列的状态
            const buttons = document.querySelectorAll('.sort-btn');
            buttons.forEach(btn => {
                const field = btn.getAttribute('onclick').match(/'(\w+)'/)[1];
                if (field === currentSortField) {
                    btn.classList.add(currentSortOrder);
                }
            });
        }
        
        // 搜索功能
        document.getElementById('searchInput').addEventListener('input', (e) => {
            // 重新过滤数据（包括来源和搜索）
            filterBySource();
            renderTable();
        });
        
        // 显示添加监控对话框
        function showAddMonitorModal() {
            if (currentSource === 'auto') {
                alert('自动来源列表不支持手动添加，请切换到人工或高频标签。');
                return;
            }
            document.getElementById('addMonitorModal').style.display = 'flex';
            document.getElementById('addTickerInput').value = '';
            document.getElementById('addIntervalSelect').value = '1D';
            
            const info = document.getElementById('addModalInfo');
            if (info) {
                const sourceText = currentSource === 'highfreq' ? '高频来源' : '人工导入';
                info.textContent = `ℹ️ 默认为 bn_futures 交易所，监控日期为今天，标识为${sourceText}`;
            }
        }
        
        // 关闭添加监控对话框
        function closeAddMonitorModal() {
            document.getElementById('addMonitorModal').style.display = 'none';
        }
        
        // 提交添加监控
        async function submitAddMonitor() {
            const ticker = document.getElementById('addTickerInput').value.trim().toUpperCase();
            const interval = document.getElementById('addIntervalSelect').value;
            
            if (!ticker) {
                alert('请填写交易对名称');
                return;
            }
            if (!['manual', 'highfreq'].includes(currentSource)) {
                alert('当前来源不支持添加，请切换到人工或高频标签。');
                return;
            }
            
            try {
                const response = await fetch('/api/monitor/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        ticker: ticker,
                        interval: interval,
                        source: currentSource
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ ' + result.message);
                    closeAddMonitorModal();
                    loadData(); // 重新加载数据
                } else {
                    alert('❌ ' + result.message);
                }
            } catch (error) {
                alert('❌ 添加失败: ' + error.message);
            }
        }
        
        // 移除Token（仅限人工导入）
        async function removeToken(monitorId, ticker) {
            if (!confirm(`确定要移除监控 ${ticker} 吗？\n\n此操作将永久删除该监控记录，无法恢复。`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/monitor/remove', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        id: monitorId
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ ' + result.message);
                    // 重新加载数据
                    loadData();
                } else {
                    alert('❌ ' + result.message);
                }
            } catch (error) {
                alert('❌ 移除失败: ' + error.message);
            }
        }
        
        // 初始加载
        window.addEventListener('load', () => {
            loadData();
            // 每60秒自动刷新
            setInterval(loadData, 60000);
            // 初始化排序按钮状态
            updateSortButtons();
            // 初始化来源统计
            updateSourceStats();
        });
    </script>
</body>
</html>'''


def get_open_interest_html_template():
    """获取合约持仓量HTML模板"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>合约持仓量监控</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .header h1 { color: #2d3748; font-size: 32px; margin-bottom: 10px; }
        .header p { color: #718096; font-size: 14px; }
        
        .nav-link {
            display: inline-block;
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            padding: 8px 16px;
            background: #f0f4ff;
            border-radius: 8px;
            transition: all 0.3s ease;
            margin-top: 15px;
        }
        .nav-link:hover {
            background: #667eea;
            color: white;
        }
        
        .info-box {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .info-box h3 {
            color: #2d3748;
            margin-bottom: 15px;
            font-size: 18px;
        }
        .info-box p {
            color: #718096;
            line-height: 1.8;
            font-size: 14px;
        }
        
        .controls {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .btn:hover { background: #5a67d8; }
        .search-box { flex: 1; min-width: 250px; }
        .search-box input {
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
        }
        
        .table-container {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #f7fafc;
            color: #2d3748;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            border-bottom: 2px solid #e2e8f0;
        }
        td {
            padding: 15px;
            border-bottom: 1px solid #e2e8f0;
            color: #4a5568;
        }
        tr:hover { background: #f7fafc; }
        .token-symbol { 
            font-weight: 600; 
            color: #667eea; 
            cursor: pointer;
        }
        .token-symbol:hover { text-decoration: underline; }
        .positive-change { color: #10b981; font-weight: 600; }
        .negative-change { color: #ef4444; font-weight: 600; }
        .loading { text-align: center; padding: 50px; }
        .no-data { text-align: center; padding: 50px; color: #718096; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 合约持仓量监控</h1>
            <p id="updateTime">加载中...</p>
            <a href="/" class="nav-link">← 返回主页</a>
        </div>
        
        <div class="info-box">
            <h3>ℹ️ 功能说明</h3>
            <p>
                <strong>监控对象：</strong>仅上线合约但未上线现货的USDT交易对<br>
                <strong>计算频率：</strong>每小时整点自动计算一次<br>
                <strong>筛选条件：</strong>过去1小时持仓增长率 > 20% 或 持仓增涨金额 > 100万USDT<br>
                <strong>更新时间：</strong>数据每小时更新，页面每60秒自动刷新
            </p>
        </div>
        
        <div class="controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 搜索Token...">
            </div>
            <button class="btn" onclick="refreshData()">🔄 刷新数据</button>
        </div>
        
        <div class="table-container">
            <div id="loading" class="loading">正在加载数据...</div>
            <div id="noData" class="no-data" style="display:none;">暂无符合条件的持仓量异常数据</div>
            <table id="dataTable" style="display:none;">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>交易对</th>
                        <th>当前持仓量(BTC)</th>
                        <th>1小时前持仓量(BTC)</th>
                        <th>持仓增长率</th>
                        <th>持仓增长金额(USDT)</th>
                        <th>更新时间</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>
    
    <script>
        let allData = [];
        let displayData = [];
        
        // 加载数据
        async function loadData() {
            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('noData').style.display = 'none';
                document.getElementById('dataTable').style.display = 'none';
                
                const response = await fetch('/api/open-interest');
                const result = await response.json();
                
                if (result.success) {
                    allData = result.data || [];
                    displayData = [...allData];
                    
                    // 优先显示计算时间，如果没有则显示更新时间
                    const timeToDisplay = result.calculation_time || result.update_time || '';
                    if (timeToDisplay) {
                        document.getElementById('updateTime').textContent = 
                            `数据计算时间: ${timeToDisplay}`;
                    } else {
                        document.getElementById('updateTime').textContent = '最后更新: 无数据';
                    }
                    
                    renderTable();
                } else {
                    document.getElementById('loading').innerHTML = 
                        `<p style="color: red;">❌ ${result.message}</p>`;
                }
            } catch (error) {
                document.getElementById('loading').innerHTML = 
                    `<p style="color: red;">❌ 加载失败: ${error.message}</p>`;
            }
        }
        
        // 渲染表格
        function renderTable() {
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            if (displayData.length === 0) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('noData').style.display = 'block';
                return;
            }
            
            displayData.forEach((item, index) => {
                const row = document.createElement('tr');
                
                const growthRate = item.growth_rate || 0;
                const growthAmount = item.growth_amount_usdt || 0;
                const growthRateClass = growthRate > 0 ? 'positive-change' : 'negative-change';
                
                row.innerHTML = `
                    <td><strong>${index + 1}</strong></td>
                    <td class="token-symbol" onclick="window.open('https://www.binance.com/zh-CN/trade/${item.symbol}', '_blank')">${item.symbol}</td>
                    <td>${(item.current_oi || 0).toFixed(2)}</td>
                    <td>${(item.previous_oi || 0).toFixed(2)}</td>
                    <td><span class="${growthRateClass}">${growthRate > 0 ? '+' : ''}${growthRate.toFixed(2)}%</span></td>
                    <td><span class="${growthRateClass}">${growthAmount > 0 ? '+' : ''}${(growthAmount / 10000).toFixed(2)}万USDT</span></td>
                    <td>${item.update_time || '-'}</td>
                `;
                tbody.appendChild(row);
            });
            
            document.getElementById('loading').style.display = 'none';
            document.getElementById('noData').style.display = 'none';
            document.getElementById('dataTable').style.display = 'table';
        }
        
        function refreshData() {
            loadData();
        }
        
        // 搜索功能
        document.getElementById('searchInput').addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            displayData = allData.filter(item => 
                item.symbol.toLowerCase().includes(term)
            );
            renderTable();
        });
        
        // 初始加载
        window.addEventListener('load', () => {
            loadData();
            // 每60秒自动刷新
            setInterval(loadData, 60000);
        });
    </script>
</body>
</html>'''


def init_scheduler():
    """初始化定时任务"""
    scheduler = BackgroundScheduler()
    
    # 每天早上8点执行任务
    scheduler.add_job(
        func=auto_fetch_and_filter,
        trigger='cron',
        hour=8,
        minute=0,
        id='daily_update',
        name='每日数据更新任务',
        replace_existing=True
    )
    
    # 每小时过1分钟执行合约持仓量计算任务
    scheduler.add_job(
        func=calculate_and_save_open_interest,
        trigger='cron',
        minute=1,
        id='open_interest_update',
        name='合约持仓量计算任务',
        replace_existing=True
    )
    
    scheduler.start()
    
    # 启动后才能获取下次运行时间
    job = scheduler.get_job('daily_update')
    if job:
        next_run = scheduler.get_job('daily_update').next_run_time
        task_status['next_run'] = next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else '每天 08:00'
    else:
        task_status['next_run'] = '每天 08:00'
    
    # 获取持仓量计算任务的下次运行时间
    oi_job = scheduler.get_job('open_interest_update')
    if oi_job:
        oi_next_run = oi_job.next_run_time
        if oi_next_run:
            logger.info(f"  持仓量计算下次运行时间: {oi_next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    logger.info("✓ 定时任务调度器已启动")
    logger.info(f"  下次运行时间: {task_status['next_run']}")
    
    return scheduler


if __name__ == '__main__':
    import sys
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Flask自动化服务')
    parser.add_argument('port', type=int, nargs='?', default=5000, help='服务端口（默认: 5000）')
    parser.add_argument('-n', '--top-n', type=int, default=None, help='获取前N个代币（默认: 100）')
    parser.add_argument('-k', '--kline', type=int, default=None, help='每个Token获取的K线数据条数（默认: 200）')
    args = parser.parse_args()
    
    # 更新配置
    if args.top_n:
        CONFIG['top_n'] = args.top_n
    if args.kline:
        CONFIG['kline_records'] = args.kline
    
    # 从环境变量读取配置（优先级：命令行 > 环境变量 > 默认值）
    if not args.top_n and 'TOP_N' in os.environ:
        CONFIG['top_n'] = int(os.environ['TOP_N'])
    if not args.kline and 'KLINE_RECORDS' in os.environ:
        CONFIG['kline_records'] = int(os.environ['KLINE_RECORDS'])
    
    # 创建logs目录
    os.makedirs('logs', exist_ok=True)
    
    # 初始化调度器
    scheduler = init_scheduler()
    
    print("="*80)
    print("多周期Token筛选 - 全市场自动化服务")
    print("="*80)
    print()
    print("✓ 服务器启动成功")
    print(f"✓ 配置: Top{CONFIG['top_n']} 代币（BN市场+OK市场）+ US股票反包")
    print(f"✓ 定时任务: 每天早上 08:00 自动更新")
    print(f"✓ 下次运行: {task_status['next_run']}")
    print()
    print("访问地址:")
    print(f"  http://localhost:{args.port}")
    print(f"  http://127.0.0.1:{args.port}")
    print()
    print("功能:")
    print("  - 三市场: 同时处理BN市场、OK市场、US股票市场")
    print("  - 自动化: 每天早上8点自动获取数据并筛选")
    print("    · BN/OK市场: K线数据获取+筛选")
    print("    · US股票: 反包形态检测（自动从history获取昨日和前日数据）")
    print("  - 手动触发: 在Web界面点击按钮立即执行")
    print("  - 实时查看: 任务状态和执行结果")
    print("  - 市场切换: 在Web界面切换查看三个市场结果")
    print()
    print("配置:")
    print(f"  - Top N: {CONFIG['top_n']} 代币（BN市场+OK市场）")
    print(f"  - 端口: {args.port}")
    print("  - 数据源: 币安市场 + OKX市场（现货+合约合并）+ Polygon.io（US股票）")
    print()
    print("按 Ctrl+C 停止服务")
    print("="*80)
    print()
    
    try:
        app.run(host='0.0.0.0', port=args.port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        if scheduler:
            scheduler.shutdown()
