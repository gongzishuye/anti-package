# Token Config Only Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract `/token-config` page to a standalone Flask server in a new branch, removing all unrelated subsystems while preserving exact behavior of `/token-config`.

**Architecture:** Create `src/crypto/token_config_server.py` (≈750 lines) containing the 4 token-config routes + HTML template, copied verbatim from main branch's `flask_auto_server.py` lines 1317-2085. Stripped imports: only `flask`, `flask-cors`, stdlib (`os`, `sys`, `argparse`, `logging`, `datetime`). Delete all other modules/directories. Config file path unchanged.

**Tech Stack:** Python 3, Flask, Flask-CORS

**Spec:** `docs/superpowers/specs/2026-09-26-token-config-only-refactor-design.md`

## Global Constraints

- Branch name: `refactor/token-config-only`
- New file: `src/crypto/token_config_server.py` (≈750 lines)
- Config file path: `src/alert/tokens-config-dynamic.md` (unchanged from main)
- HTML template: copied verbatim from `src/crypto/flask_auto_server.py` lines 1521-2085 (no edits)
- Route handlers: copied verbatim from `src/crypto/flask_auto_server.py` lines 1317-1520 (no edits to logic, only imports stripped)
- CLI args: only `port` (positional, default 5000) — no `--top-n` or `--kline`
- File encoding: UTF-8 throughout
- `requirements.txt`: only `flask` and `flask-cors`
- All file paths inside the new server are absolute or relative to `src/crypto/` (do not depend on CWD)

## Review Focus

These input classes / failure modes are NOT exercised by this plan's tests but the spec implies they must work:

1. **Cold start (config file does not exist)** — GET `/api/token-config` returns `success: false` with a clear message, does not 500.
2. **Save with write permission denied** — POST `/api/token-config/save` returns `success: false` with error detail, does not crash.
3. **Empty content submit** — POST `/api/token-config/validate` with `{"content": ""}` returns `success: true` with `tokens: []`, no error.
4. **Malformed JSON in save/validate** — server returns 400/JSON error, not a stack trace.
5. **Line numbers preserved through save → reload** — after save, GET returns the exact same content (no BOM/translation).

Each is handled by the original code we are copying; the implementer verifies them by reading the copied code in Task 2 and including these scenarios in Task 3's curl-based verification.

---

## Task 1: Create Refactor Branch

**Files:**
- Modify: git branch state (no file changes)

**Interfaces:**
- Consumes: nothing
- Produces: new branch `refactor/token-config-only` checked out in working tree

- [ ] **Step 1: Verify working tree is clean**

Run: `git status`
Expected: "nothing to commit, working tree clean" OR list of pre-existing modifications matching initial snapshot. If unrelated modifications exist, stop and ask user how to proceed.

- [ ] **Step 2: Fetch latest main and create branch**

Run:
```bash
git fetch origin main
git checkout -b refactor/token-config-only origin/main
```
Expected: branch created and checked out, `git branch --show-current` prints `refactor/token-config-only`.

- [ ] **Step 3: Verify baseline state**

Run: `git log --oneline -1 && wc -l src/crypto/flask_auto_server.py`
Expected: latest commit on the new branch is the design doc commit (`225a48a`), and `flask_auto_server.py` reports `5536`.

- [ ] **Step 4: No commit needed**

Branch creation is the deliverable. No new files to add at this step.

---

## Task 2: Extract token_config_server.py

**Files:**
- Create: `src/crypto/token_config_server.py`
- Reference (do not modify): `src/crypto/flask_auto_server.py` lines 1-60 (boilerplate) and 1317-2085 (token-config code)

**Interfaces:**
- Consumes: file I/O on `src/alert/tokens-config-dynamic.md` (UTF-8)
- Produces:
  - Flask app object runnable via `python3 src/crypto/token_config_server.py [port]`
  - Routes: `GET /token-config`, `GET /api/token-config`, `POST /api/token-config/save`, `POST /api/token-config/validate`
  - Logs to `logs/token_config_server.log` AND stderr

- [ ] **Step 1: Read the source ranges to copy**

Read these ranges in full (do not paraphrase):
  - `src/crypto/flask_auto_server.py` lines 1-60 (imports, logging setup, Flask app init, config constants) — for boilerplate pattern
  - `src/crypto/flask_auto_server.py` lines 1317-1520 (4 route handlers)
  - `src/crypto/flask_auto_server.py` lines 1521-2085 (HTML template inside `get_token_config_html_template()`)

- [ ] **Step 2: Compute absolute path to config file**

The new file lives at `src/crypto/token_config_server.py`. Define at module level:
```python
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'alert', 'tokens-config-dynamic.md'))
```
Use this constant in all 4 handlers. Do NOT hard-code a CWD-relative path.

- [ ] **Step 3: Write `src/crypto/token_config_server.py`**

File structure (top to bottom):
1. Shebang + module docstring (`"""Token 配置管理 Flask 服务"""`)
2. Imports — only these:
   ```python
   from flask import Flask, jsonify, render_template_string, request
   from flask_cors import CORS
   from datetime import datetime
   import os
   import sys
   import argparse
   import logging
   ```
3. Logging setup (copy pattern from lines 21-29 of source file, change log filename to `logs/token_config_server.log`)
4. Flask app init: `app = Flask(__name__)` + `CORS(app)`
5. `CONFIG_FILE` constant (from Step 2)
6. Route handlers — copy VERBATIM from lines 1317-1520 of `flask_auto_server.py`. Replace any `BLACKLIST_FILE` / `WATCHLIST_FILE` references (there are none in this range) with `CONFIG_FILE`. Keep all logic, docstrings, return statements identical.
7. `get_token_config_html_template()` function — copy VERBATIM from lines 1521-2085. The returned string is the full HTML.
8. CLI main block:
   ```python
   def main():
       parser = argparse.ArgumentParser(description='Token 配置管理服务')
       parser.add_argument('port', nargs='?', type=int, default=5000, help='监听端口（默认 5000）')
       args = parser.parse_args()
       # ensure logs/ exists
       os.makedirs('logs', exist_ok=True)
       app.run(host='0.0.0.0', port=args.port, debug=False)

   if __name__ == '__main__':
       main()
   ```

- [ ] **Step 4: Verify file size and structure**

Run:
```bash
wc -l src/crypto/token_config_server.py
grep -n '@app.route\|def get_token_config_html_template\|if __name__' src/crypto/token_config_server.py
```
Expected:
- Line count between 700 and 800
- 4 `@app.route` decorators matching `/token-config`, `/api/token-config` (GET), `/api/token-config/save`, `/api/token-config/validate`
- One `get_token_config_html_template` definition
- One `if __name__ == '__main__'` block

- [ ] **Step 5: Smoke test — server starts**

Run:
```bash
mkdir -p logs
python3 src/crypto/token_config_server.py 8866 > /tmp/tcs_stdout.log 2>&1 &
echo $! > /tmp/tcs.pid
sleep 2
ss -tln | grep 8866
```
Expected: line containing `0.0.0.0:8866`. If not present, `cat /tmp/tcs_stdout.log` to diagnose.

- [ ] **Step 6: Smoke test — page renders**

Run:
```bash
curl -s -o /tmp/page.html -w '%{http_code}\n' http://localhost:8866/token-config
head -5 /tmp/page.html
```
Expected: HTTP `200`, output contains `<title>Token配置管理</title>` (or similar Chinese title from the original template).

- [ ] **Step 7: Smoke test — GET API**

Run:
```bash
curl -s http://localhost:8866/api/token-config | head -c 200
echo
```
Expected: JSON with at least keys `success` and `content`. Either `success: true` with content, or `success: false` with a "file not found" message (both are valid depending on whether `tokens-config-dynamic.md` exists).

- [ ] **Step 8: Stop test server**

Run:
```bash
kill $(cat /tmp/tcs.pid) 2>/dev/null
rm -f /tmp/tcs.pid
```

- [ ] **Step 9: Commit**

```bash
git add src/crypto/token_config_server.py
git commit -m "feat: extract /token-config to standalone Flask server"
```

---

## Task 3: API Consistency Verification

**Files:**
- No new files. This task only produces verification output.

**Interfaces:**
- Consumes: running instances of (a) main branch's `flask_auto_server.py` on port 8867, (b) new branch's `token_config_server.py` on port 8866
- Produces: a verification record (commit message body or temp file) showing identical or schema-equivalent responses

- [ ] **Step 1: Start main branch server on port 8867**

In a separate worktree OR by temporarily checking out main:
```bash
git worktree add /tmp/main-worktree main 2>/dev/null || git worktree add /tmp/main-worktree origin/main
cd /tmp/main-worktree
mkdir -p logs
python3 src/crypto/flask_auto_server.py 8867 > /tmp/main_stdout.log 2>&1 &
echo $! > /tmp/main.pid
cd -
sleep 3
ss -tln | grep 8867
```
Expected: line containing `0.0.0.0:8867`. If the worktree command fails, ask the user before retrying.

- [ ] **Step 2: Start new branch server on port 8866**

Run:
```bash
mkdir -p logs
python3 src/crypto/token_config_server.py 8866 > /tmp/new_stdout.log 2>&1 &
echo $! > /tmp/new.pid
sleep 2
ss -tln | grep 8866
```
Expected: line containing `0.0.0.0:8866`.

- [ ] **Step 3: Capture responses — GET /api/token-config**

Run:
```bash
curl -s http://localhost:8867/api/token-config > /tmp/main_get.json
curl -s http://localhost:8866/api/token-config > /tmp/new_get.json
```
If `main_get.json` is `success: false` due to missing data files in the worktree, fall back to checking that both responses share the same JSON keys and error structure. Skip the literal diff in that case.

- [ ] **Step 4: Capture responses — POST /api/token-config/validate**

Run with a known-good payload:
```bash
curl -s -X POST http://localhost:8867/api/token-config/validate \
  -H 'Content-Type: application/json' \
  -d '{"content":"BTCUSDT 0\nETHUSDT 1\n# comment\nDOGEUSDT 2"}' > /tmp/main_validate.json
curl -s -X POST http://localhost:8866/api/token-config/validate \
  -H 'Content-Type: application/json' \
  -d '{"content":"BTCUSDT 0\nETHUSDT 1\n# comment\nDOGEUSDT 2"}' > /tmp/new_validate.json
```

- [ ] **Step 5: Capture responses — POST /api/token-config/validate (error cases)**

Run with a known-bad payload (invalid level):
```bash
curl -s -X POST http://localhost:8867/api/token-config/validate \
  -H 'Content-Type: application/json' \
  -d '{"content":"BTCUSDT 9\nETHUSDT 1\nBTCUSDT 0"}' > /tmp/main_validate_err.json
curl -s -X POST http://localhost:8866/api/token-config/validate \
  -H 'Content-Type: application/json' \
  -d '{"content":"BTCUSDT 9\nETHUSDT 1\nBTCUSDT 0"}' > /tmp/new_validate_err.json
```
Expected: both responses include `success: false`, `errors` array containing invalid level and duplicate symbol messages. The exact wording may differ if you copy from different sections — verify field structure matches, not literal strings.

- [ ] **Step 6: Capture responses — POST /api/token-config/save (dry-run)**

To avoid clobbering the real config file, first back it up:
```bash
cp src/alert/tokens-config-dynamic.md /tmp/config_backup.md
TEST_CONTENT=$(printf '# test\nBTCUSDT 0\n')
curl -s -X POST http://localhost:8866/api/token-config/save \
  -H 'Content-Type: application/json' \
  -d "{\"content\":\"$TEST_CONTENT\"}" > /tmp/new_save.json
# Restore the file
cp /tmp/config_backup.md src/alert/tokens-config-dynamic.md
```
Expected: `success: true`, message contains "成功" or similar.

- [ ] **Step 7: Diff responses**

Run:
```bash
diff /tmp/main_validate.json /tmp/new_validate.json
diff /tmp/main_validate_err.json /tmp/new_validate_err.json
```
Expected: no output (responses are byte-identical). If `diff` shows differences, re-read lines 1317-1520 of `flask_auto_server.py` against the new file to find the divergence and fix before continuing.

- [ ] **Step 8: HTML template byte-diff**

Run:
```bash
python3 -c "
import sys
sys.path.insert(0, '/tmp/main-worktree/src/crypto')
import flask_auto_server as m1
sys.path.insert(0, 'src/crypto')
import token_config_server as m2
t1 = m1.get_token_config_html_template()
t2 = m2.get_token_config_html_template()
print('IDENTICAL' if t1 == t2 else 'DIFFER')
print(f'main bytes: {len(t1.encode())}')
print(f'new bytes:  {len(t2.encode())}')
"
```
Expected: `IDENTICAL`. If `DIFFER`, fix the template in the new file to match.

- [ ] **Step 9: Stop both servers and clean up**

Run:
```bash
kill $(cat /tmp/main.pid) 2>/dev/null
kill $(cat /tmp/new.pid) 2>/dev/null
rm -f /tmp/main.pid /tmp/new.pid
git worktree remove /tmp/main-worktree --force 2>/dev/null
rm -f /tmp/*.json /tmp/main_stdout.log /tmp/new_stdout.log /tmp/tcs_stdout.log /tmp/config_backup.md
```

- [ ] **Step 10: Commit verification record (only if any fix was needed)**

If Steps 7-8 required fixes, amend or add a new commit. Otherwise no commit.

---

## Task 4: Update Supporting Files

**Files:**
- Modify: `requirements.txt`
- Create: `scripts/crypto/start_token_config.sh`
- Modify: `CLAUDE.md`
- Modify: `env.example`

**Interfaces:**
- Consumes: existing `scripts/crypto/start_flask_auto.sh` (for reference, do not copy unused args)
- Produces: minimal dependency list, new launch script, updated documentation

- [ ] **Step 1: Trim `requirements.txt`**

Replace the entire contents of `requirements.txt` with:
```
flask>=2.0.0
flask-cors>=3.0.0
```

Verify with: `cat requirements.txt`
Expected: two lines as above.

- [ ] **Step 2: Verify deps install cleanly (optional sanity check)**

Run:
```bash
python3 -c "import flask, flask_cors; print('OK', flask.__version__, flask_cors.__version__)"
```
Expected: prints `OK` followed by version numbers. If missing, run `pip3 install flask flask-cors --break-system-packages` first.

- [ ] **Step 3: Create `scripts/crypto/start_token_config.sh`**

File contents:
```bash
#!/bin/bash
# Token 配置管理服务启动脚本

PORT="${1:-5000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/token_config_server.log"
PID_FILE="$PROJECT_ROOT/logs/token_config_server.pid"

mkdir -p "$PROJECT_ROOT/logs"

# 清理旧进程
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "停止旧进程 (PID=$OLD_PID)"
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PID_FILE"
fi
pkill -f token_config_server.py 2>/dev/null
sleep 1

cd "$PROJECT_ROOT"
nohup python3 src/crypto/token_config_server.py "$PORT" >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

sleep 2
if ps -p "$NEW_PID" > /dev/null 2>&1; then
    echo "Token 配置服务已启动"
    echo "  PID:  $NEW_PID"
    echo "  端口: $PORT"
    echo "  访问: http://localhost:$PORT/token-config"
    echo "  日志: $LOG_FILE"
else
    echo "启动失败，请查看日志: $LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi
```

Make executable:
```bash
chmod +x scripts/crypto/start_token_config.sh
```

- [ ] **Step 4: Smoke test the launch script**

Run:
```bash
bash scripts/crypto/start_token_config.sh 8866
```
Expected: prints "Token 配置服务已启动" with PID and URL. Then verify:
```bash
ss -tln | grep 8866
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8866/token-config
```
Expected: port listening, HTTP `200`.

Stop it (the script's PID file logic):
```bash
kill $(cat logs/token_config_server.pid) 2>/dev/null
rm -f logs/token_config_server.pid
```

- [ ] **Step 5: Update `CLAUDE.md`**

Replace the "启动服务" section to describe only the new server. Key edits:
- Change launch command from `bash scripts/crypto/start_flask_auto.sh` to `bash scripts/crypto/start_token_config.sh`
- Change Python entry from `src/crypto/flask_auto_server.py` to `src/crypto/token_config_server.py`
- Remove mentions of Top N代币 / K线条数 parameters (they no longer exist)
- Update dependency install line to only mention `flask flask-cors`
- Remove the entire "Alert 定时任务服务（可选）" section (no scheduler anymore)

Verify by reading the file after editing and confirming no references to the old server name or removed sections remain.

- [ ] **Step 6: Simplify `env.example`**

Inspect current `env.example` content. Remove variables that are no longer used by the new server (BINANCE_API_KEY, BINANCE_SECRET_KEY, WECOM_WEBHOOK_URL, OKX_*, POLYGON_* etc.). Keep an empty placeholder section:
```
# 当前服务无必需环境变量
# 以下为预留扩展项（暂未使用）
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt scripts/crypto/start_token_config.sh CLAUDE.md env.example
git commit -m "chore: update supporting files for standalone token-config server"
```

---

## Task 5: Remove Unused Modules

**Files:**
- Delete:
  - `src/crypto/flask_auto_server.py`
  - `src/crypto/fetch_multi_period_data.py` (and any sibling helpers in `src/crypto/` other than `token_config_server.py`)
  - `src/crypto/token_filter_multi_period.py`
  - `src/crypto/__init__.py` if present and unused
  - All other `src/crypto/` files except `token_config_server.py` and any `__init__.py` needed
  - `src/alert/combined_scheduler.py`
  - `src/alert/crypto_reversal_detector.py`
  - `src/alert/monitor_config.py`
  - `src/alert/price_updater.py`
  - `src/alert/tokens-config.md`
  - Entire `src/database/`, `src/metal/`, `src/equity/`, `src/futu/`, `src/data/` directories
  - All files in `scripts/crypto/` except `start_token_config.sh`
  - `data/` directory if empty after deletion (decide based on `ls data/`)
- Preserve:
  - `src/alert/tokens-config-dynamic.md`
  - `src/crypto/token_config_server.py`
  - `scripts/crypto/start_token_config.sh`
  - `logs/`

**Interfaces:**
- Consumes: current working tree state from end of Task 4
- Produces: a working tree containing only the files listed under "Preserve" plus updated supporting files from Task 4

- [ ] **Step 1: Snapshot the config file before deletion**

Run:
```bash
ls -la src/alert/
md5sum src/alert/tokens-config-dynamic.md
```
Expected: file exists. Record the md5sum to compare after deletion that nothing in it changed.

- [ ] **Step 2: Delete `src/alert/` non-data files**

Run:
```bash
rm -f src/alert/combined_scheduler.py
rm -f src/alert/crypto_reversal_detector.py
rm -f src/alert/monitor_config.py
rm -f src/alert/price_updater.py
rm -f src/alert/tokens-config.md
ls -la src/alert/
```
Expected: directory contains only `tokens-config-dynamic.md`.

- [ ] **Step 3: Delete other crypto files**

Run:
```bash
rm -f src/crypto/flask_auto_server.py
# List what's left before continuing
ls src/crypto/
```
Inspect the listing. Remove every file in `src/crypto/` except `token_config_server.py`. If `__init__.py` exists, decide based on whether it's imported elsewhere — in this refactor it should NOT be needed; delete it. Example:
```bash
rm -f src/crypto/fetch_multi_period_data.py
rm -f src/crypto/token_filter_multi_period.py
# ...repeat for any other files shown
ls src/crypto/
```
Expected: directory contains only `token_config_server.py` (and possibly an empty `__init__.py` if present).

- [ ] **Step 4: Delete entire subdirectories**

Run:
```bash
rm -rf src/database/
rm -rf src/metal/
rm -rf src/equity/
rm -rf src/futu/
rm -rf src/data/
ls src/
```
Expected: `src/` contains only `crypto/` and `alert/`.

- [ ] **Step 5: Delete unused scripts**

Run:
```bash
# Identify what to keep vs delete
ls scripts/crypto/
# Keep only start_token_config.sh
cd scripts/crypto/ && ls | grep -v '^start_token_config.sh$' | xargs -I {} rm -f {} && cd ../..
ls scripts/crypto/
```
Expected: directory contains only `start_token_config.sh`.

- [ ] **Step 6: Verify config file unchanged**

Run:
```bash
md5sum src/alert/tokens-config-dynamic.md
```
Expected: matches the value recorded in Step 1.

- [ ] **Step 7: Commit**

```bash
git add -A
git status   # review the deletion list before committing
git commit -m "chore: remove unused modules, keep only token-config functionality"
```

If `git status` shows unexpected files (e.g., `tokens-config-dynamic.md` modified, or new untracked files), STOP and investigate before committing.

---

## Task 6: Final End-to-End Verification

**Files:**
- No new files. Verification only.

**Interfaces:**
- Consumes: clean working tree from end of Task 5
- Produces: confirmation that the new branch is independently runnable

- [ ] **Step 1: Confirm clean state**

Run:
```bash
git status
git log --oneline -7
```
Expected: working tree clean. Recent commits in order: spec commit, feat extract server, chore supporting files, chore remove unused.

- [ ] **Step 2: Confirm directory layout matches spec**

Run:
```bash
find src scripts -type f | sort
```
Expected output contains ONLY:
- `src/alert/tokens-config-dynamic.md`
- `src/crypto/token_config_server.py`
- `scripts/crypto/start_token_config.sh`

- [ ] **Step 3: Cold-start launch via script**

Run:
```bash
bash scripts/crypto/start_token_config.sh 8866
sleep 2
ss -tln | grep 8866
curl -s -o /dev/null -w 'page: %{http_code}\n' http://localhost:8866/token-config
curl -s -o /dev/null -w 'api:  %{http_code}\n' http://localhost:8866/api/token-config
```
Expected: server listening, both endpoints return `200`.

- [ ] **Step 4: End-to-end write/read cycle**

Run:
```bash
# Save a known config
curl -s -X POST http://localhost:8866/api/token-config/save \
  -H 'Content-Type: application/json' \
  -d '{"content":"# final test\nBTCUSDT 1\n"}'
echo
# Read it back
curl -s http://localhost:8866/api/token-config | python3 -m json.tool
```
Expected: save response `success: true`; read response contains the saved content with line numbers preserved.

- [ ] **Step 5: Validation roundtrip**

Run:
```bash
curl -s -X POST http://localhost:8866/api/token-config/validate \
  -H 'Content-Type: application/json' \
  -d '{"content":"BTCUSDT 5\nINVALID\nBTCUSDT 0"}' | python3 -m json.tool
```
Expected: `success: false`, `errors` array contains entries for invalid level and duplicate symbol. `tokens` array contains only valid entries.

- [ ] **Step 6: Stop server and clean up**

Run:
```bash
kill $(cat logs/token_config_server.pid) 2>/dev/null
rm -f logs/token_config_server.pid
```

- [ ] **Step 7: Final commit if any cleanup needed**

If any temp files were left in the working tree, remove them and commit:
```bash
git status
# remove any temp files
git add -A
git commit -m "chore: post-refactor cleanup" --allow-empty
```

Otherwise no commit — verification is the deliverable.

---

## Summary

After all 6 tasks, the `refactor/token-config-only` branch will:
- Contain exactly 3 source files: `src/crypto/token_config_server.py`, `src/alert/tokens-config-dynamic.md`, `scripts/crypto/start_token_config.sh`
- Plus updated `requirements.txt`, `CLAUDE.md`, `env.example`
- Provide identical `/token-config` behavior to main branch (verified via byte-diff and JSON diff)
- Run as a standalone Flask app with only `flask` + `flask-cors` dependencies