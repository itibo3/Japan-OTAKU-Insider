#!/bin/bash
# RSS Manager を起動するスクリプト（ダブルクリックで実行可能）
cd "$(dirname "$0")"

# .venv があれば activate する
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

python3 rss_manager.py
read -p "終了するには Enter キーを押してください..."
