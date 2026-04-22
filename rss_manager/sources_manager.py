from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from .db import get_connection


@dataclass
class Source:
    id: str
    name: str
    url: str
    rss_url: Optional[str]
    type: str
    categories: List[str]
    language: str = "ja"
    status: str = "alive"
    fetch_interval_minutes: int = 60


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def list_sources(data_dir: Path) -> List[dict]:
    from .db import get_db_path

    with get_connection(data_dir) as conn:
        rows = conn.execute(
            "SELECT id, name, url, rss_url, type, categories, language, status, "
            "last_fetched_at, last_checked_at, fetch_interval_minutes, error_count, disabled "
            "FROM sources ORDER BY id"
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        if item.get("categories"):
            try:
                item["categories"] = json.loads(item["categories"])
            except Exception:
                item["categories"] = []
        else:
            item["categories"] = []
        result.append(item)
    return result


def upsert_source(data_dir: Path, source: Source, disabled: bool = False) -> None:
    payload = asdict(source)
    payload["categories"] = json.dumps(payload["categories"])
    payload["disabled"] = 1 if disabled else 0
    now = _now()
    with get_connection(data_dir) as conn:
        conn.execute(
            """
            INSERT INTO sources (
                id, name, url, rss_url, type, categories, language,
                status, fetch_interval_minutes, disabled, created_at, updated_at
            ) VALUES (
                :id, :name, :url, :rss_url, :type, :categories, :language,
                :status, :fetch_interval_minutes, :disabled, :created_at, :updated_at
            )
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                url=excluded.url,
                rss_url=excluded.rss_url,
                type=excluded.type,
                categories=excluded.categories,
                language=excluded.language,
                status=excluded.status,
                fetch_interval_minutes=excluded.fetch_interval_minutes,
                disabled=excluded.disabled,
                updated_at=excluded.updated_at
            ;
            """,
            {
                **payload,
                "created_at": now,
                "updated_at": now,
            },
        )


def delete_source(data_dir: Path, source_id: str) -> None:
    with get_connection(data_dir) as conn:
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))


def update_source_category(data_dir: Path, source_id: str, categories: List[str]) -> None:
    with get_connection(data_dir) as conn:
        conn.execute(
            "UPDATE sources SET categories = ?, updated_at = ? WHERE id = ?",
            (json.dumps(categories), _now(), source_id),
        )


def mark_source_check(data_dir: Path, source_id: str, success: bool) -> None:
    with get_connection(data_dir) as conn:
        if success:
            conn.execute(
                "UPDATE sources SET last_checked_at = ?, error_count = 0, status = 'alive' WHERE id = ?",
                (_now(), source_id),
            )
        else:
            conn.execute(
                "UPDATE sources SET last_checked_at = ?, error_count = error_count + 1 WHERE id = ?",
                (_now(), source_id),
            )


def import_from_sources_json(
    data_dir: Path, json_path: Path, replace: bool = False
) -> dict[str, Any]:
    """
    既存の data/sources.json からDBに取り込むヘルパ。
    replace=False: すでにDBに同じIDがあればスキップ（足りない分だけ追加）
    replace=True: 全ソースを削除してから sources.json の内容で再構築
    """
    if not json_path.exists():
        return {"ok": False, "error": "sources.json not found", "added": 0}

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    sources_list = data.get("sources", [])
    if not sources_list:
        return {"ok": True, "added": 0, "message": "sources.json is empty"}

    existing_ids: set[str] = set()
    if not replace:
        existing_ids = {row["id"] for row in list_sources(data_dir)}
    else:
        with get_connection(data_dir) as conn:
            conn.execute("DELETE FROM sources")

    added = 0
    for raw in sources_list:
        if raw.get("id") in existing_ids:
            continue
        src = Source(
            id=raw["id"],
            name=raw["name"],
            url=raw["url"],
            rss_url=raw.get("rss"),
            type=raw.get("type", "rss"),
            categories=raw.get("categories", []),
            language=raw.get("language", "ja"),
            status="alive",
        )
        upsert_source(data_dir, src, disabled=bool(raw.get("disabled", False)))
        added += 1

    return {"ok": True, "added": added, "total": len(sources_list)}


def export_to_sources_json(data_dir: Path, json_path: Path, backup: bool = True) -> dict[str, Any]:
    """
    DBのsourcesを data/sources.json に書き戻す。
    - 既存ファイルの content_tags / update_frequency は可能な範囲で保持する
    - まずは Phase A として「壊れない書き戻し」を優先する
    """
    existing_meta: dict[str, dict[str, Any]] = {}
    if json_path.exists():
        try:
            with json_path.open("r", encoding="utf-8") as f:
                old = json.load(f)
            for s in old.get("sources", []):
                sid = s.get("id")
                if isinstance(sid, str) and sid:
                    existing_meta[sid] = s
        except Exception:
            existing_meta = {}

    if backup and json_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = json_path.with_name(f"{json_path.name}.backup_{ts}")
        backup_path.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")

    exported = []
    for s in list_sources(data_dir):
        sid = s.get("id") or ""
        if not sid:
            continue
        old = existing_meta.get(sid, {})
        content_tags = old.get("content_tags") or []
        if not isinstance(content_tags, list):
            content_tags = []
        # 新規ソースは content_tags が空になりがちなので最低限 id を入れておく
        if len(content_tags) == 0:
            content_tags = [sid]
        entry: dict[str, Any] = {
            "id": sid,
            "name": s.get("name") or sid,
            "url": s.get("url") or "",
            "rss": s.get("rss_url"),
            "type": s.get("type") or old.get("type") or "rss",
            "categories": s.get("categories") or old.get("categories") or [],
            "content_tags": content_tags,
            "language": s.get("language") or old.get("language") or "ja",
            "update_frequency": old.get("update_frequency") or "daily",
        }
        # ng_keywords / ok_keywords / disabled は既存ファイルの値を引き継ぐ
        # （DBスキーマにこれらのカラムはないため、sources.json が唯一の正）
        if old.get("ng_keywords"):
            entry["ng_keywords"] = old["ng_keywords"]
        if old.get("ok_keywords"):
            entry["ok_keywords"] = old["ok_keywords"]
        if old.get("disabled"):
            entry["disabled"] = True
        exported.append(entry)

    out = {"sources": exported}
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=4), encoding="utf-8")
    return {"ok": True, "count": len(exported), "path": str(json_path)}

