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
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except Exception:  # pragma: no cover - optional runtime dependency fallback
    GoogleTranslator = None

JST = timezone(timedelta(hours=9))


def _contains_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text or ""))


def _is_mostly_japanese(text: str) -> bool:
    s = text or ""
    if not s.strip():
        return False
    jp_chars = re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", s)
    significant = re.sub(r"\s+", "", s)
    if not significant:
        return False
    return (len(jp_chars) / len(significant)) >= 0.2


def _weekly_en_body_looks_too_short(body_en: str, summary_en: str) -> bool:
    """週刊本文として短すぎる英語本文（実質サマリ）を検出する。"""
    body = (body_en or "").strip()
    summary = (summary_en or "").strip()
    if not body:
        return True
    if len(body) < 700:
        return True
    if summary and body == summary:
        return True
    heading_count = len(re.findall(r"(?m)^#{1,3}\s+", body))
    if heading_count < 3:
        return True
    return False


def _translate_markdown_ja_to_en(md: str) -> str:
    """日本語Markdownを英語Markdownへ簡易変換する（行単位）。"""
    text = (md or "").strip()
    if not text:
        return ""
    if GoogleTranslator is None:
        return ""
    tr = GoogleTranslator(source="ja", target="en")
    out_lines: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out_lines.append("")
            continue
        # markdown記号は保持したいので、先頭プレフィックスを分離
        prefix = ""
        body = line
        for token in ("### ", "## ", "# ", "- "):
            if line.startswith(token):
                prefix = token
                body = line[len(token):]
                break
        try:
            translated = tr.translate(body.strip()) if body.strip() else ""
        except Exception:
            translated = body.strip()
        out_lines.append(f"{prefix}{translated}".rstrip())
    out = "\n".join(out_lines).strip()
    # 固有名詞として日本語が少量残ることは許容し、本文の大半が日本語のときだけ失敗扱い
    if _is_mostly_japanese(out):
        return ""
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="JOI素材を entries 追加用JSONに変換")
    parser.add_argument("--input", type=Path, required=True, help="joi_entry_source.json")
    parser.add_argument("--output", type=Path, required=True, help="出力JSON（配列）")
    parser.add_argument("--url", default="", help="記事の参照URL（任意）")
    parser.add_argument(
        "--header-image",
        default="cool",
        choices=["cool", "emotional", "elegant"],
        help="週間JOI通信のヘッダー画像スタイル（cool/emotional/elegant、デフォルト: cool）",
    )
    args = parser.parse_args()

    src = json.loads(args.input.read_text(encoding="utf-8"))
    now = datetime.now(JST)
    stamp = now.strftime("%Y%m%d%H%M")
    title_ja = (src.get("title_ja") or f"週間JOI通信（{now.strftime('%Y-%m-%d')}）").strip()
    title_en = (src.get("title_en") or f"Weekly JOI Bulletin ({now.strftime('%Y-%m-%d')})").strip()
    summary_ja = (src.get("summary_ja") or "").strip()
    summary_en = (src.get("summary_en") or "").strip()
    body_md = (src.get("body_ja_markdown") or "").strip()
    body_en_md = (src.get("body_en_markdown") or "").strip()
    header_image_prompt_en = (src.get("header_image_prompt_en") or "").strip()
    if not header_image_prompt_en:
        header_image_prompt_en = (
            "Anime and otaku weekly news collage, neon Tokyo night, manga style headline banner, "
            "featuring anime broadcast, figure release, cosplay event atmosphere, vivid cyan and magenta, 16:9"
        )
    if (not body_en_md) or _weekly_en_body_looks_too_short(body_en_md, summary_en):
        body_en_md = _translate_markdown_ja_to_en(body_md)
    if not body_en_md:
        body_en_md = summary_en or "Weekly otaku highlights article."
    tags = src.get("tags") or ["weekly-joi", "otaku-news", "analytics"]
    if not isinstance(tags, list):
        tags = ["weekly-joi", "otaku-news", "analytics"]
    digest = hashlib.md5((title_ja + stamp).encode()).hexdigest()[:6]

    # ヘッダー画像（icons/ に置いた固定画像をスタイルで切り替え）
    _header_image_map = {
        "cool": "/icons/weekly-header-cool.png",
        "emotional": "/icons/weekly-header-emotional.png",
        "elegant": "/icons/weekly-header-elegant.png",
    }
    thumbnail_url = _header_image_map.get(args.header_image, _header_image_map["cool"])

    # 本文を description にも入れて、カード/モーダルで読めるようにする
    body_as_desc = (summary_en + "\n\n" + body_md).strip() if summary_en else body_md
    if not body_as_desc:
        body_as_desc = summary_ja or "Weekly JOI report."

    entry_id = f"otaku-news-{stamp}-joi-{digest}"
    article_url = args.url.strip() if isinstance(args.url, str) and args.url.strip() else f"/weekly.html?id={entry_id}"

    entry = {
        "id": entry_id,
        "categories": ["otaku-news"],
        "status": "active",
        "title": title_en,
        "title_ja": title_ja,
        "dates": {"display": now.strftime("%Y-%m-%d")},
        "description": body_as_desc,
        "summary_ja": summary_ja,
        "summary_en": summary_en,
        "article_markdown_ja": body_md,
        "article_markdown_en": body_en_md,
        "header_image_prompt_en": header_image_prompt_en,
        "thumbnail": thumbnail_url,
        "source": {"url": article_url},
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
