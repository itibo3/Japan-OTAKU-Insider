#!/usr/bin/env python3
"""
JSONエントリーをメインDBに追加するスクリプト
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path("data/entries.json")

def load_entries():
    if ENTRIES_FILE.exists():
        with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_updated": "", "total_entries": 0, "entries": []}

def save_entries(db):
    db["last_updated"] = datetime.now(JST).isoformat()
    db["total_entries"] = len(db["entries"])
    with open(ENTRIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def add_entries_from_file(filepath):
    """Geminiの出力JSONファイルからエントリーを追加"""
    with open(filepath, 'r', encoding='utf-8') as f:
        new_entries = json.load(f)

    # 配列でない場合（単一エントリー）は配列に変換
    if isinstance(new_entries, dict):
        new_entries = [new_entries]

    db = load_entries()
    existing_ids = {e["id"] for e in db["entries"]}

    added = 0
    for entry in new_entries:
        if entry["id"] not in existing_ids:
            db["entries"].append(entry)
            added += 1
            print(f"  Added: {entry['title']}")
        else:
            print(f"  Skip (duplicate): {entry['title']}")

    save_entries(db)
    print(f"\n{added} entries added. Total: {db['total_entries']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_entry.py <gemini_output.json>")
        print("  or:  python add_entry.py --from <filepath>")
        sys.exit(1)

    filepath = sys.argv[-1]
    add_entries_from_file(filepath)
