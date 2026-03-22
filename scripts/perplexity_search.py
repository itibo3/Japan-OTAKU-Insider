#!/usr/bin/env python3
"""
perplexity_search.py — Perplexity API でカテゴリ別検索し、staging JSON を出力する

使い方:
  python3 scripts/perplexity_search.py --category cafe
  python3 scripts/perplexity_search.py --category cafe --debug   # 生レスポンス保存・0件時の診断
  python3 scripts/perplexity_search.py --category cafe --dry-run # 送信内容のみ表示（キー不要）

環境変数 PERPLEXITY_API_KEY が未設定の場合は何もしずに終了（exit 0）
出力: data/staging/perplexity_{category}_YYYYMMDD.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
STAGING_DIR = Path(__file__).resolve().parent.parent / "data" / "staging"

CATEGORIES = ("cafe", "vtuber", "figure", "game", "anime", "other")

# 検索結果から除外するドメイン（英語圏の旅行・アグリゲーター・ゲームメディア等）
# API 用: - プレフィックスで search_domain_filter に渡す
# パイプライン用: URL が含まれる場合は staging に追加しない
_EXCLUDED_RAW = (
    # 旅行・観光系（英語圏）
    "japantravel.com",
    "tripadvisor.com",
    "magical-trip.com",
    "gotokyo.org",
    "trustpilot.com",
    "alibaba.com",
    "essential-japan.com",
    "lonelyplanet.com",
    "timeout.com",
    "viator.com",
    "expedia.com",
    "booking.com",
    "tokyocheapo.com",
    "japantravel.navitime.com",
    "livejapan.com",
    "gaijinpot.com",
    "japantimes.co.jp",
    "soranews24.com",
    "tokyoweekender.com",
    "savvytokyo.com",
    "japan-guide.com",
    "tsunagujapan.com",
    "matcha-jp.com",
    "jrailpass.com",
    "japan.travel",
    "en.wikipedia.org",
    "fandom.com",
    # 英語ゲーム・アニメメディア
    "cbr.com",
    "screenrant.com",
    "polygon.com",
    "kotaku.com",
    "ign.com",
    "gamerant.com",
    "thegamer.com",
    "siliconera.com",
    "dualshockers.com",
    "pushsquare.com",
    "nintendolife.com",
    "eurogamer.net",
    "destructoid.com",
    "gematsu.com",
)
EXCLUDED_DOMAINS = tuple(f"-{d}" for d in _EXCLUDED_RAW)

# 英語サイトでも許可する既知の日本サイト（ホワイトリスト）
_ALLOWED_DOMAINS = (
    "collabo-cafe.com",
    "animate.co.jp",
    "amiami.jp",
    "amiami.com",
    "goodsmile.info",
    "goodsmile.com",
    "kotobukiya.co.jp",
    "4gamer.net",
    "famitsu.com",
    "dengeki.com",
    "natalie.mu",
    "nijisanji.jp",
    "hololive.tv",
    "bushiroad.com",
    "capcom.co.jp",
    "bandainamco.co.jp",
    "square-enix.com",
    "sega.co.jp",
    "konami.com",
    "akihabara-bc.jp",
    "otamonth.com",
    "hobby.watch.impress.co.jp",
    "hobby.dengeki.com",
    "hjweb.jp",
    "hobbystock.jp",
    "toranoana.jp",
    "melonbooks.co.jp",
    "animate.co.jp",
    "gamecity.ne.jp",
    "walkerplus.com",
    "enjoytokyo.jp",
    "akibablog.blog.jp",
)

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
ARRAY_RE = re.compile(r"\[\s*\{[\s\S]*\}\s*\]")


def _is_excluded_url(url: str) -> bool:
    """
    URLが除外対象かどうかを判定する。
    除外条件（いずれかに該当すれば除外）:
      1. _EXCLUDED_RAW に含まれるドメイン
      2. URL に /en/ が含まれる（英語版ページ）
      3. .com ドメインで、かつ _ALLOWED_DOMAINS に含まれない
         （.jp / .co.jp / .ne.jp 等の日本語ドメインは常に許可）
    """
    url_lower = url.lower()

    # 1. 明示的除外ドメイン
    if any(d in url_lower for d in _EXCLUDED_RAW):
        return True

    # 2. /en/ パス（英語版ページ）
    if "/en/" in url_lower:
        return True

    # 3. ホワイトリストにない .com ドメイン
    #    日本系 TLD (.jp, .co.jp, .ne.jp, .or.jp, .ac.jp) は常に許可
    try:
        from urllib.parse import urlparse
        host = urlparse(url_lower).hostname or ""
        # 日本系TLDは許可
        jp_tlds = (".jp",)
        if any(host.endswith(t) for t in jp_tlds):
            return False
        # ホワイトリストに含まれていれば許可
        if any(wl in host for wl in _ALLOWED_DOMAINS):
            return False
        # .com / .net / .org 等で非日本ドメインは除外
        non_jp_tlds = (".com", ".net", ".org", ".io", ".co")
        if any(host.endswith(t) for t in non_jp_tlds):
            return True
    except Exception:
        pass

    return False


SYSTEM_PROMPT = (
    "You are a JSON API. You MUST respond with ONLY a single JSON object, no markdown, no explanation, no text before or after. "
    'Format: {"cat":1,"news":[{"title":"日本語タイトル","desc":"日本語2文の説明","date":"YYYY-MM-DD or range","place":"場所","url":"https://source-url"}]}. '
    "Search Japanese sources only. Return title and desc in Japanese. Return 5-8 news items."
)


def load_user_prompt(category: str) -> str:
    path = PROMPTS_DIR / f"perplexity_{category}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def call_perplexity(api_key: str, messages: list, model: str = "sonar-pro") -> str:
    import requests

    url = "https://api.perplexity.ai/v1/sonar"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.2,
        "search_recency_filter": "week",
        "search_language_filter": ["ja"],
        "search_domain_filter": list(EXCLUDED_DOMAINS),
        "web_search_options": {
            "user_location": {"country": "JP"},
        },
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Perplexity API error: HTTP {resp.status_code} {resp.text[:300]}")

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Perplexity API returned no choices")
    content = choices[0].get("message", {}).get("content", "")
    return content.strip()


OBJ_RE = re.compile(r"\{[\s\S]*\}")


def extract_json(text: str) -> list:
    """
    レスポンスから JSON を抽出する。
    対応パターン（優先順）:
      1. ```json ... ``` コードブロック内
      2. テキスト全体がそのまま JSON
      3. テキスト中の [...] 配列
      4. テキスト中の {...} オブジェクト（Markdown 混在対応）
    """
    def try_parse(s: str):
        try:
            return json.loads(s.strip())
        except json.JSONDecodeError:
            return None

    # 1. ```json ... ``` ブロック
    m = JSON_BLOCK_RE.search(text)
    if m:
        parsed = try_parse(m.group(1))
        if parsed is not None:
            return _normalize_to_list(parsed)

    # 2. テキスト全体
    obj = try_parse(text)
    if obj is not None:
        return _normalize_to_list(obj)

    # 3. [...] 配列を探す
    m = ARRAY_RE.search(text)
    if m:
        parsed = try_parse(m.group(0))
        if isinstance(parsed, list):
            return parsed

    # 4. {...} オブジェクトを探す（Markdown 混在時のフォールバック）
    m = OBJ_RE.search(text)
    if m:
        parsed = try_parse(m.group(0))
        if parsed is not None:
            return _normalize_to_list(parsed)

    return []


def _normalize_to_list(parsed) -> list:
    """{cat, news:[...]} または [...] を list に正規化"""
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and "news" in parsed:
        news = parsed.get("news")
        return news if isinstance(news, list) else []
    return []


def to_entry(raw: dict, category: str, index: int) -> dict:
    """Perplexity の生データを entries 形式に変換。新スキーマ(title/desc)と旧スキーマ(title_ja/description)の両対応"""
    title_ja = str(raw.get("title_ja", raw.get("title", "")) or "").strip()
    description = str(raw.get("desc", raw.get("description", "")) or "").strip()
    dates_str = str(raw.get("date", raw.get("dates", "")) or "").strip()
    location = str(raw.get("place", raw.get("location", "")) or "").strip()
    source_url = str(raw.get("url", raw.get("source_url", "")) or "").strip()

    if not title_ja:
        return None

    h = hashlib.md5((source_url or title_ja + str(index)).encode()).hexdigest()[:6]
    date_str = datetime.now(JST).strftime("%Y%m%d%H%M")
    entry_id = f"{category}-{date_str}-pplx-{h}"

    entry = {
        "id": entry_id,
        "categories": [category],
        "status": "active",
        "title": f"[未翻訳] {title_ja}",
        "title_ja": title_ja,
        "description": f"[未翻訳] {description}",
        "source": {"url": source_url} if source_url else {},
        "tags": [category],
        "_source": "perplexity",
    }

    if dates_str:
        entry["dates"] = {"display": dates_str}
    if location:
        entry["location"] = location

    return entry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", choices=CATEGORIES, required=True)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="生レスポンスをファイルに保存し、パース失敗時も診断情報を出力する",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="API を呼ばず、送信するプロンプト内容だけ表示する（キー不要）",
    )
    args = parser.parse_args()

    api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    if not api_key and not args.dry_run:
        print("PERPLEXITY_API_KEY が未設定なので、検索をスキップします。", file=sys.stderr)
        sys.exit(0)

    try:
        user_query = load_user_prompt(args.category)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    today = datetime.now(JST).strftime("%Y/%m/%d")
    user_content = f"{today} {user_query}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    if args.dry_run:
        print(f"[dry-run] キー未設定でも送信内容を確認できます")
        print(f"  category: {args.category}")
        print(f"  user_prompt: {user_query[:80]}...")
        print(f"  user_content: {user_content[:100]}...")
        print(f"  system_prompt: {SYSTEM_PROMPT[:80]}...")
        return

    print(f"Perplexity 検索中: {args.category} (sonar-pro) ...")
    try:
        content = call_perplexity(api_key, messages, model="sonar-pro")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # debug: 生レスポンスを保存
    if args.debug:
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = STAGING_DIR / f"perplexity_debug_raw_{args.category}.txt"
        raw_path.write_text(content, encoding="utf-8")
        print(f"  [DEBUG] 生レスポンス保存: {raw_path} ({len(content)} 文字)")
        print(f"  [DEBUG] 先頭 500 文字: {repr(content[:500])}")

    raw_list = extract_json(content)
    if not isinstance(raw_list, list):
        raw_list = []

    entries = []
    for i, raw in enumerate(raw_list):
        if not isinstance(raw, dict):
            continue
        entry = to_entry(raw, args.category, i)
        if entry:
            entries.append(entry)

    if not entries:
        print(f"  {args.category}: 0 件（パースできなかったか、結果なし）")
        if args.debug:
            print(f"  [DEBUG] extract_json の結果: type={type(raw_list)}, len={len(raw_list) if isinstance(raw_list, list) else 'N/A'}")
            print(f"  [DEBUG] 想定形式: {{cat:int, news:[{{title, desc, date, place?, url}}]}} または [...]")
        return

    seen_urls = set()
    unique_entries = []
    for entry in entries:
        url = (entry.get("source") or {}).get("url", "").strip()
        title_disp = entry.get("title_ja", entry.get("title", ""))[:40]
        if url and url in seen_urls:
            print(f"  SKIP (同一URL): {title_disp}...")
            continue
        if url and _is_excluded_url(url):
            print(f"  SKIP (除外ドメイン/英語URL): {title_disp}... -> {url[:60]}")
            continue
        if url:
            seen_urls.add(url)
        unique_entries.append(entry)
    entries = unique_entries

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(JST).strftime("%Y%m%d_%H%M")
    out_path = STAGING_DIR / f"perplexity_{args.category}_{date_str}.json"
    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {args.category}: {len(entries)} 件 -> {out_path}")


if __name__ == "__main__":
    main()
