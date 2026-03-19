#!/usr/bin/env python3
"""
rss_fetch.py — RSSソースから記事を取得し、重複チェック後にステージングJSONとして保存するスクリプト

使い方:
  python3 scripts/rss_fetch.py                       # 全ソースを取得
  python3 scripts/rss_fetch.py --source amiami-news # 特定ソースのみ
  python3 scripts/rss_fetch.py --limit 10          # 1ソースあたりの上限件数を指定
  python3 scripts/rss_fetch.py --fetch-thumbnails # URL先HTMLから画像を抽出。news.amiami.jpはog:image優先、他は先頭画像優先
  python3 scripts/rss_fetch.py --reset            # リセット用: 重複チェックなしで全件取得、reset_*.json に出力

終了後、 data/staging/YYYYMMDD.json に未翻訳の記事が保存されます。
そのJSONをGeminiへ渡して英語化 → add_entry.py で entries.json に追加してください。
"""

import json
import sys
import re
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import unescape
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from typing import Optional

try:
    import feedparser
except ImportError:
    print("ERROR: feedparser がインストールされていません。")
    print("  pip install feedparser")
    sys.exit(1)

JST = timezone(timedelta(hours=9))
SOURCES_FILE = Path("data/sources.json")
ENTRIES_FILE = Path("data/entries.json")
STAGING_DIR = Path("data/staging")

META_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)
META_OG_IMAGE_SECURE_RE = re.compile(
    r'<meta[^>]+property=[\'"]og:image:secure_url[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)

IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)

# og:image を優先するドメイン（記事シェア時と同じ画像を安定して取得）
OG_FIRST_DOMAINS = ("news.amiami.jp",)

GENERIC_THUMB_PATTERNS = (
    "oglogo",
    "default_ogp",
    "apple-touch-icon",
    "/logo",
    "og-image",
)


def is_generic_thumbnail(url: str) -> bool:
    """サイトロゴ等の汎用画像かどうか"""
    if not url:
        return False
    url_lower = url.lower()
    return any(p in url_lower for p in GENERIC_THUMB_PATTERNS)


def choose_thumbnail(lead: Optional[str], og: Optional[str], source_url: str) -> Optional[str]:
    """
    ドメインに応じて lead / og の優先順位を決める。
    OG_FIRST_DOMAINS の場合は og:image を優先（シェア時と同じ画像）。
    """
    domain = urlparse(source_url).netloc
    if domain in OG_FIRST_DOMAINS and og and not is_generic_thumbnail(og):
        return og
    return lead or og


def fetch_html(url: str, timeout_sec: int, max_bytes: int) -> str:
    """指定URLのHTMLを取得（失敗は例外で呼び元へ）"""
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; JapanOTAKUInsiderBot/1.0; +https://itibo3.github.io/Japan-OTAKU-Insider/)"
        },
    )
    with urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read(max_bytes)
        return raw.decode("utf-8", errors="replace")


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
    元記事の「先頭に出てくる画像っぽいもの」を雑に抽出する（完全保証はしない）

    方針:
    - article/main 付近を優先的に探し、その中で最初の img を候補にする
    - src/data-src/srcset からURLを復元
    - logo/icon/favicon/pixel っぽいURLは軽くスキップして次を探す
    """
    # 可能なら main/article 付近だけ切り出す（regexなので限界はある）
    lower = html.lower()
    starts = []
    for token in ["<article", "<main", "role=\"main\"", "role='main'"]:
        idx = lower.find(token)
        if idx != -1:
            starts.append(idx)
    start = min(starts) if starts else 0
    segment = html[start : start + 250000]  # 重くならないよう上限

    skip_keywords = [
        "favicon",
        "icon",
        "logo",
        "avatar",
        "sprite",
        "badge",
        "button",
        "twitter",
        "pixel",
        "1x1",
        "spacer",
        "blank",
    ]

    for img_match in IMG_TAG_RE.finditer(segment):
        tag = img_match.group(0)

        def get_attr(attr_name: str) -> Optional[str]:
            m = re.search(rf'{attr_name}\s*=\s*[\'"]([^\'"]+)[\'"]', tag, flags=re.IGNORECASE)
            return m.group(1).strip() if m else None

        src = get_attr("src") or get_attr("data-src") or get_attr("data-original")
        if not src:
            srcset = get_attr("srcset") or get_attr("data-srcset")
            if srcset:
                first = srcset.split(",")[0].strip()
                # "url 1x" / "url 2x" などの "url only" 以外を落とす
                src = first.split()[0].strip() if first else None

        if not src:
            continue

        src = unescape(src)
        if src.startswith("data:"):
            continue

        # protocol-relative を補完
        if src.startswith("//"):
            src = "https:" + src
        elif not (src.startswith("http://") or src.startswith("https://")):
            src = urljoin(base_url, src)

        src_lower = src.lower()
        if any(k in src_lower for k in skip_keywords):
            continue

        # 明らかな装飾用gif（例: SNSボタン）を避ける
        if src_lower.endswith(".gif"):
            continue

        return src

    return None

# --- ヘルパー関数 ---

def load_sources():
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["sources"]

def load_entries():
    if not ENTRIES_FILE.exists():
        return []
    with open(ENTRIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("entries", [])

def is_duplicate(url, title, existing_entries):
    """URLまたはタイトルがすでに entries.json に存在するならTrue"""
    for e in existing_entries:
        ex_url = e.get("source", {}).get("url", "")
        ex_title = e.get("title", "")
        ex_title_ja = e.get("title_ja", "")
        if url and url == ex_url:
            return True
        if title and (title == ex_title or title == ex_title_ja):
            return True
    return False

def entry_id_from_url(url, category):
    """URLのハッシュからユニークなIDを生成（英語化後に proper IDに置き換える）"""
    h = hashlib.md5(url.encode()).hexdigest()[:6]
    date_str = datetime.now(JST).strftime("%Y%m%d")
    return f"{category}-{date_str}-rss-{h}"

def extract_category(source):
    """ソースのcategoriesから最初のカテゴリを返す"""
    cats = source.get("categories", ["event"])
    return cats[0] if cats else "event"

def clean_html(text):
    """HTMLタグを除去して平文にする"""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()

# --- メイン処理 ---

def fetch_source(
    source,
    existing_entries,
    limit=20,
    fetch_thumbnails: bool = False,
    thumb_timeout: int = 20,
    thumb_max_bytes: int = 2_000_000,
):
    """1ソースのRSSをフェッチして新規記事のリストを返す"""
    rss_url = source.get("rss")
    if not rss_url:
        print(f"  [{source['id']}] RSS URLなし（スクレイピングソース）— スキップ")
        return []

    print(f"\n📡 [{source['id']}] {source['name']} をフェッチ中...")
    try:
        feed = feedparser.parse(rss_url)
    except Exception as e:
        print(f"  ERROR: フェッチ失敗 — {e}")
        return []

    if feed.bozo and not feed.entries:
        print(f"  WARNING: フィードの解析に問題がありました — {feed.bozo_exception}")

    new_items = []
    category = extract_category(source)
    content_tags = source.get("content_tags", [source["id"]])

    for i, entry in enumerate(feed.entries[:limit]):
        title_ja = clean_html(entry.get("title", "")).strip()
        url = entry.get("link", "")
        summary = clean_html(entry.get("summary", entry.get("description", ""))).strip()
        # 長すぎる場合はトリム
        if len(summary) > 400:
            summary = summary[:400] + "…"

        # 公開日の取得
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(JST)
                published = dt.strftime("%b %-d, %Y")
            except Exception:
                pass

        if not url:
            continue

        thumbnail = None
        if fetch_thumbnails:
            try:
                page_html = fetch_html(url, timeout_sec=thumb_timeout, max_bytes=thumb_max_bytes)
                lead = extract_lead_image(page_html, base_url=url)
                og = extract_og_image(page_html)
                thumbnail = choose_thumbnail(lead, og, url)
                if thumbnail:
                    thumbnail = thumbnail.strip()
                    if thumbnail.startswith("//"):
                        thumbnail = "https:" + thumbnail
                    elif not (thumbnail.startswith("http://") or thumbnail.startswith("https://")):
                        thumbnail = urljoin(url, thumbnail)
            except Exception:
                thumbnail = None

        # 重複チェック
        if is_duplicate(url, title_ja, existing_entries):
            print(f"  SKIP (重複): {title_ja[:50]}")
            continue

        item = {
            "id": entry_id_from_url(url, category),
            "categories": source.get("categories", [category]),
            "status": "active",
            "title": f"[未翻訳] {title_ja}",
            "title_ja": title_ja,
            "dates": {"display": published} if published else {},
            "description": f"[未翻訳] {summary}",
            "source": {"url": url},
            "tags": content_tags,
            **({"thumbnail": thumbnail} if thumbnail else {}),
            "_source_id": source["id"]
        }
        new_items.append(item)
        print(f"  NEW: {title_ja[:60]}")

    print(f"  → {len(new_items)} 件の新規記事を取得")
    return new_items

def main():
    # 引数解析
    args = sys.argv[1:]
    target_source = None
    limit = 20
    fetch_thumbnails = "--fetch-thumbnails" in args
    reset_mode = "--reset" in args
    if reset_mode:
        fetch_thumbnails = True
    thumb_timeout = 20
    thumb_max_bytes = 2_000_000

    if "--source" in args:
        idx = args.index("--source")
        target_source = args[idx + 1] if idx + 1 < len(args) else None

    if "--limit" in args:
        idx = args.index("--limit")
        try:
            limit = int(args[idx + 1])
        except (IndexError, ValueError):
            pass

    sources = load_sources()
    existing_entries = [] if reset_mode else load_entries()

    # 対象ソースをフィルタ
    rss_sources = [s for s in sources if s.get("rss")]
    if target_source:
        rss_sources = [s for s in rss_sources if s["id"] == target_source]
        if not rss_sources:
            print(f"ERROR: ソース '{target_source}' が見つかりません")
            sys.exit(1)

    print(f"=== RSS Fetch 開始 ===")
    if reset_mode:
        print("  [RESET モード] 重複チェックなし、全件取得")
    print(f"対象ソース: {len(rss_sources)} 件 / 上限: 各 {limit} 件")

    all_new_items = []
    for source in rss_sources:
        items = fetch_source(
            source,
            existing_entries,
            limit=limit,
            fetch_thumbnails=fetch_thumbnails,
            thumb_timeout=thumb_timeout,
            thumb_max_bytes=thumb_max_bytes,
        )
        all_new_items.extend(items)

    if not all_new_items:
        print("\n✅ 新規記事はありませんでした（全て重複）" if not reset_mode else "新規記事がありませんでした")
        return

    # ステージングJSONに保存
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(JST).strftime("%Y%m%d_%H%M")
    staging_file = STAGING_DIR / f"reset_{date_str}.json" if reset_mode else STAGING_DIR / f"{date_str}.json"

    with open(staging_file, "w", encoding="utf-8") as f:
        json.dump(all_new_items, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ 完了！ {len(all_new_items)} 件の新規記事をステージングに保存しました")
    print(f"   ファイル: {staging_file}")
    print(f"\n🛑 次のステップ:")
    if reset_mode:
        print(f"   1. entries.json をバックアップ済みなら空にする")
        print(f"   2. translate_with_deepl.py で {staging_file} を英訳")
        print(f"   3. add_entry.py --reset {staging_file} で entries.json を再構築")
    else:
        print(f"   1. Antigravity の Gemini に切り替えてください")
        print(f"   2. 「{staging_file} の記事を英語化して entries.json に追加し、")
        print(f"      GitHub にプッシュしてください」と依頼してください")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
