# RSS Manager — 全ソースコードまとめ
作成日: 2026-03-22

## 1. ファイル構成一覧
```
/
├── rss_manager.py
├── start_rss_manager.sh
├── requirements-rss-manager.txt
├── README_rss_manager.md
├── rss_manager/
│   ├── __init__.py
│   ├── server.py
│   ├── db.py
│   ├── sources_manager.py
│   ├── rss_fetcher.py
│   └── rss_finder.py
├── rss_manager_ui/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── manifest.json
│   └── sw.js
└── rss_manager_data/
    └── manager.db
```

## 2. バックエンド

### rss_manager/__init__.py
```python
"""
Japan OTAKU Insider RSS Manager V2 パッケージ。

Phase A では:
- SQLite の初期化
- ソース情報のCRUD
- RSSフィードURLの自動発見
- シンプルなHTTP APIサーバ
のみを提供する。
"""
```

### rss_manager/server.py
```python
"""
server.py — RSS Manager のローカル HTTP サーバー

目的: rss_manager_ui/ の静的ファイル配信 + /api/* の REST API 提供
入力: run_server(host, port, project_root) で起動
触っていい所: API ハンドラの追加・修正。do_* のラッパーは触らない方が安全
"""
from __future__ import annotations

import json
import subprocess
import traceback
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import urlparse, parse_qs

import requests

from .db import initialize_database, list_articles, toggle_article_bookmark
from .rss_finder import find_rss
from .rss_fetcher import fetch_all_sources
from .sources_manager import (
    Source,
    delete_source,
    import_from_sources_json,
    list_sources,
    mark_source_check,
    update_source_category,
    upsert_source,
    export_to_sources_json,
)


class RssManagerHandler(SimpleHTTPRequestHandler):
    server_version = "RSSManagerHTTP/0.1"

    def translate_path(self, path: str) -> str:
        if path.startswith("/api/"):
            return super().translate_path(path)
        ui_root: Path = self.server.ui_root  # type: ignore[attr-defined]
        if path == "/" or path == "":
            return str(ui_root / "index.html")
        rel = path.lstrip("/")
        return str(ui_root / rel)

    # --- API routing（全メソッドを try-except で囲む） ---

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._safe_call(self.handle_api_get)
        else:
            super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._safe_call(self.handle_api_post)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_DELETE(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._safe_call(self.handle_api_delete)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_PUT(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._safe_call(self.handle_api_put)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def _safe_call(self, handler_fn) -> None:
        """API ハンドラを安全に実行。未処理例外は JSON エラーとして返す"""
        try:
            handler_fn()
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[ERROR] {self.path}: {e}\n{tb}")
            try:
                self.json_response(
                    {"error": f"サーバー内部エラー: {type(e).__name__}: {e}"},
                    status=500,
                )
            except Exception:
                pass

    # --- Helpers ---

    def json_response(self, data: Any, status: int = 200) -> None:
        try:
            body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        except Exception:
            body = json.dumps(
                {"error": "レスポンスのシリアライズに失敗しました"}, ensure_ascii=False
            ).encode("utf-8")
            status = 500
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def parse_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # --- API implementations ---

    @property
    def data_dir(self) -> Path:
        return self.server.data_dir  # type: ignore[attr-defined]

    @property
    def project_root(self) -> Path:
        return self.server.project_root  # type: ignore[attr-defined]

    def handle_api_get(self) -> None:
        req = urlparse(self.path)
        path = req.path
        qs = parse_qs(req.query)

        if path == "/api/sources":
            items = list_sources(self.data_dir)
            self.json_response({"sources": items})
            return

        if path.startswith("/api/sources/") and path.endswith("/check"):
            source_id = path.split("/")[3]
            sources = {s["id"]: s for s in list_sources(self.data_dir)}
            s = sources.get(source_id)
            if not s:
                self.json_response({"error": "not found"}, status=404)
                return
            ok = self._check_source_alive(s)
            mark_source_check(self.data_dir, source_id, success=ok)
            self.json_response({"ok": ok})
            return

        if path == "/api/articles":
            limit = 50
            if "limit" in qs:
                try:
                    limit = int((qs.get("limit") or ["50"])[0])
                except Exception:
                    limit = 50
            items = list_articles(self.data_dir, limit=limit)
            self.json_response({"ok": True, "count": len(items), "articles": items})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def handle_api_post(self) -> None:
        req_path = urlparse(self.path).path

        if req_path == "/api/sources/search":
            payload = self.parse_json_body()
            url = payload.get("url") or ""
            if not url:
                self.json_response({"error": "url is required"}, status=400)
                return
            result = find_rss(url)
            self.json_response(result)
            return

        if req_path == "/api/sources/add":
            payload = self.parse_json_body()
            try:
                source_id = (payload.get("id") or "").strip()
                if not source_id:
                    self.json_response({"error": "id is required"}, status=400)
                    return
                src = Source(
                    id=source_id,
                    name=payload.get("name") or source_id,
                    url=payload["url"],
                    rss_url=payload.get("rss_url"),
                    type=payload.get("type", "rss"),
                    categories=payload.get("categories") or [],
                    language=payload.get("language", "ja"),
                    status=payload.get("status", "alive"),
                )
            except KeyError as e:
                self.json_response({"error": f"missing field: {e.args[0]}"}, status=400)
                return
            upsert_source(self.data_dir, src)
            self.json_response({"ok": True})
            return

        if req_path == "/api/sources/check-all":
            results: Dict[str, bool] = {}
            for s in list_sources(self.data_dir):
                ok = self._check_source_alive(s)
                mark_source_check(self.data_dir, s["id"], success=ok)
                results[s["id"]] = ok
            self.json_response({"ok": True, "results": results})
            return

        if req_path == "/api/sources/export":
            sources_json = self.project_root / "data" / "sources.json"
            result = export_to_sources_json(self.data_dir, sources_json, backup=True)
            self.json_response(result)
            return

        if req_path == "/api/git/push":
            self._handle_git_push()
            return

        if req_path == "/api/sources/import":
            sources_json = self.project_root / "data" / "sources.json"
            req = urlparse(self.path)
            qs = parse_qs(req.query)
            replace = (qs.get("replace") or ["0"])[0] in ("1", "true", "yes")
            result = import_from_sources_json(
                self.data_dir, sources_json, replace=replace
            )
            self.json_response(result)
            return

        if req_path == "/api/fetch":
            payload = self.parse_json_body()
            try:
                limit = int(payload.get("limit", 20))
            except Exception:
                limit = 20
            result = fetch_all_sources(self.data_dir, limit_per_source=limit)
            self.json_response(result)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def _handle_git_push(self) -> None:
        """書き戻し → git add → commit → push を実行"""
        root = self.project_root
        sources_json = root / "data" / "sources.json"
        cwd = str(root.resolve())

        print(f"[git/push] cwd={cwd}")
        export_to_sources_json(self.data_dir, sources_json, backup=True)
        print("[git/push] export 完了")

        def run_git(*args: str, timeout: int = 15) -> subprocess.CompletedProcess:
            r = subprocess.run(
                ["git", *args],
                cwd=cwd, capture_output=True, text=True, timeout=timeout,
            )
            print(f"[git/push] git {' '.join(args)} -> rc={r.returncode}")
            if r.stdout.strip():
                print(f"  stdout: {r.stdout.strip()[:200]}")
            if r.stderr.strip():
                print(f"  stderr: {r.stderr.strip()[:200]}")
            return r

        r = run_git("add", "data/sources.json")
        if r.returncode != 0:
            self.json_response({
                "error": f"git add 失敗: {(r.stderr or r.stdout or '不明').strip()[:200]}"
            }, status=500)
            return

        r = run_git("diff", "--staged", "--quiet")
        if r.returncode == 0:
            self.json_response({"ok": True, "message": "変更なし（プッシュ不要）"})
            return

        r = run_git("commit", "-m", "chore: update sources.json")
        if r.returncode != 0:
            self.json_response({
                "error": f"git commit 失敗: {(r.stderr or r.stdout or '不明').strip()[:200]}"
            }, status=500)
            return

        run_git("pull", "--rebase", "origin", "main", timeout=30)

        r = run_git("push", "origin", "HEAD", timeout=90)
        if r.returncode != 0:
            self.json_response({
                "error": f"git push 失敗: {(r.stderr or r.stdout or '認証エラーやネットワークを確認').strip()[:300]}"
            }, status=500)
            return

        self.json_response({"ok": True, "message": "プッシュ完了"})

    def _extract_source_id(self) -> Tuple[bool, str]:
        parts = self.path.split("/")
        if len(parts) < 4:
            return False, ""
        return True, parts[3]

    def handle_api_delete(self) -> None:
        ok, source_id = self._extract_source_id()
        if not ok or not source_id:
            self.json_response({"error": "invalid source id"}, status=400)
            return
        delete_source(self.data_dir, source_id)
        self.json_response({"ok": True})

    def handle_api_put(self) -> None:
        req = urlparse(self.path)
        path = req.path

        if path.endswith("/category"):
            ok, source_id = self._extract_source_id()
            if not ok or not source_id:
                self.json_response({"error": "invalid source id"}, status=400)
                return
            payload = self.parse_json_body()
            categories = payload.get("categories") or []
            if not isinstance(categories, list):
                self.json_response({"error": "categories must be a list"}, status=400)
                return
            update_source_category(self.data_dir, source_id, categories)
            self.json_response({"ok": True})
            return

        if path.startswith("/api/articles/") and path.endswith("/bookmark"):
            parts = path.split("/")
            if len(parts) >= 5:
                try:
                    article_id = int(parts[3])
                except Exception:
                    article_id = -1
                if article_id > 0:
                    result = toggle_article_bookmark(self.data_dir, article_id)
                    if result is None:
                        self.json_response({"error": "article not found"}, status=404)
                    else:
                        self.json_response({"ok": True, "article": result})
                    return

            self.json_response({"error": "invalid article id"}, status=400)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def _check_source_alive(self, source: Dict[str, Any]) -> bool:
        target = source.get("rss_url") or source.get("url")
        if not target:
            return False
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0",
        }
        try:
            resp = requests.get(
                target,
                headers=headers,
                timeout=15,
                allow_redirects=True,
            )
            return resp.status_code < 400
        except Exception:
            return False


def run_server(host: str, port: int, project_root: Path) -> None:
    data_dir = project_root / "rss_manager_data"
    ui_root = project_root / "rss_manager_ui"

    initialize_database(data_dir)

    sources_json = project_root / "data" / "sources.json"
    from .sources_manager import import_from_sources_json, list_sources

    existing = list_sources(data_dir)
    if len(existing) == 0:
        candidates = [sources_json, Path.cwd() / "data" / "sources.json"]
        for cand in candidates:
            if cand.exists():
                import_from_sources_json(data_dir, cand, replace=True)
                print("  -> sources.json からソースを自動読み込みしました")
                break
        else:
            print("  sources.json が見つかりません。手動でソースを追加してください。")

    handler_class = RssManagerHandler

    def handler(*args: Any, **kwargs: Any) -> RssManagerHandler:
        h = handler_class(*args, directory=str(ui_root), **kwargs)
        return h

    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.data_dir = data_dir  # type: ignore[attr-defined]
    httpd.ui_root = ui_root  # type: ignore[attr-defined]
    httpd.project_root = project_root  # type: ignore[attr-defined]

    try:
        print(f"RSS Manager running on http://{host}:{port}/ (Ctrl+C to stop)")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down RSS Manager...")
    finally:
        httpd.server_close()
```

### rss_manager/db.py
```python
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DB_FILENAME = "manager.db"


def get_db_path(data_dir: Path) -> Path:
    return data_dir / DB_FILENAME


def initialize_database(data_dir: Path) -> None:
    """
    データディレクトリにSQLiteファイルがなければ作成し、必要なテーブルを作る。
    Phase A: sources
    Phase B1: articles（収集した記事を蓄積）
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = get_db_path(data_dir)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        _create_sources_table(conn)
        _create_articles_table(conn)
        _migrate_schema(conn)
        conn.commit()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """既存DBへのカラム追加（ALTER TABLE）。べき等に動作する。"""
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()}
    if "disabled" not in existing_cols:
        conn.execute("ALTER TABLE sources ADD COLUMN disabled INTEGER DEFAULT 0")


def _create_sources_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            rss_url TEXT,
            type TEXT DEFAULT 'rss',
            categories TEXT,
            language TEXT DEFAULT 'ja',
            status TEXT DEFAULT 'alive',
            last_fetched_at DATETIME,
            last_checked_at DATETIME,
            fetch_interval_minutes INTEGER DEFAULT 60,
            error_count INTEGER DEFAULT 0,
            disabled INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _create_articles_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT REFERENCES sources(id),
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            full_text TEXT,
            excerpt TEXT,
            ogp_image TEXT,
            published_at DATETIME,
            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_bookmarked BOOLEAN DEFAULT 0,
            is_exported BOOLEAN DEFAULT 0,
            exported_at DATETIME
        );
        """
    )


@contextmanager
def get_connection(data_dir: Path) -> Iterator[sqlite3.Connection]:
    db_path = get_db_path(data_dir)
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    finally:
        conn.close()


def list_articles(data_dir: Path, limit: int = 50) -> list[dict]:
    """
    収集済み articles を最新順で返す（Phase B2: 新着一覧表示用）
    """
    with get_connection(data_dir) as conn:
        rows = conn.execute(
            """
            SELECT
              id,
              source_id,
              title,
              url,
              excerpt,
              ogp_image,
              published_at,
              fetched_at,
              is_bookmarked
            FROM articles
            ORDER BY fetched_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def toggle_article_bookmark(data_dir: Path, article_id: int) -> dict | None:
    """
    articles の is_bookmarked をトグルする（任意機能: Phase B2）
    """
    with get_connection(data_dir) as conn:
        row = conn.execute(
            "SELECT is_bookmarked FROM articles WHERE id = ? LIMIT 1",
            (article_id,),
        ).fetchone()
        if not row:
            return None

        current = int(row["is_bookmarked"] or 0)
        new_val = 0 if current else 1
        conn.execute(
            "UPDATE articles SET is_bookmarked = ? WHERE id = ?",
            (new_val, article_id),
        )
        return {"id": article_id, "is_bookmarked": bool(new_val)}
```

### rss_manager/sources_manager.py
```python
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
```

### rss_manager/rss_fetcher.py
```python
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser

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
        feed = feedparser.parse(rss_url)
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
```

### rss_manager/rss_finder.py
```python
from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any, Dict, Optional

import feedparser
import requests
from bs4 import BeautifulSoup


USER_AGENT = "JapanOtakuInsider-RSS-Manager/0.1 (+https://itibo3.github.io/Japan-OTAKU-Insider/)"
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

    Stage 1: HTML内 <link rel="alternate" type="application/rss+xml"> 等の探索
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
```

### rss_manager/rss_checker.py
ファイル不在

### rss_manager/rss_preview.py
ファイル不在

## 3. フロントエンド

### rss_manager_ui/index.html
```html
<!doctype html>
<html lang="ja">

<head>
  <meta charset="utf-8" />
  <title>Japan OTAKU Insider — RSS Manager V2</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="manifest" href="manifest.json" />
  <meta name="theme-color" content="#020617" />
  <link rel="stylesheet" href="style.css" />
</head>

<body>
  <header class="app-header">
    <div class="title-block">
      <span class="logo">📡</span>
      <div>
        <h1>Japan OTAKU Insider — RSS Manager V2</h1>
        <p class="subtitle">RSSソースをまとめて管理するためのローカル専用ツール</p>
      </div>
    </div>
    <nav class="tabs">
      <button class="tab active" data-tab="sources">📡 ソース管理</button>
      <button class="tab" data-tab="articles">📥 収集記事</button>
      <button class="tab disabled" data-tab="export" title="Phase C以降で有効になります">📤 エクスポート</button>
    </nav>
  </header>

  <main class="app-main">
    <section id="tab-sources" class="tab-panel active">
      <div id="import-banner" class="import-banner" style="display:none;">
        <p>登録済みソースがありません。下のボタンで読み込んでください。</p>
        <button id="import-banner-button" class="primary">sources.json から読み込む（あみあみ・4gamer など 22 件）</button>
      </div>
      <section class="card">
        <h2>RSS検索と追加</h2>
        <div class="form-row">
          <input id="discover-url" type="url" placeholder="サイトURLを入力（例: https://natalie.mu/comic）" />
          <button id="discover-button">RSSを探す</button>
        </div>
        <div id="discover-result" class="result-box"></div>
      </section>

      <section class="card">
        <div class="card-header">
          <h2>登録済みソース</h2>
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
              <button id="import-sources-button" class="secondary" title="data/sources.json からソースを読み込み（DBが空の場合や不整合時に使用）">sources.jsonから読み込む</button>
              <button id="export-sources-button" class="secondary" title="DBの内容をdata/sources.jsonに書き戻します（バックアップ作成あり）">sources.jsonへ書き戻す</button>
              <button id="push-github-button" class="secondary" title="sources.jsonを書き戻してGitHubにコミット・プッシュ">GitHubにプッシュ</button>
              <button id="check-all-button">全ソースの生存確認</button>
            </div>
        </div>
        <div class="table-wrap">
          <table class="sources-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>名前</th>
                <th>URL</th>
                <th>RSS</th>
                <th>カテゴリ</th>
                <th>状態</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody id="sources-tbody"></tbody>
          </table>
        </div>
      </section>
    </section>

    <section id="tab-articles" class="tab-panel">
      <section class="card">
        <div class="card-header">
          <h2>記事収集</h2>
          <div style="display:flex; gap:8px; align-items:center;">
            <label class="muted" for="fetch-limit" style="margin:0;">1ソースあたり</label>
            <input id="fetch-limit" type="number" min="1" max="50" value="5" style="width:90px;" />
            <button id="fetch-articles-button">収集</button>
          </div>
        </div>
        <div id="articles-fetch-summary" class="result-box" style="margin-top:10px;"></div>
      </section>

      <section class="card">
        <div class="card-header">
          <h2>新着一覧（最新順）</h2>
          <button id="refresh-articles-button" class="secondary">一覧更新</button>
        </div>
        <div id="articles-list" class="articles-list"></div>
      </section>
    </section>

    <section id="tab-export" class="tab-panel">
      <p class="muted">エクスポートタブは Phase C で実装予定です。</p>
    </section>
  </main>

  <footer class="app-footer">
    <span>RSS Manager V2 (Phase A) — ローカル専用</span>
  </footer>

  <script src="app.js"></script>
  <script>
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("sw.js")
        .catch((err) => console.error("Service worker registration failed", err));
    }
  </script>
</body>

</html>
```

### rss_manager_ui/app.js
```javascript
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

function slugifyAscii(input) {
  return String(input || "")
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function pickHostname(urlOrRss) {
  try {
    const u = new URL(urlOrRss);
    return u.hostname || "";
  } catch {
    return "";
  }
}

async function generateSafeSourceId({ url, rss_url, site_title }) {
  // 1) URL/RSSのホスト名を最優先（日本語タイトルでも空にならない）
  const host = pickHostname(rss_url) || pickHostname(url);
  let base = slugifyAscii(host);

  // 2) それでも空なら、RSS/URL文字列からスラグ化
  if (!base) base = slugifyAscii(rss_url || url || "");

  // 3) 最後の保険：固定プレフィックス
  if (!base) base = "source";

  // 既存IDと重複しないように suffix を付与
  const data = await api("/api/sources");
  const existing = new Set((data.sources || []).map((s) => String(s.id || "")));

  let id = base;
  let i = 2;
  while (existing.has(id)) {
    id = `${base}-${i}`;
    i++;
  }
  return id;
}

function suggestCategories({ url, rss_url, site_title }) {
  const text = `${url || ""} ${rss_url || ""} ${site_title || ""}`.toLowerCase();
  const out = new Set();

  // ざっくりヒューリスティック（Phase Aはこれで十分）
  if (text.includes("collabo") || text.includes("cafe")) out.add("cafe");
  if (text.includes("figure") || text.includes("goodsmile") || text.includes("kotobukiya")) out.add("figure");
  if (text.includes("event") || text.includes("anime-japan") || text.includes("animejapan")) out.add("event");
  if (text.includes("anime") || text.includes("natalie") || text.includes("animes")) out.add("anime");
  if (text.includes("game") || text.includes("4gamer") || text.includes("dengeki") || text.includes("hobby")) out.add("game");
  if (text.includes("news") || text.includes("otaku")) out.add("otaku-news");

  return Array.from(out);
}

function renderSourcesTable(sources) {
  const tbody = $("#sources-tbody");
  tbody.innerHTML = "";
  if (!sources || sources.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="padding: 24px; text-align: center; background: rgba(56, 189, 248, 0.08); border-radius: 8px;">
          <p style="margin: 0 0 12px; font-size: 1.1em;">登録済みソースがありません</p>
          <p style="margin: 0 0 16px; color: var(--muted, #94a3b8);">data/sources.json から読み込むと、あみあみ・4gamer など 22 件のソースが使えるようになります</p>
          <button id="first-import-button" class="primary" style="font-size: 1em; padding: 10px 20px;">sources.json から読み込む</button>
        </td>
      </tr>
    `;
    const btn = document.getElementById("first-import-button");
    if (btn) btn.addEventListener("click", () => doImport());
    return;
  }
  for (const src of sources) {
    const tr = document.createElement("tr");
    tr.dataset.sourceId = src.id;
    const catsHtml = (src.categories || []).map((c) => `<span class="pill">${c}</span>`).join("") || `<span class="muted">(なし)</span>`;
    const cats = `<div class="cats-cell">${catsHtml}</div>`;
    const statusClass = `status-${src.status || "alive"}`;
    const hasValidId = typeof src.id === "string" && src.id.trim().length > 0;
    tr.innerHTML = `
      <td>${src.id}</td>
      <td>${src.name}</td>
      <td><a href="${src.url}" target="_blank" rel="noreferrer">${src.url}</a></td>
      <td>${src.rss_url ? `<a href="${src.rss_url}" target="_blank" rel="noreferrer">${src.rss_url}</a>` : "<span class=\"muted\">(未設定)</span>"}</td>
      <td>${cats || "<span class=\"muted\">(なし)</span>"}</td>
      <td class="${statusClass}">${src.status}</td>
      <td>
        <div class="btn-group">
          <button class="secondary btn-check" data-id="${src.id}" ${hasValidId ? "" : "disabled"}>チェック</button>
          <button class="secondary btn-edit-cats" data-id="${src.id}" ${hasValidId ? "" : "disabled"}>カテゴリ</button>
          <button class="danger btn-delete" data-id="${src.id}" ${hasValidId ? "" : "disabled"}>削除</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadSources() {
  let sources = [];
  try {
    const data = await api("/api/sources");
    sources = data.sources || [];
  } catch (e) {
    console.error("loadSources error:", e);
    sources = [];
  }
  renderSourcesTable(sources);
  const banner = document.getElementById("import-banner");
  const bannerBtn = document.getElementById("import-banner-button");
  if (banner && bannerBtn) {
    if (sources.length === 0) {
      banner.style.display = "block";
      bannerBtn.onclick = () => doImport();
    } else {
      banner.style.display = "none";
    }
  }
  return sources;
}

async function doImport() {
  const btn = document.getElementById("import-banner-button");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "読み込み中…";
  }
  try {
    const res = await api("/api/sources/import?replace=1", { method: "POST" });
    await loadSources();
    alert(`読み込み完了: ${res.total || res.added || "?"}件のソースを登録しました`);
  } catch (e) {
    alert(`読み込みに失敗しました: ${e.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "sources.json から読み込む（あみあみ・4gamer など 22 件）";
    }
  }
}

function safeAttrValue(value) {
  return String(value).replace(/"/g, '\\"');
}

function highlightRowById(id) {
  const tbody = $("#sources-tbody");
  const row = tbody.querySelector(`tr[data-source-id="${safeAttrValue(id)}"]`);
  if (!row) return false;
  row.scrollIntoView({ block: "center", behavior: "smooth" });
  row.style.outline = "2px solid rgba(56, 189, 248, 0.8)";
  row.style.outlineOffset = "2px";
  setTimeout(() => {
    row.style.outline = "";
    row.style.outlineOffset = "";
  }, 1800);
  return true;
}

async function discoverRss() {
  const urlInput = $("#discover-url");
  const box = $("#discover-result");
  const url = urlInput.value.trim();
  if (!url) return;
  box.textContent = "RSSを探索中…";
  try {
    const result = await api("/api/sources/search", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
    if (!result.found) {
      box.innerHTML = `<span class="muted">RSSフィードは見つかりませんでした。</span>`;
      return;
    }
    const id = await generateSafeSourceId({
      url,
      rss_url: result.rss_url,
      site_title: result.site_title,
    });
    const suggestedCategories = suggestCategories({
      url,
      rss_url: result.rss_url,
      site_title: result.site_title,
    });
    const preview = Array.isArray(result.preview) ? result.preview : [];
    const previewHtml = preview.length
      ? `
        <div style="margin-top:8px;"><strong>追加前プレビュー（最新${preview.length}件）</strong></div>
        <ol style="margin:6px 0 0 18px; display:flex; flex-direction:column; gap:4px;">
          ${preview
            .map(
              (it) =>
                `<li><a href="${it.link}" target="_blank" rel="noreferrer">${it.title || it.link}</a><span class="muted"> ${it.published ? `(${it.published})` : ""}</span></li>`,
            )
            .join("")}
        </ol>
      `
      : `<div class="muted" style="margin-top:8px;">プレビュー取得に失敗しました（RSSは見つかっています）。</div>`;

    const suggestedHtml = suggestedCategories.length
      ? `
        <div style="margin-top:8px;"><strong>カテゴリ候補</strong></div>
        <div style="margin-top:6px; display:flex; flex-wrap:wrap; gap:6px;">
          ${suggestedCategories
            .map((c) => `<button class="secondary btn-suggest-cat" data-cat="${c}">${c}</button>`)
            .join("")}
        </div>
        <div class="muted" style="margin-top:6px;">追加後にカテゴリを自動設定します（候補をクリック）。</div>
      `
      : `<div class="muted" style="margin-top:8px;">カテゴリ候補は見つかりませんでした。</div>`;

    box.innerHTML = `
      <div><strong>RSS発見:</strong> <a href="${result.rss_url}" target="_blank" rel="noreferrer">${result.rss_url}</a></div>
      <div>サイトタイトル: ${result.site_title || "(不明)"}</div>
      <div>検出方法: ${result.method}</div>
      <div class="muted">追加予定ID: ${id}</div>
      ${suggestedHtml}
      ${previewHtml}
      <div style="margin-top:10px;">
        <button id="add-source-button">このRSSをソースとして追加</button>
      </div>
    `;

    const selectedCats = new Set();
    box.querySelectorAll(".btn-suggest-cat").forEach((btn) => {
      btn.addEventListener("click", () => {
        const cat = btn.getAttribute("data-cat");
        if (!cat) return;
        if (selectedCats.has(cat)) {
          selectedCats.delete(cat);
          btn.style.borderColor = "";
          btn.style.color = "";
        } else {
          selectedCats.add(cat);
          btn.style.borderColor = "rgba(56, 189, 248, 0.7)";
          btn.style.color = "var(--text)";
        }
      });
    });
    $("#add-source-button").addEventListener("click", async () => {
      try {
        await api("/api/sources/add", {
          method: "POST",
          body: JSON.stringify({
            id,
            name: result.site_title || id,
            url,
            rss_url: result.rss_url,
            type: "rss",
            categories: Array.from(selectedCats),
          }),
        });
        // 追加後もプレビューが確認できるよう、画面は極力そのままにしてメッセージだけ出す
        const note = document.createElement("div");
        note.className = "muted";
        note.style.marginTop = "8px";
        note.textContent = `追加しました。追加ID: ${id}（下の一覧へ移動します）`;
        box.appendChild(note);
        const pushNote = document.createElement("div");
        pushNote.className = "muted";
        pushNote.style.marginTop = "6px";
        pushNote.style.color = "var(--accent-cyan, #38bdf8)";
        pushNote.textContent = "※ Daily Update ワークフローで反映するには「GitHubにプッシュ」を押してください。";
        box.appendChild(pushNote);
        urlInput.value = "";
        await loadSources();
        // 追加された行が見つからない場合は、同じIDで上書きされた可能性がある
        const found = highlightRowById(id);
        if (!found) {
          const warn = document.createElement("div");
          warn.className = "muted";
          warn.style.marginTop = "6px";
          warn.textContent =
            "一覧にIDが見つかりませんでした（同じIDで上書きされた/並び替えの影響の可能性があります）。";
          box.appendChild(warn);
        }
      } catch (e) {
        box.textContent = `追加に失敗しました: ${e.message}`;
      }
    });
  } catch (e) {
    box.textContent = `エラー: ${e.message}`;
  }
}

function setupTabs() {
  $$(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.classList.contains("disabled")) return;
      const tab = btn.getAttribute("data-tab");
      $$(".tab").forEach((b) => b.classList.toggle("active", b === btn));
      $$(".tab-panel").forEach((p) => {
        p.classList.toggle("active", p.id === `tab-${tab}`);
      });
      // 収集記事タブに切り替えたら一覧を再読み込み（運用品質の詰め）
      if (tab === "articles") {
        loadArticles();
      }
    });
  });
}

function promptCategories(defaultValue) {
  const input = window.prompt(
    "カテゴリをカンマ区切りで入力（例: cafe,figure,otaku-news）",
    defaultValue || "",
  );
  if (input == null) return null;
  return input
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function setupTableActions() {
  const tbody = $("#sources-tbody");
  tbody.addEventListener("click", async (e) => {
    const target = e.target;
    if (!(target instanceof HTMLButtonElement)) return;
    const id = target.getAttribute("data-id");
    if (!id) return;

    if (target.classList.contains("btn-check")) {
      try {
        const res = await api(`/api/sources/${encodeURIComponent(id)}/check`);
        await loadSources();
        highlightRowById(id);
        if (res && typeof res.ok === "boolean") {
          const msg = res.ok ? "OK（到達できた）" : "NG（到達できない）";
          alert(`生存確認: ${id} → ${msg}`);
        }
      } catch (err) {
        alert(`生存確認に失敗しました: ${err.message}`);
      }
      return;
    }

    if (target.classList.contains("btn-delete")) {
      if (!window.confirm(`ソース「${id}」を削除しますか？`)) return;
      await api(`/api/sources/${encodeURIComponent(id)}`, { method: "DELETE" });
      loadSources();
      return;
    }

    if (target.classList.contains("btn-edit-cats")) {
      const row = target.closest("tr");
      const catsCell = row?.querySelector("td:nth-child(5)");
      const currentText = catsCell?.textContent || "";
      const current =
        currentText && !currentText.includes("なし")
          ? currentText
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean)
            .join(",")
          : "";
      const categories = promptCategories(current);
      if (categories == null) return;
      await api(`/api/sources/${encodeURIComponent(id)}/category`, {
        method: "PUT",
        body: JSON.stringify({ categories }),
      });
      loadSources();
    }
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPublishedAt(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleDateString("ja-JP", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return String(isoStr).slice(0, 10);
  }
}

function renderArticlesList(articles, totalCount) {
  const list = $("#articles-list");
  if (!list) return;

  const items = Array.isArray(articles) ? articles : [];
  if (items.length === 0) {
    list.innerHTML = `<div class="muted">記事がありません（まだ収集されていません）。</div>`;
    return;
  }

  const countHtml = totalCount != null
    ? `<div class="muted" style="margin-bottom:12px;">全 ${totalCount} 件中 ${items.length} 件表示</div>`
    : "";

  list.innerHTML = countHtml + items
    .map((a) => {
      const id = a.id;
      const title = escapeHtml(a.title);
      const url = a.url || "#";
      let excerpt = a.excerpt ? escapeHtml(a.excerpt) : "";
      if (excerpt.length > 120) excerpt = excerpt.slice(0, 117) + "…";
      const publishedAt = formatPublishedAt(a.published_at);
      const isBookmarked = Boolean(a.is_bookmarked);
      const star = isBookmarked ? "★" : "☆";
      const sourceId = a.source_id ? `<span class="pill">${escapeHtml(a.source_id)}</span>` : "";
      const ogpHtml = a.ogp_image
        ? `<img class="article-ogp" src="${escapeHtml(a.ogp_image)}" alt="" loading="lazy">`
        : "";

      return `
        <article class="article-item ${a.is_bookmarked ? 'bookmarked' : ''}">
          <div class="article-top">
            ${ogpHtml}
            <div class="article-body">
              <a class="article-link" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${title}</a>
              ${excerpt ? `<div class="article-excerpt">${excerpt}</div>` : ""}
              <div class="muted article-meta">
                ${publishedAt ? `${publishedAt}` : ""}
                ${sourceId}
              </div>
            </div>
            <button class="secondary btn-bookmark" data-id="${id}" title="ブックマーク">${star}</button>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadArticles() {
  const list = $("#articles-list");
  if (!list) return;
  list.innerHTML = `<div class="muted">読み込み中…</div>`;
  try {
    const data = await api("/api/articles?limit=100", { method: "GET" });
    renderArticlesList(data.articles || [], data.count);
  } catch (e) {
    list.innerHTML = `<div class="muted">記事一覧の読み込みに失敗しました: ${escapeHtml(
      e.message || String(e)
    )}</div>`;
  }
}

function setupArticlesActions() {
  const list = $("#articles-list");
  if (!list) return;

  list.addEventListener("click", async (e) => {
    const target = e.target;
    if (!(target instanceof HTMLButtonElement)) return;
    if (!target.classList.contains("btn-bookmark")) return;

    const id = target.getAttribute("data-id");
    if (!id) return;

    target.disabled = true;
    try {
      await api(`/api/articles/${encodeURIComponent(id)}/bookmark`, {
        method: "PUT",
        body: JSON.stringify({}),
      });
      await loadArticles();
    } catch (err) {
      alert(`ブックマーク切替に失敗: ${err.message}`);
    } finally {
      target.disabled = false;
    }
  });
}

function setupArticlesButtons() {
  const fetchBtn = $("#fetch-articles-button");
  const refreshBtn = $("#refresh-articles-button");
  const limitInput = $("#fetch-limit");
  const summary = $("#articles-fetch-summary");
  if (!fetchBtn || !refreshBtn || !limitInput || !summary) return;

  fetchBtn.addEventListener("click", async () => {
    fetchBtn.disabled = true;
    summary.innerHTML = `<div class="muted">収集中…</div>`;

    const limit = Math.max(1, Math.min(50, parseInt(limitInput.value || "5", 10) || 5));

    try {
      const res = await api("/api/fetch", {
        method: "POST",
        body: JSON.stringify({ limit }),
      });

      const totalInserted = res.total_inserted ?? 0;
      const results = Array.isArray(res.results) ? res.results : [];

      const breakdownHtml =
        results.length > 0
          ? `
        <div style="margin-top:6px;">
          <strong>ソース別</strong>
          <div style="display:flex; flex-direction:column; gap:4px; margin-top:6px;">
            ${results
              .map((r) => {
                const sid = escapeHtml(r.source_id || "");
                const inserted = r.inserted ?? 0;
                const skipped = r.skipped_existing ?? 0;
                const ok = r.ok ? "OK" : "NG";
                const err = r.error ? ` (${escapeHtml(r.error)})` : "";
                return `<div class="muted">${sid}: ${ok} / +${inserted}（既存スキップ:${skipped}）${err}</div>`;
              })
              .join("")}
          </div>
        </div>
      `
          : "";

      summary.innerHTML = `
        <div><strong>新規件数:</strong> ${totalInserted}</div>
        ${breakdownHtml}
      `;

      await loadArticles();
    } catch (e) {
      summary.innerHTML = `<div class="muted">収集に失敗しました: ${escapeHtml(
        e.message || String(e)
      )}</div>`;
    } finally {
      fetchBtn.disabled = false;
    }
  });

  refreshBtn.addEventListener("click", async () => {
    await loadArticles();
  });
}

function setupButtons() {
  $("#discover-button").addEventListener("click", (e) => {
    e.preventDefault();
    discoverRss();
  });
  $("#discover-url").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      discoverRss();
    }
  });
  $("#check-all-button").addEventListener("click", async () => {
    try {
      await api("/api/sources/check-all", { method: "POST" });
      loadSources();
    } catch (e) {
      alert(`生存確認に失敗しました: ${e.message}`);
    }
  });

  $("#import-sources-button").addEventListener("click", async () => {
    const replace = window.confirm(
      "data/sources.json からソースを読み込みます。\n\n" +
      "OK: 足りない分だけ追加（既存はそのまま）\n" +
      "キャンセル: 強制上書き（DBを空にして全件取り込み）"
    );
    try {
      const res = await api(
        `/api/sources/import?replace=${replace ? "0" : "1"}`,
        { method: "POST" }
      );
      await loadSources();
      const msg = replace
        ? `${res.added}件追加`
        : `全件再読み込み完了（${res.total || res.added || "?"}件）`;
      alert(`読み込み完了: ${msg}`);
    } catch (e) {
      alert(`読み込みに失敗しました: ${e.message}`);
    }
  });

  $("#export-sources-button").addEventListener("click", async () => {
    if (!window.confirm("DBの内容を data/sources.json に書き戻します。よろしいですか？（バックアップ作成あり）")) {
      return;
    }
    try {
      const res = await api("/api/sources/export", { method: "POST" });
      alert(`書き戻し完了: ${res.count}件\n${res.path}`);
    } catch (e) {
      alert(`書き戻しに失敗しました: ${e.message}`);
    }
  });

  $("#push-github-button").addEventListener("click", async () => {
    if (!window.confirm("sources.json を書き戻して GitHub にプッシュします。よろしいですか？")) return;
    try {
      const res = await api("/api/git/push", { method: "POST" });
      alert(res.message || "プッシュ完了");
    } catch (e) {
      let msg = e.message || String(e);
      try {
        const err = JSON.parse(msg);
        if (err.error) msg = err.error;
      } catch (_) {
        if (msg.includes("<!") || msg.length > 150) {
          msg = "サーバーエラーです。RSS Manager を再起動してからもう一度お試しください。";
        }
      }
      alert(`プッシュに失敗しました: ${msg}`);
    }
  });
}

window.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupButtons();
  setupTableActions();
  setupArticlesActions();
  setupArticlesButtons();
  loadSources();
  loadArticles();
});
```

### rss_manager_ui/style.css
```css
:root {
  color-scheme: dark;
  --bg: #020617;
  --bg-card: #0b1120;
  --bg-card-hover: #0f1a30;
  --border: #1e293b;
  --border-bright: #2d4165;
  --accent: #38bdf8;
  --accent-glow: rgba(56, 189, 248, 0.15);
  --accent-soft: #0f172a;
  --text: #e2e8f0;
  --text-muted: #64748b;
  --text-dim: #334155;
  --danger: #f87171;
  --danger-soft: rgba(248, 113, 113, 0.12);
  --green: #4ade80;
  --green-soft: rgba(74, 222, 128, 0.12);
  --yellow: #fbbf24;
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  min-height: 100vh;
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #020617;
  background-image:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(56, 189, 248, 0.05), transparent),
    radial-gradient(ellipse 60% 40% at 80% 80%, rgba(99, 102, 241, 0.04), transparent);
  color: var(--text);
  font-size: 14px;
}

/* ─── Header ─── */
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(16px) saturate(1.5);
  -webkit-backdrop-filter: blur(16px) saturate(1.5);
  background: rgba(2, 6, 23, 0.88);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px 0;
}

.title-block {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  font-size: 28px;
  line-height: 1;
  filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.5));
}

h1 {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.3px;
  background: linear-gradient(135deg, #e2e8f0, #94a3b8);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  margin-top: 2px;
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0.2px;
}

/* ─── Tabs ─── */
.tabs {
  display: flex;
  gap: 4px;
  margin-top: 12px;
}

.tab {
  border: 0;
  border-radius: 8px 8px 0 0;
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  color: var(--text-muted);
  transition: all 0.15s;
  border-bottom: 2px solid transparent;
}

.tab:hover:not(.disabled) {
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
}

.tab.active {
  background: rgba(56, 189, 248, 0.08);
  color: var(--accent);
  border-bottom: 2px solid var(--accent);
  font-weight: 600;
}

.tab.disabled {
  opacity: 0.35;
  cursor: default;
}

/* ─── Main layout ─── */
.app-main {
  max-width: 1300px;
  margin: 0 auto;
  padding: 20px 24px 80px;
}

/* ─── Cards ─── */
.card {
  background: var(--bg-card);
  border-radius: 14px;
  padding: 18px 20px;
  border: 1px solid var(--border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
  margin-bottom: 16px;
}

.import-banner {
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(56, 189, 248, 0.05));
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 20px;
  text-align: center;
}
.import-banner p {
  margin: 0 0 14px;
  font-size: 15px;
  color: var(--text);
}
.import-banner .primary {
  font-size: 16px;
  padding: 12px 24px;
  font-weight: 600;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.card h2 {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.2px;
}

/* ─── Form ─── */
.form-row {
  display: flex;
  gap: 8px;
  margin-top: 0;
}

input[type="url"] {
  flex: 1;
  padding: 9px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.8);
  color: var(--text);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

input[type="url"]:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

input[type="url"]::placeholder {
  color: var(--text-muted);
}

/* ─── Buttons ─── */
button {
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 7px 14px;
  font-size: 12px;
  font-weight: 500;
  background: var(--accent);
  color: #020617;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  line-height: 1.2;
}

button:hover {
  filter: brightness(1.1);
}

button.secondary {
  background: rgba(148, 163, 184, 0.08);
  color: var(--text-muted);
  border-color: var(--border);
}

button.secondary:hover {
  background: rgba(148, 163, 184, 0.14);
  color: var(--text);
  border-color: var(--border-bright);
}

button.danger {
  background: var(--danger-soft);
  color: var(--danger);
  border-color: rgba(248, 113, 113, 0.2);
}

button.danger:hover {
  background: rgba(248, 113, 113, 0.2);
  border-color: var(--danger);
}

button:disabled {
  opacity: 0.4;
  cursor: default;
  filter: none;
}

/* ─── Result box ─── */
.result-box {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid var(--border);
  min-height: 38px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-box:empty {
  display: none;
}

.result-box strong {
  color: var(--text);
}

/* ─── Sources Table ─── */
.table-wrap {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.sources-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  min-width: 900px;
}

.sources-table thead {
  background: rgba(15, 23, 42, 0.6);
}

.sources-table th {
  padding: 10px 12px;
  text-align: left;
  color: var(--text-muted);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

/* 列幅の固定 */
.sources-table th:nth-child(1),
.sources-table td:nth-child(1) {
  width: 130px;
  min-width: 100px;
}

.sources-table th:nth-child(2),
.sources-table td:nth-child(2) {
  width: 140px;
  min-width: 110px;
}

.sources-table th:nth-child(3),
.sources-table td:nth-child(3) {
  width: 220px;
}

.sources-table th:nth-child(4),
.sources-table td:nth-child(4) {
  width: 220px;
}

.sources-table th:nth-child(5),
.sources-table td:nth-child(5) {
  width: 130px;
}

.sources-table th:nth-child(6),
.sources-table td:nth-child(6) {
  width: 70px;
  text-align: center;
}

.sources-table th:nth-child(7),
.sources-table td:nth-child(7) {
  width: 140px;
  min-width: 130px;
  white-space: nowrap;
}

.sources-table td {
  padding: 9px 12px;
  border-bottom: 1px solid rgba(30, 41, 59, 0.6);
  color: var(--text);
  vertical-align: middle;
}

.sources-table td:nth-child(3),
.sources-table td:nth-child(4) {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sources-table tbody tr {
  transition: background 0.1s;
}

.sources-table tbody tr:hover {
  background: var(--bg-card-hover);
}

.sources-table tbody tr:last-child td {
  border-bottom: none;
}

.sources-table a {
  color: var(--accent);
  text-decoration: none;
  font-size: 11.5px;
}

.sources-table a:hover {
  text-decoration: underline;
}

/* 操作列のボタンを横並びに */
.btn-group {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: nowrap;
}

/* カテゴリセルのpillを横並びsに */
.sources-table td:nth-child(5) {
  padding-top: 8px;
  padding-bottom: 8px;
}

.cats-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  align-items: center;
}

/* ─── Pills ─── */
.pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 10.5px;
  font-weight: 500;
  border: 1px solid rgba(56, 189, 248, 0.2);
  margin: 1px 2px 1px 0;
}

/* ─── Status ─── */
.status-alive {
  color: var(--green);
  font-weight: 600;
  font-size: 11px;
  text-align: center;
}

.status-alive::before {
  content: "✓ ";
}

.status-dead,
.status-disabled {
  color: var(--danger);
  font-weight: 600;
  font-size: 11px;
  text-align: center;
}

.status-dead::before {
  content: "✗ ";
}

.status-disabled::before {
  content: "— ";
}

/* ─── Misc ─── */
.muted {
  color: var(--text-muted);
  font-size: 12px;
}

.tab-panel {
  display: none;
}

.tab-panel.active {
  display: block;
}

/* ─── Articles (Phase B2) ─── */
.articles-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 10px;
}

.article-item {
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(30, 41, 59, 0.75);
  border-radius: 14px;
  padding: 14px 14px;
}

.article-item.bookmarked {
  border-color: rgba(250, 204, 21, 0.4);
}

.article-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.article-ogp {
  width: 72px;
  height: 50px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
}

.article-body {
  flex: 1;
  min-width: 0;
}

.article-link {
  color: var(--text);
  text-decoration: none;
  font-weight: 650;
  font-size: 12.5px;
  line-height: 1.35;
}

.article-link:hover {
  text-decoration: underline;
}

.article-excerpt {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-meta {
  margin-top: 4px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-bookmark {
  font-size: 14px;
  padding: 6px 10px;
  min-width: 46px;
  line-height: 1;
}

/* ─── Footer ─── */
.app-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 6px 24px;
  font-size: 11px;
  color: var(--text-dim);
  background: linear-gradient(to top, rgba(2, 6, 23, 0.98) 60%, transparent);
  pointer-events: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ─── Responsive ─── */
@media (max-width: 720px) {
  .app-header {
    padding: 10px 16px 0;
  }

  .app-main {
    padding: 16px 12px 80px;
  }

  .form-row {
    flex-direction: column;
  }

  .card {
    padding: 14px 14px;
    border-radius: 10px;
  }

  h1 {
    font-size: 13px;
  }
}
```

### rss_manager_ui/manifest.json
```json
{
  "name": "Japan OTAKU Insider — RSS Manager V2",
  "short_name": "RSS Manager",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#020617",
  "theme_color": "#020617",
  "icons": []
}
```

### rss_manager_ui/sw.js
```javascript
const CACHE_NAME = "rss-manager-v5-b2";
const ASSETS = ["./", "./index.html", "./style.css", "./app.js", "./manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    }),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        }),
      ),
    ),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  if (request.url.includes("/api/")) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request);
    }),
  );
});
```

## 4. 設定・起動

### rss_manager.py
```python
#!/usr/bin/env python3
import argparse
import webbrowser
import threading
import time
from rss_manager import server

def main():
    parser = argparse.ArgumentParser(description="Japan OTAKU Insider - RSS Manager")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_all() if hasattr(parser, "parse_all") else parser.parse_args()

    url = f"http://{args.host}:{args.port}/"

    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)
            print(f"\n[*] Opening browser: {url}")
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"[*] RSS Manager V2 starting at {url}")
    print("[*] Press Ctrl+C to stop.\n")

    try:
        server.run_server(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n[*] Stopping RSS Manager...")

if __name__ == "__main__":
  main()
```

### start_rss_manager.sh
```bash
#!/bin/bash
# RSS Manager 起動スクリプト

cd "$(dirname "$0")"

# 仮想環境があれば有効化（任意）
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 rss_manager.py
```

### requirements-rss-manager.txt
```text
feedparser
requests
beautifulsoup4
lxml
html2text
```

### README_rss_manager.md
```markdown
# Japan OTAKU Insider — RSS Manager V2 (Phase A)

RSSソースを収集・管理し、Japan OTAKU Insiderのコンテンツ生成を補助するためのローカルツールです。

## 概要

このツールは、以下の機能をローカル環境で提供します。

- **RSSソース管理**: サイトURLからRSSフィードを自動検出し、カテゴリを付けて保存。
- **生存確認**: 登録済みソースが現在も有効か（404等になっていないか）を一括チェック。
- **データ同期**: ローカルDBの内容を `data/sources.json` に書き出し、GitHubへプッシュして Daily Update ワークフローに反映。
- **記事収集**: 登録したRSSから最新記事をDBに溜め込み、簡易的なプレビューが可能。

## セットアップと起動

1. **依存パッケージのインストール**
   ```bash
   pip install -r requirements-rss-manager.txt
   ```

2. **起動**
   ```bash
   ./start_rss_manager.sh
   # または
   python3 rss_manager.py
   ```
   起動後、ブラウザで `http://127.0.0.1:8000/` が開きます。

## データ管理について

- **データベース**: `rss_manager_data/manager.db` (SQLite) に保存されます。
- **外部連携**: ツール上の「GitHubにプッシュ」ボタンを押すと、以下の処理が行われます。
  1. DBのソース一覧を `data/sources.json` に書き出し。
  2. `git add data/sources.json` -> `git commit` -> `git push` を実行。
  これにより、GitHub Actions 上の自動更新プロセスが新しいソースを認識できるようになります。

## 注意事項

- **ローカル専用**: このツールは認証機能を備えておらず、ローカル（127.0.0.1）での使用のみを想定しています。外部公開はしないでください。
- **Git管理**: `rss_manager_data/` フォルダは `.gitignore` によりGit管理から除外されています。
```

## 5. DB構造

### sources テーブル
RSSフィードの供給元情報を管理します。

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `id` | TEXT | プライマリキー（スラグ形式のID） |
| `name` | TEXT | サイト名/表示名 |
| `url` | TEXT | サイトのトップURL |
| `rss_url` | TEXT | RSSフィードのURL |
| `type` | TEXT | ソースの種類（現在は 'rss' 固定） |
| `categories` | TEXT | カテゴリの配列（JSON文字列） |
| `language` | TEXT | 言語（デフォルト 'ja'） |
| `status` | TEXT | 生存状態（'alive', 'dead' など） |
| `last_fetched_at` | DATETIME | 最後に記事を取得した日時 |
| `last_checked_at` | DATETIME | 最後に生存確認を行った日時 |
| `fetch_interval_minutes`| INTEGER | 取得間隔（分） |
| `error_count` | INTEGER | 連続失敗回数 |
| `disabled` | INTEGER | 無効化フラグ（1で無効） |
| `created_at` | DATETIME | 作成日時 |
| `updated_at` | DATETIME | 更新日時 |

### articles テーブル
収集された記事データを管理します。

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `id` | INTEGER | プライマリキー（自動インクリメント） |
| `source_id` | TEXT | 外部キー（sources.id） |
| `title` | TEXT | 記事タイトル |
| `url` | TEXT | 記事URL（UNIQUE） |
| `full_text` | TEXT | 本文（現在は未使用） |
| `excerpt` | TEXT | 記事の抜粋/サマリー |
| `ogp_image` | TEXT | OGP画像URL |
| `published_at`| DATETIME | 記事の公開日時 |
| `fetched_at` | DATETIME | 記事を収集した日時 |
| `is_bookmarked`| BOOLEAN | ブックマークフラグ |
| `is_exported` | BOOLEAN | エクスポート済みフラグ |
| `exported_at` | DATETIME | エクスポート日時 |

## 6. APIリスト

| メソッド | エンドポイント | 説明 |
| :--- | :--- | :--- |
| **GET** | `/api/sources` | 登録済みソース一覧を取得 |
| **GET** | `/api/sources/{id}/check` | 指定ソースの生存確認を実行 |
| **GET** | `/api/articles` | 収集済み記事一覧を取得（`limit`引数可） |
| **POST** | `/api/sources/search` | URLからRSSフィードを探索 |
| **POST** | `/api/sources/add` | 新しいソースを追加 |
| **POST** | `/api/sources/check-all` | 全全ソースの生存確認を一括実行 |
| **POST** | `/api/sources/export` | DBの内容を `data/sources.json` に書き出し |
| **POST** | `/api/git/push` | `sources.json` を更新して GitHub へプッシュ |
| **POST** | `/api/sources/import` | `sources.json` からデータをインポート |
| **POST** | `/api/fetch` | 全ソースから最新記事を収集 |
| **DELETE** | `/api/sources/{id}` | ソースを削除 |
| **PUT** | `/api/sources/{id}/category` | ソースのカテゴリを更新 |
| **PUT** | `/api/articles/{id}/bookmark` | 記事のブックマーク状態を反転 |
