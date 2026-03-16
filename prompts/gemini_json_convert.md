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
