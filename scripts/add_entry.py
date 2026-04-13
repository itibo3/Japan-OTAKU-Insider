#!/usr/bin/env python3
"""
JSONエントリーをメインDBに追加するスクリプト
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

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

UNTRANSLATED_PREFIX = "[未翻訳]"


def has_untranslated_marker(entry):
    """title または description に [未翻訳] プレースホルダが残っているか確認する"""
    title = entry.get("title", "") or ""
    description = entry.get("description", "") or ""
    return title.strip().startswith(UNTRANSLATED_PREFIX) or description.strip().startswith(UNTRANSLATED_PREFIX)


def has_low_quality_source_url(entry):
    """トップページ等の中身が薄いURLを簡易判定で弾く（主に Perplexity 由来）。"""
    source_url = ((entry.get("source") or {}).get("url") or "").strip()
    if not source_url:
        return False
    if entry.get("_source_id") == "joi-weekly" and source_url.startswith("/weekly.html"):
        return False
    try:
        parsed = urlparse(source_url)
    except Exception:
        return True
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return True
    # Perplexity はトップURLをでっち上げる傾向があるため、root / index は登録しない
    if entry.get("_source") == "perplexity":
        path = (parsed.path or "").strip().lower()
        if path in ("", "/", "/index.html", "/index.php", "/home", "/top"):
            return True
        depth = len([x for x in path.split("/") if x])
        if depth <= 1 and not parsed.query:
            return True
    return False


def add_entries_from_file(filepath, reset=False):
    """Geminiの出力JSONファイルからエントリーを追加。reset=True のときは既存を空にしてから追加"""
    with open(filepath, 'r', encoding='utf-8') as f:
        new_entries = json.load(f)

    # 配列でない場合（単一エントリー）は配列に変換
    if isinstance(new_entries, dict):
        new_entries = [new_entries]

    db = load_entries()
    if reset:
        db["entries"] = []
        print("  (reset: entries を空にしました)")
    existing_entries = db["entries"]

    added = 0
    for entry in new_entries:
        normalize_categories(entry)
        # 週刊JOIを追加する場合、既存JOIは archive 扱いにして pinned_top を外す
        if entry.get("_source_id") == "joi-weekly":
            for e in db["entries"]:
                if e.get("_source_id") == "joi-weekly" or e.get("_source") == "joi-weekly":
                    if e.get("pinned_top"):
                        e["pinned_top"] = False
                    e["_weekly_archived"] = True
            entry["pinned_top"] = True
            entry["_weekly_archived"] = False
        title = (entry.get("title") or "").strip()
        desc = (entry.get("description") or "").strip()
        if not title or not desc:
            title_disp = entry.get('title_ja', title or 'Unknown')
            print(f"  SKIP (empty field): {title_disp[:60]} — title/description が空")
            continue
        # 翻訳未完了チェック: [未翻訳] プレースホルダが残っている記事は登録しない
        if has_untranslated_marker(entry):
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (未翻訳): {title_disp[:60]} — title/description に [未翻訳] が残っています")
            continue
        # 品質チェック: トップページ等の薄いURLは除外
        if has_low_quality_source_url(entry):
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (source quality): {title_disp[:60]} — URL がトップ/不正形式の可能性")
            continue
        is_dup, reason, is_warn = check_duplicate(entry, existing_entries)
        
        if is_dup:
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (duplicate): {title_disp} — 理由: {reason}")
        else:
            if is_warn:
                print(f"  ⚠ WARNING: \"{entry.get('title', 'Unknown')}\" may be similar to {reason} — 確認してください")
            
            db["entries"].insert(0, entry)
            added += 1
            print(f"  Added: {entry.get('title', 'Unknown')}")

    save_entries(db)
    print(f"\n{added} entries added. Total: {db['total_entries']}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python add_entry.py [--reset] <gemini_output.json>")
        print("  --reset : entries を空にしてから追加（リセット後の再構築用）")
        sys.exit(1)

    reset = "--reset" in args
    if reset:
        args = [a for a in args if a != "--reset"]
    filepath = args[-1] if args else ""
    if not filepath or filepath.startswith("--"):
        print("ERROR: ファイルパスを指定してください")
        sys.exit(1)

    add_entries_from_file(filepath, reset=reset)
