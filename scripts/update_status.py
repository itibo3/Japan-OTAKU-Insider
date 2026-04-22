#!/usr/bin/env python3
"""
日付ベースでステータスを自動更新
- 終了日を過ぎたエントリー → "ended"
- 開始日前のエントリー → "upcoming"
- 開催中のエントリー → "active"
- 開始/終了日が無い通常記事は、公開日から一定日数で "ended" にする
"""

import json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
ENTRIES_FILE = ROOT / "data" / "entries.json"
# 通常ニュースの鮮度管理。45日を過ぎたら ended 扱いにする。
ACTIVE_WINDOW_DAYS = 45


def _parse_display_date(dates: dict) -> date | None:
    """dates.display から公開日を推定して date を返す。"""
    raw = (dates.get("display") or "").strip()
    if not raw:
        return None
    # 例: 2026-04-22, 2026-04-22T12:00:00+09:00
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    # 例: Apr 22, 2026
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None

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

        # 開始/終了日がない通常ニュースは、公開日ベースで鮮度を落とす
        if not start_date and not end_date:
            published = _parse_display_date(dates)
            if published:
                age_days = (today - published).days
                if age_days > ACTIVE_WINDOW_DAYS:
                    new_status = "ended"
                else:
                    new_status = "active"

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
