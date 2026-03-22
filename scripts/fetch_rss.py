#!/usr/bin/env python3
"""
RSS自動取得 → JSON変換スクリプト
1日1回cronまたは手動で実行
"""

import feedparser
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
DATA_DIR = Path("data")
ENTRIES_FILE = DATA_DIR / "entries.json"
SOURCES_FILE = DATA_DIR / "sources.json"

def load_entries():
    """既存エントリーを読み込み"""
    if ENTRIES_FILE.exists():
        with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_updated": "", "total_entries": 0, "entries": []}

def load_sources():
    """情報ソース一覧を読み込み"""
    with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_id(category, title):
    """エントリーIDを生成"""
    today = datetime.now(JST).strftime("%Y%m%d")
    hash_suffix = hashlib.md5(title.encode()).hexdigest()[:6]
    return f"{category}-{today}-{hash_suffix}"

def is_duplicate(entries, url):
    """URLベースの重複チェック"""
    existing_urls = [e.get("source", {}).get("url", "") for e in entries]
    return url in existing_urls

def fetch_rss_entries(source):
    """
    RSSフィードからエントリーを取得
    返り値: 仮エントリーのリスト（英訳前の日本語データ）
    """
    if not source.get("rss"):
        return []

    feed = feedparser.parse(source["rss"])
    raw_entries = []

    for item in feed.entries[:10]:  # 最新10件
        raw_entries.append({
            "title_ja": item.get("title", ""),
            "description_ja": item.get("summary", "")[:500],
            "url": item.get("link", ""),
            "published": item.get("published", ""),
            "source_id": source["id"],
            "source_name": source["name"],
            "categories": source["categories"]
        })

    return raw_entries

def save_raw_for_translation(raw_entries, output_path="data/pending_translation.json"):
    """
    英訳待ちのエントリーをJSONで保存
    この後Geminiに投げて英訳＋カテゴリ判定＋構造化してもらう
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "fetched_at": datetime.now(JST).isoformat(),
            "count": len(raw_entries),
            "raw_entries": raw_entries
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(raw_entries)} entries to {output_path}")

def main():
    sources = load_sources()
    db = load_entries()
    all_raw = []

    for source in sources["sources"]:
        if source["type"] == "rss":
            raw = fetch_rss_entries(source)
            # 重複除外
            raw = [r for r in raw if not is_duplicate(db["entries"], r["url"])]
            all_raw.extend(raw)
            print(f"[{source['name']}] {len(raw)} new entries")

    if all_raw:
        save_raw_for_translation(all_raw)
        print(f"\nTotal: {len(all_raw)} new entries ready for translation")
        print("Next step: Run Gemini translation with gemini_json_convert prompt")
    else:
        print("No new entries found.")

if __name__ == "__main__":
    main()
