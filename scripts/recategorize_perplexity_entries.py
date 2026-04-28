#!/usr/bin/env python3
"""
公開済み DB のうち Perplexity 由来（_source=perplexity）の primary カテゴリを、
タイトル・説明・URL を材料に Gemini で振り直す。

使い方:
  python3 scripts/recategorize_perplexity_entries.py              # プレビュー MD + JSON（API 必須）
  python3 scripts/recategorize_perplexity_entries.py --apply      # entries.json / entries_ja.json を更新

環境変数: GEMINI_API_KEY（未設定なら終了）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from gemini_flash_review import (  # noqa: E402
    DEFAULT_GEMINI_MODEL,
    _entry_primary_fallback,
    _parse_json_object,
    normalize_primary_category,
)

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
ENTRIES_EN = ROOT / "data" / "entries.json"
ENTRIES_JA = ROOT / "data" / "entries_ja.json"
PREVIEW_MD = ROOT / "data" / "recategorize_pplx_preview.md"
CHANGES_JSON = ROOT / "data" / "recategorize_pplx_changes.json"

RECLASSIFY_SYSTEM = """あなたは日本オタクニュースサイトのカテゴリ分類担当です。
与えられた記事それぞれについて、内容に最も合う primary_category を1つだけ選んでください。

primary_category は次のいずれか1語のみ: cafe, vtuber, figure, game, anime, other
- cafe: コラボカフェ・カフェイベント・飲食コラボが主題
- vtuber: VTuber・にじさんじ・ホロライブ等の配信・グッズ・企画が主題
- figure: フィギュア・プラモデル・ホビー製品の予約・発売が主題
- game: ゲーム本体・DLC・ゲームイベントが主題
- anime: アニメ放送・映画・声優・制作ニュースが主題
- other: 上記のどれにも明確に当てはまらない

必ず次の JSON だけを返す:
{"results":[{"index":0,"primary_category":"game"}, ...]}
index は入力バッチ内の 0 始まり。バッチ内の全件分の results を含める。
"""


def _compact_for_batch(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for i, e in enumerate(batch):
        src = e.get("source") or {}
        url = (src.get("url") or "")[:500] if isinstance(src, dict) else ""
        out.append(
            {
                "index": i,
                "id": e.get("id"),
                "title_ja": (e.get("title_ja") or e.get("title") or "")[:350],
                "description": (e.get("description") or "")[:450],
                "url": url,
                "current_category": _entry_primary_fallback(e),
            }
        )
    return out


def call_gemini_reclassify(api_key: str, model: str, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = _compact_for_batch(batch)
    user = "記事バッチ:\n" + json.dumps(compact, ensure_ascii=False, indent=2)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    params = {"key": api_key}
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": RECLASSIFY_SYSTEM}]},
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
    results = parsed.get("results")
    if not isinstance(results, list):
        raise ValueError("応答に results 配列がありません")
    return results


def _model_fallback_chain(preferred: str) -> list[str]:
    """Gemini のモデル名が環境で 404 になる場合に次を試す（daily 検閲と同趣旨）。"""
    chain: list[str] = []
    for m in (
        (preferred or "").strip(),
        DEFAULT_GEMINI_MODEL,
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ):
        if m and m not in chain:
            chain.append(m)
    return chain


def collect_perplexity_active(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        if e.get("_source") != "perplexity":
            continue
        if e.get("status") != "active":
            continue
        out.append(e)
    return out


def run_classification(
    targets: list[dict[str, Any]],
    *,
    api_key: str,
    model: str,
    batch_size: int,
) -> list[tuple[str, str, str]]:
    """[(id, old_cat, new_cat), ...]"""
    changes: list[tuple[str, str, str]] = []
    models = _model_fallback_chain(model)
    for start in range(0, len(targets), batch_size):
        batch = targets[start : start + batch_size]
        raw = None
        last_err: RuntimeError | None = None
        used_model: str | None = None
        for m in models:
            try:
                raw = call_gemini_reclassify(api_key, m, batch)
                used_model = m
                break
            except RuntimeError as e:
                last_err = e
                err_s = str(e)
                if "404" in err_s or "NOT_FOUND" in err_s or "not found" in err_s.lower():
                    continue
                raise
        if raw is None:
            raise last_err if last_err else RuntimeError("Gemini 分類に失敗しました")
        if start == 0 and used_model:
            print(f"使用モデル: {used_model}", file=sys.stderr)
        by_idx: dict[int, str] = {}
        for row in raw:
            if not isinstance(row, dict):
                continue
            idx = row.get("index")
            if isinstance(idx, int):
                by_idx[idx] = normalize_primary_category(row.get("primary_category"), "other")
        for i, e in enumerate(batch):
            eid = str(e.get("id") or "")
            old_c = _entry_primary_fallback(e)
            new_c = by_idx.get(i, old_c)
            new_c = normalize_primary_category(new_c, old_c)
            changes.append((eid, old_c, new_c))
    return changes


def apply_changes(db_en: dict[str, Any], db_ja: dict[str, Any], changes: list[tuple[str, str, str]]) -> int:
    """同一 id の categories / tags を更新。変更有りのユニーク id 数を返す。"""
    id_to_new = {cid: new_c for cid, _old, new_c in changes if cid}
    touched: set[str] = set()
    for db in (db_en, db_ja):
        for e in db.get("entries") or []:
            if not isinstance(e, dict):
                continue
            eid = e.get("id")
            if eid not in id_to_new:
                continue
            new_c = id_to_new[eid]
            old_c = _entry_primary_fallback(e)
            if new_c == old_c:
                continue
            e["categories"] = [new_c]
            e["tags"] = [new_c]
            e["_category_from_search"] = old_c
            e["_category_assigned_by"] = "gemini-reclassify"
            if isinstance(eid, str):
                touched.add(eid)
    return len(touched)


def write_preview_md(changes: list[tuple[str, str, str]], path: Path) -> None:
    lines = [
        "# Perplexity 記事カテゴリ再分類プレビュー",
        "",
        f"- 生成: {datetime.now(JST).isoformat()}",
        f"- 件数: {len(changes)}",
        "",
        "| id | 変更前 | 変更後 |",
        "|----|--------|--------|",
    ]
    for eid, old_c, new_c in changes:
        lines.append(f"| `{eid}` | {old_c} | {new_c} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Perplexity 由来記事のカテゴリを Gemini で再分類")
    parser.add_argument("--apply", action="store_true", help="entries.json / entries_ja.json に反映する")
    parser.add_argument("--batch-size", type=int, default=12, help="Gemini 1回あたりの件数")
    parser.add_argument("--model", default=(os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL))
    parser.add_argument("--limit", type=int, default=0, help="先頭 N 件だけ（デバッグ用）")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY が未設定です。GitHub Secrets またはローカル環境で設定してください。", file=sys.stderr)
        sys.exit(2)

    if not ENTRIES_EN.exists():
        print(f"見つかりません: {ENTRIES_EN}", file=sys.stderr)
        sys.exit(1)

    db_en = json.loads(ENTRIES_EN.read_text(encoding="utf-8"))
    entries = db_en.get("entries") or []
    targets = collect_perplexity_active(entries)
    if args.limit > 0:
        targets = targets[: args.limit]

    if not targets:
        print("対象（perplexity + active）がありません。")
        return

    print(f"対象 {len(targets)} 件を分類します（model={args.model}）...")
    changes = run_classification(targets, api_key=api_key, model=args.model, batch_size=max(1, args.batch_size))

    CHANGES_JSON.parent.mkdir(parents=True, exist_ok=True)
    CHANGES_JSON.write_text(
        json.dumps(
            [{"id": a, "category_before": b, "category_after": c} for a, b, c in changes],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_preview_md(changes, PREVIEW_MD)
    print(f"書き出し: {CHANGES_JSON}")
    print(f"書き出し: {PREVIEW_MD}")

    n_diff = sum(1 for _a, b, c in changes if b != c)
    print(f"変更あり: {n_diff} / {len(changes)} 件")

    if args.apply:
        if not ENTRIES_JA.exists():
            print(f"entries_ja.json がありません: {ENTRIES_JA}", file=sys.stderr)
            sys.exit(1)
        db_ja = json.loads(ENTRIES_JA.read_text(encoding="utf-8"))
        apply_changes(db_en, db_ja, changes)
        now = datetime.now(JST).isoformat()
        db_en["last_updated"] = now
        db_ja["last_updated"] = now
        db_en["total_entries"] = len(db_en.get("entries") or [])
        db_ja["total_entries"] = len(db_ja.get("entries") or [])
        ENTRIES_EN.write_text(json.dumps(db_en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ENTRIES_JA.write_text(json.dumps(db_ja, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("entries.json / entries_ja.json を更新しました。")
    else:
        print("（--apply なしのため DB は未更新。反映する場合は --apply を付けて再実行）")


if __name__ == "__main__":
    main()
