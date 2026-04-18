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
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
URL_CHECK_TIMEOUT = 12
URL_CHECK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JOI-PerplexityVerifier/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

MAX_PPLX_ARTICLE_AGE_DAYS = int(os.getenv("JOI_PPLX_MAX_ARTICLE_AGE_DAYS", "14") or "14")

ALLOWED_PRIMARY_CATEGORIES = ("cafe", "vtuber", "figure", "game", "anime", "other")
_ALLOWED_PRIMARY_SET = frozenset(ALLOWED_PRIMARY_CATEGORIES)


def normalize_primary_category(raw: Any, fallback: str) -> str:
    """Gemini やルールから来た文字列を許容カテゴリに収める。"""
    s = str(raw or "").strip().lower()
    if s in _ALLOWED_PRIMARY_SET:
        return s
    fb = str(fallback or "other").strip().lower()
    return fb if fb in _ALLOWED_PRIMARY_SET else "other"


def _entry_primary_fallback(entry: dict[str, Any]) -> str:
    cats = entry.get("categories")
    if isinstance(cats, list) and cats:
        return normalize_primary_category(cats[0], "other")
    return "other"


_GENERIC_THUMB_PATTERNS = (
    "like_on.png",
    "notop_catch",
    "apple-touch-icon",
    "favicon",
    "/logo",
    "og-image",
    "default",
    "noimage",
    "no_image",
    "dummy",
    "banner",
    ".svg",
)
_TITLE_STOPWORDS = (
    "開催",
    "開始",
    "決定",
    "発売",
    "予約",
    "再販",
    "公開",
    "発表",
    "決まる",
    "告知",
    "コラボ",
)

REVIEW_SYSTEM = """あなたは「Japan OTAKU Insider」という英語向け日本オタクニュースサイトの厳格な検閲担当です。
与えられた候補記事それぞれについて、サイトに載せるべきか boolean で判定します。

次のいずれかに該当する場合は ok=false にしてください（理由は reason_ja に短く日本語で）:
- 実在のニュース記事ページではなく、公式サイトのトップや一覧だけをURLにしており、タイトル・本文の具体的出来事を裏付けできない疑いが強い
- ゲーム枠なのにプロ野球・WBC・Baseball5 等の一般スポーツ実況・国際試合が主題
- コミケ・同人即売会の開催時期や回次が明らかに誤り（既知の史実と矛盾）
- イベント名・日付・場所の組み合わせがでっち上げっぽい、または確認不可能で危険
- オタク文化（アニメ・ゲーム・フィギュア・コラボカフェ・VTuber 等）と無関係

RSS 由来の具体的な製品発表・予約開始など、一次ソースらしいURLで裏付けできるものは ok=true でよい。
ただし url_status が 200 でない候補は必ず ok=false にしてください。
page_title が title_ja と噛み合わない（別記事に飛んでいる疑い）場合も ok=false にしてください。
published_date が取得できていて、直近のニュースとして古すぎる場合（例: 何年も前）も ok=false にしてください。
og_image が取れない/明らかに汎用画像しかない場合は、内容が検証不能として ok=false でよい。

各候補について、記事の内容（title_ja / description / URL・ドメイン）から最も適切な primary_category を1つ選んでください。
primary_category は次のいずれか1語のみ: cafe, vtuber, figure, game, anime, other
- cafe: コラボカフェ・カフェイベント・飲食コラボが主題
- vtuber: VTuber・にじさんじ・ホロライブ等の配信・グッズ・企画が主題
- figure: フィギュア・プラモデル・ホビー製品の予約・発売が主題
- game: ゲーム本体・DLC・ゲームイベントが主題
- anime: アニメ放送・映画・声優・制作ニュースが主題（グッズが主なら figure 寄りでもよい）
- other: 上記のどれにも明確に当てはまらない、または複数混在で一つに決められない

必ず次の JSON だけを返す（前後に説明文を付けない）:
{"decisions":[{"index":0,"ok":true,"reason_ja":"","primary_category":"game"}, ...]}
index は入力配列の 0 始まりの番号。全件分の decisions を含める。primary_category は必須。
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
        url = (src.get("url") or "")[:500]
        host = ""
        try:
            host = urlparse(url).netloc.lower()
        except Exception:
            host = ""
        verified = e.get("_url_verified") or {}
        compact.append(
            {
                "index": i,
                "id": e.get("id"),
                "source_id": e.get("_source_id"),
                "source_type": e.get("_source"),
                "source_domain": host,
                "categories": e.get("categories"),
                "title_ja": e.get("title_ja") or e.get("title"),
                "description": (e.get("description") or "")[:500],
                "url": url,
                "url_status": verified.get("status"),
                "final_url": (verified.get("final_url") or "")[:500],
                "page_title": (verified.get("page_title") or "")[:200],
                "published_date": verified.get("published_date"),
                "og_image": (verified.get("og_image") or "")[:500],
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
    """通過したエントリと、ログ用の行を返す。Perplexity 由来かつ通過分は primary_category で categories を上書きする。"""
    ok_by_index: dict[int, bool] = {}
    reasons: dict[int, str] = {}
    primary_by_index: dict[int, Any] = {}
    for d in decisions:
        if not isinstance(d, dict):
            continue
        idx = d.get("index")
        if isinstance(idx, int):
            ok_by_index[idx] = bool(d.get("ok"))
            reasons[idx] = str(d.get("reason_ja") or "")
            if "primary_category" in d:
                primary_by_index[idx] = d.get("primary_category")

    approved: list[dict[str, Any]] = []
    log_rows: list[dict[str, Any]] = []
    for i, e in enumerate(entries):
        ok = ok_by_index.get(i, False)
        old_primary = _entry_primary_fallback(e)
        raw_pc = primary_by_index.get(i)
        new_pc = normalize_primary_category(raw_pc, old_primary)

        if e.get("_source") == "perplexity" and ok:
            if new_pc != old_primary:
                e["_category_from_search"] = old_primary
            e["categories"] = [new_pc]
            e["_category_assigned_by"] = "gemini"
            e["tags"] = [new_pc]

        src = e.get("source") or {}
        verified = e.get("_url_verified") or {}
        row = {
            "index": i,
            "id": e.get("id"),
            "ok": ok,
            "reason_ja": reasons.get(i, "(判定なし)"),
            "primary_category": new_pc,
            "category_before": old_primary,
            "source_url": (src.get("url") or "") if isinstance(src, dict) else str(src),
            "source_type": e.get("_source"),
            "source_id": e.get("_source_id"),
            "url_status": verified.get("status"),
            "final_url": verified.get("final_url"),
            "page_title": verified.get("page_title"),
            "published_date": verified.get("published_date"),
            "og_image": verified.get("og_image"),
        }
        log_rows.append(row)
        if ok:
            approved.append(e)
    return approved, log_rows


def _fill_missing_primary_categories(decisions: list[dict[str, Any]], entries: list[dict[str, Any]]) -> None:
    """Gemini が primary_category を省略した場合にフォールバックする。"""
    for d in decisions:
        if not isinstance(d, dict):
            continue
        idx = d.get("index")
        if not isinstance(idx, int) or idx < 0 or idx >= len(entries):
            continue
        if not d.get("primary_category"):
            d["primary_category"] = _entry_primary_fallback(entries[idx])


def _url_http_status(url: str, cache: dict[str, tuple[int | None, str, str]]) -> tuple[int | None, str, str]:
    """URL の HTTP status / final_url / error を返す（同一URLはキャッシュ）。"""
    if url in cache:
        return cache[url]
    try:
        resp = requests.get(
            url,
            headers=URL_CHECK_HEADERS,
            timeout=URL_CHECK_TIMEOUT,
            allow_redirects=True,
        )
        item = (resp.status_code, resp.url, "")
    except Exception as e:
        item = (None, url, f"{type(e).__name__}: {e}")
    cache[url] = item
    return item


def _looks_generic_image(url: str) -> bool:
    u = (url or "").lower()
    if not u:
        return True
    return any(p in u for p in _GENERIC_THUMB_PATTERNS)


def _extract_page_title(html: str) -> str:
    m = re.search(r'<meta[^>]+property=[\'"]og:title[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', html, re.I)
    if m:
        return (m.group(1) or "").strip()
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    return (m.group(1) or "").strip() if m else ""


def _extract_og_image(html: str) -> str:
    m = re.search(
        r'<meta[^>]+property=[\'"]og:image(?::secure_url)?[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
        html,
        re.I,
    )
    if m:
        return (m.group(1) or "").strip()
    m = re.search(r'<meta[^>]+name=[\'"]twitter:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', html, re.I)
    return (m.group(1) or "").strip() if m else ""


def _parse_published_date(html: str) -> str:
    m = re.search(
        r'<meta[^>]+property=[\'"]article:published_time[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
        html,
        re.I,
    )
    if m:
        return (m.group(1) or "").strip()
    m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html, re.I)
    if m:
        return (m.group(1) or "").strip()
    m = re.search(r"<time[^>]+datetime=[\"']([^\"']+)[\"']", html, re.I)
    if m:
        return (m.group(1) or "").strip()
    return ""


def _date_too_old(iso_like: str, max_age_days: int) -> bool:
    if not iso_like:
        return False
    try:
        s = iso_like.strip().replace("/", "-")
        # ISO8601 full
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            d = dt.date()
        else:
            d = datetime.fromisoformat(s[:10]).date()
        today = datetime.now().astimezone().date()
        return (today - d).days > max_age_days
    except Exception:
        return False


def _extract_title_tokens(text: str) -> set[str]:
    t = (text or "").strip()
    if not t:
        return set()
    tokens: set[str] = set()
    for m in re.finditer(r"[A-Za-z0-9]+|[\u3040-\u30ff\u4e00-\u9fff]{2,}", t):
        tok = m.group(0)
        if not tok or tok in _TITLE_STOPWORDS:
            continue
        if len(tok) >= 2:
            tokens.add(tok)
    return tokens


def _title_mismatch(title_ja: str, page_title: str) -> bool:
    tj = (title_ja or "").strip()
    pt = (page_title or "").strip()
    if not (tj and pt):
        return False
    a = _extract_title_tokens(tj)
    b = _extract_title_tokens(pt)
    if not a or not b:
        return False
    return len(a & b) == 0


def _fetch_page_meta(
    url: str,
    *,
    url_status_cache: dict[str, tuple[int | None, str, str]],
    page_meta_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if url in page_meta_cache:
        return page_meta_cache[url]
    status, final_url, err = _url_http_status(url, url_status_cache)
    meta: dict[str, Any] = {"status": status, "final_url": final_url, "error": err}
    if status != 200:
        page_meta_cache[url] = meta
        return meta
    try:
        resp = requests.get(final_url, headers=URL_CHECK_HEADERS, timeout=URL_CHECK_TIMEOUT, allow_redirects=True)
        html = resp.text or ""
    except Exception as e:
        meta["status"] = None
        meta["error"] = f"{type(e).__name__}: {e}"
        page_meta_cache[url] = meta
        return meta
    meta["page_title"] = _extract_page_title(html)
    meta["published_date"] = _parse_published_date(html)
    meta["og_image"] = _extract_og_image(html)
    page_meta_cache[url] = meta
    return meta


def _prefilter_reason(
    entry: dict[str, Any],
    *,
    url_status_cache: dict[str, tuple[int | None, str, str]],
    page_meta_cache: dict[str, dict[str, Any]],
    max_age_days: int,
) -> str | None:
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
        meta = _fetch_page_meta(url, url_status_cache=url_status_cache, page_meta_cache=page_meta_cache)
        entry["_url_verified"] = meta
        status = meta.get("status")
        final_url = meta.get("final_url") or url
        if status != 200:
            err = meta.get("error") or ""
            if status is None:
                return f"Perplexity由来URLの疎通失敗: {str(err)[:120]}"
            return f"Perplexity由来URLがHTTP {status}: {str(final_url)[:120]}"
        page_title = meta.get("page_title") or ""
        if _title_mismatch(title, page_title):
            return f"Perplexity由来URLの内容不一致疑い: page_title={page_title[:60]}"
        pub = meta.get("published_date") or ""
        if pub and _date_too_old(pub, max_age_days=max_age_days):
            return f"Perplexity由来URLが古い: published_date={str(pub)[:20]}"
        og = meta.get("og_image") or ""
        thumb = (entry.get("thumbnail") or "").strip()
        if og and not _looks_generic_image(og):
            if (not thumb) or _looks_generic_image(thumb):
                entry["thumbnail"] = og
        else:
            if (not thumb) or _looks_generic_image(thumb):
                return "Perplexity由来URLでOG画像取得不可"
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
    url_status_cache: dict[str, tuple[int | None, str, str]] = {}
    page_meta_cache: dict[str, dict[str, Any]] = {}
    review_candidates: list[tuple[int, dict[str, Any]]] = []
    for i, e in enumerate(entries):
        reason = _prefilter_reason(
            e,
            url_status_cache=url_status_cache,
            page_meta_cache=page_meta_cache,
            max_age_days=MAX_PPLX_ARTICLE_AGE_DAYS,
        )
        if reason:
            pre_reject_indices[i] = reason
        else:
            review_candidates.append((i, e))

    if args.dry_run:
        # dry-run でも prefilter は有効にして「落ちるべきものが落ちるか」を確認できるようにする
        decisions = []
        for i in range(len(entries)):
            fb = _entry_primary_fallback(entries[i])
            if i in pre_reject_indices:
                decisions.append(
                    {"index": i, "ok": False, "reason_ja": f"dry-run: {pre_reject_indices[i]}", "primary_category": fb}
                )
            else:
                decisions.append({"index": i, "ok": True, "reason_ja": "dry-run", "primary_category": fb})
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
            decisions.append(
                {
                    "index": idx,
                    "ok": False,
                    "reason_ja": reason,
                    "primary_category": _entry_primary_fallback(entries[idx]),
                }
            )

    _fill_missing_primary_categories(decisions, entries)
    approved, log_rows = apply_decisions(entries, decisions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(json.dumps(log_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"検閲: 入力 {len(entries)} 件 → 通過 {len(approved)} 件 → {args.output}")


if __name__ == "__main__":
    main()
