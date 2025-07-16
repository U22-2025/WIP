#!/usr/bin/env bash
# ------------------------------------------------------------------
# WIP サーバー群を Ubuntu + tmux で一括起動
# ------------------------------------------------------------------

set -euo pipefail

# 1) 作業ディレクトリ & PYTHONPATH
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${CURRENT_DIR}:${PYTHONPATH:-}"

# 2) Conda をどこからでも呼べるように初期化スニペット
CONDA_INIT='source ~/miniforge3/etc/profile.d/conda.sh && conda activate U22-WIP'

# 3) 新規 tmux セッションを作成（既存なら attach）
SESSION="wip"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "既に $SESSION セッションが走っています → そのまま attach します"
  exec tmux attach -t "$SESSION"
fi

tmux new-session  -d -s "$SESSION" -c "$CURRENT_DIR" \
  "$CONDA_INIT && python python/launch_server.py --weather  --debug"

tmux split-window -v  -t "$SESSION":0 -c "$CURRENT_DIR" \
  "$CONDA_INIT && python python/launch_server.py --query    --debug"

tmux select-pane  -t "$SESSION":0.0        # ← 元 bat の focus-pane 相当
tmux split-window -h  -t "$SESSION":0 -c "$CURRENT_DIR" \
  "$CONDA_INIT && python python/launch_server.py --location --debug"

tmux select-pane  -t "$SESSION":0.1
tmux split-window -h  -t "$SESSION":0 -c "$CURRENT_DIR" \
  "$CONDA_INIT && python python/launch_server.py --report   --debug"

tmux split-window -v  -t "$SESSION":0.3 -c "$CURRENT_DIR" \
  "$CONDA_INIT && python python/application/map/start_fastapi_server.py --debug"

tmux select-layout -t "$SESSION":0 tiled   # 見やすくタイル配置
tmux select-pane   -t "$SESSION":0.0       # 最初のペインにカーソル
tmux set-option    -t "$SESSION":0 remain-on-exit on  # 異常終了を確認しやすく

# 4) ブラウザを自動起動（GUI 環境前提）
xdg-open 'http://localhost:5000' >/dev/null 2>&1 &

echo "🐧 すべてのサーバーを起動しました。tmux 画面へ切り替えます。"
exec tmux attach -t "$SESSION"
