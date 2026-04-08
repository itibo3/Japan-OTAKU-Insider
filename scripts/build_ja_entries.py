#!/usr/bin/env python3
"""
build_ja_entries.py
entries.json から entries_ja.json を生成する。
title_ja が存在するエントリは title として title_ja を使い、
description_ja があれば description として使う。
なければ元の英語フィールドをそのまま使う（フォールバック）。
"""

import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE_DIR, "data", "entries.json")
DST = os.path.join(BASE_DIR, "data", "entries_ja.json")


UNTRANSLATED_PREFIX = "[未翻訳]"


def has_untranslated_marker(title: str) -> bool:
    """title に [未翻訳] プレースホルダが含まれるか確認する"""
    return (title or "").strip().startswith(UNTRANSLATED_PREFIX)


def build():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    ja_entries = []
    fallback_count = 0
    untranslated_count = 0

    for entry in entries:
        e = dict(entry)
        # title_ja があれば title に適用
        if e.get("title_ja"):
            e["title"] = e["title_ja"]
        else:
            # title_ja がない場合: 英語フィールドをそのまま使用（フォールバック）
            fallback_count += 1
            if has_untranslated_marker(e.get("title", "")):
                untranslated_count += 1
                print(f"  [WARN] 未翻訳フォールバック: {e.get('id', 'unknown')} — {e.get('title', '')[:60]}")
        # description_ja があれば description に適用
        if e.get("description_ja"):
            e["description"] = e["description_ja"]
        ja_entries.append(e)

    out = {
        "last_updated": data.get("last_updated", datetime.now(timezone.utc).isoformat()),
        "total_entries": len(ja_entries),
        "lang": "ja",
        "entries": ja_entries,
    }

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✅ entries_ja.json を生成しました（{len(ja_entries)} 件）")
    title_ja_count = sum(1 for e in entries if e.get("title_ja"))
    print(f"   title_ja あり: {title_ja_count} 件 / {len(entries)} 件")
    if fallback_count:
        print(f"   英語フォールバック: {fallback_count} 件（うち [未翻訳] マーカあり: {untranslated_count} 件）")


if __name__ == "__main__":
    build()
