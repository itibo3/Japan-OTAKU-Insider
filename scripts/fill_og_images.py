#!/usr/bin/env python3
"""
fill_og_images.py — entries.json の missing thumbnail を埋める

狙い:
- cards/list & modal のサムネ表示を安定させるために
- 各 entry の `source.url` 先HTMLから画像を抽出して `entry.thumbnail` に書き込む
- 取得順序: 先頭画像（article/main内の最初のimg）を優先、なければ og:image
- og:image がサイトロゴ等の汎用画像の場合も、先頭画像があればそちらを採用

実行例:
  python3 scripts/fill_og_images.py --only-missing
  python3 scripts/fill_og_images.py --limit 20
  python3 scripts/fill_og_images.py --replace-generic  # ロゴ等を先頭画像で差し替え
"""

import argparse
import json
import re
import time
from datetime import datetime, timezone, timedelta
from html import unescape
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path("data/entries.json")

IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)

# サイトロゴ・デフォルトOGPっぽいURL（先頭画像を優先したい）
GENERIC_THUMB_PATTERNS = (
    "oglogo",
    "default_ogp",
    "apple-touch-icon",
    "/logo",
    "og-image",
)

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


def extract_lead_image(html: str, base_url: str) -> Optional[str]:
    """
    元記事の article/main 付近から先頭のコンテンツ画像を抽出する（rss_fetch と同様の方針）
    """
    lower = html.lower()
    starts = []
    for token in ["<article", "<main", 'role="main"', "role='main'"]:
        idx = lower.find(token)
        if idx != -1:
            starts.append(idx)
    start = min(starts) if starts else 0
    segment = html[start : start + 250000]

    skip_keywords = (
        "favicon", "icon", "logo", "avatar", "sprite", "badge", "button",
        "twitter", "pixel", "1x1", "spacer", "blank",
    )

    for img_match in IMG_TAG_RE.finditer(segment):
        tag = img_match.group(0)

        def get_attr(attr_name: str) -> Optional[str]:
            pat = rf'{attr_name}\s*=\s*["\']([^"\']+)["\']'
            m = re.search(pat, tag, flags=re.IGNORECASE)
            return m.group(1).strip() if m else None

        src = get_attr("src") or get_attr("data-src") or get_attr("data-original")
        if not src:
            srcset = get_attr("srcset") or get_attr("data-srcset")
            if srcset:
                first = srcset.split(",")[0].strip()
                src = first.split()[0].strip() if first else None
        if not src:
            continue

        src = unescape(src)
        if src.startswith("data:"):
            continue
        if src.startswith("//"):
            src = "https:" + src
        elif not (src.startswith("http://") or src.startswith("https://")):
            src = urljoin(base_url, src)
        src_lower = src.lower()
        if any(k in src_lower for k in skip_keywords):
            continue
        if src_lower.endswith(".gif"):
            continue
        return src
    return None


def is_generic_thumbnail(url: str) -> bool:
    """サイトロゴ等の汎用画像かどうか"""
    if not url:
        return False
    url_lower = url.lower()
    return any(p in url_lower for p in GENERIC_THUMB_PATTERNS)


def normalize_thumb_url(og_url: str, source_url: str) -> str:
    og_url = og_url.strip()
    if og_url.startswith("//"):
        return "https:" + og_url
    if og_url.startswith("http://") or og_url.startswith("https://"):
        return og_url
    return urljoin(source_url, og_url)


def should_process(entry: dict, only_missing: bool, replace_generic: bool) -> bool:
    thumb = entry.get("thumbnail")
    has_thumb = thumb is not None and isinstance(thumb, str) and thumb.strip()
    if not has_thumb:
        return True
    if not only_missing:
        return True
    if replace_generic and is_generic_thumbnail(thumb):
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-missing", action="store_true", default=False, help="thumbnail が未設定/空だけ処理する")
    parser.add_argument("--replace-generic", action="store_true", default=False, help="ロゴ等の汎用サムネを先頭画像で差し替える")
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
        if not should_process(entry, only_missing=args.only_missing, replace_generic=args.replace_generic):
            continue

        source = entry.get("source")
        source_url = source.get("url") if isinstance(source, dict) else source
        if not source_url or not isinstance(source_url, str):
            skipped += 1
            continue

        try:
            html = fetch_html(source_url, timeout_sec=args.timeout, max_bytes=args.max_bytes)
            lead = extract_lead_image(html, base_url=source_url)
            og = extract_og_image(html)
            thumb = lead or og
            if not thumb:
                skipped += 1
                continue
            entry["thumbnail"] = normalize_thumb_url(thumb, source_url)
            updated += 1
            print(f"UPDATED [{i+1}/{len(entries)}]: {entry.get('title','')} -> {entry['thumbnail']}")
        except Exception as e:
            skipped += 1
            print(f"SKIP ERROR [{i+1}/{len(entries)}]: {entry.get('title','')} ({e})")

        time.sleep(args.sleep)

    if updated > 0:
        save_db(db)
    print(f"\nDone. scanned={scanned}, updated={updated}, skipped={skipped}, only_missing={args.only_missing}, replace_generic={args.replace_generic}")


if __name__ == "__main__":
    main()

