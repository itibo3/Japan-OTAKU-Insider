#!/usr/bin/env python3
"""
週次の「自己改善ループ」オーケストレーター。

1) entries.json から直近の件数・カテゴリ内訳などを集計
2) Gemini Flash で週次レポート（日本語 Markdown）を生成
3) Claude API にレポート + 現行 prompts/perplexity_*.md を渡し、検索ワード行の改善案を JSON で受け取る
4) 出力は指定ディレクトリに保存（GitHub Actions では Artifact 化想定）。prompts/ 本体は自動では書き換えない。

触っていい所: 集計日数、Claude/Gemini の指示文（定数）。
危ない所: API キーは環境変数のみ（GEMINI_API_KEY, ANTHROPIC_API_KEY）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
PERPLEXITY_FILES = (
    "perplexity_cafe.md",
    "perplexity_vtuber.md",
    "perplexity_figure.md",
    "perplexity_game.md",
    "perplexity_anime.md",
    "perplexity_other.md",
)

JST = timezone(timedelta(hours=9))
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

REPORT_SYSTEM = """あなたは Japan OTAKU Insider の運用アナリストです。
与えられたサイト統計（JSON）を読み、週次の振り返りレポートを日本語の Markdown で書いてください。

含めること:
- 総記事数とカテゴリ別の雰囲気（多い/少ない）
- 直近追加の活発さ（件数の目安）
- Perplexity 補完を再開する場合のリスク（幻覚・スポーツ混入・偽イベント）への短い注意
- 次の1週間の運用上の提案（箇条書き3つまで）

含めないこと: 憶測で具体的なイベント名や日付を新たにでっち上げないこと。
"""

CLAUDE_SYSTEM = """You are a prompt engineer for a Perplexity search pipeline.
The site uses one English keyword line per file in prompts/perplexity_*.md (collab cafe, vtuber, figure, game, anime, other).
Your job: propose improved single-line keyword strings that:
- Target Japanese primary sources (the API already filters to Japanese)
- Reduce hallucinated events, wrong Comiket numbering/dates, fake fairs
- Keep "game" category away from real-world pro sports / Baseball5 / WBC unless clearly a video game tie-in
- Stay concise (one line each, space-separated keywords/phrases, like the originals)

Output ONLY valid JSON (no markdown fences) with exactly these keys:
"perplexity_cafe.md", "perplexity_vtuber.md", "perplexity_figure.md", "perplexity_game.md", "perplexity_anime.md", "perplexity_other.md"
Each value is a single string (the new one-line prompt).
"""


def _id_date(entry: dict[str, Any]) -> str | None:
    """id 内の日付を YYYYMMDD で返す（例: anime-202603302009-rss-xxx / figure-20260319-rss-xxx）。"""
    m = re.search(r"-(\d{8})(?:\d{4})?-", entry.get("id") or "")
    return m.group(1) if m else None


def collect_stats(entries: list[dict[str, Any]], days: int = 7) -> dict[str, Any]:
    today = datetime.now(JST).date()
    cutoff = today - timedelta(days=days)
    by_cat: dict[str, int] = {}
    recent = 0
    pplx = 0
    for e in entries:
        for c in e.get("categories") or []:
            by_cat[c] = by_cat.get(c, 0) + 1
        if "-pplx-" in (e.get("id") or "") or e.get("_source") == "perplexity":
            pplx += 1
        ds = _id_date(e)
        if ds:
            y, m, d = int(ds[:4]), int(ds[4:6]), int(ds[6:8])
            try:
                if datetime(y, m, d).date() >= cutoff:
                    recent += 1
            except ValueError:
                pass
    return {
        "generated_at_jst": datetime.now(JST).isoformat(),
        "total_entries": len(entries),
        "by_category": by_cat,
        f"entries_with_id_date_in_last_{days}_days_approx": recent,
        "perplexity_like_entries": pplx,
    }


def load_perplexity_prompts() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in PERPLEXITY_FILES:
        p = PROMPTS_DIR / name
        if p.exists():
            out[name] = p.read_text(encoding="utf-8").strip()
        else:
            out[name] = ""
    return out


def call_gemini_markdown(api_key: str, model: str, stats: dict[str, Any]) -> str:
    user = "統計JSON:\n" + json.dumps(stats, ensure_ascii=False, indent=2)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    params = {"key": api_key}
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": REPORT_SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 4096},
    }
    resp = requests.post(url, params=params, json=body, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"Gemini API HTTP {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Gemini が空応答")
    return parts[0].get("text", "").strip()


def call_claude_json(api_key: str, model: str, weekly_report: str, prompts: dict[str, str]) -> dict[str, str]:
    payload = {
        "weekly_report_ja": weekly_report,
        "current_perplexity_prompts": prompts,
    }
    user = (
        "以下の JSON を読み、Perplexity 用の1行プロンプトを改善してください。\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 8192,
        "system": CLAUDE_SYSTEM,
        "messages": [{"role": "user", "content": user}],
    }
    resp = requests.post(url, headers=headers, json=body, timeout=180)
    if resp.status_code >= 400:
        raise RuntimeError(f"Claude API HTTP {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    texts: list[str] = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
    raw = "\n".join(texts).strip()
    return _parse_claude_json(raw)


def _parse_claude_json(raw: str) -> dict[str, str]:
    raw = raw.strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise ValueError("Claude 応答から JSON を抽出できませんでした")
        obj = json.loads(m.group(0))
    out: dict[str, str] = {}
    for k in PERPLEXITY_FILES:
        if k in obj and isinstance(obj[k], str):
            out[k] = obj[k].strip()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="週次レポート + Claude による Perplexity プロンプト改善案")
    parser.add_argument("--out-dir", type=Path, required=True, help="成果物ディレクトリ")
    parser.add_argument("--days", type=int, default=7, help="集計に使う直近日数（id 内日付ベース・近似）")
    parser.add_argument("--dry-run", action="store_true", help="API を呼ばず統計と現行プロンプトだけ出力")
    parser.add_argument("--gemini-model", default=(os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL))
    parser.add_argument(
        "--claude-model",
        default=(os.getenv("ANTHROPIC_MODEL", "").strip() or DEFAULT_ANTHROPIC_MODEL),
    )
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    entries_path = ROOT / "data" / "entries.json"
    if not entries_path.exists():
        print("data/entries.json がありません", file=sys.stderr)
        sys.exit(1)
    db = json.loads(entries_path.read_text(encoding="utf-8"))
    entries = db.get("entries") or []
    stats = collect_stats(entries, days=args.days)
    (out_dir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    prompts = load_perplexity_prompts()
    (out_dir / "current_perplexity_prompts.json").write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    if args.dry_run:
        stub = (
            "# 週次レポート（dry-run）\n\n"
            f"- 総記事数: {stats['total_entries']}\n"
            f"- カテゴリ別件数: {stats['by_category']}\n"
            "- API は呼んでいません。\n"
        )
        (out_dir / "weekly_report_ja.md").write_text(stub, encoding="utf-8")
        print(f"dry-run 完了 → {out_dir}")
        return

    if not gemini_key:
        print("GEMINI_API_KEY 未設定: weekly_report_ja.md は stats から簡易生成のみ", file=sys.stderr)
        (out_dir / "weekly_report_ja.md").write_text(
            "# 週次レポート（API なし）\n\n```json\n"
            + json.dumps(stats, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
    else:
        try:
            report = call_gemini_markdown(gemini_key, args.gemini_model, stats)
        except Exception as e:
            print(f"Gemini 失敗 ({e}); 代替モデルを順に試します。", file=sys.stderr)
            report = None
            for m in ("gemini-2.5-flash-lite", "gemini-1.5-flash"):
                try:
                    report = call_gemini_markdown(gemini_key, m, stats)
                    print(f"Gemini 代替モデルで成功: {m}", file=sys.stderr)
                    break
                except Exception as e2:
                    print(f"  失敗: {m} ({e2})", file=sys.stderr)
            if report is None:
                raise
        (out_dir / "weekly_report_ja.md").write_text(report + "\n", encoding="utf-8")

    report_text = (out_dir / "weekly_report_ja.md").read_text(encoding="utf-8")

    if not anthropic_key:
        print("ANTHROPIC_API_KEY 未設定: プロンプト改善案はスキップ", file=sys.stderr)
        (out_dir / "claude_prompt_proposals.json").write_text("{}\n", encoding="utf-8")
        print(f"部分完了 → {out_dir}")
        return

    try:
        proposals = call_claude_json(anthropic_key, args.claude_model, report_text, prompts)
    except Exception as e:
        print(f"Claude 失敗: {e}", file=sys.stderr)
        sys.exit(1)

    (out_dir / "claude_prompt_proposals.json").write_text(
        json.dumps(proposals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    proposed_dir = out_dir / "proposed_prompts"
    proposed_dir.mkdir(exist_ok=True)
    for name, text in proposals.items():
        (proposed_dir / name).write_text(text + "\n", encoding="utf-8")

    print(f"完了: レポート + 提案 {len(proposals)} ファイル → {out_dir}")


if __name__ == "__main__":
    main()
