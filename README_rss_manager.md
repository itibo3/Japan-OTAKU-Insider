## Japan OTAKU Insider — RSS Manager V2（Phase A）

Japan OTAKU Insider 用の **ローカル専用 RSS 管理ツール**です。
Chromebook の Linux 環境やラズパイなどで、`localhost` だけで動かして使う想定です。

### できること（Phase A）

- サイト URL から RSS/Atom フィードを自動検出（Stage 1 + Stage 2）
- 見つかった RSS を「ソース」として登録
- 登録済みソースの一覧表示・削除・カテゴリ変更
- `data/sources.json` の内容を初回起動時に SQLite に取り込み
- **DBの内容を `data/sources.json` に書き戻し（バックアップ作成あり）**

### セットアップ

```bash
cd "Japan OTAKU Insider"

# もし venv / pip が無い場合（Debian/Ubuntu）
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate  # Windows は .venv\\Scripts\\activate

python3 -m pip install -r requirements-rss-manager.txt
```

### 起動方法

**Cursorで「RSS Manager開いて」と言う** → Cursorたんが代行して起動する。

起動後、ブラウザで http://127.0.0.1:8080/ を開く（自動で開かない場合）。

### 初回セットアップ（登録済みソースが空の場合）

画面に「sources.json から読み込む」ボタンが表示されます。クリックすると 4gamer・あみあみ など 22 件のソースが登録されます。

### `sources.json` に書き戻す（エクスポート）

管理画面の「**sources.jsonへ書き戻す**」ボタンで実行できます。

- 実行すると `data/sources.json.backup_YYYYMMDD_HHMMSS` が作成されます（保険）
- DBにあるソース一覧が `data/sources.json` に反映されます

### Daily Update ワークフローでソースを反映するには

**RSS Manager でソースを追加・変更したら、必ず「GitHubにプッシュ」を実行してください。**  
「sources.jsonへ書き戻す」だけではローカルファイルが更新されるだけで、GitHub Actions の Daily Update ワークフローはリポジトリ上の `data/sources.json` を参照します。プッシュしないと新規ソースは取得対象になりません。

オプション:

```bash
python3 rss_manager.py --host 0.0.0.0 --port 8090 --no-browser
```

### データの場所とバックアップ

- 管理用 SQLite: `rss_manager_data/manager.db`
- ヲタInsider本体のデータ: `data/entries.json`, `data/sources.json`（別管理）

バックアップは SQLite ファイルをコピーするだけで OK です。

```bash
cp rss_manager_data/manager.db rss_manager_data/manager.db.backup
```

### 注意事項

- **ローカル専用ツール**です。インターネットに公開しないでください。
- `.gitignore` により `rss_manager.py` / `rss_manager/` / `rss_manager_ui/` / `rss_manager_data/` は Git に含まれません。
- Phase B 以降（記事収集・全文閲覧・エクスポート連携）は別フェーズで実装予定です。

