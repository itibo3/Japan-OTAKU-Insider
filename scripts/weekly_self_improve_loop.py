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
from datetime import date, datetime, timedelta, timezone
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
DEFAULT_OPUS_MODEL = "claude-opus-4-6"
DEFAULT_SONNET_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_PERPLEXITY_MODEL = "sonar-pro"

REPORT_SYSTEM = """あなたは Japan OTAKU Insider の運用アナリストです。
与えられた統計（GA4 + 内部運用データ）を読み、週次の振り返りレポートを日本語Markdownで書いてください。
必ず次を含めてください:
- 先週の要点（3点以内）
- 良かった点 / 悪化点
- Perplexity運用リスク（幻覚・誤カテゴリ）の短い評価
- 次週アクション（最大3つ、具体）
憶測で存在しない数字・イベントを作らないこと。
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

JOI_SYSTEM = """あなたは Japan OTAKU Insider の編集長です。
受け取った週次分析と「直近記事サンプル」をもとに、サイト掲載用の「週間JOI通信」を作成してください。
出力は必ず JSON のみ:
{
  "title_ja": "...",
  "title_en": "...",
  "summary_ja": "...",
  "summary_en": "...",
  "body_ja_markdown": "...",
  "body_en_markdown": "...",
  "header_image_prompt_en": "...",
  "tags": ["weekly-joi","otaku-news","analytics"]
}
要件:
- これは「運用KPIレポート」ではなく、ヲタ向けの週刊かわら版（ホットニュースまとめ）
- 「今週アツかった話題」「注目ニュース振り返り」を中心に、読んで楽しい文体で書く
- body は見出し付き Markdown で、最低 4 セクション構成にする
- 直近記事サンプルから最低 5 件以上、具体的な話題・作品名・イベント名を拾って紹介する
- 最低でも次の3系統を含める:
  1) アニメ/ゲームの今週ホット話題（例: 話題回・PV・配信開始）
  2) フィギュア/グッズの発売・予約・再販の注目
  3) イベント/コスプレ/コラボカフェなど現地系トピック
- 単なる数値列挙は避け、必要な数字は文脈の補足として短く使う
- 最後に「来週の注目ポイント」を 2〜3 個入れる
- 断定しすぎず、誤情報を作らない（入力にない固有名詞や日付をでっち上げない）
- 禁止: 「アクティブユーザー◯%減」「PV◯%減」などKPI中心の見出しを本文主役にすること
- header_image_prompt_en には、記事見出し画像を生成するための英語プロンプトを1文で入れる
"""


def _contains_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text or ""))


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


def _ga4_access_token(creds_json: str) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    creds.refresh(Request())
    if not creds.token:
        raise RuntimeError("GA4 token 取得失敗")
    return creds.token


def fetch_ga4_summary(*, creds_json: str, property_id: str, days: int = 7) -> dict[str, Any]:
    if not (creds_json and property_id):
        return {"status": "skipped", "reason": "missing credentials or property id"}
    token = _ga4_access_token(creds_json)
    today = date.today()
    start = (today - timedelta(days=days)).isoformat()
    end = (today - timedelta(days=1)).isoformat()
    prev_start = (today - timedelta(days=days * 2)).isoformat()
    prev_end = (today - timedelta(days=days + 1)).isoformat()

    def run(start_date: str, end_date: str) -> dict[str, float]:
        resp = requests.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                "metrics": [
                    {"name": "activeUsers"},
                    {"name": "sessions"},
                    {"name": "screenPageViews"},
                    {"name": "engagementRate"},
                ],
            },
            timeout=60,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"GA4 runReport HTTP {resp.status_code}: {resp.text[:240]}")
        rows = (resp.json() or {}).get("rows") or []
        if not rows:
            return {"activeUsers": 0.0, "sessions": 0.0, "screenPageViews": 0.0, "engagementRate": 0.0}
        vals = rows[0].get("metricValues") or []
        names = ["activeUsers", "sessions", "screenPageViews", "engagementRate"]
        out: dict[str, float] = {}
        for i, n in enumerate(names):
            try:
                out[n] = float((vals[i] or {}).get("value") or 0)
            except Exception:
                out[n] = 0.0
        return out

    current = run(start, end)
    prev = run(prev_start, prev_end)
    delta = {k: current.get(k, 0.0) - prev.get(k, 0.0) for k in current.keys()}
    return {
        "status": "ok",
        "window": {"start": start, "end": end},
        "current": current,
        "previous": prev,
        "delta": delta,
    }


def collect_internal_pipeline_stats(entries: list[dict[str, Any]], days: int = 7) -> dict[str, Any]:
    cutoff = datetime.now(JST).date() - timedelta(days=days)
    recent = []
    untranslated = 0
    by_source: dict[str, int] = {}
    pplx_recent = 0
    for e in entries:
        src = e.get("_source_id", "(unknown)")
        by_source[src] = by_source.get(src, 0) + 1
        title = (e.get("title") or "").strip()
        desc = (e.get("description") or "").strip()
        if title.startswith("[未翻訳]") or desc.startswith("[未翻訳]"):
            untranslated += 1
        ds = _id_date(e)
        if not ds:
            continue
        try:
            d = datetime(int(ds[:4]), int(ds[4:6]), int(ds[6:8])).date()
        except Exception:
            continue
        if d >= cutoff:
            recent.append(e)
            if "-pplx-" in (e.get("id") or "") or e.get("_source") == "perplexity":
                pplx_recent += 1
    top_sources = sorted(by_source.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "recent_entries": len(recent),
        "recent_perplexity_entries": pplx_recent,
        "untranslated_marker_entries": untranslated,
        "top_sources": top_sources,
    }


def collect_recent_hot_topics(entries: list[dict[str, Any]], days: int = 7, limit: int = 40) -> list[dict[str, Any]]:
    """JOI通信用に、直近記事の見出しサンプルを抽出する。"""
    cutoff = datetime.now(JST).date() - timedelta(days=days)
    picked: list[tuple[str, dict[str, Any]]] = []
    seen_title: set[str] = set()
    for e in entries:
        if e.get("_source") == "joi-weekly" or e.get("_source_id") == "joi-weekly":
            continue
        ds = _id_date(e)
        if not ds:
            continue
        try:
            d = datetime(int(ds[:4]), int(ds[4:6]), int(ds[6:8])).date()
        except Exception:
            continue
        if d < cutoff:
            continue
        title = (e.get("title_ja") or e.get("title") or "").strip()
        if not title or title in seen_title:
            continue
        seen_title.add(title)
        picked.append(
            (
                ds,
                {
                    "id": e.get("id"),
                    "date": ds,
                    "title_ja": title,
                    "categories": e.get("categories") or [],
                    "source_url": ((e.get("source") or {}).get("url") or ""),
                    "source_id": e.get("_source_id", ""),
                },
            )
        )
    picked.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in picked[:limit]]


def fetch_perplexity_weekly_highlights(*, api_key: str, model: str = DEFAULT_PERPLEXITY_MODEL) -> dict[str, Any]:
    """Perplexityで今週のヲタニュース要点を補助取得する（失敗時は skipped を返す）。"""
    if not api_key:
        return {"status": "skipped", "reason": "missing PERPLEXITY_API_KEY"}
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Japanese otaku weekly editor. "
                    "Return concise highlights from this week in Japan only. "
                    "Output must be JSON object only with keys: anime_game, figure_goods, events_cosplay, note."
                ),
            },
            {
                "role": "user",
                "content": (
                    "今週の日本オタクニュースの注目トピックを要約して。"
                    "アニメ/ゲーム、フィギュア/グッズ、イベント/コスプレの3軸で各3件程度。"
                    "推測は禁止、実在記事ベースで。JSONのみ返して。"
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
        "search_recency_filter": "week",
        "search_language_filter": ["ja"],
        "web_search_options": {"user_location": {"country": "JP"}},
    }
    resp = requests.post(
        "https://api.perplexity.ai/v1/sonar",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if resp.status_code >= 400:
        return {"status": "error", "reason": f"HTTP {resp.status_code}", "body": resp.text[:300]}
    data = resp.json() or {}
    text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    if not text:
        return {"status": "error", "reason": "empty response"}
    try:
        obj = _parse_json_object(text)
    except Exception as e:
        return {"status": "error", "reason": f"json parse failed: {e}", "raw": text[:400]}
    return {"status": "ok", "highlights": obj}


def call_anthropic_text(*, api_key: str, model: str, system: str, user_text: str, max_tokens: int = 8192) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_text}],
        },
        timeout=180,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Anthropic API HTTP {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    texts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
    out = "\n".join(texts).strip()
    if not out:
        raise RuntimeError("Anthropic 応答が空")
    return out


def ensure_joi_english_fields(*, api_key: str, model: str, joi_obj: dict[str, Any]) -> dict[str, Any]:
    """JOI出力に英語本文が不足/日本語混入している場合に補完する。"""
    body_ja = str(joi_obj.get("body_ja_markdown") or "").strip()
    summary_ja = str(joi_obj.get("summary_ja") or "").strip()
    summary_en = str(joi_obj.get("summary_en") or "").strip()
    body_en = str(joi_obj.get("body_en_markdown") or "").strip()

    # summary_en が空または日本語なら補完
    if (not summary_en) or _contains_japanese(summary_en):
        user = (
            "次の日本語要約を、ニュース記事向けの自然な英語1-2文に翻訳してください。"
            "出力は本文のみ。\n\n"
            f"{summary_ja}"
        )
        summary_en = call_anthropic_text(
            api_key=api_key,
            model=model,
            system="You are a professional Japanese-to-English editor for otaku news.",
            user_text=user,
            max_tokens=300,
        ).strip()
        joi_obj["summary_en"] = summary_en

    # body_en が空または日本語なら補完
    if (not body_en) or _contains_japanese(body_en):
        src = body_ja or summary_ja
        user = (
            "次の日本語Markdownを英語Markdownへ翻訳してください。"
            "見出し構造（#, ##, ###, 箇条書き）を保ち、自然な英語にすること。"
            "出力はMarkdown本文のみ。\n\n"
            f"{src}"
        )
        body_en = call_anthropic_text(
            api_key=api_key,
            model=model,
            system="You are a professional Japanese-to-English editor for otaku weekly newsletters.",
            user_text=user,
            max_tokens=3500,
        ).strip()
        joi_obj["body_en_markdown"] = body_en
    return joi_obj


def call_claude_json(api_key: str, model: str, weekly_report: str, prompts: dict[str, str]) -> dict[str, str]:
    payload = {
        "weekly_report_ja": weekly_report,
        "current_perplexity_prompts": prompts,
    }
    user = (
        "以下の JSON を読み、Perplexity 用の1行プロンプトを改善してください。\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    raw = call_anthropic_text(api_key=api_key, model=model, system=CLAUDE_SYSTEM, user_text=user, max_tokens=8192)
    return _parse_claude_json(raw)


def _parse_json_object(raw: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw.strip())
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        return json.loads(m.group(0))
    raise ValueError("JSON オブジェクトを抽出できませんでした")


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


def _fallback_prompt_proposals() -> dict[str, str]:
    """API 未接続時でも空JSONにせず、保守的な検索ワード案を返す。"""
    return {
        "perplexity_cafe.md": (
            "site:collabo-cafe.com OR site:prtimes.jp anime collaboration cafe 開催 予約 メニュー 特典 期間"
        ),
        "perplexity_vtuber.md": (
            "site:nijisanji.jp OR site:hololive.hololivepro.com OR site:prtimes.jp VTuber 新衣装 3D 配信 告知"
        ),
        "perplexity_figure.md": (
            "site:goodsmile.info OR site:kotobukiya.co.jp OR site:amiami.jp フィギュア 予約開始 発売日 再販"
        ),
        "perplexity_game.md": (
            "site:4gamer.net OR site:famitsu.com OR site:dengekionline.com ゲーム 発売日 アップデート DLC 体験版"
        ),
        "perplexity_anime.md": (
            "site:natalie.mu/comic OR site:animeanime.jp アニメ 新作 放送日 PV キービジュアル キャスト"
        ),
        "perplexity_other.md": (
            "site:prtimes.jp OR site:akihabara-bc.jp otaku event exhibition pop-up 開催 日程 会場"
        ),
    }


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
    parser.add_argument(
        "--opus-model",
        default=(os.getenv("ANTHROPIC_OPUS_MODEL", "").strip() or DEFAULT_OPUS_MODEL),
        help="週次分析/JOI通信に使う Opus モデル",
    )
    parser.add_argument(
        "--sonnet-model",
        default=(os.getenv("ANTHROPIC_SONNET_MODEL", "").strip() or DEFAULT_SONNET_MODEL),
        help="週次分析/改善案に優先利用する Sonnet モデル",
    )
    parser.add_argument("--emit-joi-json", type=Path, help="JOI記事素材JSONの出力先")
    parser.add_argument(
        "--require-anthropic",
        action="store_true",
        help="ANTHROPIC_API_KEY 未設定を許容せず、エラーで終了する",
    )
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    llm_trace: dict[str, Any] = {
        "anthropic_key_present": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
        "report_attempts": [],
        "proposal_attempts": [],
        "joi_attempts": [],
    }

    entries_path = ROOT / "data" / "entries.json"
    if not entries_path.exists():
        print("data/entries.json がありません", file=sys.stderr)
        sys.exit(1)
    db = json.loads(entries_path.read_text(encoding="utf-8"))
    entries = db.get("entries") or []
    base_stats = collect_stats(entries, days=args.days)
    internal_stats = collect_internal_pipeline_stats(entries, days=args.days)
    ga4_stats = fetch_ga4_summary(
        creds_json=os.getenv("GA4_CREDENTIALS_JSON", "").strip(),
        property_id=os.getenv("GA4_PROPERTY_ID", "").strip(),
        days=args.days,
    )
    hot_topics = collect_recent_hot_topics(entries, days=args.days, limit=40)
    perplexity_weekly = fetch_perplexity_weekly_highlights(
        api_key=os.getenv("PERPLEXITY_API_KEY", "").strip(),
        model=(os.getenv("PERPLEXITY_MODEL", "").strip() or DEFAULT_PERPLEXITY_MODEL),
    )
    stats = {
        "base": base_stats,
        "internal": internal_stats,
        "ga4": ga4_stats,
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    prompts = load_perplexity_prompts()
    (out_dir / "current_perplexity_prompts.json").write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    if args.dry_run:
        stub = (
            "# 週次レポート（dry-run）\n\n"
            f"- 総記事数: {base_stats['total_entries']}\n"
            f"- カテゴリ別件数: {base_stats['by_category']}\n"
            f"- 直近{args.days}日投稿: {internal_stats['recent_entries']}\n"
            "- API は呼んでいません。\n"
        )
        (out_dir / "weekly_report_ja.md").write_text(stub, encoding="utf-8")
        if args.emit_joi_json:
            args.emit_joi_json.parent.mkdir(parents=True, exist_ok=True)
            args.emit_joi_json.write_text(
                json.dumps(
                    {
                        "title_ja": f"週間JOI通信（{datetime.now(JST).strftime('%Y-%m-%d')}）",
                        "title_en": f"Weekly JOI Bulletin ({datetime.now(JST).strftime('%Y-%m-%d')})",
                        "summary_ja": "dry-run のためダミー本文です。",
                        "summary_en": "Dry-run generated placeholder.",
                        "body_ja_markdown": "# 週間JOI通信\n\ndry-run のため本文は未生成です。",
                        "tags": ["weekly-joi", "otaku-news", "analytics"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        print(f"dry-run 完了 → {out_dir}")
        return

    if not anthropic_key:
        print("ANTHROPIC_API_KEY 未設定: レポート/改善案/JOI通信は簡易出力", file=sys.stderr)
        if args.require_anthropic:
            print("--require-anthropic が有効のため終了します", file=sys.stderr)
            (out_dir / "llm_trace.json").write_text(
                json.dumps({**llm_trace, "error": "missing ANTHROPIC_API_KEY"}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            sys.exit(2)
        (out_dir / "weekly_report_ja.md").write_text(
            "# 週次レポート（API なし）\n\n```json\n"
            + json.dumps(stats, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        fallback = _fallback_prompt_proposals()
        (out_dir / "claude_prompt_proposals.json").write_text(
            json.dumps(fallback, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if args.emit_joi_json:
            args.emit_joi_json.parent.mkdir(parents=True, exist_ok=True)
            args.emit_joi_json.write_text(
                json.dumps(
                    {
                        "title_ja": f"週間JOI通信（{datetime.now(JST).strftime('%Y-%m-%d')}）",
                        "title_en": f"Weekly JOI Bulletin ({datetime.now(JST).strftime('%Y-%m-%d')})",
                        "summary_ja": "API未設定のため簡易生成。",
                        "summary_en": "Fallback report without API.",
                        "body_ja_markdown": "# 週間JOI通信\n\nAPI未設定のため簡易生成です。",
                        "tags": ["weekly-joi", "otaku-news", "analytics"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        (out_dir / "llm_trace.json").write_text(
            json.dumps({**llm_trace, "mode": "fallback_without_anthropic"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"部分完了 → {out_dir}")
        return

    # Sonnet 優先で週次分析レポートを生成（失敗時 Opus）
    report_user = "統計JSON:\n" + json.dumps(stats, ensure_ascii=False, indent=2)
    try:
        llm_trace["report_attempts"].append({"model": args.sonnet_model, "status": "try"})
        report = call_anthropic_text(
            api_key=anthropic_key,
            model=args.sonnet_model,
            system=REPORT_SYSTEM,
            user_text=report_user,
            max_tokens=4096,
        )
        llm_trace["report_attempts"][-1]["status"] = "ok"
    except Exception as e:
        llm_trace["report_attempts"][-1]["status"] = "error"
        llm_trace["report_attempts"][-1]["error"] = str(e)
        print(f"Sonnet 週次レポート失敗 ({e}); Opus へフォールバック", file=sys.stderr)
        llm_trace["report_attempts"].append({"model": args.opus_model, "status": "try"})
        report = call_anthropic_text(
            api_key=anthropic_key,
            model=args.opus_model,
            system=REPORT_SYSTEM,
            user_text=report_user,
            max_tokens=4096,
        )
        llm_trace["report_attempts"][-1]["status"] = "ok"
    (out_dir / "weekly_report_ja.md").write_text(report + "\n", encoding="utf-8")

    report_text = (out_dir / "weekly_report_ja.md").read_text(encoding="utf-8")

    # 検索ワード改善案（Artifactのみ）
    try:
        llm_trace["proposal_attempts"].append({"model": args.sonnet_model, "status": "try"})
        proposals = call_claude_json(anthropic_key, args.sonnet_model, report_text, prompts)
        llm_trace["proposal_attempts"][-1]["status"] = "ok"
    except Exception as e:
        llm_trace["proposal_attempts"][-1]["status"] = "error"
        llm_trace["proposal_attempts"][-1]["error"] = str(e)
        print(f"Sonnet 改善案失敗 ({e}); Opus へフォールバック", file=sys.stderr)
        llm_trace["proposal_attempts"].append({"model": args.opus_model, "status": "try"})
        proposals = call_claude_json(anthropic_key, args.opus_model, report_text, prompts)
        llm_trace["proposal_attempts"][-1]["status"] = "ok"

    (out_dir / "claude_prompt_proposals.json").write_text(
        json.dumps(proposals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    proposed_dir = out_dir / "proposed_prompts"
    proposed_dir.mkdir(exist_ok=True)
    for name, text in proposals.items():
        (proposed_dir / name).write_text(text + "\n", encoding="utf-8")

    # JOI通信の素材JSONを生成（後続スクリプトで entries 形式へ変換）
    joi_user = (
        "編集ガイド:\n"
        "これはヲタ向けの今週ニュースかわら版。KPI解説ではなく、今週の具体話題を中心に書くこと。\n"
        "\n\n直近記事サンプル（最優先で参照）:\n"
        + json.dumps(hot_topics, ensure_ascii=False, indent=2)
        + "\n\nPerplexity 週次ハイライト（補助。status=ok の場合のみ参照）:\n"
        + json.dumps(perplexity_weekly, ensure_ascii=False, indent=2)
        + "\n\n週次分析レポート（参考。本文主役にしない）:\n"
        + report_text
        + "\n\n補助統計:\n"
        + json.dumps(stats, ensure_ascii=False, indent=2)
    )
    try:
        llm_trace["joi_attempts"].append({"model": args.sonnet_model, "status": "try"})
        joi_raw = call_anthropic_text(
            api_key=anthropic_key,
            model=args.sonnet_model,
            system=JOI_SYSTEM,
            user_text=joi_user,
            max_tokens=4096,
        )
        llm_trace["joi_attempts"][-1]["status"] = "ok"
    except Exception as e:
        llm_trace["joi_attempts"][-1]["status"] = "error"
        llm_trace["joi_attempts"][-1]["error"] = str(e)
        print(f"Sonnet JOI通信失敗 ({e}); Opus へフォールバック", file=sys.stderr)
        llm_trace["joi_attempts"].append({"model": args.opus_model, "status": "try"})
        joi_raw = call_anthropic_text(
            api_key=anthropic_key,
            model=args.opus_model,
            system=JOI_SYSTEM,
            user_text=joi_user,
            max_tokens=4096,
        )
        llm_trace["joi_attempts"][-1]["status"] = "ok"
    joi_obj = _parse_json_object(joi_raw)
    try:
        joi_obj = ensure_joi_english_fields(api_key=anthropic_key, model=args.sonnet_model, joi_obj=joi_obj)
    except Exception as e:
        print(f"JOI英語補完失敗 ({e}); 既存値で継続", file=sys.stderr)
    joi_path = args.emit_joi_json or (out_dir / "joi_entry_source.json")
    joi_path.parent.mkdir(parents=True, exist_ok=True)
    joi_path.write_text(json.dumps(joi_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "llm_trace.json").write_text(
        json.dumps(llm_trace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"完了: レポート + 提案 {len(proposals)} + JOI素材 -> {out_dir}")
    return


if __name__ == "__main__":
    main()
