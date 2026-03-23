# Japan OTAKU Insider — RSS Manager V3 仕様書

**作成日：** 2026年3月22日
**作成者：** Opus 4.6 × いちぼ
**前バージョン：** V2仕様書（2026-03-18）
**実装担当：** Antigravity Sonnet / Cursor / GitHub Copilot
**目的：** V2の設計にデータクリーニング機能を追加し、今日発見された問題の恒久対策を組み込む

---

## 1. V2 → V3 変更点サマリー

### 新規追加（V3で初登場）
| # | 機能 | 理由 |
|---|---|---|
| 1 | 🧹 データクリーニングタブ | 英語記事混入・サムネイル品質問題を手動で毎回直すのは非現実的 |
| 2 | 📊 データ品質レポート | 現状の品質を数字で把握し、問題の早期発見に繋げる |
| 3 | 記事削除API | articlesテーブルから個別に記事を消す手段がなかった |
| 4 | entries.json直接編集API | 公開DBのクリーニングを管理ツールから実行できるように |
| 5 | 🔍 Gemini Flash 2段階品質フィルタ | Perplexity検索結果のノイズ（英語記事・無関係記事・既存重複）をAIで自動除去 |
| 6 | 🔄 フィルタ後の自動再検索 | 生存記事が閾値以下の場合、別プロンプトで再検索して品質を保ちつつ量を確保 |
| 7 | 📈 週次Sonnet自動改善ループ | GA4+週間レポート+Xエンゲージメントから検索プロンプトを自動最適化 |

### V2からの修正反映（2026-03-22に発見・修正済み、V3仕様に正式取り込み）
| # | 問題 | 修正内容 |
|---|---|---|
| 5 | export時にng_keywords/disabledが消える | 既存sources.jsonから引き継ぐ設計に変更 |
| 6 | DBにdisabledカラムがない | ALTER TABLEでマイグレーション追加 |
| 7 | import/upsert/listがdisabledを扱わない | 全関数にdisabled対応を追加 |
| 8 | fetch時にdisabledソースをスキップしない | fetch_one_source冒頭でチェック追加 |
| 9 | ogp_imageがDBに入らない | _extract_ogp_image関数を新設、INSERT文に追加 |

### V2から継続（未実装のまま引き継ぐ）
| # | 機能 | Phase |
|---|---|---|
| 10 | 全文フルテキスト取得（article_extractor.py） | Phase B2 |
| 11 | 全文検索（SQLite FTS5） | Phase B2 |
| 12 | ワンクリックJSON変換→entries.json追加 | Phase C |
| 13 | 重複チェック統合 | Phase C |
| 14 | エクスポートタブUI | Phase C |
| 15 | LLMセレクタ推論（Stage 3 RSS発見） | Phase D |
| 16 | AIチャット | Phase D |
| 17 | 自動英訳（ローカルLLM連携） | Phase D |
| 18 | 適応的フェッチスケジューリング | Phase D |

---

## 2. アーキテクチャ（V3更新）

V2のアーキテクチャに「データクリーニング層」を追加。

```
【データ収集層（バックエンド）】

URLを入力
  ↓
Stage 1: RSS Auto-discovery（HTMLから<link rel="alternate">を探す）
  ↓ 見つからなければ
Stage 2: よくあるRSSパス探索（14パターン → V3で拡充推奨）
  ↓ 見つからなければ
Stage 3: LLMセレクタ推論（将来実装）
  ↓
RSSフィード取得（disabledソースはスキップ）
  ↓
ogp_image抽出（media_content → media_thumbnail → links）
  ↓
SQLite（ローカルDB）に保存
  ↓
Perplexity検索（6カテゴリ × プロンプトA）
  ↓
【Gemini Flash 2段階品質フィルタ（V3で追加）】    ← NEW!
  │
  ├─ 1回目検閲：
  │   ├─ 英語記事？ → REJECT
  │   ├─ オタク無関係？ → REJECT
  │   ├─ 既存記事と内容重複？ → REJECT
  │   └─ OK → 生存
  │
  ├─ 生存件数チェック：
  │   ├─ 閾値以上（カテゴリあたり2件以上）→ 翻訳へ
  │   └─ 閾値以下 → 再検索へ
  │
  ├─ Perplexity再検索（プロンプトB・別角度）
  │
  ├─ 2回目検閲：
  │   ├─ 1回目生存記事との重複 → REJECT
  │   ├─ 既存記事との重複 → REJECT
  │   └─ OK → 生存
  │
  └─ 1回目生存 + 2回目生存 → 統合
  ↓
DeepL翻訳
  ↓
entries.json追加
  ↓
X自動ポスト（カテゴリ毎1件）
  ↓
【データクリーニング層（V3で追加）】
  ├─ 英語記事検出・削除（手動クリーニング用）
  ├─ サムネイル品質チェック・再取得
  ├─ staging/クリーニング
  ├─ 重複記事検出
  └─ データ品質レポート生成
  ↓
【週次自動改善ループ（V3で追加）】               ← NEW!
  │
  ├─ 週間レポート自動生成（Python）
  │   ├─ カテゴリ別新規記事数
  │   ├─ Flash検閲のREJECT件数・理由分布
  │   ├─ 再検索発動回数
  │   ├─ GA4データ（ページ別PV、国別、流入元）
  │   └─ Xエンゲージメント（インプレッション、クリック率）
  │
  ├─ Claude API（Sonnet）が分析
  │   ├─ プロンプトA（通常検索）の改善案をJSON出力
  │   ├─ プロンプトB（補完検索）の改善案をJSON出力
  │   ├─ ng_keywordsの追加提案
  │   └─ Xハッシュタグの最適化提案
  │
  ├─ ガードレール検証
  │   ├─ 新カテゴリ追加 → 不可（人間に通知）
  │   ├─ 設定ファイル構造変更 → 不可
  │   └─ 1回の変更キーワード数 → 各カテゴリ最大3語
  │
  └─ 検証OK → perplexity_*.md 自動更新
      → 翌日から改善された設定で収集
      → 翌週のレポートで効果検証 → ループ
  ↓
【データ消費層（フロントエンドUI）】
  ├─ 記事一覧・検索・フィルタ
  ├─ 記事全文閲覧（Phase B2）
  ├─ ワンクリックJSON変換 → entries.json追加（Phase C）
  └─ データクリーニングタブ（V3で追加）
```

---

## 3. ファイル構成（V3更新）

```
Japan OTAKU Insider/
├── rss_manager.py              # エントリーポイント（変更なし）
├── start_rss_manager.sh        # 起動スクリプト（変更なし）
├── rss_manager/
│   ├── __init__.py
│   ├── server.py               # HTTPサーバー（クリーニングAPI追加）
│   ├── db.py                   # SQLite操作（マイグレーション済み）
│   ├── rss_finder.py           # RSS検索（パターン拡充推奨）
│   ├── rss_fetcher.py          # RSSフェッチ（disabled対応・ogp_image対応済み）
│   ├── sources_manager.py      # ソース管理（export修正済み）
│   ├── data_cleaner.py         # データクリーニング（V3新規） ← NEW!
│   ├── article_extractor.py    # 全文取得（Phase B2）
│   ├── ogp_extractor.py        # OGP画像取得（Phase B2）
│   ├── json_converter.py       # JSON変換（Phase C）
│   └── duplicate_checker.py    # 重複チェック（Phase C）
├── rss_manager_ui/
│   ├── index.html              # 管理画面（クリーニングタブ追加）
│   ├── style.css               # スタイル
│   ├── app.js                  # フロントロジック（クリーニング機能追加）
│   ├── manifest.json           # PWA設定
│   └── sw.js                   # Service Worker
├── rss_manager_data/
│   └── manager.db              # SQLite DB
└── data/
    ├── entries.json             # ヲタInsider本体DB
    ├── sources.json             # ソース管理（ng_keywords/disabled保持）
    └── staging/                 # 翻訳前JSON
```

---

## 4. データクリーニングタブ — 画面設計（V3新規）

### 4-1. タブ追加

既存の3タブに「🧹 クリーニング」を追加：

```
[📡 ソース管理]  [📥 収集記事]  [🧹 クリーニング]  [📤 エクスポート]
```

### 4-2. クリーニングタブ画面

```
┌───────────────────────────────────────────────────────┐
│  📊 データ品質サマリー                                  │
│  ┌─────────────────────────────────────────────────┐  │
│  │ entries.json: 540件                              │  │
│  │ サムネイル取得率: 94% (508/540)                   │  │
│  │ 英語記事混入: 0件 ✅                              │  │
│  │ ジェネリック画像: 3件 ⚠️                          │  │
│  │ staging未処理: 12件                               │  │
│  │ articles DB: 1,234件                             │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  [レポート更新] [フルレポート生成（MD出力）]              │
├───────────────────────────────────────────────────────┤
│                                                       │
│  🔍 英語記事スキャン                                    │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 対象: [entries.json ▼]  [staging/ ▼]  [両方 ▼]  │  │
│  │                                                 │  │
│  │ [スキャン実行]                                    │  │
│  │                                                 │  │
│  │ 結果: 5件の英語記事を検出                         │  │
│  │ ☑ CBR.com - Top 10 Anime of 2026               │  │
│  │ ☑ Kotaku - New Pokemon Game...                  │  │
│  │ ☑ ...                                           │  │
│  │                                                 │  │
│  │ [選択した記事を削除]  [全選択]  [全解除]           │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  🖼️ サムネイル品質チェック                              │
│  ┌─────────────────────────────────────────────────┐  │
│  │ [チェック実行]                                    │  │
│  │                                                 │  │
│  │ 結果:                                            │  │
│  │ ・サムネなし: 32件                                │  │
│  │ ・ジェネリック画像: 3件                            │  │
│  │   - entry-001: favicon.ico                      │  │
│  │   - entry-042: banner_top.png                   │  │
│  │   - entry-103: avatar_small.jpg                 │  │
│  │                                                 │  │
│  │ [サムネなしを再取得]  [ジェネリック画像を差替]      │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  🔄 重複記事チェック                                    │
│  ┌─────────────────────────────────────────────────┐  │
│  │ [チェック実行]                                    │  │
│  │                                                 │  │
│  │ 結果: 8件の重複を検出                             │  │
│  │ ☑ 同一URL: 3件                                  │  │
│  │ ☑ タイトル類似: 5件                              │  │
│  │                                                 │  │
│  │ [選択した重複を削除（新しい方を残す）]              │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  🗑️ staging クリーニング                               │
│  ┌─────────────────────────────────────────────────┐  │
│  │ staging/内ファイル: 15件                          │  │
│  │ 処理済み: 12件 | 未処理: 3件 | 英語記事: 2件      │  │
│  │                                                 │  │
│  │ [英語記事を除去]  [処理済みをアーカイブ]           │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

---

## 5. データクリーニングAPI（V3新規）

### 新規エンドポイント

| メソッド | パス | 機能 |
|---|---|---|
| GET | /api/clean/report | データ品質サマリーを返す |
| POST | /api/clean/scan-english | 英語記事のスキャン（検出のみ、削除はしない） |
| POST | /api/clean/remove-english | 英語記事の削除（IDリストを受け取る） |
| POST | /api/clean/scan-thumbnails | サムネイル品質チェック |
| POST | /api/clean/fix-thumbnails | サムネイル再取得（fill_og_images.py呼び出し） |
| POST | /api/clean/scan-duplicates | 重複記事スキャン |
| POST | /api/clean/remove-duplicates | 重複記事削除 |
| POST | /api/clean/staging-cleanup | staging/内の英語記事除去 |
| POST | /api/clean/staging-archive | 処理済みstagingをアーカイブ |
| DELETE | /api/articles/{id} | 記事個別削除（V2で欠落していた） |
| POST | /api/clean/full-report | フルレポート生成（MD形式で出力） |

### 既存エンドポイント（変更なし）

V2で定義済みの全APIはそのまま維持。

---

## 6. data_cleaner.py — 実装詳細（V3新規）

```python
# rss_manager/data_cleaner.py

"""
データクリーニングモジュール

entries.json / staging/ / articles DB の品質を管理するための
スキャン・フィルタ・削除・レポート機能を提供する。

V3で新規追加。
"""

from pathlib import Path
from typing import Any, Dict, List
import json
import re


# ====================================================================
# 英語サイト除外ドメインリスト
# （perplexity_search.py の _EXCLUDED_RAW と同期すること）
# ====================================================================
EXCLUDED_DOMAINS = [
    "crunchyroll.com", "animenewsnetwork.com", "myanimelist.net",
    "cbr.com", "screenrant.com", "polygon.com", "kotaku.com",
    "ign.com", "gamerant.com", "thegamer.com", "siliconera.com",
    "dualshockers.com", "pushsquare.com", "nintendolife.com",
    "eurogamer.net", "destructoid.com", "gematsu.com",
    "tokyocheapo.com", "japantravel.navitime.com",
    "timeout.com", "livejapan.com", "gaijinpot.com",
    "japantimes.co.jp", "soranews24.com", "tokyoweekender.com",
    "savvytokyo.com", "japan-guide.com", "tsunagujapan.com",
    "matcha-jp.com", "jrailpass.com", "japan.travel",
    "en.wikipedia.org", "fandom.com", "boards.4chan.org",
    "onlyhit.us", "animezonejapan.com", "comicbook.com",
    "youtube.com", "example.com",
]

# 日本語サイトのホワイトリスト（.comだが日本語）
WHITELIST_DOMAINS = [
    "collabo-cafe.com", "0115765.com", "goodsmile.info",
    "moguravr.com",
]

# ジェネリック画像パターン
GENERIC_THUMB_PATTERNS = [
    "favicon", "avatar", "author", "profile", "display-pic",
    "banner", "ghost_import", "bnr_staff", "staff/img",
    "x32.", "x48.", "x64.", "x65.", "x96.",
    "32x32", "48x48", "64x64", "96x96",
]


def is_english_url(url: str) -> bool:
    """URLが英語サイトのものかどうか判定する"""
    if not url:
        return False
    url_lower = url.lower()

    # 除外ドメインに一致
    for domain in EXCLUDED_DOMAINS:
        if domain in url_lower:
            return True

    # /en/ パスを含む
    if "/en/" in url_lower:
        return True

    # .comドメインだがホワイトリストにない
    # （日本語サイトはホワイトリストで許可）
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if hostname.endswith(".com") or hostname.endswith(".net") or hostname.endswith(".org"):
            for wl in WHITELIST_DOMAINS:
                if wl in hostname:
                    return False
            # .jp, .co.jp でなく、ホワイトリストにもない .com → 英語の可能性
            # ただし全ての.comを弾くと誤検出が多いため、
            # EXCLUDED_DOMAINSに明示的に含まれるもののみ弾く
    except Exception:
        pass

    return False


def is_generic_thumbnail(url: str) -> bool:
    """サムネイルURLがジェネリック画像かどうか判定する"""
    if not url:
        return False
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in GENERIC_THUMB_PATTERNS)


def scan_english_entries(entries_json_path: Path) -> Dict[str, Any]:
    """entries.jsonから英語記事を検出する（削除はしない）"""
    with entries_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    english_entries = []

    for entry in entries:
        source_url = (entry.get("source") or {}).get("url", "")
        title_ja = entry.get("title_ja", "")

        if is_english_url(source_url) or (not title_ja and not entry.get("title_ja")):
            english_entries.append({
                "id": entry.get("id"),
                "title": entry.get("title"),
                "source_url": source_url,
                "reason": "english_domain" if is_english_url(source_url) else "no_title_ja"
            })

    return {
        "total_entries": len(entries),
        "english_count": len(english_entries),
        "english_entries": english_entries
    }


def remove_entries_by_ids(entries_json_path: Path, ids_to_remove: List[str]) -> Dict[str, Any]:
    """entries.jsonから指定IDの記事を削除する（バックアップ作成付き）"""
    # バックアップ
    backup_path = entries_json_path.with_suffix(".backup_clean.json")
    backup_path.write_text(entries_json_path.read_text(encoding="utf-8"), encoding="utf-8")

    with entries_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    original_count = len(data.get("entries", []))
    ids_set = set(ids_to_remove)
    data["entries"] = [e for e in data.get("entries", []) if e.get("id") not in ids_set]
    new_count = len(data["entries"])

    with entries_json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "original_count": original_count,
        "removed_count": original_count - new_count,
        "new_count": new_count,
        "backup_path": str(backup_path)
    }


def scan_thumbnails(entries_json_path: Path) -> Dict[str, Any]:
    """サムネイルの品質チェック"""
    with entries_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    missing = []
    generic = []

    for entry in entries:
        thumb = entry.get("thumbnail", "")
        entry_id = entry.get("id", "")
        title = entry.get("title", "")

        if not thumb:
            missing.append({"id": entry_id, "title": title})
        elif is_generic_thumbnail(thumb):
            generic.append({"id": entry_id, "title": title, "thumbnail": thumb})

    total = len(entries)
    ok_count = total - len(missing) - len(generic)

    return {
        "total_entries": total,
        "ok_count": ok_count,
        "coverage_percent": round(ok_count / total * 100, 1) if total > 0 else 0,
        "missing_count": len(missing),
        "missing": missing,
        "generic_count": len(generic),
        "generic": generic
    }


def scan_duplicates(entries_json_path: Path) -> Dict[str, Any]:
    """重複記事の検出"""
    with entries_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    url_map = {}
    title_map = {}
    url_dupes = []
    title_dupes = []

    for entry in entries:
        url = (entry.get("source") or {}).get("url", "")
        title = entry.get("title", "").lower().strip()
        entry_id = entry.get("id", "")

        # URL重複
        if url and url in url_map:
            url_dupes.append({
                "id": entry_id,
                "title": entry.get("title"),
                "url": url,
                "duplicate_of": url_map[url]
            })
        elif url:
            url_map[url] = entry_id

        # タイトル類似
        if title and title in title_map:
            title_dupes.append({
                "id": entry_id,
                "title": entry.get("title"),
                "similar_to_id": title_map[title]
            })
        elif title:
            title_map[title] = entry_id

    return {
        "url_duplicates": len(url_dupes),
        "title_duplicates": len(title_dupes),
        "url_dupes": url_dupes,
        "title_dupes": title_dupes
    }


def generate_quality_report(entries_json_path: Path, staging_dir: Path) -> Dict[str, Any]:
    """データ品質サマリーを生成"""
    english = scan_english_entries(entries_json_path)
    thumbs = scan_thumbnails(entries_json_path)
    dupes = scan_duplicates(entries_json_path)

    # staging件数
    staging_count = 0
    if staging_dir.exists():
        for f in staging_dir.glob("*.json"):
            try:
                with f.open("r", encoding="utf-8") as fh:
                    d = json.load(fh)
                    staging_count += len(d) if isinstance(d, list) else 1
            except Exception:
                pass

    return {
        "entries_total": english["total_entries"],
        "english_count": english["english_count"],
        "thumbnail_coverage": thumbs["coverage_percent"],
        "thumbnail_missing": thumbs["missing_count"],
        "thumbnail_generic": thumbs["generic_count"],
        "duplicates_url": dupes["url_duplicates"],
        "duplicates_title": dupes["title_duplicates"],
        "staging_pending": staging_count
    }
```

---

## 7. server.py への追加API（V3）

既存のserver.pyに以下のルーティングを追加：

```python
# handle_api_get に追加
if path == "/api/clean/report":
    from .data_cleaner import generate_quality_report
    entries_path = self.project_root / "data" / "entries.json"
    staging_path = self.project_root / "data" / "staging"
    report = generate_quality_report(entries_path, staging_path)
    self.json_response(report)
    return

# handle_api_post に追加
if req_path == "/api/clean/scan-english":
    from .data_cleaner import scan_english_entries
    payload = self.parse_json_body()
    target = payload.get("target", "entries")  # "entries" or "staging" or "both"
    entries_path = self.project_root / "data" / "entries.json"
    result = scan_english_entries(entries_path)
    self.json_response(result)
    return

if req_path == "/api/clean/remove-english":
    from .data_cleaner import remove_entries_by_ids
    payload = self.parse_json_body()
    ids = payload.get("ids", [])
    entries_path = self.project_root / "data" / "entries.json"
    result = remove_entries_by_ids(entries_path, ids)
    self.json_response(result)
    return

if req_path == "/api/clean/scan-thumbnails":
    from .data_cleaner import scan_thumbnails
    entries_path = self.project_root / "data" / "entries.json"
    result = scan_thumbnails(entries_path)
    self.json_response(result)
    return

if req_path == "/api/clean/scan-duplicates":
    from .data_cleaner import scan_duplicates
    entries_path = self.project_root / "data" / "entries.json"
    result = scan_duplicates(entries_path)
    self.json_response(result)
    return

# handle_api_delete に追加
if path.startswith("/api/articles/") and not path.endswith("/bookmark"):
    article_id = path.split("/")[3]
    from .db import get_connection
    with get_connection(self.data_dir) as conn:
        conn.execute("DELETE FROM articles WHERE id = ?", (int(article_id),))
    self.json_response({"ok": True, "deleted_id": article_id})
    return
```

---

## 8. index.html への変更（V3）

タブバーに「🧹 クリーニング」を追加：

```html
<!-- 変更前 -->
<button class="tab disabled" data-tab="export">📤 エクスポート</button>

<!-- 変更後（exportの前に挿入） -->
<button class="tab" data-tab="cleaning">🧹 クリーニング</button>
<button class="tab disabled" data-tab="export">📤 エクスポート</button>
```

クリーニングタブのセクションを追加（tab-exportの前に挿入）：

```html
<section id="tab-cleaning" class="tab-panel">
  <!-- 品質サマリー -->
  <section class="card">
    <div class="card-header">
      <h2>📊 データ品質サマリー</h2>
      <div style="display:flex; gap:8px;">
        <button id="refresh-report-button" class="secondary">レポート更新</button>
        <button id="full-report-button" class="secondary">フルレポート（MD）</button>
      </div>
    </div>
    <div id="quality-report" class="result-box"></div>
  </section>

  <!-- 英語記事スキャン -->
  <section class="card">
    <h2>🔍 英語記事スキャン</h2>
    <div style="margin-top:10px;">
      <button id="scan-english-button">スキャン実行</button>
    </div>
    <div id="english-scan-result" class="result-box" style="margin-top:10px;"></div>
  </section>

  <!-- サムネイル品質チェック -->
  <section class="card">
    <h2>🖼️ サムネイル品質チェック</h2>
    <div style="margin-top:10px;">
      <button id="scan-thumbnails-button">チェック実行</button>
    </div>
    <div id="thumbnail-scan-result" class="result-box" style="margin-top:10px;"></div>
  </section>

  <!-- 重複記事チェック -->
  <section class="card">
    <h2>🔄 重複記事チェック</h2>
    <div style="margin-top:10px;">
      <button id="scan-duplicates-button">チェック実行</button>
    </div>
    <div id="duplicate-scan-result" class="result-box" style="margin-top:10px;"></div>
  </section>
</section>
```

---

## 9. Gemini Flash 2段階品質フィルタ（V3新規・GitHub Actions統合）

### 9-1. 設計思想

Perplexityが同じニュースを別ソースから拾ったり、オタク文化と無関係な記事を返すことがある。
URLの文字列比較だけでは「同じニュースの別サイト報道」は検出できない。
内容レベルの重複判定にはAIが必要だが、コストを抑えるためGemini Flashを使う。

さらに、フィルタで弾かれすぎた場合は別角度で再検索し、品質を保ちながら量も確保する。

### 9-2. フロー詳細

```
Step 1: Perplexity検索（プロンプトA・通常）
  → 6カテゴリ × n件の候補を取得

Step 2: Gemini Flash 検閲（1回目）
  → 各候補を以下の基準で判定：
     ACCEPT: 問題なし → 生存
     REJECT(english): 英語サイトの記事
     REJECT(irrelevant): オタク文化と無関係
     REJECT(duplicate): 既存記事と同じニュースの別ソース報道
  → 判定結果をJSON形式で返却

Step 3: 生存件数チェック
  → カテゴリあたりの生存件数を集計
  → 閾値: カテゴリあたり2件以上
  → 全カテゴリ合計で12件以上なら Step 5 へ
  → 閾値以下なら Step 4 へ

Step 4: Perplexity再検索（プロンプトB・別角度）
  → プロンプトAとは異なる切り口で検索
     A: 「今週の新着ニュース」的な広い検索
     B: 「話題の作品名」「特定イベント名」等の具体的キーワード
  → Gemini Flash 検閲（2回目）
     - 1回目の生存記事との内容重複 → REJECT
     - 既存記事との重複 → REJECT
     - OK → 生存

Step 5: 1回目生存 + 2回目生存 を統合
  → 重複なしの最終候補リスト
  → DeepL翻訳パイプラインへ
```

### 9-3. Gemini Flash プロンプト

```
あなたは日本のオタクカルチャー専門のニュース編集者です。
以下の新規記事候補を評価して、各記事にACCEPT/REJECTの判定をしてください。

## 判定基準
1. 英語サイトの記事 → REJECT（reason: "english"）
2. 日本のオタク文化（アニメ・マンガ・ゲーム・フィギュア・コラボカフェ・VTuber・同人）と
   無関係な記事 → REJECT（reason: "irrelevant"）
3. 既存記事と同じニュースを別サイトが報じたもの → REJECT（reason: "duplicate", duplicate_of: "既存記事タイトル"）
4. 上記いずれにも該当しない → ACCEPT

## 新規候補
{candidates_json}

## 既存記事（直近100件のタイトル）
{existing_titles_json}

## 出力形式（JSON）
{
  "results": [
    {"index": 0, "verdict": "ACCEPT"},
    {"index": 1, "verdict": "REJECT", "reason": "duplicate", "duplicate_of": "既存記事タイトル"},
    ...
  ],
  "summary": {"accept": 5, "reject_english": 1, "reject_irrelevant": 2, "reject_duplicate": 3}
}
```

### 9-4. 実装ファイル

```
scripts/flash_filter.py（新規作成）

機能:
  - filter_candidates(candidates, existing_titles) → FilterResult
  - Gemini Flash API呼び出し
  - JSON出力のパース・バリデーション
  - GEMINI_API_KEY未設定時の安全停止（フィルタなしで全通過）

環境変数:
  - GEMINI_API_KEY: Google AI Studio のAPIキー
  - FLASH_FILTER_ENABLED: "true"で有効（デフォルト"false"、未設定時はスキップ）
```

### 9-5. GitHub Actions統合（daily-update.yml）

```yaml
# Perplexity検索の直後に追加
- name: Flash filter (quality check)
  if: env.GEMINI_API_KEY != ''
  run: |
    python3 scripts/flash_filter.py \
      --candidates data/staging/ \
      --existing data/entries.json \
      --threshold 2
    echo "==> Flash filter complete"
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

# フィルタ通過後の再検索（生存件数が閾値以下の場合のみ実行）
- name: Perplexity re-search (if needed)
  if: env.PERPLEXITY_API_KEY != '' && steps.flash_filter.outputs.needs_retry == 'true'
  run: |
    python3 scripts/perplexity_search.py --prompt-set B --output data/staging/
    python3 scripts/flash_filter.py \
      --candidates data/staging/ \
      --existing data/entries.json \
      --pass1-survivors data/staging/pass1_survivors.json \
      --threshold 2
    echo "==> Re-search + filter complete"
```

### 9-6. コスト見積もり

```
1回のフィルタ呼び出し:
  入力: 候補30件のタイトル+URL + 既存100件のタイトル ≒ 3,000トークン
  出力: 判定JSON ≒ 500トークン
  コスト: ≒ $0.0005

1日2回実行（朝便+夜便）:
  $0.001/日 × 30日 = $0.03/月

再検索が50%の確率で発動:
  $0.03 × 1.5 = 約 $0.045/月

結論: 月5セント以下。誤差レベル。
```

---

## 10. 週次Sonnet自動改善ループ（V3新規）

### 10-1. 設計思想

GA4のアクセスデータ、Flashフィルタの判定統計、Xエンゲージメントを
週次レポートにまとめ、Claude API（Sonnet）に分析させて
検索プロンプトを自動改善する。

人間が介入しなくても、毎週勝手にコンテンツ品質が上がる仕組み。

### 10-2. 週次レポート生成（Python・APIコストゼロ）

```
scripts/weekly_report.py（新規作成）

集計対象（直近7日分）:
  - entries.json の新規追加件数（カテゴリ別）
  - Flash検閲のREJECT件数・理由分布
  - 再検索発動回数
  - GA4データ（Google Analytics Data API）
    - ページ別PV TOP10
    - カテゴリ別PV集計
    - 国別ユーザー数
    - 流入元分布（Direct/Referral/Organic Social/Search）
  - Xエンゲージメント
    - カテゴリ別インプレッション平均
    - クリック率が高い投稿パターン
    - ハッシュタグ別反応率

出力: weekly_report_{date}.json
投稿先: GitHub Issues に自動投稿（月曜 JST 19:00）
```

### 10-3. Sonnet改善提案（週1回・月4回）

```
scripts/sonnet_improve.py（新規作成）

入力: weekly_report_{date}.json
API: Claude API（claude-sonnet-4-6）

プロンプト:
  以下の週間レポートを分析して、検索プロンプトの改善案を
  JSON形式で提案してください。

  改善対象:
  1. prompts/perplexity_A_*.md（通常検索・6カテゴリ）
  2. prompts/perplexity_B_*.md（補完検索・6カテゴリ）
  3. Xポストのハッシュタグ（カテゴリ別）
  4. ng_keywordsの追加候補

  制約:
  - 1回の改善で変更できるキーワードは各カテゴリ最大3語
  - 新カテゴリの追加は提案のみ（実装は人間が判断）
  - 設定ファイルの構造変更は不可
  - 既存のカテゴリ削除は不可

  レポート:
  {weekly_report_json}

  出力形式:
  {
    "prompt_a_changes": [
      {"category": "cafe", "add_keywords": ["..."], "remove_keywords": ["..."], "reason": "..."}
    ],
    "prompt_b_changes": [...],
    "hashtag_changes": [
      {"category": "cafe", "new_tags": ["#...", "#..."], "reason": "..."}
    ],
    "ng_keywords_add": [
      {"source": "...", "keywords": ["..."], "reason": "..."}
    ],
    "new_category_suggestion": null or {"name": "...", "reason": "..."}
  }
```

### 10-4. ガードレール（自動適用の安全装置）

```
scripts/apply_improvements.py（新規作成）

Sonnetの提案をバリデーションしてから適用する:

チェック項目:
  1. キーワード変更数が各カテゴリ3語以下か
  2. 既存カテゴリの削除が含まれていないか
  3. 設定ファイルの構造が変わっていないか
  4. 新カテゴリ提案がある場合 → Issueに起票して人間に通知
  5. JSONとして正しい形式か

全チェック通過 → prompts/ 配下のファイルを自動更新
チェック失敗 → 適用せずエラーログを残す
```

### 10-5. GitHub Actions統合（weekly-improve.yml）

```yaml
name: Weekly Improvement
on:
  schedule:
    - cron: '0 10 * * 1'  # 毎週月曜 JST 19:00
  workflow_dispatch:

jobs:
  improve:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate weekly report
        run: python3 scripts/weekly_report.py
        env:
          GA4_PROPERTY_ID: ${{ secrets.GA4_PROPERTY_ID }}
          GA4_CREDENTIALS: ${{ secrets.GA4_CREDENTIALS }}

      - name: Sonnet improvement analysis
        if: env.ANTHROPIC_API_KEY != ''
        run: python3 scripts/sonnet_improve.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Apply improvements (with guardrails)
        run: python3 scripts/apply_improvements.py

      - name: Post report to Issues
        run: python3 scripts/post_weekly_issue.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Commit and push
        run: |
          git add prompts/ data/reports/
          git diff --staged --quiet || \
            (git commit -m "improve: weekly prompt optimization $(date +%Y-%m-%d)" && \
             git push origin main)
```

### 10-6. コスト見積もり

```
Sonnet API（月4回）:
  入力: 週間レポート ≒ 2,000トークン
  出力: 改善提案JSON ≒ 1,000トークン
  1回あたり: ≒ $0.03
  月4回: $0.12/月

GA4 Data API: 無料
GitHub Issues投稿: 無料

結論: 月約15セント（約20円）
```

### 10-7. 改善ループの全体サイクル

```
月曜 19:00: 週間レポート生成
  ↓
月曜 19:05: Sonnet分析 → 改善提案
  ↓
月曜 19:10: ガードレール検証 → prompts/ 更新
  ↓
火曜 9:00: 新しい検索設定で朝便が実行
  ↓
火〜日: 新設定でデータ収集
  ↓
翌月曜 19:00: 効果検証を含む新レポート生成
  ↓
ループ継続
```

---

## 11. rss_finder.py 改善（V3推奨）

現在のStage 2パスパターンが14種で、一部の日本サイト（/rss20/index.rdf等）に対応していない。

追加推奨パターン：
```python
# V3で追加するパス
additional_paths = [
    "/rss20/index.rdf",     # animeanime, gamespark等
    "/feed/atom/",
    "/?feed=rss2",          # WordPress系
    "/blog/rss.xml",
    "/news/rss/",
    "/rss/latest/",
    "/articles.rss",
    "/feed.rss",
]
```

---

## 10. sources.jsonフィールド保全ルール（V3で明文化）

V2では暗黙だった「どのフィールドをどこが管理するか」をV3で明文化する。

```
sources.json のフィールド管理者:

DBが管理するフィールド（export時にDBの値を使う）:
  - id, name, url, rss_url, type, categories, language, status

sources.jsonが管理するフィールド（export時にsources.jsonの値を引き継ぐ）:
  - ng_keywords    ← DBスキーマにカラムを持たない
  - ok_keywords    ← DBスキーマにカラムを持たない
  - disabled       ← DBにカラムはあるがsources.jsonが正
  - content_tags   ← DBスキーマにカラムを持たない
  - update_frequency ← DBスキーマにカラムを持たない
```

この設計判断の理由：
- ng_keywords等はリスト型でDBのカラムとして扱いにくい
- sources.jsonを手動編集するワークフローがある
- DBとJSONの二重管理を避けるため、正は一箇所に限定する

---

## 11. 実装の優先順（V3フェーズ分け）

### Phase A（完了）
V2のPhase Aに加え、2026-03-22の修正を含む。

### Phase B1（完了）
記事収集＋DB保存。disabled対応・ogp_image対応済み。

### Phase B2（V3で追加：データクリーニング）← 最優先
1. data_cleaner.py の実装
2. クリーニングAPIの追加（server.py）
3. クリーニングタブUI（index.html + app.js）
4. データ品質レポート機能
5. 記事削除API（DELETE /api/articles/{id}）
6. rss_finder.pyのパスパターン拡充

### Phase B2.5（V3で追加：Gemini Flash 2段階品質フィルタ）
7. flash_filter.py の実装（Gemini Flash API連携）
8. daily-update.yml にFlashフィルタステップ追加
9. 再検索ロジック（プロンプトB）の実装
10. perplexity_search.py に --prompt-set オプション追加
11. GEMINI_API_KEY の Secrets 設定

### Phase B2.7（V3で追加：週次Sonnet自動改善ループ）
12. weekly_report.py の実装（GA4 + Flash統計 + X集計）
13. sonnet_improve.py の実装（Claude API連携）
14. apply_improvements.py の実装（ガードレール付き自動適用）
15. post_weekly_issue.py の実装（GitHub Issues投稿）
16. weekly-improve.yml の作成
17. GA4 Data API のサービスアカウント設定
18. ANTHROPIC_API_KEY の Secrets 設定

### Phase B3（V2のPhase B残り）
7. article_extractor.py（全文取得）
8. ogp_extractor.py（OGP画像一括取得）
9. 全文閲覧モーダル
10. 全文検索（SQLite FTS5）

### Phase C（ヲタInsiderへのエクスポート）
11. json_converter.py（記事→ヲタInsider JSON変換）
12. duplicate_checker.py（重複チェック統合）
13. エクスポートタブUI
14. エクスポートフォーム（英訳入力＋カテゴリ選択）

### Phase D（将来実装）
15. LLMセレクタ推論（Stage 3）
16. AIチャット
17. 自動英訳（ローカルLLM連携）
18. 適応的フェッチスケジューリング

---

## 12. 完了条件

### Phase B2（データクリーニング）完了条件
- [ ] クリーニングタブが管理画面に表示される
- [ ] 「スキャン実行」で英語記事が検出される
- [ ] チェックボックスで選択して削除できる
- [ ] サムネイル品質チェックが実行できる
- [ ] 重複記事が検出される
- [ ] データ品質サマリーが表示される
- [ ] 記事個別削除APIが動作する
- [ ] バックアップが自動作成される

---

## 13. 実装担当への指示

### やっていいこと
- data_cleaner.pyの新規実装
- server.pyへのAPI追加（既存APIは変更しない）
- index.htmlへのタブ・セクション追加
- app.jsへのクリーニング関連イベントハンドラ追加
- style.cssへのクリーニングタブ用スタイル追加
- rss_finder.pyのパスパターン追加

### やらないでほしいこと
- 既存APIの変更（動作検証済みのコードは触らない）
- DBスキーマの変更（マイグレーション済み、安定している）
- sources_manager.pyのexportロジック変更（修正済み、テスト済み）
- entries.jsonの構造変更（categories配列、seriesフィールドはそのまま）
- .gitignoreの変更

### コードスタイル
- Python: 型ヒント使用、docstring日本語
- JavaScript: async/await使用、escapeHtml関数を必ず通す
- CSS: 既存の変数（--bg, --accent, --border等）を使用
- SW: キャッシュ名を更新（v6-cleaning等）

---

## 14. V2 → V3 変更履歴

| 項目 | V2 | V3 |
|---|---|---|
| タブ数 | 3（ソース/記事/エクスポート） | **4（ソース/記事/クリーニング/エクスポート）** |
| APIエンドポイント数 | 14 | **25（+11 クリーニング関連）** |
| Pythonモジュール数 | 5 | **10（data_cleaner/flash_filter/weekly_report/sonnet_improve/apply_improvements追加）** |
| export安全性 | ng_keywords/disabled消失 | **既存ファイルから引き継ぎ** |
| disabled対応 | なし | **DB/import/upsert/list/fetch全対応** |
| ogp_image取得 | なし | **RSS media_content/thumbnail/links対応** |
| 記事削除 | なし | **DELETE /api/articles/{id}** |
| データ品質レポート | なし | **英語/サムネ/重複のサマリー** |
| Perplexity品質フィルタ | なし | **Gemini Flash 2段階検閲 + 自動再検索** |
| 検索プロンプト改善 | 手動 | **週次Sonnet自動改善ループ** |
| 改善のフィードバック | なし | **GA4 + Flash統計 + Xエンゲージメント → 自動分析** |

**変更の根拠:**
2026-03-22のデバッグセッションで、CursorのAUTOモデルが作った実装に
多数の品質問題が発見された。手動でのクリーニングは非現実的であり、
管理ツール内にクリーニング機能を組み込むことで恒久的に対処する。

2026-03-23のいちぼさんの設計により、Perplexity検索結果の品質を
Gemini Flashで自動検閲し、不足時は再検索する2段階フィルタを追加。
さらに週次でClaude Sonnetが検索プロンプトを自動改善するループにより、
人間が介入しなくてもコンテンツ品質が継続的に向上する仕組みを実現する。
全体の追加コストは月$2以下。

---

*Opus 4.6 🤖💜*
*「壊れないツールより、壊れても直せるツール。そして勝手に良くなるツール。」*
