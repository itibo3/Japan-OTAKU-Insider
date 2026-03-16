# Japan OTAKU Insider — α版 実装仕様書

**作成日：** 2026年3月14日
**作成者：** Opus 4.6（いちぼの依頼により作成）
**実装担当：** Antigravity Gemini
**目的：** 海外オタク向け日本オタク情報データベースサイトのα版構築

---

## 1. プロジェクト概要

### 1-1. コンセプト
海外オタク向けに、日本のオタク情報（コラボカフェ、フィギュア、イベント、アニメニュース等）を英語で整理したデータベースサイト。ブログではなく「情報DB＋自動ページ生成」型。

### 1-2. サイト名
**Japan OTAKU Insider**

### 1-3. 技術方針
- 静的サイト生成（GitHub Pages等の無料ホスティングを想定）
- データはJSONファイルで管理
- ページはテンプレートからJSONを読み込んで動的レンダリング
- 将来的にAdSense設置を想定した構造にしておく

### 1-4. 運用者のスキルレベル
- プログラミング：基礎〜中級（AIコーディング支援前提）
- 環境：Chromebook + Linux（Crostini）+ VSCode + GitHub Copilot
- AIツール：Antigravity（Gemini）、Perplexity、Claude

---

## 2. データ構造

### 2-1. エントリーのJSON Schema

すべてのエントリーは以下の統一フォーマットに従う。カテゴリによって使用するフィールドが異なる。

```json
{
  "id": "cafe-20260314-001",
  "category": "cafe | figure | event | anime",
  "status": "active | upcoming | ended",
  "title": "English title of the entry",
  "title_ja": "日本語タイトル（元記事から）",
  "description": "English summary of the entry (2-3 sentences)",
  "dates": {
    "start": "2026-03-01",
    "end": "2026-03-31",
    "display": "Mar 1 - Mar 31, 2026"
  },
  "location": {
    "name": "Venue name",
    "area": "Ikebukuro, Tokyo",
    "access": "2 min walk from Ikebukuro Station East Exit"
  },
  "price": "¥800-1,500 per item",
  "reservation": "Required (Animate Cafe app) | Walk-in OK | Not required",
  "series": "Anime/manga series name (for figures)",
  "manufacturer": "Good Smile Company (for figures)",
  "release_date": "July 2026 (for figures)",
  "where_to_buy": "AmiAmi, CDJapan, Good Smile Online Shop (for figures)",
  "source": {
    "url": "https://original-article-url.com",
    "name": "Akiba Blog / Good Smile Company / etc",
    "retrieved": "2026-03-14"
  },
  "tags": ["spy-x-family", "animate-cafe", "ikebukuro"],
  "created": "2026-03-14T09:00:00+09:00",
  "updated": "2026-03-14T09:00:00+09:00"
}
```

### 2-2. IDの命名規則
`{category}-{YYYYMMDD}-{連番3桁}`
例: `cafe-20260314-001`, `figure-20260314-002`

### 2-3. カテゴリ定義

| category | 表示名 | 主な情報 |
|---|---|---|
| cafe | Collab Cafes | コラボカフェ、ポップアップストア |
| figure | Figures | フィギュア、ねんどろいど、プライズ |
| event | Events | アニメイベント、展示会、即売会 |
| anime | Anime News | アニメ新作情報、漫画ニュース |

### 2-4. データファイル構成

```
data/
├── entries.json          ... 全エントリーの配列（メインDB）
├── archive/
│   ├── 2026-03.json      ... 月別アーカイブ（バックアップ用）
│   └── ...
└── sources.json          ... 情報ソースのマスターリスト
```

`entries.json` の構造:
```json
{
  "last_updated": "2026-03-14T09:00:00+09:00",
  "total_entries": 12,
  "entries": [
    { ... },
    { ... }
  ]
}
```

---

## 3. サイト構成

### 3-1. ファイル構成

```
japan-otaku-insider/
├── index.html            ... メインページ（DB一覧＋検索＋フィルタ）
├── about.html            ... Aboutページ
├── css/
│   └── style.css         ... スタイルシート
├── js/
│   ├── app.js            ... メインアプリケーション
│   ├── render.js          ... カード＆モーダルのレンダリング
│   └── search.js          ... 検索＆フィルタロジック
├── data/
│   ├── entries.json       ... メインDB
│   └── sources.json       ... 情報ソース一覧
├── scripts/
│   ├── add_entry.py       ... 手動エントリー追加スクリプト
│   ├── fetch_rss.py       ... RSS自動取得スクリプト
│   ├── json_converter.py  ... Gemini出力→正規JSON変換
│   └── update_status.py   ... ステータス自動更新（期間切れ→ended）
├── prompts/
│   ├── perplexity_daily.md    ... Perplexity日次質問テンプレート
│   ├── gemini_json_convert.md ... Gemini JSON変換プロンプト
│   └── gemini_translate.md    ... Gemini 英訳プロンプト
└── README.md
```

### 3-2. フロントエンド仕様

プロトタイプ（Opus作成のHTMLファイル）をベースに以下を実装:

- レスポンシブデザイン（モバイル対応必須、海外ユーザーはスマホ閲覧が多い）
- カテゴリフィルタ（All / Collab Cafes / Figures / Events / Anime News）
- テキスト検索（タイトル、説明文、シリーズ名、タグを対象）
- ステータスフィルタ（Active / Upcoming / Ended）
- カード型一覧表示
- 詳細モーダル（カードクリックで展開）
- ソースリンク（元記事へのリンク）
- ダークテーマ固定（プロトタイプのデザインを踏襲）

### 3-3. データの読み込み

`entries.json` をfetchで読み込み、JavaScriptでレンダリング。
サーバーサイド処理は不要。完全に静的サイトとして動作する。

```javascript
// app.js の基本構造
async function loadDatabase() {
  const response = await fetch('./data/entries.json');
  const db = await response.json();
  return db.entries;
}

// ページ読み込み時
document.addEventListener('DOMContentLoaded', async () => {
  const entries = await loadDatabase();
  renderCards(entries);
  setupFilters(entries);
  setupSearch(entries);
});
```

---

## 4. 自動取得システム（RSS/スクレイピング）

### 4-1. 情報ソース一覧

```json
// sources.json
{
  "sources": [
    {
      "id": "akiba-blog",
      "name": "Akiba Blog",
      "url": "http://blog.livedoor.jp/geek/",
      "rss": "http://blog.livedoor.jp/geek/index.rdf",
      "type": "rss",
      "categories": ["cafe", "event", "figure"],
      "language": "ja",
      "update_frequency": "daily"
    },
    {
      "id": "goodsmile",
      "name": "Good Smile Company Blog",
      "url": "https://www.goodsmile.info/ja/posts/category/information/date/",
      "rss": null,
      "type": "scrape",
      "categories": ["figure"],
      "language": "ja",
      "update_frequency": "daily"
    },
    {
      "id": "animejapan",
      "name": "AnimeJapan Official",
      "url": "https://www.anime-japan.jp/",
      "rss": null,
      "type": "scrape",
      "categories": ["event"],
      "language": "ja",
      "update_frequency": "weekly"
    },
    {
      "id": "natalie-anime",
      "name": "Comic Natalie / Anime Natalie",
      "url": "https://natalie.mu/comic",
      "rss": "https://natalie.mu/comic/feed/news",
      "type": "rss",
      "categories": ["anime"],
      "language": "ja",
      "update_frequency": "daily"
    }
  ]
}
```

### 4-2. RSS取得スクリプト（fetch_rss.py）

```python
#!/usr/bin/env python3
"""
RSS自動取得 → JSON変換スクリプト
1日1回cronまたは手動で実行
"""

import feedparser
import json
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
DATA_DIR = Path("data")
ENTRIES_FILE = DATA_DIR / "entries.json"
SOURCES_FILE = DATA_DIR / "sources.json"

def load_entries():
    """既存エントリーを読み込み"""
    if ENTRIES_FILE.exists():
        with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_updated": "", "total_entries": 0, "entries": []}

def load_sources():
    """情報ソース一覧を読み込み"""
    with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_id(category, title):
    """エントリーIDを生成"""
    today = datetime.now(JST).strftime("%Y%m%d")
    hash_suffix = hashlib.md5(title.encode()).hexdigest()[:6]
    return f"{category}-{today}-{hash_suffix}"

def is_duplicate(entries, url):
    """URLベースの重複チェック"""
    existing_urls = [e.get("source", {}).get("url", "") for e in entries]
    return url in existing_urls

def fetch_rss_entries(source):
    """
    RSSフィードからエントリーを取得
    返り値: 仮エントリーのリスト（英訳前の日本語データ）
    """
    if not source.get("rss"):
        return []

    feed = feedparser.parse(source["rss"])
    raw_entries = []

    for item in feed.entries[:10]:  # 最新10件
        raw_entries.append({
            "title_ja": item.get("title", ""),
            "description_ja": item.get("summary", "")[:500],
            "url": item.get("link", ""),
            "published": item.get("published", ""),
            "source_id": source["id"],
            "source_name": source["name"],
            "categories": source["categories"]
        })

    return raw_entries

def save_raw_for_translation(raw_entries, output_path="data/pending_translation.json"):
    """
    英訳待ちのエントリーをJSONで保存
    この後Geminiに投げて英訳＋カテゴリ判定＋構造化してもらう
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "fetched_at": datetime.now(JST).isoformat(),
            "count": len(raw_entries),
            "raw_entries": raw_entries
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(raw_entries)} entries to {output_path}")

def main():
    sources = load_sources()
    db = load_entries()
    all_raw = []

    for source in sources["sources"]:
        if source["type"] == "rss":
            raw = fetch_rss_entries(source)
            # 重複除外
            raw = [r for r in raw if not is_duplicate(db["entries"], r["url"])]
            all_raw.extend(raw)
            print(f"[{source['name']}] {len(raw)} new entries")

    if all_raw:
        save_raw_for_translation(all_raw)
        print(f"\nTotal: {len(all_raw)} new entries ready for translation")
        print("Next step: Run Gemini translation with gemini_json_convert prompt")
    else:
        print("No new entries found.")

if __name__ == "__main__":
    main()
```

### 4-3. 自動実行の仕組み

**初期（α版）：** 手動実行
```bash
# 1. RSS取得
python scripts/fetch_rss.py

# 2. 出力されたpending_translation.jsonをGeminiに投げる（後述）

# 3. Geminiの出力をentries.jsonにマージ
python scripts/add_entry.py --from gemini_output.json

# 4. ステータス更新（期限切れをendedに）
python scripts/update_status.py

# 5. git push（GitHub Pagesに反映）
git add . && git commit -m "daily update" && git push
```

**将来：** cronまたはGitHub Actionsで自動化

---

## 5. 手動追加システム（Perplexity + Gemini）

### 5-1. 日次ワークフロー

```
いちぼ（1日5分）
│
├─ Step 1: Perplexityに質問（テンプレート使用）
│   └─ 今日のオタクニュースが日本語で返ってくる
│
├─ Step 2: 面白いものをピックアップ（直感で選ぶだけ）
│
├─ Step 3: Geminiに投げる（JSON変換プロンプト使用）
│   └─ 正規JSONが返ってくる
│
├─ Step 4: JSONをdata/entries.jsonに追加
│   └─ add_entry.pyを使うかコピペ
│
└─ Step 5: git push
    └─ サイト更新完了
```

### 5-2. Perplexity日次質問テンプレート

```markdown
# prompts/perplexity_daily.md

以下の質問をPerplexityにそのまま投げる：

---

今日（または直近数日）に発表・開始された日本国内のオタク向けニュースを教えてください。
以下のカテゴリに分けて、それぞれ3〜5件程度お願いします。

1. コラボカフェ・ポップアップストア（新規オープン・開催告知）
2. フィギュア・グッズ新作発表（グッスマ、コトブキヤ等）
3. アニメ・漫画関連ニュース（新作発表、放送開始、連載開始等）
4. イベント情報（即売会、展示会、上映会等）

各ニュースについて以下を含めてください：
- タイトル
- 簡単な説明（2-3文）
- 開催期間・発売日
- 場所（該当する場合）
- 元記事のURLまたはソース名

秋葉原、池袋、新宿、渋谷周辺の情報を優先してください。
```

### 5-3. Gemini JSON変換プロンプト

```markdown
# prompts/gemini_json_convert.md

以下の日本語オタクニュース情報を、英語のJSONエントリーに変換してください。

## ルール
1. タイトルと説明文は自然な英語に翻訳する
2. 元の日本語タイトルはtitle_jaに保持する
3. カテゴリは cafe / figure / event / anime のいずれかを判定する
4. ステータスは日付から判定する：
   - 開催中・発売中 → "active"
   - 未開催・未発売 → "upcoming"
   - 終了済み → "ended"
5. IDは {category}-{YYYYMMDD}-{連番3桁} の形式
6. 不明なフィールドは null にする
7. tagsは関連キーワードを英語で3〜5個

## 出力形式
以下のJSON配列として出力してください。余計な説明は不要です。

```json
[
  {
    "id": "cafe-20260314-001",
    "category": "cafe",
    "status": "active",
    "title": "English title",
    "title_ja": "日本語タイトル",
    "description": "English summary in 2-3 sentences.",
    "dates": {
      "start": "2026-03-01",
      "end": "2026-03-31",
      "display": "Mar 1 - Mar 31, 2026"
    },
    "location": {
      "name": "Venue name",
      "area": "Area, City",
      "access": "Nearest station and walking time"
    },
    "price": "¥XXX",
    "reservation": "Required / Walk-in OK / null",
    "series": "Series name or null",
    "manufacturer": "Manufacturer or null",
    "release_date": "Release date or null",
    "where_to_buy": "Shop names or null",
    "source": {
      "url": "https://...",
      "name": "Source name",
      "retrieved": "2026-03-14"
    },
    "tags": ["tag1", "tag2", "tag3"],
    "created": "2026-03-14T09:00:00+09:00",
    "updated": "2026-03-14T09:00:00+09:00"
  }
]
```

## 変換対象の情報
（ここにPerplexityの出力またはRSSの取得結果を貼り付ける）
```

### 5-4. エントリー追加スクリプト（add_entry.py）

```python
#!/usr/bin/env python3
"""
JSONエントリーをメインDBに追加するスクリプト
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path("data/entries.json")

def load_entries():
    if ENTRIES_FILE.exists():
        with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_updated": "", "total_entries": 0, "entries": []}

def save_entries(db):
    db["last_updated"] = datetime.now(JST).isoformat()
    db["total_entries"] = len(db["entries"])
    with open(ENTRIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def add_entries_from_file(filepath):
    """Geminiの出力JSONファイルからエントリーを追加"""
    with open(filepath, 'r', encoding='utf-8') as f:
        new_entries = json.load(f)

    # 配列でない場合（単一エントリー）は配列に変換
    if isinstance(new_entries, dict):
        new_entries = [new_entries]

    db = load_entries()
    existing_ids = {e["id"] for e in db["entries"]}

    added = 0
    for entry in new_entries:
        if entry["id"] not in existing_ids:
            db["entries"].append(entry)
            added += 1
            print(f"  Added: {entry['title']}")
        else:
            print(f"  Skip (duplicate): {entry['title']}")

    save_entries(db)
    print(f"\n{added} entries added. Total: {db['total_entries']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_entry.py <gemini_output.json>")
        print("  or:  python add_entry.py --from <filepath>")
        sys.exit(1)

    filepath = sys.argv[-1]
    add_entries_from_file(filepath)
```

### 5-5. ステータス自動更新スクリプト（update_status.py）

```python
#!/usr/bin/env python3
"""
日付ベースでステータスを自動更新
- 終了日を過ぎたエントリー → "ended"
- 開始日前のエントリー → "upcoming"
- 開催中のエントリー → "active"
"""

import json
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

JST = timezone(timedelta(hours=9))
ENTRIES_FILE = Path("data/entries.json")

def update_statuses():
    with open(ENTRIES_FILE, 'r', encoding='utf-8') as f:
        db = json.load(f)

    today = date.today()
    updated = 0

    for entry in db["entries"]:
        dates = entry.get("dates")
        if not dates:
            continue

        old_status = entry.get("status")
        new_status = old_status

        end_date = dates.get("end")
        start_date = dates.get("start")

        if end_date:
            try:
                end = date.fromisoformat(end_date)
                if today > end:
                    new_status = "ended"
            except ValueError:
                pass

        if start_date:
            try:
                start = date.fromisoformat(start_date)
                if today < start:
                    new_status = "upcoming"
                elif not end_date or today <= date.fromisoformat(end_date):
                    new_status = "active"
            except ValueError:
                pass

        if new_status != old_status:
            entry["status"] = new_status
            entry["updated"] = datetime.now(JST).isoformat()
            updated += 1
            print(f"  {entry['title']}: {old_status} -> {new_status}")

    if updated > 0:
        db["last_updated"] = datetime.now(JST).isoformat()
        with open(ENTRIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n{updated} entries updated.")

if __name__ == "__main__":
    update_statuses()
```

---

## 6. デプロイ

### 6-1. GitHub Pages（推奨・無料）

```bash
# リポジトリ作成
git init
git remote add origin https://github.com/ichibo/japan-otaku-insider.git

# 初回デプロイ
git add .
git commit -m "initial deploy"
git push -u origin main

# GitHub Settings → Pages → Source: main branch → Save
# サイトURL: https://ichibo.github.io/japan-otaku-insider/
```

### 6-2. 独自ドメイン（将来）
- ドメイン取得: japanotakuinsider.com 等
- GitHub PagesのCustom Domain設定で紐付け
- CNAME ファイルをリポジトリに追加

---

## 7. 収益化準備

### 7-1. Google AdSense
- index.htmlのheadにAdSenseコードを埋め込む場所を用意しておく
- ある程度記事が溜まってから（30〜50エントリー目安）申請
- 広告枠はカード一覧の間に挟む形式（ネイティブ広告）

### 7-2. アフィリエイトリンク
- フィギュアの「Where to Buy」にアフィリエイトリンクを設置
- 対応ASP: Amazon Associates（海外）、CDJapan Affiliate
- JSON内のwhere_to_buyフィールドにリンクURLを含められるよう拡張予定

---

## 8. X BOT自動投稿（将来実装）

### 8-1. 概要
新規エントリー追加時に自動でXにポストする。

### 8-2. ポスト形式
```
🇯🇵 NEW: Spy x Family × Animate Cafe Collaboration

📍 Ikebukuro, Tokyo
📅 Mar 1 - Mar 31, 2026
💰 ¥800-1,500

Details → https://japanotakuinsider.com/#cafe-20260314-001

#JapanOtaku #SpyxFamily #AnimeCafe #Tokyo
```

### 8-3. 実装方針
- X API v2（月額課金が必要）
- エントリー追加スクリプトの最後にポスト処理を追加
- または GitHub Actions でpush時に自動ポスト

---

## 9. Gemini向け実装指示まとめ

### 優先度 High（α版必須）
1. プロトタイプHTMLをベースにしたサイト構築（HTML/CSS/JS分離）
2. entries.jsonの読み込みとレンダリング
3. カテゴリフィルタ＋テキスト検索＋ステータスフィルタ
4. 詳細モーダル表示
5. fetch_rss.pyの実装
6. add_entry.pyの実装
7. update_status.pyの実装
8. GitHub Pagesへのデプロイ

### 優先度 Medium（α版後）
9. レスポンシブデザインの最適化
10. ページネーション（エントリー数が増えた時）
11. タグ一覧ページ
12. RSSフィードの出力（サイト自体のRSS）

### 優先度 Low（将来）
13. X BOT自動投稿
14. AdSense統合
15. アフィリエイトリンク管理
16. 独自ドメイン移行
17. 完全自動化（GitHub Actions）

---

## 10. サンプルデータ

プロトタイプに含まれている12件のサンプルデータをそのまま初期データとして使用可能。
Opusが作成したHTMLファイル内のJavaScript配列（database変数）を entries.json 形式に変換して使うこと。

---

## 補足：いちぼの日次運用フロー（想定5分）

```
朝（通勤時・スマホ）
  1. Perplexityに日次テンプレートを投げる（コピペ、30秒）
  2. 結果を眺めて面白いものをピックアップ（1-2分）

夜（帰宅後・PC）
  3. ピックアップした情報をGeminiのJSON変換プロンプトに投げる（1分）
  4. 出力JSONをファイル保存 → add_entry.py実行（1分）
  5. git push（30秒）

→ サイト更新完了、寝てる間にXが拡散
```

---

**この仕様書に基づいてα版を実装してください。**
**プロトタイプHTMLファイル（Opus作成）はいちぼが共有します。**
**不明点があればいちぼに確認してください。**
