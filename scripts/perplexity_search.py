#!/usr/bin/env python3
"""
perplexity_search.py — Perplexity API でカテゴリ別検索し、staging JSON を出力する

使い方:
  python3 scripts/perplexity_search.py --category cafe
  python3 scripts/perplexity_search.py --category vtuber
  python3 scripts/perplexity_search.py --category figure
  python3 scripts/perplexity_search.py --category game
  python3 scripts/perplexity_search.py --category anime
  python3 scripts/perplexity_search.py --category other

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

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
ARRAY_RE = re.compile(r"\[\s*\{[\s\S]*\}\s*\]")


SYSTEM_PROMPT = (
    'JSON only. Output: {cat:int, news:[{title:str, desc:str(2sent), date:str, place:str?, url:str}]}. '
    "Return Japanese content for title and desc from Japanese sources."
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


def extract_json(text: str) -> list:
    """
    レスポンスから JSON を抽出する。
    新スキーマ {cat:int, news:[...]} または旧スキーマ [...] の両方に対応。
    """
    def try_parse(s: str):
        try:
            return json.loads(s.strip())
        except json.JSONDecodeError:
            return None

    m = JSON_BLOCK_RE.search(text)
    if m:
        parsed = try_parse(m.group(1))
        if parsed is not None:
            return _normalize_to_list(parsed)

    m = ARRAY_RE.search(text)
    if m:
        parsed = try_parse(m.group(0))
        if isinstance(parsed, list):
            return parsed

    obj = try_parse(text)
    if obj is not None:
        return _normalize_to_list(obj)

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
    date_str = datetime.now(JST).strftime("%Y%m%d")
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
    args = parser.parse_args()

    api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
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

    print(f"Perplexity 検索中: {args.category} (sonar-pro) ...")
    try:
        content = call_perplexity(api_key, messages, model="sonar-pro")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

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
        return

    seen_urls = set()
    for entry in entries:
        url = (entry.get("source") or {}).get("url", "").strip()
        if url and url in seen_urls:
            entry["source"] = {}
            print(f"  WARNING: 重複URLをクリア — {entry.get('title_ja', entry.get('title', ''))[:40]}...")
        elif url:
            seen_urls.add(url)

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(JST).strftime("%Y%m%d_%H%M")
    out_path = STAGING_DIR / f"perplexity_{args.category}_{date_str}.json"
    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {args.category}: {len(entries)} 件 -> {out_path}")


if __name__ == "__main__":
    main()
