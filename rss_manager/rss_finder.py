from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Dict, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from http_fetch_config import FETCH_USER_AGENT as USER_AGENT

TIMEOUT = 10


@dataclass
class RssDiscoveryResult:
    found: bool
    rss_url: Optional[str] = None
    method: Optional[str] = None
    site_title: Optional[str] = None
    preview: Optional[list[dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        out: Dict[str, Any] = {
            "found": self.found,
            "rss_url": self.rss_url,
            "method": self.method,
            "site_title": self.site_title,
        }
        if self.preview is not None:
            out["preview"] = self.preview
        return out


def _get(url: str) -> Optional[requests.Response]:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        if resp.status_code >= 400:
            return None
        return resp
    except Exception:
        return None


def _preview_feed_items(rss_url: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    RSS/Atomの先頭数件をプレビュー用に抽出する。
    UIで「追加前プレビュー（最新5件）」を出すための補助。
    """
    parsed = feedparser.parse(
        rss_url,
        request_headers={"User-Agent": USER_AGENT},
    )
    items: list[dict[str, Any]] = []
    for entry in (parsed.entries or [])[:limit]:
        items.append(
            {
                "title": getattr(entry, "title", "") or "",
                "link": getattr(entry, "link", "") or "",
                "published": getattr(entry, "published", "") or getattr(entry, "updated", "") or "",
            }
        )
    return items


def find_rss(url: str) -> Dict[str, Optional[str]]:
    """
    URLからRSS/Atomフィードを探す。

    Stage 1: HTML内 <link rel=\"alternate\" type=\"application/rss+xml\"> 等の探索
    Stage 2: よくあるパスパターンを順番に試す
    """
    # Stage 1
    resp = _get(url)
    if resp is not None and "html" in resp.headers.get("Content-Type", ""):
        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        # サイトタイトル
        title_tag = soup.find("title")
        site_title = unescape(title_tag.get_text(strip=True)) if title_tag else None

        for link in soup.find_all("link", rel=lambda v: v and "alternate" in v):
            t = (link.get("type") or "").lower()
            if "rss" in t or "atom" in t or "xml" in t:
                href = link.get("href")
                if not href:
                    continue
                rss_url = requests.compat.urljoin(resp.url, href)
                return RssDiscoveryResult(
                    found=True,
                    rss_url=rss_url,
                    method="meta_tag",
                    site_title=site_title,
                    preview=_preview_feed_items(rss_url),
                ).to_dict()

    # Stage 2
    common_paths = [
        "/feed/",
        "/feed/rss2/",
        "/rss/",
        "/rss/index.xml",
        "/atom.xml",
        "/index.xml",
        "/rss.xml",
        "/feed.xml",
        "/blog/feed/",
        "/news/feed/",
    ]
    base = url.rstrip("/")
    for path in common_paths:
        candidate = base + path
        resp2 = _get(candidate)
        if not resp2:
            continue
        ctype = resp2.headers.get("Content-Type", "").lower()
        text_start = resp2.text.lstrip()[:100].lower()
        if any(x in ctype for x in ["xml", "rss", "atom"]) or re.match(r"<\?xml|<rss|<feed", text_start):
            return RssDiscoveryResult(
                found=True,
                rss_url=resp2.url,
                method="common_path",
                site_title=None,
                preview=_preview_feed_items(resp2.url),
            ).to_dict()

    return RssDiscoveryResult(found=False).to_dict()

