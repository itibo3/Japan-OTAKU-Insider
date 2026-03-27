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


def build():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    ja_entries = []

    for entry in entries:
        e = dict(entry)
        # title_ja があれば title に適用
        if e.get("title_ja"):
            e["title"] = e["title_ja"]
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


if __name__ == "__main__":
    build()
