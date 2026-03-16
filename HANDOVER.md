# Japan OTAKU Insider — 引継書

**作成日:** 2026-03-16  
**ステータス:** α版 完了  
**開発期間:** 約4時間  
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
│   └── fetch_rss.py    # RSS取得スクリプト（未完成）
└── prompts/
    ├── perplexity_daily.md   # 日次情報収集プロンプト
    └── gemini_json_convert.md # JSONフォーマット変換プロンプト
```

---

## 日常運用ワークフロー

```
1. Perplexityで情報収集
   └─ prompts/perplexity_daily.md のプロンプトを使用

2. GeminiでJSON変換
   └─ prompts/gemini_json_convert.md のプロンプトを使用

3. エントリー追加
   └─ python scripts/add_entry.py <生成したJSONファイル>

4. ステータス自動更新（日付ベースでACTIVE/UPCOMING/ENDEDを更新）
   └─ python scripts/update_status.py

5. デプロイ
   └─ git add . && git commit -m "update: YYYY-MM-DD" && git push
```

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

### 🔴 Phase 1 — コンテンツ強化（エントリー50件まで）
優先度が高く、すぐに着手すべき内容。

| タスク | 詳細 |
|---|---|
| **OGP画像の設定** | `og:image` と `twitter:image` にバナー画像を追加。XやDiscordシェア時に画像付きで表示される |
| **エントリーの継続追加** | 週2〜3回ペースで更新。まず50件が目標 |
| **`update_status.py` の定期実行** | 手動 or GitHub Actions で日次自動実行化 |
| **`fetch_rss.py` の完成** | RSS取得→JSON変換の半自動化 |

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
| **多言語対応** | 日本語版の追加 |

### 🔵 Phase 4 — スケールアップ（長期）

| タスク | 詳細 |
|---|---|
| **バックエンドAPI化** | エントリー数が大量になったらNext.js + Supabase等に移行 |
| **ユーザー投稿機能** | コミュニティ駆動の情報追加 |
| **メールニュースレター** | 週次まとめのメール配信 |

---

## 既知の課題・注意点

- **Service Workerのキャッシュ更新**: `sw.js` の `CACHE_NAME` を `otaku-insider-v2` のようにバージョンアップしないと古いキャッシュが残る。`entries.json` を更新したら都度バージョンを上げること
- **`og:image` 未設定**: SNSシェア時に画像が表示されない。要対応
- **`node_modules/` に `sharp` が残存**: ローカルにのみ存在、gitignore済みなので問題なし。不要なら `rm -rf node_modules` で削除可

---

## 次のセッションで最初にやること

1. `og:image` と `twitter:image` の追加（OGPバナー画像を用意してから）
2. エントリーデータの継続追加
3. `update_status.py` をGitHub Actionsで自動化（cron設定）
