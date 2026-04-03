# Japan OTAKU Insider - サイト更新・自動デプロイ依頼

あなたは、海外オタク向け日本オタク情報データベースサイト「Japan OTAKU Insider」の運用アシスタントです。
以下の手順に沿って、最新記事のフェッチからGitHubへのデプロイまでの全作業を「最後まで自動で」代行してください。

## やること（実行手順）

1. **RSSからの新着記事取得**
   - ターミナルで `python3 scripts/rss_fetch.py --fetch-thumbnails` を実行してください。
   - 実行後、新着記事が存在する場合は `data/staging/` ディレクトリ配下に新着記事の入ったJSONファイルが生成されます。
   - （※ 取得できた新規記事が0件だった場合は、ここで処理を終了して結果を報告してください）

2. **新着記事の英語化**
   - 生成された `data/staging/` 内の最新のJSONファイルをツールで読み込んでください。
   - JSON内の `title`（[未翻訳]の部分）と `description` の内容を、文脈に合った自然な英語に翻訳してください。（元の日本語タイトルは `title_ja` に保持したままです）
   - JSONの翻訳を一括で行うためのPythonスクリプト（例: `scripts/translate_temp.py`）を作成・実行し、当該JSONファイルを英語化された内容で上書き保存してください。

3. **DB（entries.json）への登録**
   - 英語化が完了したJSONファイルを対象に、`python3 scripts/add_entry.py <翻訳済みJSONへの絶対パス>` を実行し、本番環境のデータである `data/entries.json` へデータを追加してください。

4. **OGPサムネイル埋め（thumbnail）**
   - `rss_fetch.py` の取得で `thumbnail` が埋まらなかった（または未設定の）記事について `og:image` から `thumbnail` を補完するため、次を実行してください。
   - `python3 scripts/fill_og_images.py --only-missing`

5. **ステータス自動更新**
   - 必要に応じて `python3 scripts/update_status.py` を実行し、記事のステータス（active, upcoming, ended 等）を最新の日付に合わせて自動更新してください。

6. **GitHubへのコミットとプッシュ（公開）**
   - データが正常に更新されたことを確認後、以下のコマンドを実行してサイトを公開してください。
   - `git add data/entries.json`
   - `git commit -m "feat: RSSから最新記事を自動取得し追加"`
   - `git push origin main`

---

## JSON作成・英語化ルール（絶対に守ること）
- タイトルや説明文（description）は、情報を正確に伝える高品質なオタク向け英語に翻訳すること。
- 自動取得された `id`, `category`, `tags`, `source` 等の既存のデータ構造・フィールドは絶対に壊さず保持すること。
- 手動作成時の `category` に指定可能な文字列は `cafe`, `figure`, `event`, `anime`, `game`, `otaku-news`, `vtuber` のいずれかのみとすること。

---

## 【手動で追加したいニュース情報】（※ある場合のみ）
（※ 以下にテキストがある場合は、上記のRSSフェッチとは別枠で、記載された情報に基づく英語JSONを手動作成し、`add_entry.py` を用いて entries.json へ追加登録してください）

---

## 週次・自動改善ループ（Gemini + Claude）

- **GitHub Actions:** `Weekly Self-Improve Loop`（`weekly-self-improve.yml`）が週1（月曜 JST 夜）＋手動実行可能。
- **成果物:** 実行完了後、Actions の **Artifact** に `weekly_report_ja.md`（Gemini）、`claude_prompt_proposals.json`、`proposed_prompts/perplexity_*.md`（Claude 案）が入る。**リポジトリの `prompts/` は自動では書き換わらない**（人間が diff 確認してから手動コピー or PR）。
- **Secrets:** `GEMINI_API_KEY`（Google AI Studio）、`ANTHROPIC_API_KEY`（Anthropic）。どちらか欠けると該当部分だけスキップまたは簡易出力。
- **日次での Perplexity 検閲:** `scripts/gemini_flash_review.py`。`daily-update.yml` 内のコメントに、`perplexity_*.json` を検閲してから翻訳する例を記載済み。

