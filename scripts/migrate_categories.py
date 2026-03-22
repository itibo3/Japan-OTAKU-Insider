#!/usr/bin/env python3
"""
entries.json の category(単数) を categories(配列) に移行する。

方針:
- 既存の entries を壊さない（categories が既にあるなら触らない）
- 実行前に data/entries.json をバックアップする
- 変換後は category を削除する
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path


JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path("data/entries.json")


def main() -> None:
    if not ENTRIES_FILE.exists():
        raise SystemExit(f"ERROR: {ENTRIES_FILE} が見つかりません")

    raw = ENTRIES_FILE.read_text(encoding="utf-8")
    try:
        db = json.loads(raw)
    except Exception as e:
        raise SystemExit(f"ERROR: JSON読み込みに失敗: {e}")

    entries = db.get("entries")
    if not isinstance(entries, list):
        raise SystemExit("ERROR: entries.json の entries が list ではありません")

    backup = ENTRIES_FILE.with_name(
        f"entries.json.backup_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy2(ENTRIES_FILE, backup)

    migrated = 0
    skipped = 0
    for entry in entries:
        if not isinstance(entry, dict):
            skipped += 1
            continue

        if isinstance(entry.get("categories"), list):
            continue

        cat = entry.get("category")
        if isinstance(cat, str) and cat.strip():
            entry["categories"] = [cat.strip()]
            entry.pop("category", None)
            migrated += 1
        else:
            # category が無い/空の場合は categories は作らず、そのまま
            skipped += 1

    # メタ更新
    db["last_updated"] = datetime.now(JST).isoformat()
    db["total_entries"] = len(entries)

    ENTRIES_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: backup={backup}")
    print(f"OK: migrated={migrated}, skipped={skipped}, total={len(entries)}")


if __name__ == "__main__":
    main()

