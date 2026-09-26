#!/usr/bin/env python3
"""
Token 配置管理 Flask 服务

唯一功能：读写 src/alert/tokens-config-dynamic.md，提供：
- /token-config                Token 配置管理页面
- /api/token-config            读取配置 JSON
- /api/token-config/save       保存配置 JSON
- /api/token-config/validate   校验配置 JSON
"""

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from datetime import datetime
import os
import sys
import argparse
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/token_config_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 配置文件路径（绝对路径，指向 src/alert/tokens-config-dynamic.md）
CONFIG_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'alert', 'tokens-config-dynamic.md')
)

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
        config_file = CONFIG_FILE

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

        config_file = CONFIG_FILE

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


@app.route('/api/token-config/validate', methods=['POST'])
def validate_token_config():
    """
    验证Token配置格式

    配置格式要求:
    - 每行为: SYMBOL 0/1/2/3  (SYMBOL是交易对，数字表示报警频率级别)
    - 0: 15分钟及以上周期报警
    - 1: 1小时及以上周期报警
    - 2: 4小时及以上周期报警
    - 3: 日线及以上周期报警
    - 支持 # 注释
    - 允许不带级别（默认0）
    """
    try:
        data = request.get_json()
        content = data.get('content', '')

        errors = []
        warnings = []
        tokens = []  # [(symbol, level), ...]
        seen_symbols = set()

        for line_no, line in enumerate(content.split('\n'), 1):
            stripped = line.strip()

            # 跳过空行和注释行
            if not stripped or stripped.startswith('#'):
                continue

            # 去掉行内注释
            code_part = stripped.split('#')[0].strip()
            if not code_part:
                continue

            # 解析: SYMBOL 0/1
            parts = code_part.split()
            if len(parts) < 1:
                errors.append(f'第{line_no}行: 格式错误（空内容）')
                continue

            symbol = parts[0].upper()

            # 验证交易对格式（以USDT结尾的基本格式）
            if not symbol.isalnum() or len(symbol) < 5:
                errors.append(f'第{line_no}行: 交易对格式错误 "{symbol}"（应为字母数字组合，至少5位）')
                continue

            # 验证级别
            if len(parts) == 1:
                level = 0  # 默认级别
                warnings.append(f'第{line_no}行: "{symbol}" 未指定级别，使用默认值 0（15m+）')
            elif len(parts) >= 2:
                level_str = parts[1]
                if level_str not in ('0', '1', '2', '3'):
                    errors.append(f'第{line_no}行: 级别值无效 "{level_str}"（应为 0/1/2/3）')
                    continue
                level = int(level_str)

                if len(parts) > 2:
                    warnings.append(f'第{line_no}行: 多余的参数被忽略 "{symbol} {level_str} ..."')

            # 检查重复
            if symbol in seen_symbols:
                errors.append(f'第{line_no}行: 重复的交易对 "{symbol}"')
                continue

            seen_symbols.add(symbol)
            tokens.append((symbol, level, line_no))

        # 统计
        level_0_count = sum(1 for _, lvl, _ in tokens if lvl == 0)
        level_1_count = sum(1 for _, lvl, _ in tokens if lvl == 1)
        level_2_count = sum(1 for _, lvl, _ in tokens if lvl == 2)
        level_3_count = sum(1 for _, lvl, _ in tokens if lvl == 3)

        return jsonify({
            'success': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'tokens': [{'symbol': s, 'level': l, 'line': ln} for s, l, ln in tokens],
            'summary': {
                'total': len(tokens),
                'level_0_count': level_0_count,
                'level_1_count': level_1_count,
                'level_2_count': level_2_count,
                'level_3_count': level_3_count
            },
            'message': '配置格式正确' if not errors else f'发现 {len(errors)} 个错误'
        })

    except Exception as e:
        logger.error(f"验证Token配置失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'errors': [str(e)],
            'warnings': [],
            'tokens': [],
            'summary': {'total': 0, 'level_0_count': 0, 'level_1_count': 0, 'level_2_count': 0, 'level_3_count': 0}
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


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='Token 配置管理服务')
    parser.add_argument('port', nargs='?', type=int, default=5000, help='监听端口（默认 5000）')
    args = parser.parse_args()

    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)

    logger.info(f"启动 Token 配置管理服务，端口: {args.port}")
    app.run(host='0.0.0.0', port=args.port, debug=False)


if __name__ == '__main__':
    main()