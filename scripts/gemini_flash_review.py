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
from urllib.parse import urlparse

import requests
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"

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


def _prefilter_reason(entry: dict[str, Any]) -> str | None:
    """Gemini 前に機械的に弾ける品質NGを返す。None の場合は判定対象。"""
    title = (entry.get("title_ja") or entry.get("title") or "").strip()
    desc = (entry.get("description") or "").strip()
    src = entry.get("source") or {}
    url = (src.get("url") or "").strip()
    if not title:
        return "タイトルが空"
    if not desc:
        return "説明文が空"
    if not url:
        return "URLが空"

    try:
        parsed = urlparse(url)
    except Exception:
        return "URL形式が不正"
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "URL形式が不正"

    # Perplexity 由来は「トップ/一覧ページ」混入が多いため厳しめに弾く
    if entry.get("_source") == "perplexity":
        path = (parsed.path or "").strip().lower()
        if path in ("", "/", "/index.html", "/index.php", "/home", "/top"):
            return "Perplexity由来URLがトップページ"
        # 具体記事URLとして弱い階層（例: /foo/）は除外
        depth = len([x for x in path.split("/") if x])
        if depth <= 1 and not parsed.query:
            return "Perplexity由来URLが一覧/ランディング疑い"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini Flash で staging 記事を検閲する")
    parser.add_argument("--input", type=Path, required=True, help="入力 JSON（配列 or entries 包み）")
    parser.add_argument("--output", type=Path, required=True, help="通過分だけを書き出す JSON 配列")
    parser.add_argument("--log", type=Path, help="判断ログ JSON の保存先（任意）")
    parser.add_argument("--dry-run", action="store_true", help="API を呼ばず全件通過（接続テスト用）")
    parser.add_argument("--model", default=(os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL), help="Gemini モデル名")
    parser.add_argument(
        "--missing-key-policy",
        choices=("reject", "pass", "error"),
        default="reject",
        help="GEMINI_API_KEY 未設定時の動作: reject=全件却下(pass-through防止), pass=全件通過, error=異常終了",
    )
    args = parser.parse_args()

    entries = _load_entries(args.input)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not args.dry_run and not api_key:
        if args.missing_key_policy == "error":
            print("GEMINI_API_KEY が未設定です（--missing-key-policy=error）", file=sys.stderr)
            sys.exit(2)
        if args.missing_key_policy == "pass":
            print("GEMINI_API_KEY が未設定のため検閲をスキップし、入力をそのまま出力します。", file=sys.stderr)
            approved = entries
            log_rows = [
                {"index": i, "id": e.get("id"), "ok": True, "reason_ja": "GEMINI_API_KEY 未設定（pass-through）"}
                for i, e in enumerate(entries)
            ]
        else:
            print("GEMINI_API_KEY が未設定のため未審査記事を全件却下します。", file=sys.stderr)
            approved = []
            log_rows = [
                {"index": i, "id": e.get("id"), "ok": False, "reason_ja": "GEMINI_API_KEY 未設定のため未審査で却下"}
                for i, e in enumerate(entries)
            ]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.log:
            args.log.parent.mkdir(parents=True, exist_ok=True)
            args.log.write_text(json.dumps(log_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"検閲: 入力 {len(entries)} 件 → 通過 {len(approved)} 件 → {args.output}")
        return

    if not entries:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("[]\n", encoding="utf-8")
        print("0 件のため何もしません")
        return

    pre_reject_indices: dict[int, str] = {}
    review_candidates: list[tuple[int, dict[str, Any]]] = []
    for i, e in enumerate(entries):
        reason = _prefilter_reason(e)
        if reason:
            pre_reject_indices[i] = reason
        else:
            review_candidates.append((i, e))

    if args.dry_run:
        decisions = [{"index": i, "ok": True, "reason_ja": "dry-run"} for i in range(len(entries))]
    else:
        tried: list[str] = []
        decisions = None
        if review_candidates:
            candidate_entries = [e for _, e in review_candidates]
            for model in [args.model, "gemini-2.5-flash-lite", "gemini-1.5-flash"]:
                if model in tried:
                    continue
                tried.append(model)
                try:
                    raw_decisions = call_gemini_decisions(api_key, model, candidate_entries)
                    index_map = {new_i: old_i for new_i, (old_i, _) in enumerate(review_candidates)}
                    decisions = []
                    for row in raw_decisions:
                        if not isinstance(row, dict):
                            continue
                        new_i = row.get("index")
                        if isinstance(new_i, int) and new_i in index_map:
                            row = dict(row)
                            row["index"] = index_map[new_i]
                            decisions.append(row)
                    if model != args.model:
                        print(f"Gemini 代替モデルで成功: {model}", file=sys.stderr)
                    break
                except Exception as e:
                    print(f"Gemini 呼び出し失敗 ({model}): {e}", file=sys.stderr)
            if decisions is None:
                raise RuntimeError("Gemini 検閲: すべてのモデル候補で失敗")
        else:
            decisions = []

        # 事前NGは Gemini 結果より優先して却下
        for idx, reason in pre_reject_indices.items():
            decisions.append({"index": idx, "ok": False, "reason_ja": reason})

    approved, log_rows = apply_decisions(entries, decisions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(json.dumps(log_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"検閲: 入力 {len(entries)} 件 → 通過 {len(approved)} 件 → {args.output}")


if __name__ == "__main__":
    main()
