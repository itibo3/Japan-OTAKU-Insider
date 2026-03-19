# Japan OTAKU Insider — 引継書

**作成日:** 2026-03-16 (最終更新: 2026-03-19)  
**ステータス:** β版 (自動RSSフェッチ・ワークフロー確立)  
**開発期間:** 約6時間  
**URL:** https://itibo3.github.io/Japan-OTAKU-Insider/

---

## プロジェクト概要

日本のオタク文化（コラボカフェ・フィギュア・イベント・アニメニュース）を英語圏向けにまとめたデータベースサイト。  
GitHub Pages上で動作する完全静的サイト（維持費ゼロ）。

---

## 技術スタック

| 要素 | 内容 |
|---|---|
| ホスティング | GitHub Pages |
| フロントエンド | HTML / CSS / Vanilla JS |
| データ | `data/entries.json`（JSONファイル） |
| スタイル | カスタムCSS（ダークUI + ネオンアクセント） |
| フォント | Google Fonts: Outfit + Noto Sans JP |
| PWA | `manifest.json` + `sw.js`（Service Worker） |
| SEO | OpenGraph / Twitter Card / sitemap.xml / robots.txt |

---

## ディレクトリ構成

```
Japan OTAKU Insider/
├── index.html          # メインページ（カードDB）
├── about.html          # Aboutページ
├── manifest.json       # PWA設定
├── sw.js               # Service Worker（オフラインキャッシュ）
├── sitemap.xml         # SEO用サイトマップ
├── robots.txt          # クローラー設定
├── css/
│   └── style.css       # 全スタイル（レスポンシブ対応済み）
├── js/
│   ├── app.js          # メインロジック（初期化・カテゴリ切替）
│   ├── render.js       # カードHTML生成・モーダル表示
│   └── search.js       # 検索フィルタリング
├── data/
│   ├── entries.json    # エントリーデータ本体
│   └── sources.json    # 情報源リスト
├── icons/
│   ├── icon-192.png    # PWAアイコン（192px）
│   └── icon-512.png    # PWAアイコン（512px）
├── scripts/
│   ├── add_entry.py    # エントリー追加スクリプト
│   ├── update_status.py # ACTIVE/UPCOMING/ENDED自動更新
│   └── rss_fetch.py    # RSS自動取得・ステージング保存スクリプト
└── prompts/
    ├── perplexity_daily.md   # 手動情報収集プロンプト
    └── update_workflow.md    # サイト更新・自動デプロイ用のワークフロー指示書

---

## 日常運用ワークフロー（2026-03-18 改訂）

現在のサイト更新の基本フローは以下の通りです。詳細は `prompts/update_workflow.md` に記載されています。

```
1. RSS自動取得 (Python)
   └─ python3 scripts/rss_fetch.py --fetch-thumbnails を実行し新着記事を未翻訳で data/staging/ に保存
      （`thumbnail` は news.amiami.jp は og:image 優先。その他は先頭画像優先、取れなければ og:image）

2. 英語化・追加 (AI / Gemini)
   └─ staging のJSONデータをAIに渡し、英語化と data/entries.json への追加を依頼

3. ステータス自動更新 (Python)
   └─ python3 scripts/update_status.py

4. デプロイ (Git)
   └─ git add data/entries.json && git commit -m "feat: xxx" && git push
```

※ 単発の手動追加の場合は `prompts/perplexity_daily.md` 等を利用してAIでJSONを作成し `add_entry.py` を使用します。

### Daily Update ワークフロー失敗時の調査

Actions タブで失敗した Run を開き、どのステップで止まったか確認する。

| 失敗ステップ | 想定原因 | 対応 |
|---|---|---|
| RSS Fetch | ネットワークエラー、sources.json 不正 | ログの ERROR 行を確認。ローカルで `python3 scripts/rss_fetch.py` を実行して再現する |
| Perplexity Search | PERPLEXITY_API_KEY 未設定、API レート制限 | Secrets にキーを設定。未設定時はスキップされるので後続は実行される |
| Translate staging | DEEPL_AUTH_KEY 不正、DeepL API エラー | ログの HTTP ステータス・メッセージを確認。Free 枠は :fx サフィックス |
| Add entries | staging JSON のフォーマット不正 | 該当ファイルを開いて配列構造を確認 |
| Fill missing thumbnails | 外部サイトへの接続失敗、タイムアウト | CI では --limit 10 で制限済み。スキップされるエントリはログに SKIP ERROR |
| Commit and push | 他ブランチとの競合 | ワークフローに `git pull --rebase` を追加済み。再実行を試す |

「Diagnose on failure」ステップが表示される場合は、data/staging の内容と entries.json の先頭を確認できる。


---

## α版で実装済みの機能

### コア機能
- [x] カードグリッド表示（カテゴリ別フィルタ）
- [x] テキスト検索（タイトル・説明文・タグ）
- [x] モーダル詳細表示
- [x] ステータスバッジ（ACTIVE / UPCOMING / ENDED）
- [x] statsバー（件数・カテゴリ数・アクティブ件数・更新日）

### インフラ・SEO・PWA（2026-03-16 追加）
- [x] OpenGraph メタタグ（SNSシェア対応）
- [x] Twitter Card メタタグ
- [x] canonical URL
- [x] `sitemap.xml`
- [x] `robots.txt`
- [x] `manifest.json`（PWA設定）
- [x] Service Worker（オフライン閲覧対応・キャッシュ優先戦略）
- [x] PWAアイコン（192px / 512px）
- [x] スマホレスポンシブ（縦1列）
- [x] タブレットレスポンシブ（2列）
- [x] カテゴリタブの横スクロール対応
- [x] ヘッダーロゴをアイコン画像に変更
- [x] `node_modules/` を `.gitignore` に追加

---

## コミット履歴

| ハッシュ | 内容 |
|---|---|
| `0eeaf4e` | feat: replace logo-icon text with PWA icon image |
| `95ebadf` | feat: add SEO, PWA support, and mobile responsive design |
| `bf8c2a3` | Fix GitHub Pages paths for resources, links, and data fetch |
| `0b2884b` | Update entries: 追加した記事のタイトル等 |
| `5d9e956` | Initial deploy: Japan OTAKU Insider alpha |

---

## ロードマップ

### 🔴 Phase 1 — コンテンツ強化（2026-03-18 ほぼ達成🎊）
目標のエントリー数オーバーに成功しました（現在100件以上）。

| タスク | 詳細 |
|---|---|
| ~~**OGP画像の設定**~~ | `icons/og-image.png` を追加。index.html / about.html にメタタグ設定済み |
| ~~**エントリーの継続追加**~~ | RSSからの自動収集フローが完成。現状120件ほどまで拡充済み |
| **`update_status.py` の定期実行** | 手動 or GitHub Actions で日次自動実行化 |
| ~~**`fetch_rss.py` の完成**~~ | `rss_fetch.py` として完成。重複チェックとステージング出力まで自動化 |

### 🟡 Phase 2 — UX改善（エントリー50〜100件）
サイトとして形になってきたら着手。

| タスク | 詳細 |
|---|---|
| **ページネーション or 無限スクロール** | 件数が増えると全件レンダリングが重くなる |
| **ソート機能** | 日付順・カテゴリ順の切替 |
| **タグフィルタ** | 作品名・場所などタグでの絞り込み |
| **スマホ用ハンバーガーメニュー** | 現状はモバイルでナビが非表示になっている |
| **`about.html` の充実** | サイトの目的・更新頻度・データソースを英語で明記 |

### 🟢 Phase 3 — 成長・マネタイズ（アクセスが増えてから）
アクセス数が伸びてきたら検討。

| タスク | 詳細 |
|---|---|
| **Google Analytics導入** | アクセス解析・人気カテゴリの把握 |
| **Google AdSense** | エントリー50件以上・月間PV1000以上が目安 |
| **X (Twitter) BOT** | 新着エントリーを自動ポスト |
| **地図機能** | Google Maps埋め込みでイベント場所をビジュアル化 |
| **独自ドメイン** | `otaku-insider.com` 等（月数百円〜） |
| **多言語対応** | 日本語版の追加。方針: 管理1本化・URL分離（`/ja/`・`/en/`）・JSONは言語別ファイル・日本語ページは未翻訳側をそのまま表示。RSS Managerの書き出しを日英対応にすると後々楽。詳細は `ROADMAP_LATEST.md` セクション8 |

### 🔵 Phase 4 — スケールアップ（長期）

| タスク | 詳細 |
|---|---|
| **バックエンドAPI化** | エントリー数が大量になったらNext.js + Supabase等に移行 |
| **ユーザー投稿機能** | コミュニティ駆動の情報追加 |
| **メールニュースレター** | 週次まとめのメール配信 |

---

## 既知の課題・注意点

- **Service Workerのキャッシュ更新**: `sw.js` の `CACHE_NAME` を `otaku-insider-v2` のようにバージョンアップしないと古いキャッシュが残る。`entries.json` を更新したら都度バージョンを上げること
- ~~**`og:image` 未設定**~~: `icons/og-image.png` を追加済み。index.html / about.html にメタタグ設定済み
- **`node_modules/` に `sharp` が残存**: ローカルにのみ存在、gitignore済みなので問題なし。不要なら `rm -rf node_modules` で削除可

---

## 開発履歴・アップデートログ

- **2026-03-19 (Daily Update ワークフロー堅牢化 #2):**
  - `daily-update.yml` の Translate ステップ: `set -e` を除去し、1ファイルの翻訳が失敗しても残りのファイルは処理を続行するように変更。失敗数もログに出力。
  - `daily-update.yml` の Commit and push ステップ: `git pull --rebase` でコンフリクトが発生した場合、`rebase --abort` して安全に終了するように変更（不整合な状態でのプッシュを防止）。
- **2026-03-19 (RSS Manager 安定化・GitHubプッシュボタン):**
  - `rss_manager/server.py` を全面改修: 全 HTTP メソッド（GET/POST/PUT/DELETE）に `_safe_call` ラッパーを追加し、未処理例外が発生しても必ず JSON エラーレスポンスを返すようにした。
  - 例外発生時はターミナルにトレースバックを出力し、原因を追いやすくした。
  - `json_response` に `default=str` を追加し、シリアライズ不可オブジェクトでもクラッシュしないようにした。
  - `project_root` プロパティを追加してコードの重複を削減。
  - `POST /api/git/push`: 書き戻し → `git add` → `git pull --rebase` → `git commit` → `git push` を一括実行する API を追加。
  - `rss_manager_ui/index.html`: 「GitHubにプッシュ」ボタンを追加。
  - `rss_manager_ui/app.js`: プッシュボタンのクリックハンドラを追加。HTML エラーが返った場合は汎用メッセージを表示。
  - `rss_manager_ui/sw.js`: キャッシュ名を `rss-manager-v4-gitpush` に更新（古い UI のキャッシュを破棄）。
  - `start_rss_manager.sh`: `.venv` があれば自動で activate するように改善。
- **2026-03-19 (4gamer サムネイル修正):**
  - `rss_fetch.py` / `fill_og_images.py`: `www.4gamer.net` を `OG_FIRST_DOMAINS` に追加。バナー広告画像（`banner` キーワード）を除外対象に追加。
  - `fill_og_images.py --replace-generic` で既存50件のバナーサムネイルを正しい記事画像に差し替え済み。
- **2026-03-19 (Daily Update ワークフロー堅牢化):**
  - 各ステップに `==>` プレフィックスでログを明確化。
  - Translate/Add: `mkdir -p data/staging`、処理件数を出力。
  - Commit: `git pull --rebase`、`git push origin main` を明示。
  - Fill thumbnails: CI 用に `--limit 10` を追加（長時間化防止）。
  - 失敗時に「Diagnose on failure」で data/staging・entries.json を出力。
  - HANDOVER に失敗調査の簡易表を追加。
- **2026-03-19 (カテゴリタブレスポンシブ):**
  - カテゴリフィルタボタンをブラウザ幅に応じて中央寄せで折り返すよう調整。
  - `css/style.css`: `.category-tabs` に `justify-content: center` を追加。
- **2026-03-19 (プッシュ):**
  - あみあみサムネ改善＋OTAKU NEWS タグを GitHub にプッシュ。
  - 変更ファイル: rss_fetch.py, fill_og_images.py, render.js, style.css, index.html, entries.json
- **2026-03-19 (OTAKU NEWS タグ):**
  - 新タグ「OTAKU NEWS」を追加。オレンジ色のピル表示。
  - `scripts/rss_fetch.py`: source.categories を全件エントリに渡すよう変更（複数カテゴリ対応）。
  - フロントエンド: categoryLabel に otaku-news、CSS に .cat-otaku-news、index.html に OTAKU NEWS タブを追加。
  - RSS Manager: suggestCategories と prompt 例文に otaku-news を追加。
- **2026-03-19 (あみあみサムネ改善):**
  - あみあみフィギュア記事のサムネイルが粗い／欠落する問題に対応。
  - `scripts/rss_fetch.py`: news.amiami.jp 向けに og:image を優先（シェア時と同じ画像を取得）。thumb_timeout 12→20秒に延長。
  - `scripts/fill_og_images.py`: 同様に og:image 優先ロジックを追加。timeout 15→20秒に延長。
  - ドメイン別 `choose_thumbnail()` により、他サイトは従来どおり先頭画像優先を維持。
- **2026-03-19 (夜):**
  - リセット＋チェック機構＋並べ替えを実装。
  - `scripts/sort_entries.py`: entries.json を id 日付でソート（新着順/古い順）。
  - `js/render.js`: カード表示時に新着が上になるようソート。
  - `scripts/add_entry.py`: 新規追加を先頭に（`insert(0, entry)`）、`--reset` オプション追加。
  - `scripts/reset_entries_from_rss.py`: リセット用。entries をバックアップし、RSS から全件取得。
  - `scripts/rss_fetch.py`: `--reset` モード（重複チェックなし、reset_*.json 出力）追加。
  - `scripts/perplexity_search.py`: 保存前に同一 URL の重複を検出し、2 件目以降を空にする。
  - ワークフローに「Sort entries (newest first)」ステップを追加。
- **2026-03-19 (晩):**
  - Perplexity API 連携: カテゴリ別 6 検索（cafe, vtuber, figure, game, anime, other）を日次パイプラインに追加。`scripts/perplexity_search.py` と `prompts/perplexity_*.md` を新規作成。
  - 日次スケジュール: `schedule: cron '0 19 * * *'` で毎日 4:00 JST に自動実行。手動トリガも併用可能。
- **2026-03-19 (後半):**
  - DeepL 認証をヘッダー認証に変更。従来の form body 認証が非推奨化されたため、`Authorization: DeepL-Auth-Key` を使用するよう `translate_with_deepl.py` を修正。
  - プラン「今後の方針」に基づく直近タスクを実施。
  - DeepL: `--dry-run` オプション追加（キー不要で翻訳対象確認）。キー未設定時の安全停止（exit 2）は既存のまま検証済み。
  - GitHub Actions: `.github/workflows/daily-update.yml` を新規作成。手動トリガ（workflow_dispatch）。DEEPL_AUTH_KEY 未設定時は更新ジョブをスキップして安全終了。
  - categories 統一: `rss_fetch.py` の出力を `category` → `categories` 配列に変更。`add_entry.py` に `normalize_categories()` を追加し、`category` 混入時も `categories` に正規化。
  - RSS Manager B2: 収集記事タブ切替時に一覧を再読み込み。`published_at` の表示フォーマット（日本語日付）、要約の120文字省略表示を追加。
- **2026-03-18:**
  - OGP画像（`icons/og-image.png`）を追加。`og:image` / `twitter:image` を index.html・about.html に設定。
  - カード一覧 / 詳細モーダルにサムネイル表示（`entries.json.thumbnail`）を追加。
  - `scripts/rss_fetch.py --fetch-thumbnails` で先頭画像を自動抽出し、必要に応じて `og:image` へフォールバック。
  - `sources.json` に各ソースのカテゴリ分け用 `content_tags` を追加。
  - `scripts/rss_fetch.py` を実装し、RSSからの新着自動フェッチと重複チェックの仕組みを構築。
  - 過去分のRSS情報を一括取得・翻訳（総計90件追加）。エントリー数が120件規模に到達。
  - 新カテゴリ `game` (Game News) をフロントエンドへ追加し、既存の4gamer等のニュースを自動移行。
  - `prompts/update_workflow.md` をRSS自動取得を前提としたプロンプトに書き換え。
- **2026-03-19:**
  - フロントUI：VTuberカテゴリタブ追加、紫カラー（#bb33ff）適用。
  - カテゴリ：`category`（単数）→ `categories`（配列、最大3）の後方互換をフロントに実装。
    - フィルタを `includes` 対応へ更新。
    - statsバーのカテゴリ数集計を `categories` 対応に更新。
    - カード/モーダルのカテゴリ表示を複数タグ化。
  - データ移行：`scripts/migrate_categories.py` を追加し、`data/entries.json` を `category` → `categories` に一括変換（バックアップ作成）。
  - RSS Manager：VTuber系ソースとして MoguLive（`moguravr`）を登録。電撃VTuberは公式RSSを確認できなかったため `scrape` として登録（`dengeki-vtuber`）。
  - サムネイル：`scripts/rss_fetch.py --fetch-thumbnails` で先頭画像抽出→OGPフォールバックをテストし、装飾gif（button/twitter等）を候補から除外する調整を追加。
  - 翻訳パイプライン（ローカル検証）：`scripts/translate_with_deepl.py` を追加（`DEEPL_AUTH_KEY` 未設定時は安全に終了）。
- **2026-03-16:**
  - SEO・PWA機能（Twitter Card, Service Worker等）を一斉導入。レスポンシブデザインの調整。
- **2026-03-15:**
  - 初回リリース（α版）。基本UIモックアップおよびJSON読み込み機能の作成。

---

## 次のセッションで最初にやること

1. DeepL APIキー取得 → `scripts/translate_with_deepl.py` でローカル実翻訳テスト（`--dry-run` で事前確認可能）
2. GitHub Actions: リポジトリ Secrets に `DEEPL_AUTH_KEY` を設定後、手動トリガで動作確認。成功したら `schedule` で日次 cron 化
3. ~~`categories` 配列運用を追加経路まで統一~~ → 完了（rss_fetch / add_entry 対応済み）
4. ~~RSS Manager B2の運用品質調整~~ → 完了（タブ切替時再読込・日付フォーマット・要約省略）

---

## 次の予定（DeepL/自動化）

1. DeepL APIキー取得 → ローカルで翻訳（`scripts/translate_with_deepl.py`）を実データでテスト
2. 動いたら GitHub Actions で日次自動実行（キーが無い場合はスキップして安全に終了）
3. 余力があれば Perplexity 等の検索API取得 → 検索 → 結果反映も同じパイプライン形式に統合
4. 将来：ミニPC/ラズパイ＋ローカルLLM環境ができたら、DeepL/検索API部分だけ差し替えて自前運用へ

---

## ロードマップ参照

- 全体像と直近実装の統合版は `ROADMAP_LATEST.md` を参照（長期構想 + 直近スプリント優先度を統合）

---

## RSS Manager V2（ローカル管理ツール）

### 概要

ヲタInsiderの更新作業を楽にするための **ローカル専用ツール**。
公開サイトとは完全に分離し、`localhost` でのみ利用する。

### ファイル位置

- 起動: `rss_manager.py`
- バックエンド: `rss_manager/`
- UI: `rss_manager_ui/`
- 管理DB: `rss_manager_data/manager.db`
- 依存: `requirements-rss-manager.txt`
- セットアップ手順: `README_rss_manager.md`

※ GitHubに公開しないため `.gitignore` 対象（ローカル専用）。

### 現在地

- **Phase A（ソース管理）**: 完了
  - RSS探索（Stage 1+2）＋最新5件プレビュー
  - ソース追加/削除/カテゴリ編集
  - 生存確認（全体/個別）
  - `data/sources.json` への書き戻し（バックアップ作成あり）
- **Phase B1（収集をDBに溜める）**: 完了
  - `articles` テーブル追加（URLユニーク）
  - 登録済みRSSをフェッチして `articles` に保存
  - 手動フェッチAPI `POST /api/fetch`

### 起動

```bash
cd "Japan OTAKU Insider"
source .venv/bin/activate
python3 rss_manager.py
```

ブラウザ:
- `http://127.0.0.1:8080/`

### 手動フェッチ（B1）

```bash
curl -s -X POST http://127.0.0.1:8080/api/fetch \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

### 次にやること（B2候補）

#### B2（想定する日次運用の導線）

いちぼさんの運用は「選別よりも、ボタン1発で回る」ことを優先する。

1. RSS Managerを起動（ローカル）
2. 管理画面で **[収集] ボタン**を押す（= `POST /api/fetch`）
3. 画面に「今回の新規件数」「ソース別件数」を表示して確認
4. （余裕があれば）新着の一覧を眺める（選別は必須にしない）

#### B2で実装する機能（優先順）

- 収集記事タブ（UI）を有効化して、`articles` の「新着」を一覧表示
- **[収集] ボタン**をUIに追加し、`POST /api/fetch` を叩いて結果サマリーを表示
- 記事詳細の最低限（タイトル/URL/要約）表示（全文は後回しOK）
- ブックマーク（DBの `is_bookmarked`）のトグル（任意）
