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
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path(__file__).resolve().parent.parent / "data" / "entries.json"

# id から日付部分を抽出: cafe-20260316-rss-abc123 → 20260316 / cafe-202603161900-rss-abc123 → 202603161900
ID_DATE_RE = re.compile(r"^\w+-(\d{8,12})-")


def extract_sort_key(entry):
    """ソート用キー。id の日付部分を使用。8桁は0000でパディングし12桁で比較"""
    eid = entry.get("id", "")
    m = ID_DATE_RE.match(eid)
    if m:
        part = m.group(1).ljust(12, "0")
    else:
        part = "000000000000"
    return (part, eid)


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
