#!/usr/bin/env python3
"""
週間JOI通信の素材JSONを、entries追加用JSONへ変換する。

入力: weekly_self_improve_loop.py が出力する joi_entry_source.json
出力: add_entry.py に渡せる配列JSON（1件）
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))


def main() -> None:
    parser = argparse.ArgumentParser(description="JOI素材を entries 追加用JSONに変換")
    parser.add_argument("--input", type=Path, required=True, help="joi_entry_source.json")
    parser.add_argument("--output", type=Path, required=True, help="出力JSON（配列）")
    parser.add_argument("--url", default="", help="記事の参照URL（任意）")
    args = parser.parse_args()

    src = json.loads(args.input.read_text(encoding="utf-8"))
    now = datetime.now(JST)
    stamp = now.strftime("%Y%m%d%H%M")
    title_ja = (src.get("title_ja") or f"週間JOI通信（{now.strftime('%Y-%m-%d')}）").strip()
    title_en = (src.get("title_en") or f"Weekly JOI Bulletin ({now.strftime('%Y-%m-%d')})").strip()
    summary_ja = (src.get("summary_ja") or "").strip()
    summary_en = (src.get("summary_en") or "").strip()
    body_md = (src.get("body_ja_markdown") or "").strip()
    tags = src.get("tags") or ["weekly-joi", "otaku-news", "analytics"]
    if not isinstance(tags, list):
        tags = ["weekly-joi", "otaku-news", "analytics"]
    digest = hashlib.md5((title_ja + stamp).encode()).hexdigest()[:6]

    # 本文を description にも入れて、カード/モーダルで読めるようにする
    body_as_desc = (summary_en + "\n\n" + body_md).strip() if summary_en else body_md
    if not body_as_desc:
        body_as_desc = summary_ja or "Weekly JOI report."

    entry = {
        "id": f"otaku-news-{stamp}-joi-{digest}",
        "categories": ["otaku-news"],
        "status": "active",
        "title": title_en,
        "title_ja": title_ja,
        "dates": {"display": now.strftime("%Y-%m-%d")},
        "description": body_as_desc,
        "source": {"url": args.url} if args.url else {},
        "tags": tags,
        "_source": "joi-weekly",
        "_source_id": "joi-weekly",
        "pinned_top": True,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps([entry], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: JOI entry json -> {args.output}")


if __name__ == "__main__":
    main()
