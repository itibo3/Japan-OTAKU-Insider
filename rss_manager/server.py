"""
server.py — RSS Manager のローカル HTTP サーバー

目的: rss_manager_ui/ の静的ファイル配信 + /api/* の REST API 提供
入力: run_server(host, port, project_root) で起動
触っていい所: API ハンドラの追加・修正。do_* のラッパーは触らない方が安全
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone, timedelta
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import urlparse, parse_qs

import requests

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from http_fetch_config import FETCH_USER_AGENT

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

# --- ページメタ取得ユーティリティ（/api/entries/fetch-meta で使用） ---
_META_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JOI-RSSManager/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

def _scrape_page_meta(url: str) -> dict[str, Any]:
    """URL を GET して og:title / og:description / og:image / <title> を返す。"""
    try:
        resp = requests.get(url, headers=_META_HEADERS, timeout=12, allow_redirects=True)
        status = resp.status_code
        html = resp.text if status == 200 else ""
    except Exception as e:
        return {"url_status": None, "error": str(e)}

    def _og(prop: str) -> str:
        m = re.search(
            rf'<meta[^>]+property=[\'"]og:{prop}[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
            html, re.I,
        )
        if m:
            return m.group(1).strip()
        m = re.search(
            rf'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+property=[\'"]og:{prop}[\'"]',
            html, re.I,
        )
        return m.group(1).strip() if m else ""

    def _twitter(name: str) -> str:
        m = re.search(
            rf'<meta[^>]+name=[\'"]twitter:{name}[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
            html, re.I,
        )
        return m.group(1).strip() if m else ""

    def _html_title() -> str:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
        return m.group(1).strip() if m else ""

    def _desc_tag() -> str:
        m = re.search(
            r'<meta[^>]+name=[\'"]description[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
            html, re.I,
        )
        return m.group(1).strip() if m else ""

    title = _og("title") or _twitter("title") or _html_title()
    description = _og("description") or _twitter("description") or _desc_tag()
    og_image = _og("image") or _twitter("image")

    return {
        "url_status": status,
        "title": title,
        "description": description,
        "og_image": og_image,
    }


JST = timezone(timedelta(hours=9))


def _generate_entry_id(category: str) -> str:
    """[category]-[YYYYMMDDHHМM]-manual-[6hex] 形式の ID を生成する。"""
    now = datetime.now(JST)
    stamp = now.strftime("%Y%m%d%H%M")
    digest = hashlib.md5(f"{category}{stamp}{datetime.now().timestamp()}".encode()).hexdigest()[:6]
    return f"{category}-{stamp}-manual-{digest}"


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

        if req_path == "/api/entries/fetch-meta":
            payload = self.parse_json_body()
            url = (payload.get("url") or "").strip()
            if not url:
                self.json_response({"error": "url is required"}, status=400)
                return
            meta = _scrape_page_meta(url)
            self.json_response(meta)
            return

        if req_path == "/api/entries/add":
            payload = self.parse_json_body()
            url = (payload.get("url") or "").strip()
            title = (payload.get("title") or "").strip()
            title_ja = (payload.get("title_ja") or "").strip()
            description = (payload.get("description") or "").strip()
            category = (payload.get("category") or "other").strip()
            display_date = (payload.get("display_date") or datetime.now(JST).strftime("%Y-%m-%d")).strip()
            thumbnail = (payload.get("thumbnail") or "").strip()

            if not url or not title or not description:
                self.json_response({"error": "url, title, description は必須です"}, status=400)
                return

            entry_id = _generate_entry_id(category)
            entry = {
                "id": entry_id,
                "categories": [category],
                "status": "active",
                "title": title,
                "title_ja": title_ja or title,
                "description": description,
                "dates": {"display": display_date},
                "source": {"url": url},
                "tags": [category],
                "_source": "manual",
                "_source_id": "manual",
            }
            if thumbnail:
                entry["thumbnail"] = thumbnail

            # add_single_entry をインポートして呼び出す
            try:
                import importlib.util, sys as _sys
                scripts_dir = self.project_root / "scripts"
                spec = importlib.util.spec_from_file_location(
                    "add_entry_mod", scripts_dir / "add_entry.py"
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                result = mod.add_single_entry(entry)
            except Exception as e:
                self.json_response({"error": f"追加処理でエラー: {e}"}, status=500)
                return

            self.json_response(result)
            return

        if req_path == "/api/entries/push":
            self._handle_entries_push()
            return

        if req_path == "/api/entries/pull":
            self._handle_entries_pull()
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")

    def _handle_entries_pull(self) -> None:
        """origin/main から git pull --rebase して最新データを取得する。"""
        root = self.project_root
        cwd = str(root.resolve())

        def run_git(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
            r = subprocess.run(
                ["git", *args],
                cwd=cwd, capture_output=True, text=True, timeout=timeout,
            )
            print(f"[entries/pull] git {' '.join(args)} -> rc={r.returncode}")
            if r.stderr.strip():
                print(f"  stderr: {r.stderr.strip()[:200]}")
            return r

        r = run_git("pull", "--rebase", "origin", "main", timeout=60)
        if r.returncode != 0:
            self.json_response({"error": f"git pull 失敗: {(r.stderr or r.stdout or '不明').strip()[:300]}"}, status=500)
            return

        out = (r.stdout or "").strip()
        msg = "最新データに更新しました" if "Already up to date" not in out else "すでに最新です"
        self.json_response({"ok": True, "message": msg, "detail": out[:200]})

    def _handle_entries_push(self) -> None:
        """entries.json を git add → commit → push する。"""
        root = self.project_root
        cwd = str(root.resolve())

        def run_git(*args: str, timeout: int = 15) -> subprocess.CompletedProcess:
            r = subprocess.run(
                ["git", *args],
                cwd=cwd, capture_output=True, text=True, timeout=timeout,
            )
            print(f"[entries/push] git {' '.join(args)} -> rc={r.returncode}")
            if r.stdout.strip():
                print(f"  stdout: {r.stdout.strip()[:200]}")
            if r.stderr.strip():
                print(f"  stderr: {r.stderr.strip()[:200]}")
            return r

        r = run_git("add", "data/entries.json", "data/entries_ja.json")
        if r.returncode != 0:
            self.json_response({"error": f"git add 失敗: {(r.stderr or r.stdout or '不明').strip()[:200]}"}, status=500)
            return

        r = run_git("diff", "--staged", "--quiet")
        if r.returncode == 0:
            self.json_response({"ok": True, "message": "変更なし（プッシュ不要）"})
            return

        now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
        r = run_git("commit", "-m", f"feat: 手動追加エントリーを反映 ({now_str})")
        if r.returncode != 0:
            self.json_response({"error": f"git commit 失敗: {(r.stderr or r.stdout or '不明').strip()[:200]}"}, status=500)
            return

        run_git("pull", "--rebase", "origin", "main", timeout=30)

        r = run_git("push", "origin", "HEAD", timeout=90)
        if r.returncode != 0:
            self.json_response({"error": f"git push 失敗: {(r.stderr or r.stdout or '認証エラーやネットワークを確認').strip()[:300]}"}, status=500)
            return

        self.json_response({"ok": True, "message": "entries.json を GitHub に公開しました"})

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
        headers = {"User-Agent": FETCH_USER_AGENT}
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
