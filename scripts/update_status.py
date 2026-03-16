#!/usr/bin/env python3
"""
日付ベースでステータスを自動更新
- 終了日を過ぎたエントリー → "ended"
- 開始日前のエントリー → "upcoming"
- 開催中のエントリー → "active"
"""

import json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path("data/entries.json")

def update_statuses():
    with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
        db = json.load(f)

    today = date.today()
    updated = 0

    for entry in db["entries"]:
        dates = entry.get("dates")
        if not dates:
            continue

        old_status = entry.get("status")
        new_status = old_status

        end_date = dates.get("end")
        start_date = dates.get("start")

        if end_date:
            try:
                end = date.fromisoformat(end_date)
                if today > end:
                    new_status = "ended"
            except ValueError:
                pass

        if start_date:
            try:
                start = date.fromisoformat(start_date)
                if today < start:
                    new_status = "upcoming"
                elif not end_date or today <= date.fromisoformat(end_date):
                    new_status = "active"
            except ValueError:
                pass

        if new_status != old_status:
            entry["status"] = new_status
            entry["updated"] = datetime.now(JST).isoformat()
            updated += 1
            print(f"  {entry['title']}: {old_status} -> {new_status}")

    if updated > 0:
        db["last_updated"] = datetime.now(JST).isoformat()
        with open(ENTRIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n{updated} entries updated.")

if __name__ == "__main__":
    update_statuses()
