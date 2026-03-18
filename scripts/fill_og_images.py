#!/usr/bin/env python3
"""
fill_og_images.py — entries.json の missing thumbnail を埋める

狙い:
- cards/list & modal のサムネ表示を安定させるために
- 各 entry の `source.url` 先HTMLから `meta[property="og:image"]` を抽出して
  `entry.thumbnail` として書き込む

実行例:
  python3 scripts/fill_og_images.py --only-missing
  python3 scripts/fill_og_images.py --limit 20
"""

import argparse
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path("data/entries.json")

META_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)
META_OG_IMAGE_SECURE_RE = re.compile(
    r'<meta[^>]+property=[\'"]og:image:secure_url[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)


def load_db() -> dict:
    with open(ENTRIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db: dict) -> None:
    db["last_updated"] = datetime.now(JST).isoformat()
    db["total_entries"] = len(db.get("entries", []))
    with open(ENTRIES_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def fetch_html(url: str, timeout_sec: int, max_bytes: int) -> str:
    req = Request(
        url,
        headers={
            # ブラウザっぽくして取得失敗を減らす
            "User-Agent": "Mozilla/5.0 (compatible; JapanOTAKUInsiderBot/1.0; +https://itibo3.github.io/Japan-OTAKU-Insider/)"
        },
    )
    with urlopen(req, timeout=timeout_sec) as resp:
        # 取りすぎない（軽量化）
        raw = resp.read(max_bytes)
        # URL側の charset を面倒見る代わりに、まずutf-8優先→だめなら置換
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return raw.decode("latin-1", errors="replace")


def extract_og_image(html: str) -> Optional[str]:
    m = META_OG_IMAGE_RE.search(html)
    if m and m.group(1).strip():
        return m.group(1).strip()
    m = META_OG_IMAGE_SECURE_RE.search(html)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return None


def normalize_thumb_url(og_url: str, source_url: str) -> str:
    og_url = og_url.strip()
    if og_url.startswith("//"):
        return "https:" + og_url
    if og_url.startswith("http://") or og_url.startswith("https://"):
        return og_url
    return urljoin(source_url, og_url)


def should_process(entry: dict, only_missing: bool) -> bool:
    if not only_missing:
        return True
    thumb = entry.get("thumbnail")
    if thumb is None:
        return True
    if isinstance(thumb, str) and not thumb.strip():
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-missing", action="store_true", default=False, help="thumbnail が未設定/空だけ処理する")
    parser.add_argument("--limit", type=int, default=0, help="処理件数の上限（0は無制限）")
    parser.add_argument("--timeout", type=int, default=15, help="1サイトあたりのタイムアウト（秒）")
    parser.add_argument("--sleep", type=float, default=0.6, help="サイト取得間の待機（秒）")
    parser.add_argument("--max-bytes", type=int, default=2_000_000, help="取得するHTMLの最大サイズ（バイト）")
    args = parser.parse_args()

    if not ENTRIES_FILE.exists():
        raise SystemExit(f"ERROR: {ENTRIES_FILE} が見つかりません")

    db = load_db()
    entries = db.get("entries", [])
    if not isinstance(entries, list):
        raise SystemExit("ERROR: entries.json の entries フィールドが list ではありません")

    updated = 0
    scanned = 0
    skipped = 0

    for i, entry in enumerate(entries):
        if args.limit and scanned >= args.limit:
            break

        scanned += 1
        if not should_process(entry, only_missing=args.only_missing):
            continue

        source = entry.get("source")
        source_url = source.get("url") if isinstance(source, dict) else source
        if not source_url or not isinstance(source_url, str):
            skipped += 1
            continue

        try:
            html = fetch_html(source_url, timeout_sec=args.timeout, max_bytes=args.max_bytes)
            og = extract_og_image(html)  # og:image優先
            if not og:
                skipped += 1
                continue

            entry["thumbnail"] = normalize_thumb_url(og, source_url)
            updated += 1
            print(f"UPDATED [{i+1}/{len(entries)}]: {entry.get('title','')} -> {entry['thumbnail']}")
        except Exception as e:
            skipped += 1
            print(f"SKIP ERROR [{i+1}/{len(entries)}]: {entry.get('title','')} ({e})")

        time.sleep(args.sleep)

    if updated > 0:
        save_db(db)
    print(f"\nDone. scanned={scanned}, updated={updated}, skipped={skipped}, only_missing={args.only_missing}")


if __name__ == "__main__":
    main()

