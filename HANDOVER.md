# Japan OTAKU Insider — 引継書

**作成日:** 2026-03-16 (最終更新: 2026-04-11)  
**ステータス:** β版完成 / 独自ドメイン（otaku.eidosfrontier.com）移行完了 / HTTPS有効 / AdSenseは審査却下（第三者コンテンツの集約に近いと判断）— オリジナル編集・週次まとめ等で付加価値を高めたうえで再申請・改善を予定  
**開発期間:** 約6時間  
**URL:** [https://otaku.eidosfrontier.com](https://otaku.eidosfrontier.com)

---

## プロジェクト概要

日本のオタク文化（コラボカフェ・フィギュア・イベント・アニメニュース）を英語圏向けにまとめたデータベースサイト。  
GitHub Pages上で動作する完全静的サイト（維持費ゼロ）。

### データ更新まわりの現状（要約・2026-04-06）

| もの | 状態 |
|------|------|
| **Daily Update**（cron＋手動） | RSS 取得 → `translate_staging` → `entries.json` 反映まで **稼働** |
| **Perplexity 6カテゴリ検索** | **`daily-update.yml` から一時オフ**（幻覚記事の日次再投入防止。`perplexity_search.py`・`verify-perplexity.yml` は残存） |
| **Gemini 検閲** | `scripts/gemini_flash_review.py` あり。**日次には未接続**（YAML 内はコメント例のみ） |
| **週次自己改善** | `weekly-self-improve.yml`：**週1＋手動**。成果は Artifact（`prompts/` は自動では書き換えない） |

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
  - ~~Perplexity 品質チェック / Gemini Flash 連携（未実装）~~ → **一部実装済（2026-04-04）:** `weekly-self-improve.yml`（週報＋Claude 案・Artifact）、`gemini_flash_review.py`（検閲用スクリプト）。**日次 Daily Update への検閲ステップ本接続は未**（`daily-update.yml` はコメント例のみ）。**日次の Perplexity 検索は一時オフ**（同コメントアウト）。
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

※ GitHubに公開しないため `.gitignore` 対象（ローカル専用）。

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

