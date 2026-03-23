#!/usr/bin/env python3
"""animeanime-jp の thumb_l サムネを og:image で差し替えるワンショットスクリプト"""
import json, re, time, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from html import unescape

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path(__file__).resolve().parent.parent / "data" / "entries.json"

META_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)

def fetch_og_image(url: str, timeout: int = 15) -> str | None:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; OtakuBot/1.0)"})
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
    targets = [e for e in entries if e.get("_source_id") == "animeanime-jp"
               and e.get("thumbnail") and "thumb_l" in e["thumbnail"]]

    print(f"対象: {len(targets)} 件")

    updated = 0
    errors = 0
    for i, entry in enumerate(targets):
        url = entry["source"]["url"] if isinstance(entry["source"], dict) else entry["source"]
        try:
            og = fetch_og_image(url)
            if og and "thumb_l" not in og:
                entry["thumbnail"] = og
                updated += 1
                print(f"[{i+1}/{len(targets)}] OK: {entry['title'][:50]}  ->  {og}")
            else:
                print(f"[{i+1}/{len(targets)}] SKIP (no good og): {entry['title'][:50]}  og={og}")
        except Exception as e:
            errors += 1
            print(f"[{i+1}/{len(targets)}] ERROR: {entry['title'][:50]}  {e}")
        time.sleep(0.8)

    if updated > 0:
        db["last_updated"] = datetime.now(JST).isoformat()
        with open(ENTRIES_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"\n✅ entries.json 保存完了")

    print(f"\nDone: updated={updated}, errors={errors}, total_targets={len(targets)}")

if __name__ == "__main__":
    main()
