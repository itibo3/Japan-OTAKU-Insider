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

def normalize_categories(entry):
    """
    category（単数）を categories（配列）に正規化する。
    後方互換のため、category が混入していても categories に統一する。
    """
    if "category" in entry:
        cat = entry.pop("category", None)
        entry["categories"] = [cat] if cat else ["event"]
    elif "categories" in entry and isinstance(entry["categories"], list):
        return
    else:
        entry["categories"] = entry.get("categories", ["event"])
    if not isinstance(entry["categories"], list):
        entry["categories"] = [entry["categories"]] if entry["categories"] else ["event"]


def check_duplicate(new_entry, existing_entries):
    """
    重複チェック
    Returns: (is_duplicate: bool, reason: str, is_warning: bool)
    """
    new_id = new_entry.get("id", "")
    new_title = new_entry.get("title", "")
    new_title_ja = new_entry.get("title_ja", "")
    new_source_url = new_entry.get("source", {}).get("url", "")

    for existing in existing_entries:
        ex_id = existing.get("id", "")
        ex_title = existing.get("title", "")
        ex_title_ja = existing.get("title_ja", "")
        ex_source_url = existing.get("source", {}).get("url", "")

        # チェック1: ID完全一致
        if new_id and new_id == ex_id:
            return True, f"ID一致", False

        # チェック2: 英語タイトル完全一致
        if new_title and new_title == ex_title:
            return True, f"タイトル一致", False

        # チェック3: 日本語タイトル完全一致
        if new_title_ja and new_title_ja == ex_title_ja:
            return True, f"日本語タイトル一致", False

        # チェック4: ソースURL完全一致
        if new_source_url and new_source_url == ex_source_url:
            return True, f"ソースURL一致", False

        # チェック5: タイトル類似（包含関係）→ 警告のみ
        if new_title and ex_title:
            new_lower = new_title.lower()
            ex_lower = ex_title.lower()
            if len(new_lower) > 10 and len(ex_lower) > 10:  # 短すぎる場合は除外
                if new_lower in ex_lower or ex_lower in new_lower:
                    return False, f"既存「{ex_title}」", True

    return False, "", False

def add_entries_from_file(filepath):
    """Geminiの出力JSONファイルからエントリーを追加"""
    with open(filepath, 'r', encoding='utf-8') as f:
        new_entries = json.load(f)

    # 配列でない場合（単一エントリー）は配列に変換
    if isinstance(new_entries, dict):
        new_entries = [new_entries]

    db = load_entries()
    existing_entries = db["entries"]

    added = 0
    for entry in new_entries:
        normalize_categories(entry)
        is_dup, reason, is_warn = check_duplicate(entry, existing_entries)
        
        if is_dup:
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (duplicate): {title_disp} — 理由: {reason}")
        else:
            if is_warn:
                print(f"  ⚠ WARNING: \"{entry.get('title', 'Unknown')}\" may be similar to {reason} — 確認してください")
            
            db["entries"].append(entry)
            added += 1
            print(f"  Added: {entry.get('title', 'Unknown')}")

    save_entries(db)
    print(f"\n{added} entries added. Total: {db['total_entries']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_entry.py <gemini_output.json>")
        print("  or:  python add_entry.py --from <filepath>")
        sys.exit(1)

    filepath = sys.argv[-1]
    add_entries_from_file(filepath)
