#!/usr/bin/env python3
"""
entries.json をリセットし、RSS から全件取得して再構築するスクリプト

流れ:
1. entries.json をバックアップ
2. rss_fetch --reset で全 RSS ソースから取得（重複チェックなし、サムネ付き）
3. 出力: data/staging/reset_YYYYMMDD_HHMM.json

次のステップ:
  python3 scripts/translate_staging.py data/staging/reset_*.json
  python3 scripts/add_entry.py --reset data/staging/reset_*.json

使い方:
  python3 scripts/reset_entries_from_rss.py
  python3 scripts/reset_entries_from_rss.py --limit 15  # 1ソースあたりの上限
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENTRIES_FILE = PROJECT_ROOT / "data" / "entries.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="1ソースあたりの上限件数")
    parser.add_argument("--no-backup", action="store_true", help="entries.json のバックアップをスキップ")
    args = parser.parse_args()

    if ENTRIES_FILE.exists() and not args.no_backup:
        backup_path = PROJECT_ROOT / "data" / f"entries.json.backup_reset_{datetime.now(JST).strftime('%Y%m%d_%H%M')}"
        shutil.copy2(ENTRIES_FILE, backup_path)
        print(f"Backed up entries.json -> {backup_path.name}")

    cmd = [sys.executable, str(SCRIPT_DIR / "rss_fetch.py"), "--reset", "--limit", str(args.limit)]
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)


if __name__ == "__main__":
    main()
