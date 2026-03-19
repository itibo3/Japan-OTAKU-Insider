"""
作品ジャーニー — series_id 自動タグ付けスクリプト

目的: entries.json のエントリーに series_id を自動付与し、同じ作品のエントリーを紐付ける
入力: data/entries.json
出力: data/entries.json（series_id フィールドを追加/更新）

方式: title_ja のカギカッコ内テキスト or title の引用符内テキストで、
      2回以上登場する作品名を検出し、slug化した series_id を付与する
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRIES_FILE = PROJECT_ROOT / "data" / "entries.json"


def slugify(text: str) -> str:
    """作品名をスラグ化（series_id に使用）"""
    text = unicodedata.normalize("NFKC", text).lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:60] if text else ""


def extract_work_titles(entry: dict) -> list[str]:
    """エントリーのタイトルから作品名候補を抽出"""
    titles = []
    ja = entry.get("title_ja", "") or ""
    en = entry.get("title", "") or ""

    for m in re.findall(r"「([^」]+)」", ja):
        if len(m) > 2:
            titles.append(m)
    for m in re.findall(r'"([^"]+)"', en):
        if len(m) > 2:
            titles.append(m)
    return titles


def main():
    with open(ENTRIES_FILE) as f:
        data = json.load(f)
    entries = data["entries"]

    title_counter: Counter[str] = Counter()
    entry_titles: dict[str, list[str]] = {}

    for e in entries:
        eid = e.get("id", "")
        works = extract_work_titles(e)
        entry_titles[eid] = works
        for w in works:
            title_counter[w] += 1

    recurring = {t for t, c in title_counter.items() if c >= 2}
    print(f"Detected {len(recurring)} recurring series across {len(entries)} entries.")

    tagged = 0
    for e in entries:
        eid = e.get("id", "")
        works = entry_titles.get(eid, [])
        matched = [w for w in works if w in recurring]
        if matched:
            best = max(matched, key=lambda w: title_counter[w])
            sid = slugify(best)
            if sid:
                e["series_id"] = sid
                e["series"] = best
                tagged += 1

    with open(ENTRIES_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Tagged {tagged} entries with series_id.")

    series_groups: Counter[str] = Counter()
    for e in entries:
        sid = e.get("series_id")
        if sid:
            series_groups[sid] += 1
    print("\nSeries groups:")
    for sid, count in series_groups.most_common():
        print(f"  {sid}: {count} entries")


if __name__ == "__main__":
    main()
