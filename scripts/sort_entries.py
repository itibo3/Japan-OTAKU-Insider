#!/usr/bin/env python3
"""
entries.json のエントリを並べ替えるスクリプト

id 形式 {category}-{YYYYMMDD}-{suffix} から日付を抽出してソートする。
デフォルトは新着順（降順）。

使い方:
  python3 scripts/sort_entries.py                    # 新着順（デフォルト）
  python3 scripts/sort_entries.py --oldest-first     # 古い順
"""

import argparse
import calendar
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path(__file__).resolve().parent.parent / "data" / "entries.json"

# id から日付部分を抽出: cafe-20260316-rss-abc123 → 20260316 / cafe-202603161900-rss-abc123 → 202603161900
ID_DATE_RE = re.compile(r"^\w+-(\d{8,12})-")
# dates.display から YYYY-MM-DD を抽出（範囲の場合は最後の日付を採用）
ISO_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
ISO_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def parse_date_for_sort(entry):
    """dates.display からソート用 YYYYMMDD を抽出。パース失敗時は None"""
    dates_val = entry.get("dates")
    display = ""
    if isinstance(dates_val, dict):
        display = dates_val.get("display", "") or ""
    elif isinstance(dates_val, str):
        display = dates_val
    if not display or not isinstance(display, str):
        return None

    # 1. YYYY-MM-DD を正規表現で抽出（複数あれば最後を採用＝範囲の終了日）
    iso_matches = list(ISO_DATE_RE.finditer(display))
    if iso_matches:
        m = iso_matches[-1]
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"

    # 2. YYYY-MM のみの場合（月の末日で扱う）
    mm = ISO_MONTH_RE.search(display.strip())
    if mm:
        y, mon = int(mm.group(1)), int(mm.group(2))
        if 1 <= mon <= 12:
            last_day = calendar.monthrange(y, mon)[1]
            return f"{y:04d}{mon:02d}{last_day:02d}"

    # 3. "Mar 19, 2026" 形式
    try:
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y"):
            try:
                dt = datetime.strptime(display.strip(), fmt)
                return dt.strftime("%Y%m%d")
            except ValueError:
                continue
    except Exception:
        pass
    return None


def id_date_from_id(eid):
    """id から日付部分を抽出して12桁にパディング"""
    m = ID_DATE_RE.match(eid or "")
    if m:
        return m.group(1).ljust(12, "0")
    return "000000000000"


def extract_sort_key(entry):
    eid = entry.get("id", "")
    return (id_date_from_id(eid), eid)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--oldest-first", action="store_true", help="古い順にソート")
    parser.add_argument("--dry-run", action="store_true", help="変更せず先頭5件の並びだけ表示")
    args = parser.parse_args()

    descending = not args.oldest_first

    if not ENTRIES_FILE.exists():
        print(f"ERROR: {ENTRIES_FILE} が見つかりません")
        raise SystemExit(1)

    data = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        print("ERROR: entries が配列ではありません")
        raise SystemExit(1)

    sorted_entries = sorted(entries, key=extract_sort_key, reverse=descending)

    if args.dry_run:
        print(f"Dry run: 先頭5件 ({'新着順' if descending else '古い順'})")
        for i, e in enumerate(sorted_entries[:5]):
            print(f"  {i+1}. {e.get('id','')} — {e.get('title','')[:50]}")
        return

    data["entries"] = sorted_entries
    data["last_updated"] = datetime.now(JST).isoformat()
    data["total_entries"] = len(sorted_entries)

    ENTRIES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Sorted {len(sorted_entries)} entries ({'newest first' if descending else 'oldest first'})")


if __name__ == "__main__":
    main()
