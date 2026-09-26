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
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 8px;
        }
        .header .subtitle {
            opacity: 0.9;
            font-size: 14px;
        }
        .toolbar {
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        .toolbar-left {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .toolbar-right {
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-1px);
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #218838;
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background: #5a6268;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .file-info {
            font-size: 13px;
            color: #6c757d;
        }
        .editor-area {
            padding: 30px;
        }
        .editor-container {
            position: relative;
        }
        #editor {
            width: 100%;
            min-height: 500px;
            padding: 15px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 14px;
            line-height: 1.6;
            resize: vertical;
            outline: none;
            transition: border-color 0.2s;
        }
        #editor:focus {
            border-color: #667eea;
        }
        .status-bar {
            padding: 15px 30px;
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: #6c757d;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #28a745;
        }
        .status-dot.unsaved {
            background: #ffc107;
        }
        .status-dot.error {
            background: #dc3545;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal.active {
            display: flex;
        }
        .modal-content {
            background: white;
            border-radius: 12px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow: auto;
        }
        .modal-header {
            padding: 20px 30px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-header h3 {
            font-size: 18px;
        }
        .modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #6c757d;
        }
        .modal-body {
            padding: 20px 30px;
        }
        .modal-footer {
            padding: 15px 30px;
            border-top: 1px solid #e9ecef;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .summary-card {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            text-align: center;
        }
        .summary-card .label {
            font-size: 12px;
            color: #6c757d;
            margin-bottom: 5px;
        }
        .summary-card .value {
            font-size: 24px;
            font-weight: 600;
            color: #495057;
        }
        .message-list {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #e9ecef;
            border-radius: 6px;
        }
        .message-item {
            padding: 10px 15px;
            border-bottom: 1px solid #f8f9fa;
            font-size: 13px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }
        .message-item:last-child {
            border-bottom: none;
        }
        .message-item.error {
            background: #fff5f5;
            color: #c82333;
        }
        .message-item.warning {
            background: #fffbf0;
            color: #856404;
        }
        .message-item.info {
            background: #f0f9ff;
            color: #004085;
        }
        .message-icon {
            flex-shrink: 0;
            font-weight: bold;
        }
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-size: 14px;
            opacity: 0;
            transform: translateX(400px);
            transition: all 0.3s;
            z-index: 2000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .toast.show {
            opacity: 1;
            transform: translateX(0);
        }
        .toast.success {
            background: #28a745;
        }
        .toast.error {
            background: #dc3545;
        }
        .toast.info {
            background: #17a2b8;
        }
        .help-text {
            font-size: 12px;
            color: #6c757d;
            margin-top: 8px;
            line-height: 1.5;
        }
        .help-text code {
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Token 配置管理</h1>
            <div class="subtitle">编辑 tokens-config-dynamic.md 监控配置文件</div>
        </div>

        <div class="toolbar">
            <div class="toolbar-left">
                <span class="file-info" id="fileInfo">加载中...</span>
            </div>
            <div class="toolbar-right">
                <button class="btn btn-secondary" onclick="validateConfig()">🔍 校验</button>
                <button class="btn btn-primary" onclick="reloadConfig()">🔄 重新加载</button>
                <button class="btn btn-success" onclick="saveConfig()">💾 保存</button>
            </div>
        </div>

        <div class="editor-area">
            <div class="editor-container">
                <textarea id="editor" placeholder="加载中..." spellcheck="false"></textarea>
                <div class="help-text">
                    格式说明：每行一个交易对，可选告警级别（0=15m+, 1=1h+, 2=4h+, 3=daily+），默认 0。<br>
                    示例：<code>BTCUSDT 1</code> 或 <code>ETHUSDT</code>，以 <code>#</code> 开头为注释。
                </div>
            </div>
        </div>

        <div class="status-bar">
            <div class="status-item">
                <span class="status-dot" id="statusDot"></span>
                <span id="statusText">就绪</span>
            </div>
            <div class="status-item">
                <span id="charCount">0</span> 字符
            </div>
        </div>
    </div>

    <!-- 校验结果模态框 -->
    <div class="modal" id="validateModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="validateTitle">配置校验结果</h3>
                <button class="modal-close" onclick="closeModal('validateModal')">&times;</button>
            </div>
            <div class="modal-body">
                <div class="summary-grid" id="summaryGrid"></div>
                <div id="messagesContainer"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal('validateModal')">关闭</button>
                <button class="btn btn-primary" onclick="validateAndFix()">自动修复并重新校验</button>
            </div>
        </div>
    </div>

    <!-- Toast 提示 -->
    <div class="toast" id="toast"></div>

    <script>
        const editor = document.getElementById('editor');
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const charCount = document.getElementById('charCount');
        const fileInfo = document.getElementById('fileInfo');
        const toast = document.getElementById('toast');

        let originalContent = '';
        let hasUnsavedChanges = false;

        function showToast(message, type = 'info') {
            toast.textContent = message;
            toast.className = `toast ${type} show`;
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        function updateStatus(state, text) {
            statusDot.className = 'status-dot';
            if (state === 'unsaved') statusDot.classList.add('unsaved');
            else if (state === 'error') statusDot.classList.add('error');
            statusText.textContent = text;
        }

        function updateCharCount() {
            charCount.textContent = editor.value.length;
        }

        function markUnsaved() {
            if (editor.value !== originalContent) {
                if (!hasUnsavedChanges) {
                    hasUnsavedChanges = true;
                    updateStatus('unsaved', '有未保存的修改');
                }
            } else {
                hasUnsavedChanges = false;
                updateStatus('saved', '就绪');
            }
        }

        async function loadConfig() {
            try {
                updateStatus('', '加载中...');
                const response = await fetch('/api/token-config');
                const data = await response.json();

                if (data.success) {
                    editor.value = data.content;
                    originalContent = data.content;
                    hasUnsavedChanges = false;
                    fileInfo.textContent = `文件: ${data.file_path} | 修改时间: ${data.last_modified}`;
                    updateStatus('saved', '就绪');
                    updateCharCount();
                    showToast('配置加载成功', 'success');
                } else {
                    updateStatus('error', '加载失败');
                    fileInfo.textContent = data.message;
                    showToast(data.message, 'error');
                    editor.value = '';
                    originalContent = '';
                }
            } catch (error) {
                updateStatus('error', '网络错误');
                showToast(`加载失败: ${error.message}`, 'error');
            }
        }

        async function reloadConfig() {
            if (hasUnsavedChanges) {
                if (!confirm('当前有未保存的修改，确定要重新加载吗？')) return;
            }
            await loadConfig();
        }

        async function saveConfig() {
            if (!editor.value.trim()) {
                showToast('配置内容不能为空', 'error');
                return;
            }

            // 保存前先校验
            try {
                const validateResp = await fetch('/api/token-config/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: editor.value })
                });
                const validateData = await validateResp.json();

                if (!validateData.success) {
                    showValidateResult(validateData);
                    if (!confirm('配置存在错误，仍要保存吗？')) return;
                }
            } catch (error) {
                if (!confirm('校验失败，仍要保存吗？')) return;
            }

            try {
                const response = await fetch('/api/token-config/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: editor.value })
                });
                const data = await response.json();

                if (data.success) {
                    originalContent = editor.value;
                    hasUnsavedChanges = false;
                    updateStatus('saved', '已保存');
                    showToast(data.message, 'success');
                } else {
                    updateStatus('error', '保存失败');
                    showToast(data.message, 'error');
                }
            } catch (error) {
                updateStatus('error', '网络错误');
                showToast(`保存失败: ${error.message}`, 'error');
            }
        }

        async function validateConfig() {
            try {
                const response = await fetch('/api/token-config/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: editor.value })
                });
                const data = await response.json();
                showValidateResult(data);
            } catch (error) {
                showToast(`校验失败: ${error.message}`, 'error');
            }
        }

        function showValidateResult(data) {
            const modal = document.getElementById('validateModal');
            const title = document.getElementById('validateTitle');
            const summaryGrid = document.getElementById('summaryGrid');
            const messagesContainer = document.getElementById('messagesContainer');

            title.textContent = data.success ? '✅ 配置校验通过' : '❌ 配置校验失败';

            const summary = data.summary || {};
            summaryGrid.innerHTML = `
                <div class="summary-card">
                    <div class="label">总数</div>
                    <div class="value">${summary.total || 0}</div>
                </div>
                <div class="summary-card">
                    <div class="label">15m+</div>
                    <div class="value">${summary.level_0_count || 0}</div>
                </div>
                <div class="summary-card">
                    <div class="label">1h+</div>
                    <div class="value">${summary.level_1_count || 0}</div>
                </div>
                <div class="summary-card">
                    <div class="label">4h+</div>
                    <div class="value">${summary.level_2_count || 0}</div>
                </div>
                <div class="summary-card">
                    <div class="label">日线+</div>
                    <div class="value">${summary.level_3_count || 0}</div>
                </div>
                <div class="summary-card">
                    <div class="label">错误</div>
                    <div class="value" style="color: #dc3545;">${(data.errors || []).length}</div>
                </div>
            `;

            let messagesHtml = '';
            const errors = data.errors || [];
            const warnings = data.warnings || [];

            if (errors.length === 0 && warnings.length === 0) {
                messagesHtml = '<div class="message-item info"><span class="message-icon">ℹ️</span><span>没有发现问题</span></div>';
            } else {
                errors.forEach(msg => {
                    messagesHtml += `<div class="message-item error"><span class="message-icon">✗</span><span>${escapeHtml(msg)}</span></div>`;
                });
                warnings.forEach(msg => {
                    messagesHtml += `<div class="message-item warning"><span class="message-icon">⚠</span><span>${escapeHtml(msg)}</span></div>`;
                });
            }

            messagesContainer.innerHTML = `<div class="message-list">${messagesHtml}</div>`;
            modal.classList.add('active');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function validateAndFix() {
            // 简单修复：移除多余空格、补全默认级别等
            let fixed = editor.value.split('\n').map(line => {
                let stripped = line.trim();
                if (!stripped || stripped.startsWith('#')) return line;

                // 去掉行内注释
                const commentIdx = stripped.indexOf('#');
                if (commentIdx > 0) {
                    stripped = stripped.substring(0, commentIdx).trim();
                }

                // 规范化空白
                const parts = stripped.split(/\s+/);
                return parts.join(' ');
            }).join('\n');

            editor.value = fixed;
            markUnsaved();
            closeModal('validateModal');
            showToast('已尝试自动修复，请重新校验', 'info');
            setTimeout(() => validateConfig(), 500);
        }

        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
        }

        editor.addEventListener('input', () => {
            updateCharCount();
            markUnsaved();
        });

        window.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                saveConfig();
            }
        });

        window.addEventListener('beforeunload', (e) => {
            if (hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // 初始加载
        loadConfig();
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