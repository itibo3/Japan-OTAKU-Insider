# GitHub Actions セットアップ手順

Daily Update ワークフローを動かすまでの手順です。

---

## ステップ1: リポジトリのページを開く

1. ブラウザで開く: https://github.com/itibo3/Japan-OTAKU-Insider
2. 自分がログインしていることを確認

---

## ステップ2: 設定画面へ移動

1. リポジトリページの上部タブで **「Settings」** をクリック
2. 左サイドバーの **「Secrets and variables」** → **「Actions」** をクリック
3. 「Repository secrets」という見出しが表示されていればOK

---

## ステップ3: シークレットを追加

1. **「New repository secret」** ボタンをクリック
2. 次の2つを入力:

   | 項目 | 入力する値 |
   |------|------------|
   | **Name** | `DEEPL_AUTH_KEY`（このままコピペ） |
   | **Secret** | 自分の DeepL API キー（例: `xxxxxx:fx`） |

3. **「Add secret」** をクリック
4. 同様に **PERPLEXITY_API_KEY** を追加（Perplexity 検索を使う場合。未設定でも RSS のみで動作）
5. 一覧に両方表示されればOK

---

## ステップ4: ワークフローを手動実行

1. リポジトリページ上部の **「Actions」** タブをクリック
2. 左メニューで **「Daily Update」** をクリック
3. 右側の **「Run workflow」** ボタンをクリック
4. 表示される **「Run workflow」**（ドロップダウン内）をクリック
5. 黄色いマークで「In progress」と表示されれば実行開始

---

## ステップ5: 結果を確認

1. 数分待つ（RSS取得→Perplexity検索×6→翻訳→追加→push まで）
2. 緑のチェックが付けば **成功**
3. 赤いマークなら失敗 → その実行をクリックし、エラーメッセージを確認

---

## トラブルシュート

| 症状 | 確認すること |
|------|--------------|
| キー未設定でスキップされた | ステップ2〜3で Secret が正しく登録されているか |
| 403 Forbidden | DeepL キーが正しいか、Free キーなら末尾が `:fx` か |
| push に失敗 | リポジトリへの書き込み権限があるか |
| 新規記事が0件 | その日は重複ばかりで新着がなかった可能性 |

---

## 次回以降

- 手動実行はいつでも「Actions」→「Daily Update」→「Run workflow」
- 日次自動実行: 毎日 19:00 JST (UTC 10:00) に schedule で自動実行される
