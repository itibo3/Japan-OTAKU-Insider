#!/usr/bin/env python3
"""重複サムネを持つ既存記事を og:image で差し替えるワンショットスクリプト"""
import json, re, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from html import unescape
from collections import Counter

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from http_fetch_config import article_fetch_headers

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path(__file__).resolve().parent.parent / "data" / "entries.json"

META_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)

GENERIC_THUMB_PATTERNS = (
    "oglogo", "default_ogp", "apple-touch-icon", "/logo", "og-image",
    "banner", "ico_header", "ico_sns", "common/img", "shared/img",
    "noimage", "no_image", "dummy", "trustpilot",
    "display-pic", "favicon", "author", "profile", "avatar",
    "x32.", "x48.", "x64.", "x65.", "x96.",
    "32x32", "48x48", "64x64", "96x96",
    "staff/img", "ghost_import", "bnr_staff",
    "animeanime.jp/imgs/thumb_l/",
    "btn_", "/follow_tag", ".svg",
)

def is_generic(url):
    if not url:
        return False
    return any(p in url.lower() for p in GENERIC_THUMB_PATTERNS)

def fetch_og_image(url, timeout=15):
    req = Request(url, headers=article_fetch_headers())
    with urlopen(req, timeout=timeout) as resp:
        html = resp.read(500_000).decode("utf-8", errors="replace")
    m = META_OG_IMAGE_RE.search(html)
    if m:
        og = unescape(m.group(1).strip())
        if og.startswith("//"):
            og = "https:" + og
        elif not og.startswith("http"):
            og = urljoin(url, og)
        return og
    return None

def main():
    with open(ENTRIES_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    entries = db["entries"]

    # 同一サムネを2件以上で共有しているものを検出
    thumb_counter = Counter(e.get("thumbnail") for e in entries if e.get("thumbnail"))
    duplicated_thumbs = {t for t, c in thumb_counter.items() if c >= 2}

    # ジェネリックパターンにマッチするサムネを持つもの + 重複サムネの和集合
    targets = []
    for e in entries:
        t = e.get("thumbnail")
        if not t:
            continue
        if is_generic(t) or t in duplicated_thumbs:
            targets.append(e)

    print(f"対象: {len(targets)} 件 (重複サムネ or ジェネリック検出)")

    updated = 0
    errors = 0
    skipped = 0
    for i, entry in enumerate(targets):
        src = entry.get("source", {})
        url = src.get("url") if isinstance(src, dict) else src
        if not url:
            skipped += 1
            continue
        old_thumb = entry["thumbnail"]
        try:
            og = fetch_og_image(url)
            if og and og != old_thumb and not is_generic(og):
                entry["thumbnail"] = og
                updated += 1
                print(f"[{i+1}/{len(targets)}] OK: {entry.get('title','')[:45]}  ->  {og[:80]}")
            else:
                skipped += 1
                reason = "no og" if not og else "same" if og == old_thumb else "generic og"
                print(f"[{i+1}/{len(targets)}] SKIP ({reason}): {entry.get('title','')[:45]}")
        except Exception as e:
            errors += 1
            print(f"[{i+1}/{len(targets)}] ERROR: {entry.get('title','')[:45]}  {e}")
        time.sleep(0.8)

    if updated > 0:
        db["last_updated"] = datetime.now(JST).isoformat()
        with open(ENTRIES_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"\n✅ entries.json 保存完了")

    print(f"\nDone: updated={updated}, skipped={skipped}, errors={errors}, total_targets={len(targets)}")

if __name__ == "__main__":
    main()
