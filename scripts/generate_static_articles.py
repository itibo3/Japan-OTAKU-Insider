#!/usr/bin/env python3
"""
entries.json から記事ごとの静的HTMLを生成し、sitemap.xml を更新する。

目的:
- クローラー向けに /articles/*.html を用意して検索流入の受け皿を増やす
- 公開UI（JSでのカード表示）は現状維持しつつ、SEO用の静的面を追加する

使い方:
- python3 scripts/generate_static_articles.py --days 30
- python3 scripts/generate_static_articles.py --only-new --prev-entries /tmp/entries_before_daily.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRIES_JSON = PROJECT_ROOT / "data" / "entries.json"
ARTICLES_DIR = PROJECT_ROOT / "articles"
SITEMAP_XML = PROJECT_ROOT / "sitemap.xml"
SITE_URL = "https://otaku.eidosfrontier.com"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

ID_DATE_RE = re.compile(r"-(\d{8})(?:\d{4})?-")
DISPLAY_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
TAG_RE = re.compile(r"<[^>]+>")


def parse_entry_date(entry: dict) -> datetime | None:
    entry_id = str(entry.get("id") or "")
    m = ID_DATE_RE.search(entry_id)
    if m:
        ds = m.group(1)
        try:
            return datetime(int(ds[:4]), int(ds[4:6]), int(ds[6:8]), tzinfo=timezone.utc)
        except Exception:
            pass

    dates_val = entry.get("dates")
    display = ""
    if isinstance(dates_val, dict):
        display = str(dates_val.get("display") or "")
    elif isinstance(dates_val, str):
        display = dates_val
    m2 = DISPLAY_DATE_RE.search(display)
    if m2:
        try:
            return datetime(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)), tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def text_excerpt(raw: str, limit: int = 220) -> str:
    s = TAG_RE.sub(" ", str(raw or ""))
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "…"


def normalize_source_url(entry: dict) -> str:
    source = entry.get("source")
    raw = ""
    if isinstance(source, dict):
        raw = str(source.get("url") or "")
    elif source:
        raw = str(source)
    raw = raw.strip()
    if not raw:
        return SITE_URL
    if raw.startswith("/"):
        return SITE_URL + raw
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return SITE_URL


def render_article_html(entry: dict) -> str:
    entry_id = str(entry.get("id") or "")
    title = str(entry.get("title") or entry.get("title_ja") or "Untitled")
    title_ja = str(entry.get("title_ja") or "")
    categories = entry.get("categories") or []
    if not isinstance(categories, list):
        categories = []
    category_line = ", ".join(str(c) for c in categories if c)
    desc = str(entry.get("description") or entry.get("description_ja") or "")
    desc_ja = str(entry.get("description_ja") or "")
    excerpt = text_excerpt(desc or desc_ja, 250)
    display_date = ""
    dates_val = entry.get("dates")
    if isinstance(dates_val, dict):
        display_date = str(dates_val.get("display") or "")
    elif isinstance(dates_val, str):
        display_date = dates_val
    pub_dt = parse_entry_date(entry)
    iso_date = (pub_dt or datetime.now(timezone.utc)).date().isoformat()
    source_url = normalize_source_url(entry)
    canonical = f"{SITE_URL}/articles/{entry_id}.html"
    image = str(entry.get("thumbnail") or "").strip()
    if image.startswith("/"):
        image = SITE_URL + image
    if not image:
        image = f"{SITE_URL}/icons/og-image.png"

    title_h = html.escape(title)
    title_ja_h = html.escape(title_ja)
    excerpt_h = html.escape(excerpt)
    desc_h = html.escape(desc)
    desc_ja_h = html.escape(desc_ja)
    source_h = html.escape(source_url)
    category_h = html.escape(category_line)
    id_h = html.escape(entry_id)
    display_date_h = html.escape(display_date or iso_date)
    canonical_h = html.escape(canonical)
    image_h = html.escape(image)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_h} | Japan OTAKU Insider</title>
  <meta name="description" content="{excerpt_h}">
  <link rel="canonical" href="{canonical_h}">
  <meta property="og:title" content="{title_h}">
  <meta property="og:description" content="{excerpt_h}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_h}">
  <meta property="og:image" content="{image_h}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title_h}">
  <meta name="twitter:description" content="{excerpt_h}">
  <meta name="twitter:image" content="{image_h}">
  <script type="application/ld+json">{{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title_h}",
    "datePublished": "{iso_date}",
    "dateModified": "{iso_date}",
    "mainEntityOfPage": "{canonical_h}",
    "image": ["{image_h}"],
    "publisher": {{
      "@type": "Organization",
      "name": "Japan OTAKU Insider",
      "url": "{SITE_URL}/"
    }}
  }}</script>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; max-width: 860px; margin: 0 auto; padding: 24px; line-height: 1.7; color: #1a1a1a; }}
    h1 {{ line-height: 1.35; margin-bottom: 8px; }}
    .meta {{ color: #555; font-size: 14px; margin-bottom: 18px; }}
    .desc {{ white-space: pre-wrap; }}
    .box {{ background: #f7f7f8; padding: 12px; border-radius: 8px; margin: 14px 0; }}
    a {{ color: #1b61c2; }}
  </style>
</head>
<body>
  <h1>{title_h}</h1>
  <div class="meta">Published: {display_date_h}</div>
  <div class="box">
    <div><strong>ID:</strong> {id_h}</div>
    <div><strong>Category:</strong> {category_h}</div>
    <div><strong>Source:</strong> <a href="{source_h}" target="_blank" rel="noopener noreferrer">{source_h}</a></div>
  </div>
  {"<h2>Japanese title</h2><p>" + title_ja_h + "</p>" if title_ja else ""}
  <h2>Summary</h2>
  <p>{excerpt_h}</p>
  {"<h2>Details (EN)</h2><div class='desc'>" + desc_h + "</div>" if desc else ""}
  {"<h2>Details (JA)</h2><div class='desc'>" + desc_ja_h + "</div>" if desc_ja else ""}
  <p><a href="{SITE_URL}/">Back to database top</a></p>
</body>
</html>
"""


def update_sitemap(article_urls: dict[str, str]) -> None:
    ET.register_namespace("", SITEMAP_NS)
    if SITEMAP_XML.exists():
        tree = ET.parse(SITEMAP_XML)
        root = tree.getroot()
    else:
        root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
        tree = ET.ElementTree(root)

    loc_to_node: dict[str, ET.Element] = {}
    for node in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc = node.find(f"{{{SITEMAP_NS}}}loc")
        if loc is not None and loc.text:
            loc_to_node[loc.text.strip()] = node

    for loc, lastmod in article_urls.items():
        node = loc_to_node.get(loc)
        if node is None:
            node = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
            ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = loc
            ET.SubElement(node, f"{{{SITEMAP_NS}}}changefreq").text = "weekly"
            ET.SubElement(node, f"{{{SITEMAP_NS}}}priority").text = "0.6"
        lm = node.find(f"{{{SITEMAP_NS}}}lastmod")
        if lm is None:
            lm = ET.SubElement(node, f"{{{SITEMAP_NS}}}lastmod")
        lm.text = lastmod

    tree.write(SITEMAP_XML, encoding="utf-8", xml_declaration=True)


def load_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", []) if isinstance(data, dict) else []
    out: set[str] = set()
    for e in entries:
        if isinstance(e, dict):
            eid = str(e.get("id") or "").strip()
            if eid:
                out.add(eid)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="entries.json から静的記事HTMLを生成")
    parser.add_argument("--days", type=int, default=30, help="生成対象の日数（既定: 30）")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="既存記事HTMLを再生成しない")
    parser.add_argument("--force", action="store_true", help="既存記事HTMLも再生成する")
    parser.add_argument("--only-new", action="store_true", help="前回との差分（新規ID）のみ生成する")
    parser.add_argument("--prev-entries", type=Path, help="更新前 entries.json のパス（--only-new と併用）")
    args = parser.parse_args()

    with ENTRIES_JSON.open(encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", []) if isinstance(data, dict) else []

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, args.days))
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    prev_ids: set[str] = set()
    if args.only_new and args.prev_entries:
        prev_ids = load_ids(args.prev_entries)

    generated = 0
    skipped_old = 0
    skipped_exists = 0
    skipped_not_new = 0
    article_urls: dict[str, str] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "").strip()
        if not entry_id:
            continue
        if args.only_new and prev_ids and entry_id in prev_ids:
            skipped_not_new += 1
            continue
        dt = parse_entry_date(entry)
        if dt is None or dt < cutoff:
            skipped_old += 1
            continue

        out_file = ARTICLES_DIR / f"{entry_id}.html"
        if out_file.exists() and not args.force:
            skipped_exists += 1
        else:
            out_file.write_text(render_article_html(entry), encoding="utf-8")
            generated += 1

        loc = f"{SITE_URL}/articles/{entry_id}.html"
        article_urls[loc] = dt.date().isoformat()

    update_sitemap(article_urls)

    print(f"Target window: last {args.days} days")
    print(f"Generated: {generated}")
    print(f"Skipped (outside window): {skipped_old}")
    if args.only_new:
        print(f"Skipped (not new id): {skipped_not_new}")
    print(f"Skipped (already exists): {skipped_exists}")
    print(f"Sitemap article urls touched: {len(article_urls)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
