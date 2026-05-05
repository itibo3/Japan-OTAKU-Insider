# Japan OTAKU Insider — 引継書

**作成日:** 2026-03-16 (最終更新: 2026-05-05)  
**ステータス:** β版完成 / 独自ドメイン（otaku.eidosfrontier.com）移行完了 / HTTPS有効 / AdSenseは審査却下（第三者コンテンツの集約に近いと判断）— オリジナル編集・週次まとめ等で付加価値を高めたうえで再申請・改善を予定 / RSS Manager V3 リデザイン完了  
**開発期間:** 初回αの骨格構築は約6時間（以降は日次・週次で継続拡張）  
**URL:** [https://otaku.eidosfrontier.com](https://otaku.eidosfrontier.com)

---

## プロジェクト概要

日本のオタク文化（コラボカフェ・フィギュア・イベント・アニメニュース）を英語圏向けにまとめたデータベースサイト。  
GitHub Pages上で動作する完全静的サイト（維持費ゼロ）。

### データ更新まわりの現状（要約・2026-04-14）

| もの | 状態 |
|------|------|
| **Daily Update**（cron＋手動） | RSS → **Perplexity（6カテゴリ）** → **Gemini 検閲** → `translate_staging` → `entries.json` / `entries_ja.json` 反映まで **`daily-update.yml` 上は本番接続**（リポジトリの YAML が正） |
| **Perplexity 6カテゴリ検索** | 日次ワークフローに含まれる（`|| true` でカテゴリ単位失敗は継続）。単体検証は `verify-perplexity.yml` |
| **Gemini 検閲** | `scripts/gemini_flash_review.py` を日次で Perplexity staging に適用（キー・モデルは Secrets）。誤検知等は運用で調整 |
| **週次自己改善** | `weekly-self-improve.yml`：**週1＋手動**。成果は Artifact（`prompts/` は自動では書き換えない） |

---

## プロダクト戦略・横展開メモ（2026-04-14）

会話で固めた方針。実装は別タスク。詳細は `ROADMAP_LATEST.md` の **§9 プロダクト戦略・横展開メモ** も参照。

| 項目 | 内容 |
|------|------|
| **JOIのコア** | 海外ヲタ向けに、日本の一次情報を翻訳して最速で届ける。これがブランドの軸。 |
| **傘下に置ける例** | Jコア・同人・音ゲー/音楽シーンDB、聖地巡礼、漫画アニメ飯、ヲタ宿、今クール考察まとめ等（いずれも日本起点×海外向け翻訳に収まるもの）。 |
| **傘の外** | 一般ニュース、経済、株・為替、デイトレ時事、世界経済速報等 → **別ドメイン**で分離。AdSense もサイト別申請の前提。 |
| **リポ・Secrets** | **1サイト1リポ**で管理しやすく。APIキーは **Secrets のみ**（ファイルに直書きしない）。 |
| **外向き一体感** | ルートドメインの About を総合DBハブに拡張し、各DBは同一サイト内の別コンテンツとして説明。開発はリポ分割のまま。 |
| **コンテンツ** | 垂直ごとに週刊まとめを持つと強い（滞在・再訪・独自性）。 |
| **将来** | パイプライン骨組みのテンプレ化、RSS Manager をサイト切替タブで一元管理する構想（未着手）。 |
| **AdSense** | ルートドメイン登録の運用に合わせる。サブドメイン／パスだけでの別サイト分割は当てにしない。 |

---

## 技術スタック


| 要素      | 内容                                                  |
| ------- | --------------------------------------------------- |
| ホスティング  | GitHub Pages                                        |
| フロントエンド | HTML / CSS / Vanilla JS                             |
| データ     | `data/entries.json`（JSONファイル）                       |
| スタイル    | カスタムCSS（ダークUI + ネオンアクセント）                           |
| フォント    | Google Fonts: Outfit + Noto Sans JP                 |
| PWA     | `manifest.json` + `sw.js`（Service Worker）           |
| SEO     | OpenGraph / Twitter Card / sitemap.xml / robots.txt |
| アクセス解析 | Google Analytics 4（`gtag.js`、主要HTMLの `<head>` に設置）        |


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
│   ├── rss_fetch.py    # RSS自動取得・ステージング保存スクリプト
│   ├── translate_staging.py # staging JSON を Google 優先で英訳、エラー・不備時は DeepL で再翻訳（キー任意）
│   ├── translate_with_deepl.py # 互換ラッパ（中身は translate_staging）
│   ├── check_deepl_quota.py # （レガシー）DeepL枠確認。日次ワークフローでは未使用
│   └── send_x_dm.py    # X API(v2)経由の管理者向けDM送信スクリプト
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

### Cursor 作業後のお約束（引継ぎ・ワークスペースルールと同一趣旨）

コード・スクリプト・GitHub Actions など **リポジトリ上のファイルを変えたセッション**では、次までをセットで完了とみなす。

1. **HANDOVER.md** の「開発履歴・アップデートログ」に、何をしたかを追記する（該当プロジェクトに HANDOVER がある場合）。
2. 変更を **`git commit` し、`git push` して GitHub の既定ブランチに載せる**。Daily Update 等の CI は **リモートのコミット**を checkout するため、ローカルだけ直してプッシュしないと本番と認識がズレる。

※ ユーザーが「プッシュしないで」と明示したときだけ 2 を省略する。

### Daily Update ワークフロー失敗時の調査

Actions タブで失敗した Run を開き、どのステップで止まったか確認する。

| 失敗ステップ | 想定原因 | 対応 |
|---|---|---|
| RSS Fetch | ネットワークエラー、sources.json 不正 | ログの ERROR 行を確認。ローカルで `python3 scripts/rss_fetch.py` を実行して再現する |
| Perplexity Search | PERPLEXITY_API_KEY 未設定、API レート制限、パース失敗 | Secrets にキーを設定。**Verify Perplexity** ワークフローを手動実行し Artifact で生レスポンスを確認。`--debug` でパース失敗の原因を特定 |
| Translate staging | Google レート制限・`deep_translator` 例外、DeepL フォールバック失敗、ネットワーク | ログを確認。`--delay` を大きくする、時間をおいて再実行。Google 全滅かつ `DEEPL_AUTH_KEY` なしで空訳になると exit。失敗ファイルはワークフローが削除して続行 |
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
サイトとして形になってきたら着手。**（ほぼ達成🎉）**

| タスク | 詳細 |
|---|---|
| ~~**ページネーション or 無限スクロール**~~ | `Load More` ボタンで24件ずつ表示する機能として実装済み |
| ~~**ソート機能**~~ | 日時（idDate・イベント日）優先のソート機能を実装済み |
| ~~**タグフィルタ**~~ | 検索窓でタグやカテゴリ名を含めた全体検索が可能 |
| ~~**スマホ用ハンバーガーメニュー**~~ | `js/menu.js` 等でスマホ向けナビゲーション整備済み |
| ~~**about.html の充実**~~ | パイプライン・Tech Stack・データソースなど英語で明記済み |

### 🟢 Phase 3 — 成長・マネタイズ（アクセスが増えてから）
アクセス数が伸びてきたら検討。**（ほぼ完走🎉）**

| タスク | 詳細 |
|---|---|
| ~~**Google Analytics導入**~~ | GA4（`G-BP25JGCEGY`）を index / about / contact / privacy 等に設置済み |
| ~~**Google AdSense**~~ | 審査用メタタグは全主要HTMLに実装済み。審査は却下（方針: 独自コンテンツ強化後に再申請を検討） |
| ~~**X (Twitter) BOT**~~ | `post_to_x.py` とOAuthで新着の自動ポスト機能 実装済み |
| **地図機能** | （※未導入）Google Maps埋め込みでイベント場所をビジュアル化 |
| ~~**独自ドメイン**~~ | `otaku.eidosfrontier.com` に移行対応完了 |
| ~~**多言語対応**~~ | `entries_ja.json` 自動生成パイプラインとヘッダーの EN/JP 切替トグルを実装済み |

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

- **2026-05-05（検索流入改善のため静的記事ページを自動生成）:**
  - `scripts/generate_static_articles.py` を新規追加。
  - `data/entries.json` を読み、**直近30日**の記事を `/articles/{id}.html` として静的生成。
  - 同時に `sitemap.xml` へ `/articles/` URL を追記・更新（`lastmod` 付き）。
  - `.github/workflows/daily-update.yml` に「Generate static article pages (last 30 days)」ステップを追加。
  - 日次コミット対象に `articles/` と `sitemap.xml` を追加し、GitHub Pages 側でクローラーが辿れる状態を維持。

- **2026-05-02（X APIクレジット急減の原因調査 + 投稿ガード実装）:**

  **背景:** 「1日12件程度の想定なのに、$5分の X API クレジットが数日で枯渇する」事象を調査。Actions 実行ログを確認すると、日次実行1回で `8カテゴリ × EN/JA = 最大16投稿試行` になり得ること、さらに `workflow_dispatch`（手動実行）が同日に重なると追加試行が発生することを確認。`SpendCapReached` が返った後も同一実行内で投稿試行を続ける挙動もあった。

  **対応:**
  - `scripts/post_to_x.py`
    - `--max-posts`（既定12、`X_MAX_POSTS_PER_RUN` でも指定可）を追加し、**1実行あたりAPIコール上限**を導入。
    - 日次投稿に **同日重複実行ガード**を追加（既定は2回目以降スキップ、必要時のみ `--allow-multiple-runs-per-day` で解除）。
    - X API の `SpendCapReached` を検知したら即時停止し、`reset_date` までの一時停止状態を `data/.x_api_pause.json` に保存。
    - 実行日トラッキングを `data/.x_post_run_state.json` に保存。
    - 実行ログに `Max API calls this run` と `API calls attempted` を出力するよう変更。
  - `.github/workflows/daily-update.yml`
    - X投稿ステップに `X_MAX_POSTS_PER_RUN: "12"` を追加。
    - commit対象に `data/.x_post_run_state.json` / `data/.x_api_pause.json` を追加。
  - `.github/workflows/weekly-self-improve.yml`
    - 週次Top5投稿にも `X_MAX_POSTS_PER_RUN: "12"` を明示。

  **補足:** これにより「想定より多い試行」「同日重複実行」「SpendCap到達後の無駄試行」を抑制し、クレジット消費の暴発を防ぐ。

- **2026-04-23（手動追加翻訳不具合: PWAキャッシュ更新）:**
  - 症状: コード修正後も端末側で旧 `app.js` が動作し「何も変わらない」ように見える。
  - 原因: PWA の Service Worker キャッシュが古い `app.js` を保持。
  - 対応: `rss_manager_ui/sw.js` の `CACHE_NAME` を `rss-manager-v7-pwa` → `rss-manager-v8-pwa` に更新し、クライアントキャッシュを強制更新。

- **2026-04-23（手動追加: 翻訳スキップ不具合の修正）:**
  - **問題:** 手動追加の「情報取得」で日本語タイトル/概要が EN 欄にも自動入力され、`/api/entries/add` が「EN欄が空でない」と判定して翻訳をスキップ。結果として EN 側に日本語が保存されるケースが発生。
  - **対応（UI）:** `rss_manager_ui/app.js` の `fetchEntryMeta()` を修正し、メタ取得時は JP 欄（`manual-title-ja`, `manual-description-ja`）のみ自動入力するように変更。EN 欄への自動入力を停止。
  - **対応（サーバー）:** `rss_manager/server.py` の `/api/entries/add` を修正し、EN欄が非空でも `_looks_japanese(...)` が true の場合は JA→EN 翻訳を強制実行。
  - **note 改善:** EN欄に日本語が入っていたケースは `title(EN欄の日本語) を JA→EN 自動翻訳` のように返却メッセージへ明示。
  - **検証結果:**
    - JA-only: 翻訳実行され EN は英語化。
    - JA+EN（EN欄に日本語）: EN は英語へ矯正。
    - JA+EN（EN欄に英語）: EN は維持（翻訳スキップ）。

- **2026-04-23（手動追加: JP正本統一 + JP/EN同時整合ガード）:**
  - `scripts/add_entry.py` に `add_single_entry_dual()` を追加。
    - JP正本（`title_ja` / `description_ja`）と EN（`title` / `description`）を同一IDで同時追加。
    - `entries.json` と `entries_ja.json` の双方で重複チェックを実施。
    - 片側保存失敗時のロールバック保険を追加。
  - `rss_manager/server.py` の `/api/entries/add` を JP正本モードへ変更。
    - 必須入力を `url + title_ja + description_ja` に統一。
    - EN未入力時は JA→EN 自動翻訳で補完、翻訳失敗時は日本語フォールバックで継続。
    - `description_ja` を保存。
  - `rss_manager/server.py` に `entries_ja.json` / `entries.json` の整合チェックを追加。
    - push前に件数・ID集合を検証し、ズレがある場合は `GitHub に公開` を停止してエラー返却。
  - `rss_manager_ui/app.js` を JP必須へ調整。
    - バリデーションを `URL + 日本語タイトル + 日本語概要` 必須に変更。
    - 送信payloadに `description_ja` を含める。
  - 検証:
    - JA-only / JA+EN / 翻訳失敗フォールバックの分岐をスモーク確認。
    - 既存データの整合チェックは `OK`（EN/JA一致）を確認。

- **2026-04-23（手動追加: 日本語起点フロー対応）:**
  - **目的:** 手動追加フォームが英語必須だったため、日本語入力のみでも登録できるよう改善。
  - **変更点（UI）**
    - `rss_manager_ui/index.html` の手動追加フォームを日本語主入力に変更。
    - `タイトル（日本語）` / `概要（日本語）` を必須化し、英語欄は「任意（未入力なら自動生成）」へ変更。
    - `id="manual-description-ja"` を追加。
  - **変更点（フロント）**
    - `rss_manager_ui/app.js` のバリデーションを `url + (title_ja or title) + (description_ja or description)` に変更。
    - `/api/entries/add` の payload に `description_ja` を追加。
    - メタ取得時は日本語欄優先で自動入力するよう調整。
  - **変更点（サーバー）**
    - `rss_manager/server.py` の `/api/entries/add` を拡張し、英語欄が空なら `title_ja` / `description_ja` から JA→EN 自動翻訳で補完。
    - 翻訳失敗時はエラー停止せず、日本語をフォールバックとして保存しつつ `note` を返す設計にした。
  - **依存追加**
    - `requirements-rss-manager.txt` に `deep-translator` を追加（GoogleTranslator 利用）。
  - **動作確認**
    - JA-only / EN-only / JA+EN の3パターンでロジック検証。
    - 手動追加記事の削除タスクについては `entries.json` / `entries_ja.json` を確認し、`_source=manual` は 0 件（削除対象なし）だった。

- **2026-04-22（デザイン微調整・アイコン刷新）:**
  - **カテゴリタブのレイアウト修正:** Cosplay タグ追加に伴い PC 版（`max-width: 900px`）で表示がはみ出す問題を修正。タブコンテナの最大幅を `1080px` に広げ、全9タブが1行に中央揃えで収まるよう改善。モバイル端末でも横スクロールが正常に機能することを確認。
  - **アイコン・Favicon の刷新:** JOI の X（旧 Twitter）プロフィールのブランドカラー（ネオンピンク × マゼンタ）に合わせた「ネオングロー仕上げのサテライトディッシュ」アイコンを作成。
    - PWA 用: `rss_manager_ui/icon-192.png`, `icon-512.png` 差し替え
    - メインサイト用: `favicon.png`, `favicon.ico`, `icons/apple-touch-icon.png`, `icons/favicon-192.png` 新規作成、および全ての主要 HTML の `<head>` に favicon リンクタグを追加実装。
  - **PWA用アイコン更新のトラブルシュート:** ゲーミングPC上の RSS Manager で PWA アイコンが旧バージョンのまま更新されない問題が発生。
    - 原因: `rss_manager_ui/sw.js` 内の `CACHE_NAME` を更新していなかったため、旧バージョンのアイコンキャッシュがブラウザに残存していた。
    - 対応: キャッシュバージョンを `v6` から `v7` に更新して push。その後、リモートのゲーミングPC （100.64.168.28）で `git pull --rebase` を実行して最新のキャッシュフラグを適用。

- **2026-04-22（RSS Manager V3: フロントエンド全面リデザイン）:**
  **依頼書:** `/home/itibo/antigravity_rss_manager_redesign.md` に基づく V2→V3 全面リデザイン。

  **変更ファイル:**
  | ファイル | 変更内容 |
  |---|---|
  | `rss_manager_ui/app.js` | 冒頭に `SITES` 配列定数 + `CURRENT_SITE` を追加（ロジック本体は一切未変更） |
  | `rss_manager_ui/index.html` | 完全書き直し — セマンティック HTML5 + サイトセレクター + PC 2カラムレイアウト |
  | `rss_manager_ui/style.css` | 完全書き直し — HSLベースデザインシステム + グラスモーフィズム + レスポンシブ |

  **デザイン方針:**
  - Vercel / Linear / Raycast インスパイアの洗練されたダークテーマ
  - HSLベースの `--accent-hue` CSS カスタムプロパティで、将来のサイトごとカラー切替に対応
  - `backdrop-filter: blur()` によるグラスモーフィズム全面採用
  - ホバー・フォーカスのマイクロインタラクション（浮き上がり、グロー効果）
  - Google Fonts `Inter` ロード

  **新機能 — サイトセレクター（将来の複数サイト対応）:**
  - ヘッダー左上にドロップダウン型サイトセレクターを配置
  - 現在は JOI 1サイト + 「サイトを追加」プレースホルダー
  - `app.js` 冒頭の `SITES` 配列にサイトを追加するだけで複数サイト対応可能な設計
  - サイトごとに `accentHue` を変えることでUI全体のカラーが連動して切り替わる

  **レスポンシブ対応:**
  | 画面幅 | レイアウト |
  |---|---|
  | 1024px+ (PC) | 手動追加タブが2カラム、広い余白、テーブル行にglowホバー |
  | 769-1023px (タブレット) | 1カラム、縮小余白 |
  | 480px以下 (スマホ) | タブはアイコンのみ表示、ボタン全幅、font-size 16px（iOSズーム防止） |
  | PWA standalone | safe-area-inset 対応 |

  **ID/data属性の維持:** 依頼書記載の全35個のID・data-tab属性を完全維持（grep検証済み）。`app.js` のロジック本体は一切変更なし。

- **2026-04-22（RSS Manager: ゲーミングPC常時起動 + PWA化 + Git管理化）:**

  **内容:**
  - ゲーミングPC（WSL2 `DESKTOP-7J59T08`、Tailscale IP: `100.64.168.28`）に JOI リポジトリを clone し、RSS Manager を常時起動するよう設定した。
  - **systemd user サービス化** (`~/.config/systemd/user/rss-manager.service`):
    - 起動時に `git pull --rebase origin main` を自動実行してデータを最新化。
    - `--host 0.0.0.0 --port 8080` で Tailscale ネットワーク内からアクセス可能。
    - `systemctl --user enable` で PC 起動時に自動スタート。
  - **GitHub SSH 認証設定**（ゲーミングPC側）:
    - `~/.ssh/id_ed25519`（`joi-gaming-pc`）を生成し GitHub に登録。
    - git remote を SSH URL（`git@github.com:itibo3/Japan-OTAKU-Insider.git`）に変更。
    - push / pull の動作確認済み。
  - **PWA 対応**:
    - `manifest.json` に Web Share Target・アイコン設定を追加。
    - `icon-192.png` / `icon-512.png` を生成。
    - `style.css` にスマホ向けレスポンシブ（480px以下）・`display: standalone` 対応を追加。
    - `app.js` に `handleShareTarget()` を追加。Android の「共有」ボタンから URL を受け取り、手動追加タブに自動入力・情報取得を走らせる。
    - `sw.js` をキャッシュバージョン更新・アイコン対応に更新。
  - **`POST /api/entries/pull` 追加** (`rss_manager/server.py`):
    - UI の「⬇️ 最新データを取得」ボタンから `git pull --rebase origin main` を実行できる。
  - **`rss_manager/` / `rss_manager_ui/` / `rss_manager.py` を Git 管理下に追加**:
    - `.gitignore` から除外ルールを削除（`rss_manager_data/` のみ除外を維持）。
    - 初回コミット・push 済み（`b70b18a`）。
    - 以降は Antigravity などで UI を改修 → push → ゲーミングPCの「最新取得」ボタンで即同期できる。

  **アクセス方法:**
  - URL: `http://100.64.168.28:8080`（Tailscale 接続必須）
  - ROGフォン・Chromebook どこからでもアクセス可能。
  - スマホでホーム画面に追加するとアプリとして起動できる（PWA）。

  **今後の拡張メモ（Antigravity依頼書）:**
  - `/home/itibo/antigravity_rss_manager_redesign.md` に V3 リデザイン依頼書を作成済み。
  - 複数サイト対応（サイトセレクター・サイト別タブ）を見越した設計でリデザインを予定。

- **2026-04-19（RSS Manager: 手動1記事追加UI 実装）:**

  **内容:**
  - `scripts/add_entry.py` に `add_single_entry(entry: dict) -> dict` 関数を追加。既存の validate / 重複チェック / 書き込みロジックを 1 件 dict 入力で呼べる形に切り出した。
  - `rss_manager/server.py` に API 3 本を追加:
    - `POST /api/entries/fetch-meta`: URL を GET して `og:title / og:description / og:image` を返す。
    - `POST /api/entries/add`: フォーム情報を受け取り `add_single_entry()` を呼んで `entries.json` に書き込む。ID は `[category]-[YYYYMMDDHHMM]-manual-[6hex]` 形式で自動生成。
    - `POST /api/entries/push`: `entries.json` / `entries_ja.json` を `git commit & push` する。
  - `rss_manager_ui/index.html` に **✏️ 手動追加** タブを追加。URL 入力 → 情報取得 → フォーム編集 → 追加 → GitHub 公開 の一連フローを UI 上で完結できる。
  - `rss_manager_ui/app.js` に `setupManualAdd() / fetchEntryMeta() / submitManualEntry() / pushEntries()` を追加。
  - `rss_manager_ui/style.css` に `.manual-form` の入力フォームスタイルを追加。

  **使い方（非エンジニア向け）:**
  1. RSS Manager を起動して「✏️ 手動追加」タブを開く。
  2. 追加したい記事の URL を貼り付けて「情報取得」を押す → タイトル・概要・サムネが自動入力される。
  3. カテゴリと日付を選んで「entries.json に追加」を押す。
  4. 確認 OK なら「GitHub に公開」を押すと本番サイトに反映される。

  **今後の拡張メモ:**
  - `title_ja` の自動翻訳ボタン（Google Translate API 呼び出し）を追加すると利便性が上がる。
  - ~~`entries_ja.json` の同期は現状 GitHub Actions の `daily-update` に依存している（手動追加直後は EN のみ）。~~ → **2026-04-23 以降:** 手動追加は JP 正本＋`/api/entries/add` で `entries.json` / `entries_ja.json` を同時更新（`add_entry.py` の `add_single_entry_dual`）。日次 Actions への依存は補助的。

- **2026-04-22（運用改善: 鮮度ステータス自動化 + cosplay カテゴリ追加）:**

  **内容:**
  - `scripts/update_status.py` に鮮度ルールを追加。`dates.start/end` が無い通常ニュースでも `dates.display` を解析し、**公開45日超は `ended`** に自動変更するようにした。
  - これにより `active` 固定だった状態を解消（実データ適用で `ended` が 27 件反映）。
  - コスプレ用カテゴリ `cosplay` を追加:
    - `index.html` のカテゴリタブに **Cosplay** を追加。
    - `js/render.js` のカテゴリ表示名・Amazon検索ヒントに `cosplay` を追加。
    - `css/style.css` に `cat-cosplay` の色スタイルを追加。
    - `scripts/post_to_x.py` に `cosplay` 用 emoji / hashtag を追加。
    - `scripts/gemini_flash_review.py` の `primary_category` 許容値に `cosplay` を追加（将来の自動分類にも対応）。
  - データ反映:
    - `data/sources.json` の `0115765-com` を `otaku-news` → `cosplay` へ変更。
    - 既存 `entries.json` / `entries_ja.json` で `0115765-com` 由来 271 件を `cosplay` へ一括変換。
    - **後追い:** 分類名・Vol 表記・運用の都合で `0115765-com` のカテゴリは再調整されることがある。**現状のソース分類は常に `data/sources.json` を正**とする（本リポジトリでは `otaku-news` に戻している期間もある）。

- **2026-04-20（JOI全体レビュー修正: 計測・信頼性・耐障害性・コード統一）:**

  **内容:**
  - **GA4 計測追加**: `weekly.html` / `weekly-archive.html` に GA4 スニペットを追加（PV 計測漏れ解消）。
  - **about.html 事実修正**: 翻訳エンジン（Google 主・DeepL フォールバック）、更新頻度（1日1回）、Gemini 検閲ステップを実態に合わせて修正。
  - **ワークフロー耐障害性**:
    - `daily-update.yml` / `weekly-self-improve.yml` / `weekly-report.yml` に `concurrency` を追加（同時実行による push 競合防止）。
    - `git push` 失敗時に Discord へ警告通知（rebase コンフリクトの黙殺を防止）。
    - `weekly-report.yml` の権限を `contents: write` → `contents: read` に最小化。
  - **スクリプトパス統一**: `add_entry.py` / `rss_fetch.py` / `fill_og_images.py` / `update_status.py` / `check_deepl_quota.py` / `migrate_categories.py` / `translate_staging.py` の CWD 依存パスを `Path(__file__)` 基準に統一。
  - **OG/Twitter メタタグ統一**: `weekly.html` / `weekly-archive.html` / `privacy.html` / `contact.html` の不足メタタグを `index.html` 水準に揃えた。
  - **dead code 整理**:
    - `weekly_self_improve_loop.py`: 未使用の `DEFAULT_GEMINI_MODEL` / `--gemini-model` を削除。
    - `post_to_x.py`: 未使用の `MAX_POSTS_PER_RUN` を削除。
    - `sort_entries.py`: 未使用の `parse_date_for_sort()` 関数と関連定数を削除。
    - `fetch_rss.py`: 旧系統である旨のコメントを先頭に追記。

- **2026-04-20（週間JOI通信: ヘッダー画像を thumbnail に設定）:**

  **内容:**
  - `icons/` に 3 種類のヘッダー画像を追加: `weekly-header-cool.png` / `weekly-header-emotional.png` / `weekly-header-elegant.png`。
  - `scripts/build_weekly_joi_entry.py` に `--header-image <cool|emotional|elegant>` オプションを追加し、`thumbnail` フィールドを自動セット（デフォルト: `cool`）。
  - `.github/workflows/weekly-self-improve.yml` の呼び出しで `--header-image cool` を明示。
  - 画像を変えたいときは `weekly-self-improve.yml` 67 行目の `--header-image` 値を変更するだけで反映される。

  **今後の拡張メモ（RSS マネージャーから操作できるようにしたい）:**
  - RSS マネージャーの UI から「週間 JOI 通信のヘッダー画像」を選択・変更できる機能の追加を予定。
  - 画像を追加アップロードする機能（`icons/` に新画像をコミット、もしくは CDN/GitHub Release への配置）も検討。
  - 画像 URL のリストを `data/weekly_header_images.json` 等に外部化し、RSS マネージャーが読み書きして `build_weekly_joi_entry.py` が参照する構成が想定ライン。
  - 現状は `weekly-self-improve.yml` の `--header-image` 値を手動編集で切り替える運用。

- **2026-04-20（週次セルフインプルーブ: JOI記事生成の耐障害性修正）:**

  **内容:**
  - `scripts/weekly_self_improve_loop.py`:
    - JOI記事生成の `max_tokens` を 4096→8192 に増量（日英 body を含む JSON が途中で切れるのを防止）。
    - `_parse_json_object` を強化: markdown コードフェンス除去、`_repair_json_unescaped_quotes()` でエスケープ漏れダブルクォートの反復修復。
    - JOI パース失敗時もレポート＋提案は正常出力して exit 0 で終了する設計に変更（`joi_raw_debug.txt` にデバッグ用生テキストを保存）。
    - `JOI_SYSTEM` プロンプトに JSON 文字列内の `"` エスケープ必須を明記。
  - `.github/workflows/weekly-self-improve.yml`:
    - JOI ファイル未生成時は Build/Add/Commit ステップを `if: hashFiles(...)` でスキップ。
    - Artifact アップロードを `if: always()` で常時実行（JOI 失敗時もレポートを保全）。
  - **原因:** Opus が `body_ja_markdown` 内で `"山の民"` 等の半角ダブルクォートをエスケープせず出力し、JSON パースが失敗していた。

- **2026-04-18（Perplexity: 内容ベースの primary カテゴリ + 既存データ再分類スクリプト）:**

  **内容:**
  - `scripts/gemini_flash_review.py`:
    - Gemini の `decisions` に **primary_category**（cafe / vtuber / figure / game / anime / other）を必須化。
    - **通過した Perplexity 由来**について `categories` と `tags` をその値で上書き。元の検索バケットは `_category_from_search`、`_category_assigned_by: gemini` を付与。
    - 応答に primary が無い場合は既存カテゴリへフォールバック（`_fill_missing_primary_categories`）。
  - `scripts/recategorize_perplexity_entries.py`（新規）:
    - 公開中 DB の `_source=perplexity` & `active` を対象に、タイトル・説明・URL から **Gemini でカテゴリ再提案**。
    - プレビュー: `data/recategorize_pplx_changes.json` / `data/recategorize_pplx_preview.md` を出力。
    - 反映: `GEMINI_API_KEY` 設定のうえ `python3 scripts/recategorize_perplexity_entries.py --apply` で `entries.json` と `entries_ja.json` を同期更新。
  - **注意:** ローカル／Actions の実行環境に `GEMINI_API_KEY` が無い場合はスクリプトは終了コード 2（手動または Secrets 付きで実行）。
  - **運用:** `.github/workflows/recategorize-perplexity-categories.yml`（手動 `workflow_dispatch`）で Secrets の `GEMINI_API_KEY` を使い再分類→コミットまで実行可能。初回は既定モデル名が API で 404 となる場合があるため、`recategorize_perplexity_entries.py` 側で `gemini-2.5-flash-lite` → `gemini-1.5-flash` にフォールバック。

- **2026-04-16（Perplexity検閲強化: ページ実体チェック + サムネ補正 + 却下ログを週次集計）:**

  **内容:**
  - `scripts/gemini_flash_review.py` を強化（Perplexity由来のみ）:
    - URL先ページを取得して `page_title` / `published_date` / `og_image` を抽出し、`_url_verified` として候補に付与。
    - 事前フィルターで **内容取り違え（title_ja と page_title が噛み合わない）** を却下。
    - `published_date` が取れていて **古すぎる記事**（既定 14日超、`JOI_PPLX_MAX_ARTICLE_AGE_DAYS` で調整可）も却下。
    - `og_image` が取れた場合、`thumbnail` が空/汎用なら **og_imageに差し替え**。取れずサムネも弱い場合は却下。
    - dry-run でも prefilter が効くようにして、落ちるべきものが落ちるか確認しやすくした。
    - 検閲ログ `*.review_log.json` に `url_status/final_url/page_title/published_date/og_image` を含めて可観測性を上げた。
  - `daily-update.yml`:
    - `data/staging/perplexity_*.review_log.json` を `data/review_logs/YYYYMMDD/` に退避してコミット対象に追加（週次で集計するため）。
  - `scripts/weekly_self_improve_loop.py`:
    - `data/review_logs` を集計して `stats.review_logs` に追加し、週次レポートで「却下理由トップ」等が解釈材料になるようにした。

- **2026-04-15（X投稿: 週刊リンクが相対URLになる不具合を修正）:**

  **内容:**
  - `scripts/post_to_x.py` に `normalize_public_url()` を追加。
  - `source.url` が `/weekly.html?...` の相対URLでも、`https://otaku.eidosfrontier.com/` 基準で **絶対URL化**して投稿するよう修正。
  - `http/https` 以外の不正URLは `SITE_URL` へフォールバック。

- **2026-04-15（原因究明 + GeminiFLASH検閲強化 + 再発防止ガード）:**

  **原因（今回の404/偽URL混入）:**
  - 検閲フローが「文面妥当性」中心で、**Perplexity由来URLの実在性（HTTP 200）を機械的に担保していなかった**。
  - そのため、もっともらしいURL文字列（例: `prtimes ... 000001234.000012345`、`natalie ... /1234567`）が Gemini 判定をすり抜ける余地があった。

  **対策（実装済み）:**
  - `scripts/gemini_flash_review.py`
    - Perplexity由来候補に対し、Gemini判定前の **URL疎通チェック（GET, redirect追跡, 200必須）**を追加。
    - 非200/疎通失敗は prefilter で即却下（`reason_ja` に HTTP ステータスを記録）。
    - Geminiへ渡すコンテキストに `source_type/source_id/source_domain` を追加し、判定材料を強化。
    - `REVIEW_SYSTEM` に「`url_status != 200` は必ず却下」を明記。
  - `scripts/add_entry.py`
    - 最終投入ゲートとして、Perplexity由来URLの **実在チェックを再実施**（二重ガード）。
    - 非200は `SKIP (source unreachable)` で登録拒否。

  **補足:**
  - URLチェックは Perplexity由来に限定（RSS系は403等が正常運用で起こり得るため）。

- **2026-04-15（再検証: 2026-04-14 Perplexity投入分の404大量混入を修正）:**

  **内容:**
  - 画面再現に基づき、`id` が `*-202604142012-pplx-*` の投入群を全件再検証。
  - 初回調査で「PRTIMES/にじさんじ再現せず」としたが、**対象絞り込み不足**だった。再検証で以下を確認。
    - 404（削除）: anime 4件 / figure 2件 / vtuber 3件（計9件）
      - `anime-202604142012-pplx-1fd813`
      - `anime-202604142012-pplx-2046d8`
      - `anime-202604142012-pplx-3949fb`
      - `anime-202604142012-pplx-4a7b41`
      - `figure-202604142012-pplx-48ba4b`
      - `figure-202604142012-pplx-c5f8ac`
      - `vtuber-202604142012-pplx-3317df`
      - `vtuber-202604142012-pplx-4d8888`
      - `vtuber-202604142012-pplx-f01716`
    - 200（残し・サムネ修正）:
      - `figure-202604142012-pplx-818870`（Good Smile）: `notop_catch` 画像 → og:imageへ差し替え
      - `figure-202604142012-pplx-0350c6`（AmiAmi）: `like_on.png` → og:imageへ差し替え
  - `entries_ja.json` を再生成。

- **2026-04-14（リンク/サムネ異常の調査と緊急クリーンアップ）:**

  **内容:**
  - 依頼対象（あみあみ / コトブキヤ / グッスマ / PRTIMES / にじさんじ）を `entries.json` で機械検証。
  - 実測結果:
    - **再現あり**: `figure-202604111942-pplx-e17de0` のコトブキヤURLが **404**（Perplexity由来URL）。
    - **再現あり**: 今日分あみあみ3件が `thumbnail` なし（`news.amiami.jp` 側が Cloudflare 403 で本文取得不可。RSSにも画像メタがなく補完不能）。
    - **再現せず**: PRTIMES（18件）・nijisanji URL（3件）は今回のHTTP検証では非200なし。
  - 対応:
    - 直らない4件を削除（下記ID）。
      - `figure-202604132020-rss-6c9537`
      - `figure-202604132020-rss-491e8e`
      - `figure-202604132020-rss-0295ce`
      - `figure-202604111942-pplx-e17de0`
    - `entries_ja.json` を再生成。
  - 補足（再発対策案）:
    - PPLX由来URLは add前に200検証して、404は自動除外。
    - `amiami-news` は画像メタがないため、403が続く間は「サムネ必須運用」か「プレースホルダー許容運用」を明示して選ぶ。

- **2026-04-14（entries.json: [未翻訳] マーカー 11 件の除去）:**

  **内容:**
  - 週次レポートの `untranslated_marker_entries` 対象だった **title/description 先頭の `[未翻訳]`** を `scripts/strip_untranslated_markers_entries.py` で一括除去。
  - `description` が `[未翻訳] ` のみで空になっていた件は **英語 title を description に流用**。
  - `data/entries_ja.json` を `build_ja_entries.py` で再生成。

- **2026-04-14（週次ループ: Opus で統合解釈 + カレンダー運用）:**

  **内容:**
  - 補足: 当初 Sonnet を先にしていたのは **API 疎通テストで Opus を無駄にしたくなかった**ため。本番の統合解釈は **Opus 4.6 系**が前提。
  - `REPORT_SYSTEM` / `CLAUDE_SYSTEM`: チャネル横断の統合と、週報を Perplexity 検索意図のヒントに使う旨を追記。
  - JOI の `ensure_joi_english_fields` は **Sonnet 固定**（英語補完のみ）。
  - `resolve_weekly_llm_order`: **2026-05-31 まで（JST）は Opus 先（基準観測）**。**2026-06-01 から**は **偶数月 Sonnet 先 / 奇数月 Opus 先**で品質比較。`ANTHROPIC_WEEKLY_LLM_ORDER` または `--weekly-llm-order` で上書き可。`llm_trace.json` に理由タグを記録。Actions は未設定時カレンダーに任せる（`--weekly-llm-order` は渡さない）。

- **2026-04-14（集客・SEO: 正規URL統一 + サイトマップ + 構造化データ + Xリンク）:**

  **内容:**
  - 本番ドメインは `otaku.eidosfrontier.com` だが、`index` / `about` / `contact` / `privacy` の **canonical・OG・Twitter 画像**が `eidosfrontier.com` ルートや旧 GitHub Pages を指していたため **サブドメインに統一**。
  - `sitemap.xml` を同ドメインに統一し、`weekly.html` / `weekly-archive.html` / `contact` / `privacy` を追加。`robots.txt` の Sitemap 宣言を更新。
  - `index.html` に **WebSite 型 JSON-LD**（Schema.org）を追加。
  - `weekly.html` / `weekly-archive.html` に description・canonical・OG 最低限を追加。
  - `post_to_x.py` の `SITE_URL` を本番に合わせ、VTuber 第2タグを `#Hololive` → **`#VTuberEN`**（英語圏リーチ寄りの暫定。好みで戻し可）。
  - `README.md` の公開URL表記を更新。

- **2026-04-14（ロードマップ「現在地」同期 + データ更新要約の修正）:**

  **内容:**
  - `ROADMAP_LATEST.md` の §2〜§5 を **2026-04-14 時点のリポジトリ**に合わせて更新（週刊JOI・About・`entries_ja`・日次 Gemini 検閲接続・件数目安・AdSense 方針・優先度の言い換え等）。※当ファイルは `.gitignore` のため GitHub には乗らない。
  - 本ファイルの **「データ更新まわりの現状」表**を、古かった「Perplexity オフ／Gemini 未接続」記述から **`daily-update.yml` 実態**に修正。

- **2026-04-14（プロダクト戦略・横展開方針の文書化）:**

  **内容:**
  - 対話で整理した「JOIのコア定義」「傘下コンテンツ vs 別ドメイン」「1サイト1リポ・Secrets運用」「ルートドメイン総合ハブ＋リポ分割」「週刊まとめの価値」「テンプレ化・RSS Manager多サイト構想」「AdSense前提」を `HANDOVER.md`（本節の上の表）と `ROADMAP_LATEST.md`（新設 §9）に追記。
  - 実装変更なし。判断軸の記録のみ。

- **2026-04-13（About統計の動的化 + メニュー統一 + パイプライン表示）:**

  **背景:**
  - Aboutページの統計値が固定値のままで更新反映されない。
  - About末尾に自動化パイプライン状態を簡易表示したい。
  - スマホ/タブレット向けメニューで Weekly Archive 項目がページごとに欠落していた。

  **対応:**
  - `js/about.js` を新規追加し、`/data/entries.json` と `/data/sources.json` から About の統計値を動的更新。
    - Entries、RSSソース数、カテゴリ数、ソース総数を実データで表示。
    - About下部に `Automation Snapshot` を追加し、最終同期時刻・有効/停止ソース数・主要パイプライン状態を表示。
  - `about.html` の統計・Data Sources表記を動的差し込み用に更新（固定数値を廃止）。
  - ナビ統一:
    - `contact.html` / `privacy.html` のPCナビ・モバイルメニューに `Weekly Archive` を追加。
    - `weekly.html` / `weekly-archive.html` にハンバーガーメニュー一式（overlay/menu）を追加し、`menu.js` を読み込み。
  - `sw.js` を `v16` に更新し、`js/about.js` をキャッシュ対象へ追加。

- **2026-04-13（Amazonアソシエイト導線を最小実装）:**

  **背景:**
  - 「邪魔にならない場所でAmazonアソシエイトを付けたい」という要望に対応。
  - AdSense設定は既存運用を維持し、追加変更しない方針。

  **対応:**
  - `js/render.js` に Amazon 検索URL生成を追加（モーダル表示中の記事タイトルを検索語に利用）。
  - 記事モーダル最下部に、控えめなテキストリンクを追加:
    - JA: `Amazonで関連商品を見る`
    - EN: `Find related items on Amazon`
  - `window.AMAZON_ASSOCIATE_TAG` が設定されている場合は `tag` をURLへ付与。
  - `css/style.css` に小型リンク用の `modal-affiliate-link` スタイルを追加。
  - `sw.js` のキャッシュバージョンを `v13` に更新して配信反映を安定化。
  - 追加調整: StoreID `eidosfrontier-22` を `js/render.js` に既定値として設定。`window.AMAZON_ASSOCIATE_TAG` がある場合のみ上書き。
  - 追加調整: モーダルのAmazonリンク先を、指定の固定アソシエイトURLへ統一（記事ごとの検索URL生成はフォールバック扱い）。
  - キャッシュ更新: `sw.js` を `v14` へ更新。
  - 追加調整: 固定URL運用を取りやめ、記事タイトル + カテゴリヒント（figure/game/anime 等）からAmazon検索語を自動生成する方式に再変更。
  - キャッシュ更新: `sw.js` を `v15` へ更新。

- **2026-04-13（週刊ページ「サイトに戻る」文言をEN時に英語化）:**

  **背景:**
  - `weekly.html` の戻るリンク文言が日本語固定で、EN表示時も `サイトに戻る` のままになっていた。

  **対応:**
  - `weekly.html` の戻るリンクに `id="backToSiteLink"` を付与。
  - `js/weekly.js` で `otaku_lang` に応じて文言を切替:
    - JA: `サイトに戻る →`
    - EN: `Back to Site →`
  - `sw.js` のキャッシュバージョンを `v12` に更新し、即時反映しやすくした。

- **2026-04-13（EN週刊本文が短文化する問題を恒久修正）:**

  **背景:**
  - EN版の `article_markdown_en` が、本文ではなく `summary_en` 相当の短文で保存されるケースが残っていた。
  - 判定条件が「空か日本語混入か」だけだったため、英語短文が正常扱いされていた。

  **対応:**
  - `scripts/weekly_self_improve_loop.py` に `body_en_markdown` の品質判定を追加:
    - 700文字未満
    - `summary_en` と同一
    - Markdown見出し数が不足（<3）
    上記いずれかを「本文不足」と見なし、英語本文を再生成するよう修正。
  - `scripts/build_weekly_joi_entry.py` に同等の判定を追加し、変換段階でも短文EN本文を補完対象化。
  - Google翻訳フォールバックの失敗判定を改善し、固有名詞由来の少量日本語を許容（本文の大半が日本語のときのみ失敗扱い）。
  - 既存データの最新週刊記事について `article_markdown_en` を長文本文へ再補完（`entries.json` / `entries_ja.json`）。

- **2026-04-13（Antigravity納品ヘッダー画像を週刊記事へ反映）:**

  **内容:**
  - Antigravity納品の3画像を `assets/weekly-headers/` に取り込み:
    - `otaku_header_cool_editorial_1776085572240.png`
    - `otaku_header_emotional_energy_1776085587532.png`
    - `otaku_header_simple_elegant_1776085601859.png`
  - 最新週刊記事（`otaku-news-202604132128-joi-cdc70c`）の `thumbnail` に案1（クール）を設定。
  - 併せて `weekly_header_candidates` に3案のパスを保存（差し替え運用用）。
  - `sw.js` を `v11` に更新し、上記3画像をキャッシュ対象へ追加。

- **2026-04-13（EN週刊表示の日本語混入を追加修正）:**

  **背景:** EN表示時、週刊モーダルが `summary_ja` を優先していたため日本語が表示されるケースが残っていた。加えて、週刊生成時に `body_en_markdown` が欠落/日本語混入したまま残る場合があった。

  **対応:**
  - `js/render.js`  
    週刊カードのモーダル要約を `localStorage.otaku_lang` に応じて出し分け（EN時は `summary_en` 優先）。
  - `scripts/weekly_self_improve_loop.py`  
    `ensure_joi_english_fields()` を追加。`summary_en` / `body_en_markdown` が欠落または日本語混入時は、Anthropicで英訳補完してから出力。

- **2026-04-13（週刊記事 EN で日本語本文が出る問題を修正）:**

  **不具合:** `article_markdown_en` に日本語が混入したまま保存されるケースがあり、EN表示でも本文が日本語になることがあった。

  **対応:**
  - `scripts/build_weekly_joi_entry.py`  
    EN本文フォールバック生成時、英訳結果に日本語が残る場合は無効化し、`summary_en` へフォールバックするよう変更。
  - `js/weekly.js`  
    EN表示時に本文へ日本語が混入していた場合、`summary_en` を優先表示するガードを追加。
  - 既存データ修復  
    既存 `joi-weekly` の `article_markdown_en` を検査し、日本語混入分を `summary_en` ベースへ補正。

- **2026-04-13（週刊記事アーカイブ機能を追加）:**

  **要望:** 新週刊を出すと過去週刊が消える方式ではなく、過去記事を見返せる「まとめページ」を用意したい。

  **対応:**
  - `scripts/add_entry.py`  
    `joi-weekly` 追加時に旧記事を削除しないよう変更。旧週刊は `pinned_top=false` + `_weekly_archived=true` にし、新週刊のみ `pinned_top=true`。
  - `weekly-archive.html` / `js/weekly-archive.js` を新規追加。  
    `joi-weekly` 記事を日付順で一覧表示し、各記事へ `/weekly.html?id=...` で遷移可能。
  - `index.html` / `about.html` / `weekly.html` のナビに `Weekly Archive` を追加（モバイルメニュー含む）。
  - `sw.js` を `v10` に更新し、`weekly-archive.html` / `js/weekly-archive.js` をキャッシュ対象へ追加。
  - 既存データ調整: 過去週刊2件をアーカイブとして再登録し、現在は週刊3件（最新1件+過去2件）を保持。

- **2026-04-13（週刊記事が表示されない/旧記事残留/英語不足/見出し画像不足への緊急修正）:**

  **不具合:**
  - `joi-weekly` が旧形式データ（`source: {}`・`article_markdown_*`なし）のまま残り、`weekly.html` 遷移や新表示仕様に乗っていなかった。
  - 週刊記事が複数残って過去のKPI調記事が上位表示されるケースがあった。
  - 英語表示時に本文が不足しやすかった。
  - 見出し画像が未設定時に代替情報がなかった。

  **対応:**
  - `scripts/add_entry.py`  
    `joi-weekly` を追加するときは旧 `joi-weekly` を先に除去して**最新1件に置換**するよう変更。
  - `scripts/weekly_self_improve_loop.py`  
    JOI出力JSONに `body_en_markdown` と `header_image_prompt_en` を追加要件化。
  - `scripts/build_weekly_joi_entry.py`  
    `article_markdown_en` / `header_image_prompt_en` を entries に保存。画像プロンプト未指定時はデフォルト文を設定。
  - `js/weekly.js` / `weekly.html` / `css/style.css`  
    EN/JP切替に応じて本文表示を切替（`article_markdown_en` 優先）。  
    見出し画像（thumbnail）があれば表示、なければ `header_image_prompt_en` を注記表示。
  - `sw.js`  
    キャッシュ名を `v9` に更新（週刊ページUI修正を確実反映）。
  - 既存データ修復  
    旧 `joi-weekly` を最新1件へ差し替え、`source.url=/weekly.html?id=...`、`article_markdown_ja/en`、`header_image_prompt_en` を補完。

- **2026-04-13（JOI通信を「ヲタ向けホットニュース」寄りに再修正）:**

  **背景:** 週間JOI通信が運用KPI寄りになり、読者が読みたい「今週アツかった話題」中心の紙面になっていなかった。

  **対応 (`scripts/weekly_self_improve_loop.py` / `weekly-self-improve.yml`):**
  - `JOI_SYSTEM` を再強化し、以下を必須化:
    - KPI解説ではなく週刊かわら版として執筆
    - アニメ/ゲーム、フィギュア/グッズ、イベント/コスプレの3系統を必ず含める
    - 具体トピック5件以上を紹介
    - KPI（PV減など）を本文主役にしない
  - JOI生成入力の優先順を変更:
    1. 直近記事サンプル（最優先）
    2. Perplexity週次ハイライト（補助）
    3. 週次分析レポート（参考）
  - Perplexity補助取得 `fetch_perplexity_weekly_highlights()` を追加（キー未設定時は自動スキップ）。
  - `weekly-self-improve.yml` に `PERPLEXITY_API_KEY` / `PERPLEXITY_MODEL` を env で追加し、Actions から補助ハイライトを使えるようにした。

- **2026-04-13（JOI記事の別ページ化 + 検閲すり抜け対策 + 空/粗悪記事クリーンアップ）:**

  **背景:** JOI通信がモーダル内で長文表示され、読者向けの「記事ページ」になっていなかった。加えて、Perplexity由来のランディングURL記事や空欄記事が混入していた。

  **対応:**
  - **JOI記事を別ページ化**
    - `weekly.html` / `js/weekly.js` を新規追加。
    - `scripts/build_weekly_joi_entry.py` で JOIエントリに `article_markdown_ja` と `summary_*` を保存し、`source.url` は既定で `/weekly.html?id=<entry_id>` を設定。
    - `js/render.js` で `joi-weekly` のときはモーダルに本文を直載せせず、`Read Weekly Article` ボタンで別ページへ遷移。
  - **検閲すり抜け対策**
    - `scripts/gemini_flash_review.py` に事前フィルタを追加（タイトル空 / 説明空 / URL不正 / PerplexityトップURL / ランディングURL疑い）。
    - `scripts/perplexity_search.py` でも staging 化前にトップ/浅いURLを除外。
    - `scripts/add_entry.py` 側にも title/description 空チェックと、PerplexityランディングURL弾き（深さチェック）を追加。
  - **実データ掃除**
    - `data/entries.json` から 4件削除（Perplexityランディング3件 + title空1件）。
    - `scripts/build_ja_entries.py` を再実行して `data/entries_ja.json` を再生成し、件数同期（3133件）。
  - **PWA反映**
    - `sw.js` のキャッシュを `v8` に更新し、`weekly.html` / `js/weekly.js` をキャッシュ対象へ追加。

- **2026-04-13（JOI通信の生成方針を「運用レポート」から「ヲタ向け週刊かわら版」へ修正）:**

  **背景:** 週間JOI通信が、運用KPI（アクセス減・件数等）の説明に寄りすぎており、読者向けの「今週アツかったヲタニュースまとめ」になっていなかった。

  **対応 (`scripts/weekly_self_improve_loop.py`):**
  - `JOI_SYSTEM` を全面改訂し、以下を明示:
    - KPIレポートではなく、ヲタ向けの週刊かわら版として執筆
    - 直近話題を中心に、最低5件以上の具体トピック（作品名/イベント名）を含める
    - 数字は補足に留め、最後に「来週の注目ポイント」を入れる
  - 新関数 `collect_recent_hot_topics()` を追加し、直近7日（可変）の記事見出しサンプルを抽出
  - JOI生成時の入力に、週次統計だけでなく **直近記事サンプルJSON** を追加  
    （モデルが実際の話題を拾って記事化できるようにする）

  **狙い:** 「運用報告」ではなく、読者が読みたい「今週のホットなヲタニュース振り返り」を安定生成する。

- **2026-04-13（週次停止・空記事増加対策: 検閲強制化 / Opus観測ログ / 低品質URL遮断）:**

  **背景:** 週次レポートが止まって見える状態と、サイトトップに「中身の薄い記事（トップURL系）」が混入する状態を再調査。ローカルのスモークテストで `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` が未設定時に、既存実装が「成功扱いで進む」箇所を確認。

  **対応:**
  - `scripts/gemini_flash_review.py`  
    `--missing-key-policy` を追加（`reject` / `pass` / `error`、既定 `reject`）。  
    キー未設定時でも **判断ログを必ず出力**し、`reject` では未審査記事を全件却下して pass-through を防止。
  - `.github/workflows/daily-update.yml`  
    Gemini 検閲呼び出しに `--missing-key-policy reject` を追加。キー欠落時に Perplexity staging を通し込まない構成へ。
  - `scripts/weekly_self_improve_loop.py`  
    `--require-anthropic` を追加。キー未設定を成功扱いにせずエラー終了可能に。  
    併せて `llm_trace.json` を出力し、Sonnet/Opus の試行・フォールバック挙動を可視化。  
    API未接続時の `claude_prompt_proposals.json` は空 `{}` ではなく、保守的な Perplexity 検索ワード案を出すよう変更。
  - `.github/workflows/weekly-self-improve.yml`  
    週次実行を `--require-anthropic` 付きに変更し、Secrets欠落を即時検知。
  - `scripts/add_entry.py`  
    Perplexity 由来の `https://.../`（root/top/index）など低品質ソースURLを追加時に遮断。

  **確認ログ（ローカル再現）:**
  - `verify_api_keys.py` で Gemini / Anthropic / GA4 / YouTube すべて未設定を確認。
  - `gemini_flash_review.py` 実行時、`reason_ja: GEMINI_API_KEY 未設定のため未審査で却下` が全件に付与されることを確認。
  - `weekly_self_improve_loop.py --require-anthropic` 実行時、`exit 2` と `llm_trace.json`（`error: missing ANTHROPIC_API_KEY`）を確認。

- **2026-04-11（Discord週次の文字切れ修正・日次GA4メッセージ明確化・Shorts取得の試行順改善）:**

  **背景:** 週次通知が Discord の **content 2000文字上限**で途中欠落していた。日次は GA4 が Secrets 未設定でも「おかしい」ように見えた。Shorts は `day,videoType` ディメンションが環境によって拒否されることがある。  
  **対応:** `notify_discord_weekly.py` で本文を **embed description（最大約4000文字）**に載せ、結合が長いときは **2回 POST** に分割。`daily_analytics_to_discord.py` で GA4 不足時に **どの Secrets が要るか**を注記に明示。`analytics_clients.py` の Shorts 取得で **`day` のみ＋フィルタ**を先に試すよう試行順を追加。

- **2026-04-09（GA4+YouTube 日次通知ラインをDiscordへ追加）:**

  **内容:** `scripts/analytics_clients.py`（新規）で GA4 / YouTube のAPI呼び出しを共通化。`scripts/daily_analytics_to_discord.py`（新規）で **前日 vs 前々日**の差分を集計し、`DISCORD_WEBHOOK_URL` へ日次通知するラインを追加。  
  `daily-update.yml` に `Notify daily analytics to Discord` ステップを追加し、毎日 19:00 JST の更新後に同じDiscordへ投稿する。指標は **GA4（ユーザー/セッション/PV）+ YouTube（視聴回数/総再生時間/登録者増減/Shorts再生数）**。  
  Shorts 指標は API 仕様差で取れない環境があるため、0埋めせず **「取得不可」** と通知するガードを実装。GA4/YouTube のどちらかが欠けても通知全体は送る（注記に理由を表示）。

- **2026-04-09（週次レポートをSonnet優先へ切替）:**

  **内容:** `weekly_self_improve_loop.py` を更新し、週次生成のモデル優先順を **Sonnet -> Opus** に変更。`ANTHROPIC_SONNET_MODEL` を追加（未設定時は既定値）。失敗時は Opus へ自動フォールバック。  
  併せて `notify_discord_weekly.py` を更新し、通知本文を **週報要約（3点）+ 改善案要約 + 実行URL** の形式へ整理。

- **2026-04-09（JOI自動改善ループを本接続）:**

  **内容:** 日次 `daily-update.yml` で **Perplexity 検索 → Gemini 3.1 Flash Lite 検閲 → 翻訳** の順に再接続。`scripts/gemini_flash_review.py` は 3.1 Lite を既定にし、`2.5-flash-lite` / `1.5-flash` へ自動フォールバック。  
  週次 `weekly-self-improve.yml` は **GA4 + 内部データ集約**を `weekly_self_improve_loop.py` で実施し、`Opus 4.6`（`ANTHROPIC_OPUS_MODEL`）で週次分析レポートを生成。Perplexity 検索ワード改善案は引き続き **Artifact のみ**で出力（自動反映しない）。  
  さらに `build_weekly_joi_entry.py` を新設し、Opus が作成した JOI 通信素材を `entries` 追加用JSONへ変換。週次ワークフローで `add_entry.py` → `sort_entries.py` → `build_ja_entries.py` → commit/push まで自動化。`pinned_top: true` を導入し、`sort_entries.py` / `js/render.js` で最上位表示を優先する。

- **2026-04-09（週次改善案のDiscord通知を追加）:**

  **内容:** `scripts/notify_discord_weekly.py` を追加し、`artifact-out/claude_prompt_proposals.json` と `weekly_report_ja.md` の要点を Discord Webhook に投稿する機能を実装。  
  `weekly-self-improve.yml` に通知ステップを追加し、`DISCORD_WEBHOOK_URL`（任意）を設定すると毎週の改善案サマリが自動通知される。未設定時は「通知スキップ」で終了し、週次本体ジョブは止まらない設計。

- **2026-04-09（Gemini 検証モデルを Flash Lite 優先に変更 + 自動フォールバック）:**

  **内容:** `verify_api_keys.py` / `weekly_self_improve_loop.py` の Gemini 既定を `gemini-3.1-flash-lite` に変更。モデル名差異や提供状況の揺れで 404 が出た場合に備え、`gemini-2.5-flash-lite` → `gemini-1.5-flash` の順に自動フォールバックするよう更新。Secrets 側で `GEMINI_MODEL` を空/未設定にしても既定値へフォールバックするため、手入力ミスで検証が止まりにくい構成にした。

- **2026-04-09（Anthropic 既定モデルを Haiku 4.5 に更新）:**

  **内容:** `weekly_self_improve_loop.py` と `verify_api_keys.py` の `ANTHROPIC_MODEL` 既定値を `claude-haiku-4-5-20251001` に変更。`weekly-self-improve.yml` / `verify-api-secrets.yml` で `secrets.ANTHROPIC_MODEL` を環境変数として受け渡すよう統一。

- **2026-04-09（Secrets 接続確認用のスモークテスト追加）:**

  **内容:** `scripts/verify_api_keys.py` を追加。`GEMINI_API_KEY`、`ANTHROPIC_API_KEY`、`GA4_CREDENTIALS_JSON`（+ `GA4_PROPERTY_ID` 任意）、`YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET`/`YOUTUBE_REFRESH_TOKEN` をまとめて接続確認できる。`Verify API Secrets`（`.github/workflows/verify-api-secrets.yml`）を手動実行すると、各APIの最小疎通（副作用なし）をチェックし、失敗箇所をログで特定できるようにした。

- **2026-04-08（翻訳品質ガードレールの実装: 未翻訳記事の公開防止）:**

  **背景:** 日次パイプラインにおいて、Google翻訳が失敗または不備である場合に `[未翻訳]` プレースホルダが残ったまま記事が本番 DB（`entries.json`）に登録される事象が発生していた。また `build_ja_entries.py` の英語フォールバックにより、日本語ページに英語（プレースホルダ）が表示される事象も確認された。

  **対応:**
  - `scripts/add_entry.py`: `has_untranslated_marker()` 関数を追加。`title` または `description` が `[未翻訳]` で始まる記事は登録をスキップし、ログに `SKIP (未翻訳)` と出力するように変更。これにより翻訳未完了の記事が本番に流れるルートを物理的に遷断。
  - `scripts/build_ja_entries.py`: `title_ja` が欠落して英語フォールバックになる場合、健全性チェックを追加。`[未翻訳]` マーカありの場合は `[WARN]` ログを出力し、ビルド時に問題を可視化。フォールバック件数・未翻訳件数のサマリも追加。

- **2026-04-06（X 自動投稿: 英語ツイートの二重日本語防止 / PR #1 相当）:**

  **内容:** [PR #1](https://github.com/itibo3/Japan-OTAKU-Insider/pull/1)（`fix-x-post-untranslated`）をレビューし、`scripts/post_to_x.py` に **英語投稿時、`title` にひらがな・カタカナ・漢字が残っている場合は英語ポストのみスキップ**する処理を取り込み。日本語ポストは従来どおり。リモートの `main` より先行していた auto-update コミットのため **rebase 後に `main` へ push**（コミット `41e675a`）。GitHub 上の PR はブランチ SHA が一致しないため **手動で Close する必要がある**場合あり。

- **2026-04-04（コラボカフェタブ汚染の修正: amiami の誤タグ付け）:**

  **原因:** `data/sources.json` の `amiami-news` が `categories` に `figure`, `cafe`, `event` を並べており、`rss_fetch.py` が**ソースの全記事に categories 配列をそのまま付与**するため、フィギュア記事まで **Collab Cafe タブに表示**されていた（当時 47 件は `_source_id: amiami-news` のみ）。

  **対応:** `amiami-news` から **`cafe` を削除**（`figure`, `event` のみ）。将来混入防止のため `animatetimes` からも `cafe` を削除、`eeo-media` は混在フィードのため **`otaku-news` のみ**に整理。`entries.json` / `entries_ja.json` から該当 amiami 記事の `cafe` を除去。`rss_fetch.py` に **複数 categories の意味**をコメントで明記。PWA キャッシュ `sw.js` を **v7** に更新。

- **2026-04-04（週次 自動改善ループ実装: Gemini Flash レポート → Claude で perplexity ワード改善案）:**

  **内容:** `scripts/gemini_flash_review.py` で staging（Perplexity 出力の配列 JSON）を **Gemini** に検閲させ通過分だけ残せる。`scripts/weekly_self_improve_loop.py` が `entries.json` を集計 → **Gemini** で週次レポート（日本語 MD）→ **Claude** に渡し `perplexity_*.md` 相当の **1行キーワード改善案を JSON** で生成。`.github/workflows/weekly-self-improve.yml` で週1＋手動実行、**Artifact に成果物**（`prompts/` への自動コミットはしない）。`daily-update.yml` に Perplexity 再有効化時の検閲例をコメント追記。`prompts/update_workflow.md` に運用手順を追記。

- **2026-04-04（Perplexity 記事の全削除・日次パイプラインからの除外・キャッシュ更新）:**

  **原因:** 日次 `daily-update.yml` の Perplexity ステップが毎回 `pplx` 記事を staging 経由で `entries.json` に再投入していた。実在ドメインのトップURLに幻覚本文を紐づけるため、URL 必須チェックだけでは防げない。

  **対応:** `data/entries.json` / `entries_ja.json` から **`_source: perplexity` / id に `-pplx-` を含む行を全削除**（当時 19 件）。**`daily-update.yml` の Perplexity ステップをコメントアウト**（再発止め）。`perplexity_search.py` は **URL 空なら `to_entry` で捨てる**＋出力前にも URL なしを SKIP。`sw.js` の **`CACHE_NAME` を v6 に更新**（PWA が古い `entries.json` を掴み続けないため）。`render.js` の **`other` カテゴリ表示を「Other topics」に**（CSS の uppercase で単独 `OTHER` になりにくくする）。

- **2026-04-03（Perplexity 由来の幻覚・不審記事の削除と main への反映）:**

  **対応内容:** `data/entries.json` / `entries_ja.json` から Perplexity 由来（`pplx` ID）の不審エントリ **37 件**を削除。`scripts/perplexity_search.py` のシステムプロンプトを厳格化（既存コミット内容をリベースで取り込み）。リモートの `chore: auto-update entries` 系コミットと競合したため、`origin/main` 最新をベースに同一 37 ID を再削除してから `git push` 済み（コミット `0fff527`）。

- **2026-04-02（外部 HTML/RSS 取得の User-Agent 統一）:**

  **対応内容:** news.amiami.jp / goodsmile 等で Cloudflare 等により `403 Forbidden` となりサムネ取得が失敗する問題への対策として、記事 HTML・RSS・og 取得に使う `User-Agent` を **`Mozilla/5.0 (compatible; Twitterbot/1.0; +http://twitter.com/robots.txt)`** に統一した。

  | 追加・変更 | 詳細 |
  |---|---|
  | `http_fetch_config.py` | リポジトリ直下に新設。`FETCH_USER_AGENT` と `article_fetch_headers()` を定義。 |
  | `scripts/rss_fetch.py` / `fill_og_images.py` | `urllib.request` のヘッダーを上記に統一。`feedparser.parse(..., agent=...)` を指定。 |
  | `scripts/fetch_rss.py` / `_fix_*_thumbs.py` | 同様に統一。 |
  | `rss_manager/rss_finder.py` / `rss_fetcher.py` / `server.py` | HTML 取得・フィードプレビュー・ソース死活チェックの UA を統一。 |
  | 対象外 | X API・DeepL・Perplexity など **認証付き API** へのリクエストは従来どおり（名札偽装の流用なし）。 |

- **2026-04-02 (DeepL API無料枠問題を解消するための新方針):**

  **対応内容:** DeepL APIの無料枠(月間50万文字)の制約が極めて厳しくサイトの運用に支障をきたしていたための、完全移行方針の決定および実装の準備。

  | 決定事項 | 詳細 |
  |---|---|
  | DeepL APIの廃止決定 | `check_deepl_quota.py` などの監視は十分機能しているものの、API自体の文字数制約による根本的な解決にならないため、DeepL APIをパイプラインから完全撤廃する。 |
  | `deep_translator` (Google翻訳) への移行 | 無料かつ文字数制限がない `deep_translator` パッケージ（PythonからのGoogle翻訳APIラッパー）を利用した実装への置き換えを決定。固有名詞などはDeepLよりGoogle翻訳の方が意図通りの英訳が出る傾向もある。 |
  | 実装リレー（Cursor作業へ） | これら翻訳機能の置換に伴うコードの改修は、ユーザー自身が Cursor を用いて実装を行う。これまで活躍した `check_deepl_quota.py` 等はフェードアウト予定。 |

  **同日（引継書メンテ）:** ヘッダーの最終更新日・ステータス（AdSense 却下と改善予定）を反映。技術スタックに GA4 を追記し Phase 3 の Analytics/AdSense 表記を実態に合わせて修正。03-31 の開発ログを独立見出しに分離。「次のセッション」「次の予定」を Google 翻訳移行方針に整合。`entries_ja` の件数は固定数値ではなく `entries.json` 同期の説明に変更。

  **同日（Google翻訳パイプライン実装）:** `scripts/translate_staging.py` を新設（`deep_translator` の `GoogleTranslator`）。`translate_with_deepl.py` は `translate_staging` を呼ぶ互換ラッパ。`daily-update.yml` から `DEEPL_AUTH_KEY` チェックジョブと `check_deepl_quota` を外し、スケジュール実行で常に更新処理が走るように変更。`requirements-ci.txt` に `deep-translator` を追加。`weekly-report.yml` は DeepL CSV 更新を廃止し、総記事数と翻訳方式の案内のみを X DM で送信。

- **2026-04-01（Google 優先＋DeepL フォールバック）:**

  **対応内容:** 日次パイプラインの翻訳を「まず Google、失敗や不備があれば DeepL で再翻訳」に変更。

  | 変更点 | 詳細 |
  |---|---|
  | `translate_staging.py` | 各文字列を Google で個別翻訳。API 失敗・空訳・日英とも日本語っぽいまま・原文と同一（日本語）などを不備とみなし、`DEEPL_AUTH_KEY` がある場合のみその分を DeepL API で再翻訳。キー未設定時は不備があっても Google 結果のまま進み、Google が完全に失敗して訳が空のときだけ exit。 |
  | `daily-update.yml` | Translate ステップに `secrets.DEEPL_AUTH_KEY` を `env` で渡す（未設定ならフォールバックはスキップ）。 |

- **2026-04-01（`entries.json` 未翻訳記事の一括削除と、日次での再取り込み）:**

  **対応内容:** GitHub 上の `data/entries.json` から、英語欄が未整備だった記事 **326 件**を削除（Antigravity / Gemini によるデータ作業）。

  **運用上の意味:** `entries.json` に存在しない URL・記事は、RSS 取得側から見ると **新着** と同等に扱われる。`data/staging/` は `.gitignore` のためリポジトリには載らないが、次回以降の Daily Update（手動・スケジュール）で `rss_fetch.py` 等が該当記事を **staging JSON として再生成**し、`translate_staging.py`（Google 優先＋DeepL フォールバック）→ `add_entry.py` 経由で **再翻訳のうえ `entries.json` に再追加**される想定。**1 回のワークフローですべてが戻るとは限らない**（取得件数上限 `--limit` やソースの都合で複数回に分かれる可能性あり）。

- **2026-03-31 (DeepL枠監視・X連携・週次DMレポート):**

  **対応内容:** DeepL無料枠超過時に発生していた「未翻訳での記事公開」の防止策と、X API連携によるエラー検知・週間レポートのDM自動通知機能を実装。

  | 追加・修正内容 | 詳細 |
  |---|---|
  | `daily-update.yml` 改修 | 翻訳に失敗した一時JSONを `rm -f "$f"` で削除するよう変更。エラー記事は本番に取り込まず消去しておくことで、後日枠復活時にクローラが新規記事として取り直す自然リトライが機能する。 |
  | `check_deepl_quota.py` 新設 | 翻訳開始前にDeepL `/v2/usage` APIで枠を確認し、残り2万文字を下回った場合はエラー終了し翻訳を行わない。また利用実績を `data/deepl_usage_log.csv` に自動追記する。 |
  | `send_x_dm.py` 新設 | 有料X API（Basic以上）の機能を活用し、OTA Insiderの公式から `X_TARGET_USERNAME`（GitHub Secretsに登録した管理者アカウント）へ、直接DMを送信するスクリプト。 |
  | `weekly-report.yml` 新設 | 毎週日曜日の19:00（JST）に、CSVの最新の枠利用状況とサイトの総記事数をDMで報告する定期ジョブ。 |

- **2026-03-27 (ソートバグ修正):**

  **コミット: `ac06fd1`** — "fix: sortByNewestFirst をID登録日時優先に修正（イベント日付→登録日順）"

  **問題:** サイトを更新しても最上位に表示されるカードが変わらなかった。

  **原因:** `js/render.js` の `sortByNewestFirst` 関数が、エントリの「登録日（IDに埋め込まれた日時）」ではなく「イベント・発売日（`dates.display`）」を第一ソートキーとして使っていた。そのため「2026年7月発売」のフィギュア（3月に登録された古いエントリ）が常にトップに居座り続ける問題が発生していた。

  **修正:** `sortByNewestFirst` のソートキーを `idDateFromId(entry.id)`（IDの登録日時）のみに変更。
  ```diff
  - const da = (parseDateForSort(a) || idDateFromId(a.id)).padEnd(12, '0');
  - const db = (parseDateForSort(b) || idDateFromId(b.id)).padEnd(12, '0');
  + const da = idDateFromId(a.id);
  + const db = idDateFromId(b.id);
```

  **IDの日付形式:** `{カテゴリ}-{YYYYMMDDHHMM}-{ソース}-{ハッシュ}` の第2フィールド（8〜12桁）が登録日時。

- **2026-03-27 (EN/JP言語切替機能・パイプライン追加):**
  **コミット: `de28a05`** — "feat: EN/JPトグル実装・entries_ja.json自動生成パイプライン追加"

  | ファイル                                 | 変更内容                                                                             |
  | ------------------------------------ | -------------------------------------------------------------------------------- |
  | `index.html`                         | ロゴ隣に EN/JP スライドトグル追加。JP時に `(JP)` バッジ表示                                           |
  | `css/style.css`                      | `.lang-toggle` / `.lang-badge` / `.header-start` スタイル追加。スマホ対応                    |
  | `js/app.js`                          | 言語切替ロジック。`localStorage` で言語設定を保持。EN→`entries.json`、JP→`entries_ja.json` にfetch切替 |
  | `data/entries_ja.json`               | `title_ja` を `title` に適用した日本語版JSON（件数は `entries.json` と同じ。`build_ja_entries.py` で同期）                    |
  | `scripts/build_ja_entries.py`        | `entries.json` → `entries_ja.json` 生成スクリプト                                       |
  | `.github/workflows/daily-update.yml` | `Update status` 直後に `Build entries_ja.json` ステップ追加                               |
  | `sw.js`                              | v5に更新。`skipWaiting`/`clients.claim`で即時反映。`entries_ja.json` キャッシュ追加               |

  **パイプライン:** RSS取得→DeepL翻訳→entries.json更新→Update status→`build_ja_entries.py`実行→`entries_ja.json`自動生成→両JSONをまとめてgit push
  **切替の仕組み:** ヘッダー左側（タイトル隣）の `[ EN | JP ]` がクリックでカードを切替。`localStorage` で次回も言語を維持。JP時に `(JP)` バッジ表示。
- **2026-03-23 (独自ドメイン移行・AdSense準備・HYPER CANDY FACTORY):**
  **独自ドメイン（otaku.eidosfrontier.com）への移行完了**

  | 作業項目             | 詳細                                                                                                                                                |
  | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
  | Google Form 埋め込み | `contact.html` に Google Form iframeを実装                                                                                                            |
  | AdSense メタタグ追加   | 全HTMLファイル（index/about/privacy/contact）の `<head>` に `<meta name="google-adsense-account" content="ca-pub-7643085059724689">` を追加                   |
  | DNS設定（お名前.com）   | AレコードをGitHub Pages IPアドレス4件に設定。CNAMEで `otaku` → `itibo3.github.io` を設定（当初タイポあり → 修正済み）                                                            |
  | GitHub Pages設定   | Custom domain を `eidosfrontier.com` → `otaku.eidosfrontier.com` に変更                                                                               |
  | コード内URL一括置換      | HTMLファイル・sitemap.xml・robots.txを新ドメインに更新。`js/app.js` の `fetch('/Japan-OTAKU-Insider/data/entries.json')` を `/data/entries.json` に修正（記事が表示されなかった原因） |
  | HTTPS有効化         | GitHub Pages の「Enforce HTTPS」チェックを有効化 ✅                                                                                                           |

  ⚠️ **教訓 (トラブルシュート記録):**
  - ドメイン移行後に記事が全件消えた原因: `js/app.js` の `fetch()` パスが `/Japan-OTAKU-Insider/data/entries.json` のままでapiが 404 を返した。次回のドメイン変更時も必ず **JSファイル内のfetchパス** を確認すること。
  - お名前.comのCNAME VALUE欄で `itibo3.githab.io`（`github` を `githab` とタイポ）した結果、DNS check unsuccessful が1時間以上続いた。入力後は必ず綴りを確認すること。
  **eidosfrontier.com は将来の企業ページ用として確保。サイトはサブドメイン `otaku.eidosfrontier.com` で運用。**
  **HYPER CANDY FACTORY YouTubeチャンネル バナー制作**
  - チャンネルコンセプト: Breakcore / Speedcore / Gabber / Kawaii Hardcore / SUNO楽曲投稿
  - YouTubeバナー画像を生成。ネオンピンク × シアン × ブラックのカワイイカオス系デザイン。
  - バナー保存先: `/home/itibo/.gemini/antigravity/brain/32044b2f-8eb8-4d4f-b7bc-1c10bf272f90/hyper_candy_banner_v2_1774268680962.png`
  **コミット: `9ca4ebc`** — "fix: img タグに referrerpolicy=no-referrer 追加"
  **問題:** 0115765.com（オタク総研）27件のサムネが表示されない（alt テキストのみ表示）。
  - **原因:** Cloudflare のホットリンク保護。リファラー付きリクエストが 403 ブロックされる。リファラーなしなら 200 OK。
  - **修正:** `render.js` のカード・モーダル両方の `<img>` に `referrerpolicy="no-referrer"` を追加。
  - **効果:** 0115765.com 全27件 + 他の同様の保護を持つサイトでもサムネが表示される。
- **2026-03-22 (無効ソースURL Perplexity エントリ14件削除):**
  **コミット: `8a5374e`** — "fix: Perplexity由来の無効ソースURL14件を削除"
  **問題:** Perplexity由来エントリの source URL がサイトトップページ（alter.jp/, goodsmile.info/ja 等）や架空ドメイン（hololive-fan.jp, vtuber-news.jp 等）で、「View Source →」を押しても元記事に辿り着けない。
  - トップページURL: 9件（Alter, Goodsmile, Kotobukiya, Hobbysearch, Amiami, 電撃ホビー）
  - 架空ドメイン: 5件（VTuber系の存在しないドメイン）
  - entries: 554 → 540
- **2026-03-22 (データ品質一括修正: [object Object]・ジェネリックサムネ・nitroplus削除):**
  **コミット: `db614a8`** — "fix: [object Object]表示修正, ジェネリックサムネnull化, nitroplus-blog削除, サムネプレースホルダー追加"
  **修正1: `[object Object]` 表示バグ (195件)**
  - `dates: {}` (空dict) が render.js で `[object Object]` と表示されていた
  - **render.js修正:** `typeof datesRaw === 'object'` チェックを追加、`display` キーがない dict は null 扱い
  - **データ修正:** 195件の `dates: {}` → `dates: null` に一括変換
  **修正2: 残存ジェネリックサムネ (5件 → null化)**
  - Goodsmile `btn_ptop` (2件)、Kotobukiya `ogp_kt.png` (2件)、Alter `menu_bt.png` (1件)
  - ターゲットサイトに正しい og:image がないため null 化
  **修正3: choose_thumbnail() ロジック強化**
  - lead も og も両方ジェネリックの場合、`None` を返すように改善（以前は og をそのまま返していた）
  - `fill_og_images.py` + `rss_fetch.py` 両方を修正
  **修正4: nitroplus-blog 15件削除**
  - disabled 済みソース由来、ブログ記事に og:image なし（apple-touch-icon のみ）
  - entries: 569 → 554
  **修正5: サムネなしカードのUI改善**
  - `css/style.css`: `.card-thumb-placeholder` スタイル追加（📰 アイコン + 点線ボーダー）
  - `render.js`: サムネなし時にプレースホルダー div を表示
  **修正6: .gitignore 整理**
  - `data/*.backup_`* と `.vscode/` を追加
  **残存サムネなし: 12件** — すべてPerplexity由来（トップページURLや架空ドメイン）。プレースホルダー表示で対応済み。
- **2026-03-22 (サムネ取得ロジック改善 + ジェネリック画像35件差し替え):**
  **コミット: `3408e63`** — "fix: サムネ取得ロジック改善 + ジェネリック画像35件を og:image で差し替え"
  **問題:** オタク総研(0115765.com) 27件・電ファミニコゲーマー 4件・natalie 2件・kotobukiya 2件がサイト共通のジェネリック画像をサムネとして表示。
  - **根本原因:** `choose_thumbnail()` が lead 画像（ページ先頭の `<img>`）を常に og:image より優先するロジックだったため、lead がサイトロゴ（SVG等）でもそのまま採用されていた。
  - 0115765.com (オタク総研) の RSS は `sharex.svg`（サイトロゴ）が lead 画像として抽出されていた。
  - 電ファミニコゲーマーは Perplexity 由来で `fill_og_images.py` が同じバグを持つ `choose_thumbnail()` で処理していた。
  **修正内容:**
  1. `choose_thumbnail()` を改善: lead がジェネリック判定された場合、og:image にフォールバック（`fill_og_images.py` + `rss_fetch.py`）
  2. `GENERIC_THUMB_PATTERNS` に `.svg`（SVG拡張子）、`btn_`（ボタン画像）、`/follow_tag`（natalie固有）を追加
  3. 既存43件を一括スキャン → 35件を正しい og:image に差し替え（8件は og なし or 同一でスキップ）
  **今後の効果:** 新規フェッチ時も lead がロゴ/SVG/ボタンの場合は自動的に og:image が優先される。
- **2026-03-22 (animeanime-jp サムネイル修正 45件):**
  **コミット: `0b602d1`** — "fix: animeanime-jp サムネを記事固有の og:image に差し替え (45件)"
  **問題:** animeanime-jp の全記事が同じサムネイル画像を表示（2枚の画像を45件で共有）。
  - RSSフィードが提供する `thumb_l/` 画像はサイト全体で使い回されるジェネリック画像。
  - 実際の記事ページには記事固有の og:image (`ogp_f/` パス) が設定されている。
  **対応:**
  1. `GENERIC_THUMB_PATTERNS` に `animeanime.jp/imgs/thumb_l/` を追加（`fill_og_images.py` + `rss_fetch.py`）
  2. 45件全てのサムネイルを各記事ページの og:image (`ogp_f/`) で差し替え
  3. 差し替え後のユニークサムネ数: 45/45（全件固有画像に置換成功）
  **今後の効果:** 次回RSSフェッチ時も `thumb_l` はジェネリック判定され、自動的に og:image が優先取得される。
- **2026-03-22 (goodsmile/newscast-jp disabled + 記事50件削除 + FREEing偽URL削除):**
  **コミット: `164164d`** — "clean: goodsmile/newscast-jp disabled + 50件削除(newscast46+FREEing4)"
  **問題1: グッドスマイルカンパニー サイトリニューアル**
  - `goodsmile.info` → `goodsmile.com` にリニューアル済み。旧URLは「サイト移転案内ページ」のみ表示。
  - 新サイト（`www.goodsmile.com/ja/`）にはRSSフィードが存在しないことを確認。
  - 対応: `goodsmile` ソースを `disabled: true` に設定。
  **問題2: NEWSCASTが全ジャンルのプレスリリースを垂れ流し**
  - `newscast-jp` は `https://newscast.jp/rss` で全カテゴリのプレスリリースを配信。VTuber専用フィードは存在しない（`?tag=VTUBER` も全件フィードと同内容）。
  - 既存46件の内訳: 市場調査レポート・医療機器・飲料・ドローン等の業界紙が大半。VTuber関連は数件のみ。
  - 対応: `newscast-jp` ソースを `disabled: true` に設定。全46件を entries.json から削除。
  **問題3: FREEing記事のソースURLが実在しないドメイン**
  - Perplexity由来の4件（`freeing.ne.jp`, `freeing.co.jp`, `hobby.search.freeing.ne.jp` 等）がソースURLとして実在しないドメインを持っていた。スクリーンショットで確認された「View Source」がリンク切れ。
  - 対応: 該当4件を entries.json から削除。
  **削除サマリー:**

  | 対象          | 削除件数    | 理由                       |
  | ----------- | ------- | ------------------------ |
  | newscast-jp | 46件     | VTuber絞り込み不可・全ジャンルPR垂れ流し |
  | FREEing偽URL | 4件      | ソースURLが実在しないドメイン         |
  | 合計          | **50件** |                          |

  - entries.json: 619 → **569件**
  **disabled化ソース一覧（累積）:**

  | ID                   | 理由                      |
  | -------------------- | ----------------------- |
  | `gamemakers-jp-feed` | ゲーム開発者向けで読者層に合わない       |
  | `nitroplus-blog`     | 更新頻度が低くコア層向けのみ          |
  | `natalie-news`       | 映画ナタリー（ドラマ・映画・俳優）がメイン   |
  | `goodsmile`          | サイトリニューアルでRSS廃止         |
  | `newscast-jp`        | VTuber専用フィード不存在・全PR垂れ流し |

- **2026-03-22 (映画ナタリー記事削除 + natalie-news を disabled 化):**
  **コミット: `3a99649`** — "config: natalie-news を disabled に変更（コミックナタリーのみ残す）"
  **コミット: `21e2c58`** — "clean: natalie-news(映画ナタリー)の記事41件を削除 + disabled化"
  **背景**: `natalie-news` ソース（映画ナタリー `natalie.mu/eiga/feed/news`）がドラマ・映画・俳優など非オタク系の記事を大量に取り込んでいた。サイトのコンセプトに合わないため、ソースの無効化と既存記事の削除を実施。
  **変更内容:**
  - `data/sources.json`: `natalie-news` に `"disabled": true` を設定。今後 `rss_fetch.py` がスキップする。
  - `data/entries.json`: `_source_id == "natalie-news"` の記事 **41 件を削除**（660 → 619 件）。
    - 削除対象: ドラマ出演情報、映画公開情報、俳優ニュース、写真集発売など映画ナタリー由来の記事全て。
  - コミックナタリー（`natalie-anime`: `natalie.mu/comic/feed/news`）は引き続き有効。アニメ・マンガ系記事はこちらで取得。
  **残存ナタリー系ソース:**

  | ID              | RSS                          | 状態                  |
  | --------------- | ---------------------------- | ------------------- |
  | `natalie-anime` | `natalie.mu/comic/feed/news` | ✅ 有効（コミックナタリー）      |
  | `natalie-news`  | `natalie.mu/eiga/feed/news`  | 🚫 disabled（映画ナタリー） |

- **2026-03-22 (scripts/ フォルダの .gitignore 除外問題を解消 + 未追跡スクリプトを一括 git 追加):**
  **コミット: `44a0330`** — "fix: add all scripts to git tracking, remove scripts/ from .gitignore"
  **問題**: `.gitignore` に `scripts/` ディレクトリ丸ごとの除外ルールが書かれており、その後ろに例外 (`!scripts/rss_fetch.py` 等8件) を列挙する形だった。この設計では例外以外の新しいスクリプトを追加するたびに `.gitignore` を手動で更新しなければならず、管理が煩雑だった。また、すでにローカルに存在していた複数のスクリプトが git 未追跡状態になっていた。
  **修正内容 (`.gitignore`)**:
  - `scripts/` ブロック（`scripts/` + `!scripts/xxx.py` の8行）を **完全削除**。
  - 以降は `scripts/` フォルダ全体が git 追跡対象になる。
  **同時に git 追跡開始したファイル**:

  | ファイル                             | 内容                                                              |
  | -------------------------------- | --------------------------------------------------------------- |
  | `scripts/fetch_rss.py`           | RSS自動取得→JSON変換スクリプト（初期版、feedparser使用）                           |
  | `scripts/migrate_categories.py`  | `category`（単数）→`categories`（配列）への一括マイグレーション                     |
  | `scripts/bulk_fetch.py`          | 空ファイル（プレースホルダ）                                                  |
  | `scripts/translate_4gamer.py`    | 4gamer 記事の手動翻訳適用スクリプト（デッドコード候補）                                 |
  | `scripts/translate_akiba.py`     | akiba-blog 記事の手動翻訳適用スクリプト（デッドコード候補）                             |
  | `scripts/translate_amiami.py`    | あみあみ記事の手動翻訳適用スクリプト（デッドコード候補）                                    |
  | `scripts/translate_final.py`     | nitroplus-blog/dengeki-hobby/prtimes-kotobukiya の手動翻訳（デッドコード候補） |
  | `scripts/translate_natalie.py`   | natalie-anime の手動翻訳適用スクリプト（デッドコード候補）                            |
  | `scripts/translate_nitroplus.py` | nitroplus-news/nitroplus-goods の手動翻訳（デッドコード候補）                  |
  | `scripts/update_category.py`     | 4gamer の category を 'game' に更新するスクリプト                           |

  ⚠️ `translate_*.py` 系5ファイルは現在の DeepL 自動翻訳パイプラインでは使われていないデッドコード（手動翻訳時代の遺物）。`ROADMAP_LATEST.md` で `scripts/legacy/` への移動タスクとして記録済み。

---

- **2026-03-22 (ng_keywords 強化 + sources.json 設定整備 + Perplexity 除外ドメイン拡張):**
  **コミット: `29843fa`** — "feat: ng_keywords強化・4gamerカテゴリ修正・moguravr追加・nitroplus-blog/gamemakers無効化"
  **sources.json 設定整備（ng_keywords / disabled）:**
  - `4gamer`: ng_keywords を強化（「ゲーミングノート」「ゲーミングPC」「ノートPC」「ASUS」「グラフィックボード」「GPU」「DLSS」「Fortnite」「フォートナイト」「EWC」「Esports World Cup」の 11件）。PC・ハードウェア・e-Sports系の記事を除外。
  - `akiba-blog`: ng_keywords を 22件に拡充（成人向けコンテンツ全般を網羅）。
  - `dengeki-hobby`: ng_keywords に「肉感少女」「フォールアウト」「Fallout」を追加。
  - `moguravr-com`: ng_keywords 12件追加（「買収」「M&A」「資金調達」「求人」「採用」「業務提携」「B2B」「法人向け」「XREAL」「スマートグラス」「ARグラス」「ヘッドセット」）。ビジネス・業界動向系の記事を除外。
  - `gamemakers-jp-feed`: `"disabled": true` を設定（ゲーム開発者向けのため読者層に合わない）。
  - `nitroplus-blog`: `"disabled": true` を設定（更新頻度が低く、内容がコア層向けのみ）。
  `**scripts/rss_fetch.py` — disabled チェック追加:**
  - `main()` のソースループ先頭に `if source.get("disabled"): continue` を追加。
  - `disabled: true` のソースはフェッチ自体をスキップし「`[id] disabled=true のためスキップ`」とログ出力。
  `**scripts/perplexity_search.py` — 除外・許可ドメイン整備:**
  - `_EXCLUDED_RAW` に `moguravr.com` を追加（RSS で賄えるドメインの重複防止）。
  - `_ALLOWED_DOMAINS` に `kansou.me`（日本語アニメ感想）と `moguravr.com` を追加。

---

- **2026-03-22 (RSS Manager 全ソース監査 + 緊急バグ修正 3件 + sources.json 実態修正):**
  **背景**: RSS Manager の全ソースコードを精読し、実装状態・HANDOVER・ROADMAP を突き合わせた包括的監査を実施。重大バグを4件発見し、うち3件を修正・テスト・コミット済み。
  **修正1: `export_to_sources_json` が ng_keywords / disabled を消す問題**
  - 原因: `export_to_sources_json()` の出力辞書が 8 フィールドのみで `ng_keywords` / `ok_keywords` / `disabled` を含んでいなかった。呼び出すたびにこれらの設定が消えていた。
  - 修正: `existing_meta`（書き出し前の同ファイルの内容）から引き継ぐ方式に変更。
    ```python
    if old.get("ng_keywords"):  entry["ng_keywords"] = old["ng_keywords"]
    if old.get("ok_keywords"):  entry["ok_keywords"] = old["ok_keywords"]
    if old.get("disabled"):     entry["disabled"] = True
    ```
  - ファイル: `rss_manager/sources_manager.py`
  - ⚠️ **重要制約**: `export_to_sources_json()` は書き出し先 `json_path` から `existing_meta` を読む設計。`/tmp/` 等の別パスに書き出すと `ng_keywords` 等が消えるため、必ず本物のパスを渡すこと。
  **修正2: DB `disabled` カラム不足 + `upsert_source` / `import` / `list` の disabled 未対応**
  - 原因: `sources` テーブルに `disabled` カラムがなく、ソースの有効/無効状態がDBに記録されなかった。
  - 修正 (`rss_manager/db.py`):
    - `_create_sources_table()`: `disabled INTEGER DEFAULT 0` を追加。
    - `_migrate_schema()` を新設（べき等な `ALTER TABLE`。既存DBにも自動で列追加）。
    - `initialize_database()` から `_migrate_schema(conn)` を呼ぶよう変更。
  - 修正 (`rss_manager/sources_manager.py`):
    - `upsert_source(data_dir, source, disabled=False)`: `disabled` 引数を追加し INSERT / UPDATE に含める。
    - `import_from_sources_json()`: `upsert_source(..., disabled=bool(raw.get("disabled", False)))` に変更。
    - `list_sources()`: SELECT に `disabled` を追加。
  **修正3: `rss_fetcher.py` が disabled ソースをフェッチする問題 + OGP 画像未取得**
  - 原因1: `fetch_one_source()` に `disabled` チェックがなく、disabled=true のソースも毎回フェッチされていた。
  - 原因2: `articles` テーブルに `ogp_image` カラムはあるが、INSERT 文に含まれておらず DB に保存されなかった。UI が ogp_image を期待しているにもかかわらず常に NULL だった。
  - 修正 (`rss_manager/rss_fetcher.py`):
    - `fetch_one_source()` 先頭に disabled チェックを追加（fetched=0 / inserted=0 で即リターン）。
    - `_extract_ogp_image(entry)` を新設（優先順: `media_content` → `media_thumbnail` → `links[type=image]` → None）。
    - INSERT 文に `ogp_image` カラムと `_extract_ogp_image(entry)` の値を追加。
  - 副次バグ: `_extract_ogp_image` 挿入時に `fetch_all_sources` の def 行が誤って削除されたため復元（インポートエラーが発生した）。
  **修正4: `data/sources.json` のディスク実態が古かった問題**
  - 発覚経緯: テスト中に `grep` + `json.loads()` + `git show HEAD` の3重確認で、前セッションのコミット (`29843fa`) 時点で `disabled` / `ng_keywords` が実際には sources.json に含まれていないことが判明。
  - 修正: sources.json をエクスポート関数で正しい状態に書き直し。
  - 確認済み内容:
    - `4gamer`: ng_keywords 11件（ゲーミングPC/GPU/Fortnite等）
    - `akiba-blog`: ng_keywords 22件（成人向けコンテンツ全般）
    - `dengeki-hobby`: ng_keywords 3件
    - `moguravr-com`: ng_keywords 12件（買収/M&A/スマートグラス等）
    - `gamemakers-jp-feed`: `"disabled": true`
    - `nitroplus-blog`: `"disabled": true`
  - コミット: `b378015` — "fix: sources.json に ng_keywords・disabled を正しく反映"
  **テスト実績（全6件 PASS）:**
  - TEST1: DB `disabled` カラム存在確認 ✅
  - TEST2: `import_from_sources_json` 27ソース取り込み ✅
  - TEST3: DB に `disabled=1` が正しく入るか（gamemakers-jp-feed / nitroplus-blog）✅
  - TEST4: 通常ソースの `disabled=0` 確認 ✅
  - TEST5: `fetch_one_source` が disabled ソースを fetched=0 でスキップするか ✅
  - TEST6: `export_to_sources_json` 実行後も ng_keywords / disabled が保持されるか ✅
  **Git 状態:**
  - HEAD: `b378015` — "fix: sources.json に ng_keywords・disabled を正しく反映"
  - 前: `29843fa` — "feat: ng_keywords強化・4gamerカテゴリ修正・moguravr追加・nitroplus-blog/gamemakers無効化"
  **RSS Manager 現状の残課題（ROADMAP より）:**
  - `DELETE /api/articles/{id}` 記事削除 API（未実装）
  - articles → entries.json 書き出しパイプライン（未実装）
  - GitHub Actions `workflow_dispatch` による記事削除ワークフロー（未実装）
  - ~~Perplexity 品質チェック / Gemini Flash 連携（未実装）~~ → **接続済み（2026-04 時点）:** 週次 `weekly-self-improve.yml`、日次 `daily-update.yml`（Perplexity → `gemini_flash_review.py` → 翻訳）。**正は常に最新の `daily-update.yml` を参照。**
  - `thumb_utils.py` 共通化（技術的負債）
  - `translate_*.py` 系デッドコード整理（技術的負債）
- **2026-03-22 (既存データ品質クリーニング — 英語記事削除 + サムネ修復 + staging 清掃):**
  **コミット: `f8ece5c`** — "clean: remove english articles, fix thumbnails to new standards"
  **概要**: entries.json に混入していた英語サイト記事を一括削除し、サムネイルの品質を改善、staging フォルダもクリーニング。
  **作業1: 英語記事の特定と削除**
  - 全 762 件を `_EXCLUDED_RAW` + `_is_excluded_url()` で監査し、129 件の削除候補を検出。
  - ドメイン別分析の結果:
    - `0115765.com`（27件）: **偽陽性** — 日本語オタクニュースサイトだが `.com` ドメインのためホワイトリスト未登録で誤検出。→ **保持**。
    - `moguravr.com`（10件）: RSS と重複するため削除。
    - `youtube.com`（4件）: 記事ではないため削除。
    - その他英語サイト（88件）: japantravel.com / tokyotreat.com / japan-guide.com / timeout.com 等。→ 全削除。
  - 最終削除数: **102 件**（762 → 660 件）。
  - バックアップ: `data/entries_backup_before_cleanup.json` に削除前のデータを保存。
  **作業2: `0115765.com` ホワイトリスト追加**
  - `scripts/perplexity_search.py` の `_ALLOWED_DOMAINS` に `"0115765.com"` を追加。
  - 今後の Perplexity 検索で `.com` フィルタに引っかからなくなる。
  **作業3: サムネイル品質修復**
  - `fill_og_images.py --only-missing --replace-generic` を実行。660 件をスキャン。
  - 15 件が更新されたが、全てニトロプラス系の `bnr_staff.jpg`（採用バナー）→ ジェネリック画像のため null に戻し。
  - 最終状態: サムネあり **632 件 (95.8%)**、なし 28 件（主にニトロプラス系 — サイト構造上取得不可）。
  - ジェネリックサムネ: **0 件**（完全排除達成）。
  **作業4: staging/ クリーニング**
  - `data/staging_backup/` にバックアップ作成後、staging 内の英語記事 15 件を削除。
    - `20260319_1153.json`: 5 → 0 件（5 件削除）
    - `reset_20260319_1846.json`: 170 → 160 件（10 件削除）
  **変更ファイル:**
  - `data/entries.json` — 102 件削除 + ジェネリックサムネ → null
  - `scripts/perplexity_search.py` — `_ALLOWED_DOMAINS` に `0115765.com` 追加
  - `.gitignore` — バックアップファイル除外ルール追加
  **Git 状態:**
  - HEAD: `f8ece5c` — "clean: remove english articles, fix thumbnails to new standards"
  - 3 files changed, 226 insertions(+), 2405 deletions(-)
  - プッシュ済み（`b378015..f8ece5c main → main`）
- **2026-03-20 (コード品質レビュー・技術的負債特定):**
  - `rss_fetch.py` と `fill_og_images.py` に画像取得関連の同一コード（`GENERIC_THUMB_PATTERNS` 等6要素）が重複していることを確認。`ROADMAP_LATEST.md` セクション7に技術的負債として記録。
  - `translate_4gamer.py` 等5ファイルが現在の CI で使われていないデッドコードであることを確認。同じくロードマップに整理タスクとして記録。
  - 解消タスクは `ROADMAP_LATEST.md` セクション5「中」優先度に追加済み。緊急性なし・次回整理時に対応。
- **2026-03-20 (サムネ一括修正 + フィルタ強化):**
  - `fill_og_images.py` / `rss_fetch.py` の `GENERIC_THUMB_PATTERNS` に追加: `display-pic`（著者プロフィール画像）, `favicon`, `author`, `profile`, `avatar`, アイコンサイズ（`x32.` `x48.` `x64.` `x65.` `x96.` `32x32` 〜 `96x96`）, `staff/img`, `ghost_import`, `bnr_staff`（採用バナー）。
  - `fill_og_images.py` の `extract_lead_image` 内 `skip_keywords` にも `display-pic`, `profile` を追加。
  - `fill_og_images.py`: `choose_thumbnail` の返値が generic 判定を通ったとしても最終確認を追加（`is_generic_thumbnail(normalized)` チェック）。これにより lead 画像がバナーだった場合もスキップ可能に。
  - `fill_og_images.py --only-missing --replace-generic` を実行して 597 件をスキャン。62 件のサムネを新規取得・差し替え。`残りgeneric: 0` を達成（サムネあり 94%）。
  - サムネなし 33 件は存在しないドメイン（VTuber 系偽URL）・SSL エラー・403 ブロック・記事に画像がないページのため取得不可。
- **2026-03-21 (Perplexity 英語サイト除外 + Trustpilot サムネ除外):**
  - `perplexity_search.py`: `search_domain_filter` で japantravel.com / tripadvisor.com / magical-trip.com / gotokyo.org / trustpilot.com / alibaba.com 等を API リクエスト時に除外。さらにパイプラインで URL が除外ドメインを含む場合は staging に追加せず SKIP。
  - `fill_og_images.py` / `rss_fetch.py`: `GENERIC_THUMB_PATTERNS` に `trustpilot` を追加。japantravel.com の Trustpilot バナーがサムネに使われるのを防止。
- **2026-03-21 (Perplexity 検索を日本情報に固定):**
  - `perplexity_search.py`: API リクエストに `search_language_filter: ["ja"]` と `web_search_options.user_location: {country: "JP"}` を追加。プロンプトの「日本語ソースのみ」指示だけでは検索結果に反映されず海外サイトが混入していた問題を解消。全6カテゴリで共通適用。
- **2026-03-21 (Xポスト カテゴリ別ハッシュタグ):**
  - `post_to_x.py`: ハッシュタグをカテゴリごとに `CATEGORY_HASHTAGS` で定義。メインカテゴリに応じて2個まで付与（例: cafe→#CollabCafe #JapanOtaku、vtuber→#VTuber #JapanOtaku）。
- **2026-03-21 (同一URL統合 + source空記事一括削除):**
  - `perplexity_search.py`: 同じURLの複数件は「1ページ＝1記事」として最初の1件のみ残し、2件目以降を staging から除外。リンク・サムネが取れない重複記事をこれ以降発生させない。
  - `source: {}` かつ `_source == "perplexity"` の既存6件を entries.json から一括削除（Meguro River, Akihabara Tour, Yokosuka Festa, Tokyo Indie Games, Tenjin Konomi, Dark Prince）。
- **2026-03-21 (dates.display で日付ソート):**
  - 現状の記事も dates.display（記事日付）で正しく並び替わるように修正。
  - `sort_entries.py`: `parse_date_for_sort(entry)` を追加。YYYY-MM-DD、範囲（終了日）、YYYY-MM（月末）、"Mar 19, 2026" 形式に対応。パース失敗時は id にフォールバック。
  - `render.js`: `parseDateForSort(entry)` を追加し `sortByNewestFirst` で dates.display を優先。
  - entries.json を再ソートして 603 件を dates.display 基準で新着順に反映。
- **2026-03-20 (新着記事ソート順修正):**
  - id の日付部分を `YYYYMMDD` から `YYYYMMDDHHMM` に拡張。同一実行日の全記事が同じソートキーになり新着が上に出ない問題を解消。
  - `rss_fetch.py`, `perplexity_search.py`: id 生成時に `%Y%m%d%H%M` を使用。
  - `sort_entries.py`, `js/render.js`: 正規表現を 8〜12 桁対応に変更。既存 8 桁 id は `0000` パディングして比較。
- **2026-03-20 (RSSキーワードフィルター導入 + 自動改善ループ構想整理):**
  - `scripts/rss_fetch.py` にソース別キーワードフィルターを追加（重複チェック直前に挿入）。
    - `ng_keywords` に含まれるワードがタイトルに存在 → `SKIP (NG keyword)` でスキップ
    - `ok_keywords` が設定されていてタイトルに1つも含まれない → `SKIP (no OK keyword)` でスキップ
    - 他ソースへの影響ゼロ（フィールドが未設定なら従来どおり通過）
  - `data/sources.json` の `akiba-blog` に `ng_keywords: ["同人", "18禁", "R18", "成人向け", "エロ", "アダルト"]` を追加。成人向け記事を自動除外。
  - `ROADMAP_LATEST.md` に今後の実装ロードマップを追記:
    - 短期: 記事削除ワークフロー / Gemini Flash 品質チェック / 週間サバイバルレポート（直近7日区切り）
    - 中長期: 週間レポート + Analytics + X トレンドを Sonnet API に渡して検索設定を自動更新する「自己改善ループ」構想。コード側ガードレールで安全を担保し、新カテゴリ必要時はユーザー通知する設計。
- **2026-03-20 (β版完成宣言):**
  - サイトタイトルに β バッジを追加（`index.html`, `about.html`）。正式リリース時に `<small>` タグを外すだけで解除可能。
  - About ページを実態に合わせて全面改訂:
    - パイプラインの仕組み（RSS 21件 → Perplexity 6カテゴリ → DeepL翻訳 → サムネ自動取得 → GitHub Pages デプロイ）を「How It Works」セクションとして新設。
    - ソース数を正確に記載（27ソース登録、21 RSS稼働、6 AI検索補完）。
    - Tech Stack セクション新設（静的サイト / JSON / GitHub Actions / X自動投稿）。
  - カテゴリタブ下の半透明横線を修正: `.category-tabs` のスクロールバーを CSS で非表示化（`scrollbar-width: none` + `::-webkit-scrollbar { display: none }`）。原因は `overflow-x: auto` のスクロールバートラック表示だった。
  - 現在 373 エントリー、7カテゴリ、27ソース。ロードマップのフェーズ 4.1〜4.2 をほぼ完走。次はデータ蓄積を見守りつつフェーズ 4.3（収益導線・API横展開）へ。
- **2026-03-19 (RSS・サムネイル・UI 一括修正):**
  - RSS 取得失敗4ソースの修正:
    - `hobby-watch`: RSS URL を `hob/feed.rdf` → `hbw/feed.rdf` に修正（パス誤り）。
    - `natalie-news`: 存在しない `news/feed/news` → `eiga/feed/news`（映画ナタリー）に変更。
    - `animatetimes`, `anime-eiga`: 公式 RSS が廃止されていたため `rss: null`, `type: "scrape"` に変更。Perplexity 補完に委ねる。
  - RSS なし4ソース（animejapan, dengeki-vtuber, eeo-media, goodsmile）: 調査の結果すべて RSS 未提供を確認。現状の `rss: null` を維持。
  - サムネイル品質改善:
    - `skip_keywords` に `ico`_, `common/img`, `shared/img`, `noimage`, `no_image`, `dummy`, `sns_icon` を追加（rss_fetch.py, fill_og_images.py 両方）。
    - `GENERIC_THUMB_PATTERNS` に `ico_header`, `ico_sns`, `common/img`, `shared/img`, `noimage`, `no_image`, `dummy` を追加。
    - nitroplus 45件の X(Twitter) アイコン誤取得はこれで自動差し替え対象になる。
  - CI ワークフロー改善:
    - `fill_og_images.py` の `--limit` を 30 → 200 に引き上げ（大量追加時の取りこぼし防止）。
    - `--replace-generic` を CI に追加（汎用サムネの自動差し替え）。
  - UI 修正:
    - `.card` の `border` をデフォルト `transparent` に変更（半透明の枠線がカテゴリタグに被る問題を解消）。hover 時のみ `accent-cyan` で表示。
- **2026-03-19 (Perplexity 検索 全面修正 — 全6カテゴリ取得成功を確認):**
  - 問題: cafe カテゴリなどで Perplexity が JSON ではなく Markdown の説明文で返答 → パース失敗 → 0件。
  - 原因: system prompt の JSON 強制指示が弱く、user prompt がキーワード羅列のみだった。
  - 修正:
    - system prompt: 「You MUST respond with ONLY a single JSON object, no markdown, no explanation」に強化。
    - user prompt: 各カテゴリに `this week` を追加（トークン節約のため英語キーワード形式は維持）。
    - `extract_json`: Markdown 混在レスポンスからも `{...}` を抽出するフォールバック（OBJ_RE）を追加。
    - `search_recency_filter: "week"` を API リクエストに追加（直近1週間のソースに限定）。
  - 検証結果（Verify Perplexity ワークフロー実行）: cafe 8件, vtuber 8件, figure 7件, game 6件, anime 6件, other 7件 → **全6カテゴリで取得成功**。
  - `verify-perplexity.yml`: 全6カテゴリを `--debug` 付きでテストするように拡張。
  - `perplexity_search.py --debug`: 生レスポンスを保存。`--dry-run`: API 不要で送信内容確認。
- **2026-03-19 (otaku-news カテゴリの entries 未反映を修正):**
  - 問題: カテゴリ `otaku-news` のソース（0115765-com, akiba-blog, animeanime-jp, nijimen-kusuguru-co-jp 等）の記事が entries に一切入っていなかった。akiba-blog は entries に存在するが categories が `cafe` に書き換えられていた。
  - 原因: `prompts/update_workflow.md` と `prompts/gemini_json_convert.md` の許可カテゴリリストに `otaku-news` と `vtuber` が含まれておらず、AI が staging の categories を「許可外」と判断して cafe 等に変換していた。
  - 修正: 両プロンプトの許可カテゴリに `otaku-news` と `vtuber` を追加。今後 staging の categories は保持される。
  - 備考: 0115765-com と nijimen-kusuguru-co-jp は RSS 取得時に 403 Forbidden が返る場合がある（サイト側の制限またはネット環境）。GitHub Actions の daily-update では取得できるか要確認。
- **2026-03-19 (総合レビュー対応 — Phase 1-3 一括改善):**
  - サムネなし 14 件を `fill_og_images.py --only-missing` で補完。CI の `--limit` を 10→30 に引き上げ。
  - 空説明エントリー 1 件を手動修正。
  - HANDOVER / GITHUB_ACTIONS_SETUP / ROADMAP の cron 時刻記載を 19:00 JST (UTC 10:00) に統一。
  - フロントエンド UX 強化: ローディングスピナー、検索デバウンス（300ms）、空結果メッセージ、Esc キーでモーダル閉じる。
  - `about.html`: ロゴを img タグに統一、VTuber/Game/OTAKU NEWS カテゴリ追加、データソース＆更新頻度セクション追加、meta description 追加。
  - Load More ページネーション実装（24 件ずつ表示）。
  - CI の依存バージョン固定: `requirements-ci.txt` を作成し `pip install -r` に変更。
  - X (Twitter) BOT: `scripts/post_to_x.py` を新規作成。OAuth 1.0a で新着エントリーを自動ポスト（最大 3 件/回）。ワークフローに Post to X ステップを追加。
  - RSS Manager B2 仕上げ: 記事一覧に OGP 画像表示、総件数表示、ソース ID 表示、ブックマーク時のハイライト表示。SW キャッシュ名を v5 に更新。
  - 作品ジャーニー試験投入: `series_id` / `series` フィールドを entries.json に追加。`scripts/tag_series.py` で title_ja のカギカッコ内テキストから同一作品を自動検出。モーダルに「同じ作品の他のエントリー」セクションを追加。8 シリーズ・18 エントリーをタグ付け。
  - 公開サイト SW キャッシュ名を v3 に更新。
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
  - 日次スケジュール: `schedule: cron '0 10 * * *'` で毎日 19:00 JST (UTC 10:00 / 米東部 5-6時) に自動実行。手動トリガも併用可能。
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

1. ~~**Google 翻訳（`deep_translator`）移行**~~ → ✅ 実装済み（`translate_staging.py`・`daily-update.yml`・`requirements-ci.txt`）。**Actions 手動トリガで本番通し確認**は未検証なら実行して確認する
2. **RSS Manager B2 完成: articles → entries.json 書き出しパイプライン**
  - `DELETE /api/articles/{id}` API 実装
  - 承認済み記事の entries.json エクスポート機能実装
3. ~~`categories` 配列運用を追加経路まで統一~~ → ✅ 完了
4. ~~RSS Manager B2の運用品質調整~~ → ✅ 最低限完了
5. ~~Perplexity 架空URL・トップページエントリ削除~~ → ✅ 完了（14件削除）
6. ~~ホットリンク保護対策 (referrerpolicy)~~ → ✅ 完了
7. ~~[object Object] バグ修正~~ → ✅ 完了

---

## 次の予定（直近優先）

1. ~~**Google 翻訳（`deep_translator`）への翻訳移行**~~ → ✅ コード・ワークフロー反映済み（運用で挙動確認）
2. **RSS Manager B2 完成**（articles→entries.json パイプライン、DELETE API）
3. **記事削除ワークフロー**（GitHub Actions workflow_dispatch で ID 指定削除）
4. ~~**Perplexity品質チェック**（Gemini Flash）~~ → **週次ループ・検閲スクリプトは実装済**（Secrets: `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`）。**日次パイプラインへの組み込み**・**Perplexity 日次の再有効化**は要判断。
5. **週間サバイバルレポート** — **週次:** `Weekly Self-Improve Loop`（Gemini レポート＋Claude で perplexity 案、Artifact）。**X DM:** 既存 `weekly-report.yml`（総記事数等）。GitHub Issues 自動投稿は未。
6. **AdSense 再申請に向けた独自コンテンツ**（週次まとめ・編集コメント等）の整備
7. 将来：ミニPC/ラズパイ＋ローカルLLM環境ができたら、翻訳/検索API部分だけ差し替えて自前運用へ

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

※ **`rss_manager/` / `rss_manager_ui/` / `rss_manager.py` はリポジトリに含まれる**（2026-04-22 以降）。**ローカル専用で Git に載せないのは主に `rss_manager_data/`（SQLite 等）**のみ（`.gitignore` で除外）。

### 現在地

- **Phase A（ソース管理）**: 完了
  - RSS探索（Stage 1+2）＋最新5件プレビュー
  - ソース追加/削除/カテゴリ編集
  - 生存確認（全体/個別）
  - `data/sources.json` への書き戻し（バックアップ作成あり）
  - ⚠️ **2026-03-22 修正済み**: `export_to_sources_json` が ng_keywords/disabled を消すバグを修正
- **Phase B1（収集をDBに溜める）**: 完了
  - `articles` テーブル追加（URLユニーク）
  - 登録済みRSSをフェッチして `articles` に保存
  - 手動フェッチAPI `POST /api/fetch`
  - ⚠️ **2026-03-22 修正済み**:
    - `disabled` ソースをスキップするチェックを追加
    - `ogp_image` の取得・DB保存を追加（`_extract_ogp_image()` 新設）
    - DBに `disabled` カラムを追加（既存DBへの `_migrate_schema` も対応）

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

