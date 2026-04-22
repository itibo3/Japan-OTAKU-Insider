from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import feedparser

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from http_fetch_config import FETCH_USER_AGENT

from .db import get_connection
from .sources_manager import list_sources, mark_source_check


def _clean_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _to_iso(dt_struct: Any) -> Optional[str]:
    """
    feedparser の *_parsed（time.struct_time）をUTC ISOにする。
    """
    if not dt_struct:
        return None
    try:
        dt = datetime(*dt_struct[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


@dataclass
class FetchResult:
    source_id: str
    ok: bool
    fetched: int
    inserted: int
    skipped_existing: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "ok": self.ok,
            "fetched": self.fetched,
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "error": self.error,
        }


def _extract_ogp_image(entry: Any) -> Optional[str]:
    """
    feedparser のエントリから画像URLを抽出する。
    取得優先順: media_content → media_thumbnail → links[type=image]
    """
    # media_content
    media_content = getattr(entry, "media_content", None)
    if media_content and isinstance(media_content, list):
        url = (media_content[0] or {}).get("url")
        if url:
            return url

    # media_thumbnail
    media_thumb = getattr(entry, "media_thumbnail", None)
    if media_thumb and isinstance(media_thumb, list):
        url = (media_thumb[0] or {}).get("url")
        if url:
            return url

    # links から type が image のもの
    links = getattr(entry, "links", None)
    if links and isinstance(links, list):
        for link in links:
            if "image" in (link.get("type") or ""):
                href = link.get("href") or link.get("url")
                if href:
                    return href

    return None


def fetch_all_sources(data_dir, limit_per_source: int = 20) -> Dict[str, Any]:
    sources = list_sources(data_dir)
    rss_sources = [s for s in sources if s.get("rss_url")]

    results: List[Dict[str, Any]] = []
    total_inserted = 0

    for s in rss_sources:
        r = fetch_one_source(data_dir, s, limit=limit_per_source)
        results.append(r.to_dict())
        if r.ok:
            total_inserted += r.inserted

    return {"ok": True, "total_sources": len(rss_sources), "total_inserted": total_inserted, "results": results}


def fetch_one_source(data_dir, source: Dict[str, Any], limit: int = 20) -> FetchResult:
    source_id = source.get("id") or ""
    rss_url = source.get("rss_url") or ""
    if not source_id or not rss_url:
        return FetchResult(source_id=source_id or "(missing)", ok=False, fetched=0, inserted=0, skipped_existing=0, error="missing id or rss_url")

    # disabled チェック（DBの disabled カラムが 1 の場合スキップ）
    if source.get("disabled"):
        return FetchResult(source_id=source_id, ok=True, fetched=0, inserted=0, skipped_existing=0, error=None)

    try:
        feed = feedparser.parse(rss_url, agent=FETCH_USER_AGENT)
    except Exception as e:
        mark_source_check(data_dir, source_id, success=False)
        return FetchResult(source_id=source_id, ok=False, fetched=0, inserted=0, skipped_existing=0, error=str(e))

    entries = list(feed.entries or [])[:limit]
    inserted = 0
    skipped_existing = 0

    with get_connection(data_dir) as conn:
        for entry in entries:
            title = _clean_html(getattr(entry, "title", "") or "") or "(no title)"
            url = getattr(entry, "link", "") or ""
            if not url:
                continue

            # 重複はURLユニークで弾く
            exists = conn.execute("SELECT 1 FROM articles WHERE url = ? LIMIT 1", (url,)).fetchone()
            if exists:
                skipped_existing += 1
                continue

            summary = _clean_html(getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
            if len(summary) > 400:
                summary = summary[:400] + "…"

            published_at = _to_iso(getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None))
            ogp_image = _extract_ogp_image(entry)

            conn.execute(
                """
                INSERT INTO articles (source_id, title, url, excerpt, published_at, ogp_image)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source_id, title, url, summary, published_at, ogp_image),
            )
            inserted += 1

    mark_source_check(data_dir, source_id, success=True)
    return FetchResult(
        source_id=source_id,
        ok=True,
        fetched=len(entries),
        inserted=inserted,
        skipped_existing=skipped_existing,
        error=None,
    )

