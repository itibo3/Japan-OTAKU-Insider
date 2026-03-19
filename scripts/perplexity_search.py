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


def load_prompt(category: str) -> str:
    path = PROMPTS_DIR / f"perplexity_{category}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def call_perplexity(api_key: str, prompt: str, model: str = "sonar") -> str:
    import requests

    url = "https://api.perplexity.ai/v1/sonar"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
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
    """レスポンスから JSON 配列を抽出する"""
    m = JSON_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    m = ARRAY_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    return []


def to_entry(raw: dict, category: str, index: int) -> dict:
    """Perplexity の生データを entries 形式に変換"""
    title_ja = str(raw.get("title_ja", raw.get("title", "")) or "").strip()
    description = str(raw.get("description", "")) or ""
    dates_str = str(raw.get("dates", "")) or ""
    location = str(raw.get("location", "")) or ""
    source_url = str(raw.get("source_url", raw.get("url", "")) or "").strip()

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
    parser.add_argument("--model", default="sonar", help="Perplexity model (sonar, sonar-pro)")
    args = parser.parse_args()

    api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        print("PERPLEXITY_API_KEY が未設定なので、検索をスキップします。", file=sys.stderr)
        sys.exit(0)

    try:
        prompt = load_prompt(args.category)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Perplexity 検索中: {args.category} ...")
    try:
        content = call_perplexity(api_key, prompt, model=args.model)
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

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(JST).strftime("%Y%m%d_%H%M")
    out_path = STAGING_DIR / f"perplexity_{args.category}_{date_str}.json"
    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {args.category}: {len(entries)} 件 -> {out_path}")


if __name__ == "__main__":
    main()
