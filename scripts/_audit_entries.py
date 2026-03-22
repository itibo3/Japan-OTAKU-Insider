#!/usr/bin/env python3
"""
_audit_entries.py — entries.json / staging の英語記事・サムネ問題を調査するスクリプト
削除は一切しない。報告のみ。
"""
import json
import shutil
from pathlib import Path
from urllib.parse import urlparse

EXCLUDED_RAW = (
    "japantravel.com", "tripadvisor.com", "magical-trip.com", "gotokyo.org",
    "trustpilot.com", "alibaba.com", "essential-japan.com", "lonelyplanet.com",
    "timeout.com", "viator.com", "expedia.com", "booking.com", "tokyocheapo.com",
    "japantravel.navitime.com", "livejapan.com", "gaijinpot.com", "japantimes.co.jp",
    "soranews24.com", "tokyoweekender.com", "savvytokyo.com", "japan-guide.com",
    "tsunagujapan.com", "matcha-jp.com", "jrailpass.com", "japan.travel",
    "en.wikipedia.org", "fandom.com", "cbr.com", "screenrant.com", "polygon.com",
    "kotaku.com", "ign.com", "gamerant.com", "thegamer.com", "siliconera.com",
    "dualshockers.com", "pushsquare.com", "nintendolife.com", "eurogamer.net",
    "destructoid.com", "gematsu.com",
)
ALLOWED_DOMAINS = (
    "collabo-cafe.com", "amiami.jp", "amiami.com", "goodsmile.info", "goodsmile.com",
    "kotobukiya.co.jp", "4gamer.net", "famitsu.com", "dengeki.com", "natalie.mu",
    "nijisanji.jp", "hololive.tv", "bushiroad.com", "capcom.co.jp",
    "bandainamco.co.jp", "square-enix.com", "sega.co.jp", "konami.com",
    "akihabara-bc.jp", "otamonth.com", "hobby.watch.impress.co.jp",
    "hobby.dengeki.com", "hjweb.jp", "hobbystock.jp", "toranoana.jp",
    "melonbooks.co.jp", "gamecity.ne.jp", "walkerplus.com", "enjoytokyo.jp",
    "akibablog.blog.jp",
)
GENERIC_THUMB_PATTERNS = (
    "oglogo", "default_ogp", "apple-touch-icon", "/logo", "og-image", "banner",
    "ico_header", "ico_sns", "common/img", "shared/img", "noimage", "no_image",
    "dummy", "trustpilot", "display-pic", "favicon", "author", "profile", "avatar",
    "x32.", "x48.", "x64.", "x65.", "x96.", "32x32", "48x48", "64x64", "96x96",
    "staff/img", "ghost_import", "bnr_staff",
)

def is_excluded_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    if any(d in url_lower for d in EXCLUDED_RAW):
        return True
    if "/en/" in url_lower:
        return True
    try:
        host = urlparse(url_lower).hostname or ""
        if host.endswith(".jp"):
            return False
        if any(wl in host for wl in ALLOWED_DOMAINS):
            return False
        non_jp_tlds = (".com", ".net", ".org", ".io", ".co")
        if any(host.endswith(t) for t in non_jp_tlds):
            return True
    except Exception:
        pass
    return False

def has_japanese(text: str) -> bool:
    return any('\u3000' <= c <= '\u9fff' or '\u30a0' <= c <= '\u30ff' for c in (text or ""))

def is_generic_thumb(url: str) -> bool:
    if not url:
        return False
    return any(p in url.lower() for p in GENERIC_THUMB_PATTERNS)

# ============================================================
# 1. entries.json 調査
# ============================================================
db = json.loads(Path("data/entries.json").read_text(encoding="utf-8"))
entries = db["entries"]
print(f"{'='*60}")
print(f"[1] entries.json 調査  (総エントリー数: {len(entries)})")
print(f"{'='*60}")

url_excluded = []
title_en_only = []

for e in entries:
    url = (e.get("source") or {}).get("url", "")
    title = e.get("title", "")
    title_ja = e.get("title_ja", "") or ""

    url_hit = is_excluded_url(url) if url else False
    en_only = bool(title) and not has_japanese(title) and not has_japanese(title_ja)

    if url_hit:
        url_excluded.append((e.get("id",""), title[:60], url[:80]))
    if en_only and not url_hit:  # 重複表示を避ける
        title_en_only.append((e.get("id",""), title[:60], url[:80]))

print(f"\n[A] 除外ドメイン/英語URLの記事: {len(url_excluded)} 件")
for eid, t, u in url_excluded:
    print(f"  {eid}")
    print(f"    title: {t}")
    print(f"    url:   {u}")

print(f"\n[B] 英語タイトルのみ（URL除外以外）: {len(title_en_only)} 件")
for eid, t, u in title_en_only:
    print(f"  {eid}")
    print(f"    title: {t}")
    if u:
        print(f"    url:   {u}")

print(f"\n→ 削除対象合計: {len(url_excluded) + len(title_en_only)} 件")

# ============================================================
# 2. staging 調査
# ============================================================
print(f"\n{'='*60}")
print(f"[2] staging/ 調査")
print(f"{'='*60}")

staging_dir = Path("data/staging")
staging_files = sorted(staging_dir.glob("*.json"))
staging_total = 0

for sf in staging_files:
    try:
        items = json.loads(sf.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            print(f"  {sf.name}: リスト形式でない — スキップ")
            continue
        hits = []
        for item in items:
            url = (item.get("source") or {}).get("url", "")
            title = item.get("title", "") or item.get("title_ja", "") or ""
            if is_excluded_url(url):
                hits.append((title[:60], url[:80], "URL除外"))
            elif bool(title) and not has_japanese(title):
                hits.append((title[:60], url[:80], "英語タイトル"))
        print(f"\n  {sf.name}  ({len(items)}件中 {len(hits)}件該当)")
        for t, u, reason in hits:
            print(f"    [{reason}] {t}")
            if u: print(f"      url: {u}")
        staging_total += len(hits)
    except Exception as ex:
        print(f"  {sf.name}: 読み込みエラー — {ex}")

print(f"\n→ staging 削除対象合計: {staging_total} 件")

# ============================================================
# 3. サムネイルチェック
# ============================================================
print(f"\n{'='*60}")
print(f"[3] サムネイルチェック")
print(f"{'='*60}")

no_thumb = []
generic_thumb = []

for e in entries:
    thumb = e.get("thumbnail") or ""
    eid = e.get("id","")
    title = e.get("title","")[:50]
    if not thumb:
        no_thumb.append((eid, title))
    elif is_generic_thumb(thumb):
        generic_thumb.append((eid, title, thumb[:80]))

print(f"\n[A] thumbnail が null/空: {len(no_thumb)} 件")
for eid, t in no_thumb[:20]:
    print(f"  {eid}  {t}")
if len(no_thumb) > 20:
    print(f"  ... 他 {len(no_thumb)-20} 件")

print(f"\n[B] ジェネリックサムネ（GENERIC_THUMB_PATTERNS該当）: {len(generic_thumb)} 件")
for eid, t, th in generic_thumb[:20]:
    print(f"  {eid}  {t}")
    print(f"    thumb: {th}")
if len(generic_thumb) > 20:
    print(f"  ... 他 {len(generic_thumb)-20} 件")

print(f"\n{'='*60}")
print("調査完了。削除はまだ行っていません。")
print(f"{'='*60}")
