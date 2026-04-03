#!/usr/bin/env python3
"""
Gemini Flash による staging 記事の検閲（通過/却下）。

入力: Perplexity 等が出力する「エントリの配列」JSON、または {"entries":[...]} 形式。
出力: 通過したエントリだけの JSON 配列（--output）。判断ログは --log で任意保存。

触っていい所: プロンプト文言（REVIEW_SYSTEM）をサイト方針に合わせて調整。
危ない所: API キーをコードに直書きしない（環境変数 GEMINI_API_KEY）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

REVIEW_SYSTEM = """あなたは「Japan OTAKU Insider」という英語向け日本オタクニュースサイトの厳格な検閲担当です。
与えられた候補記事それぞれについて、サイトに載せるべきか boolean で判定します。

次のいずれかに該当する場合は ok=false にしてください（理由は reason_ja に短く日本語で）:
- 実在のニュース記事ページではなく、公式サイトのトップや一覧だけをURLにしており、タイトル・本文の具体的出来事を裏付けできない疑いが強い
- ゲーム枠なのにプロ野球・WBC・Baseball5 等の一般スポーツ実況・国際試合が主題
- コミケ・同人即売会の開催時期や回次が明らかに誤り（既知の史実と矛盾）
- イベント名・日付・場所の組み合わせがでっち上げっぽい、または確認不可能で危険
- オタク文化（アニメ・ゲーム・フィギュア・コラボカフェ・VTuber 等）と無関係

RSS 由来の具体的な製品発表・予約開始など、一次ソースらしいURLで裏付けできるものは ok=true でよい。

必ず次の JSON だけを返す（前後に説明文を付けない）:
{"decisions":[{"index":0,"ok":true,"reason_ja":""}, ...]}
index は入力配列の 0 始まりの番号。全件分の decisions を含める。
"""


def _load_entries(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
        return [x for x in raw["entries"] if isinstance(x, dict)]
    raise ValueError("JSON はエントリの配列、または {\"entries\": [...]} 形式にしてください")


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return json.loads(m.group(0))
    raise ValueError("Gemini の応答から JSON オブジェクトを解析できませんでした")


def call_gemini_decisions(api_key: str, model: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """候補一覧を渡し、decisions 配列を返す。"""
    compact = []
    for i, e in enumerate(entries):
        src = e.get("source") or {}
        compact.append(
            {
                "index": i,
                "id": e.get("id"),
                "categories": e.get("categories"),
                "title_ja": e.get("title_ja") or e.get("title"),
                "description": (e.get("description") or "")[:500],
                "url": (src.get("url") or "")[:500],
            }
        )
    user = "候補記事:\n" + json.dumps(compact, ensure_ascii=False, indent=2)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    params = {"key": api_key}
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": REVIEW_SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    resp = requests.post(url, params=params, json=body, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"Gemini API HTTP {resp.status_code}: {resp.text[:400]}")

    data = resp.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Gemini API が空の応答を返しました")
    text = parts[0].get("text", "")
    parsed = _parse_json_object(text)
    decisions = parsed.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("応答に decisions 配列がありません")
    return decisions


def apply_decisions(entries: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """通過したエントリと、ログ用の行を返す。"""
    ok_by_index: dict[int, bool] = {}
    reasons: dict[int, str] = {}
    for d in decisions:
        if not isinstance(d, dict):
            continue
        idx = d.get("index")
        if isinstance(idx, int):
            ok_by_index[idx] = bool(d.get("ok"))
            reasons[idx] = str(d.get("reason_ja") or "")

    approved: list[dict[str, Any]] = []
    log_rows: list[dict[str, Any]] = []
    for i, e in enumerate(entries):
        ok = ok_by_index.get(i, False)
        row = {"index": i, "id": e.get("id"), "ok": ok, "reason_ja": reasons.get(i, "(判定なし)")}
        log_rows.append(row)
        if ok:
            approved.append(e)
    return approved, log_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini Flash で staging 記事を検閲する")
    parser.add_argument("--input", type=Path, required=True, help="入力 JSON（配列 or entries 包み）")
    parser.add_argument("--output", type=Path, required=True, help="通過分だけを書き出す JSON 配列")
    parser.add_argument("--log", type=Path, help="判断ログ JSON の保存先（任意）")
    parser.add_argument("--dry-run", action="store_true", help="API を呼ばず全件通過（接続テスト用）")
    parser.add_argument("--model", default=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"), help="Gemini モデル名")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not args.dry_run and not api_key:
        print("GEMINI_API_KEY が未設定のため検閲をスキップし、入力をそのまま出力します。", file=sys.stderr)
        entries = _load_entries(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sys.exit(0)

    entries = _load_entries(args.input)
    if not entries:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("[]\n", encoding="utf-8")
        print("0 件のため何もしません")
        return

    if args.dry_run:
        decisions = [{"index": i, "ok": True, "reason_ja": "dry-run"} for i in range(len(entries))]
    else:
        try:
            decisions = call_gemini_decisions(api_key, args.model, entries)
        except Exception as e:
            print(f"Gemini 呼び出し失敗 ({e}); gemini-1.5-flash にフォールバックします。", file=sys.stderr)
            if args.model != "gemini-1.5-flash":
                decisions = call_gemini_decisions(api_key, "gemini-1.5-flash", entries)
            else:
                raise

    approved, log_rows = apply_decisions(entries, decisions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(json.dumps(log_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"検閲: 入力 {len(entries)} 件 → 通過 {len(approved)} 件 → {args.output}")


if __name__ == "__main__":
    main()
