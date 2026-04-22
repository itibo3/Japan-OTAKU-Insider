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

