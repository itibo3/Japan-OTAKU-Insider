#!/usr/bin/env python3
"""
Google Search Console: 日次クリック数を取得し、期間サマリを標準出力＋ファイルに書く。

用途:
- 「検索からのクリックが本当に落ちたか」を GA4 ではなく GSC 一次データで確認する
- GitHub Actions（手動）で Artifact として保存

前提:
- 環境変数 GA4_CREDENTIALS_JSON にサービスアカウント JSON（全文）
- そのサービスアカウントのメールアドレスを Search Console の対象プロパティに「ユーザー」として追加済み
  （権限: 閲覧で可）
- GSC_SITE_URL … 例: https://otaku.eidosfrontier.com/ （末尾スラッシュ推奨）
  ドメインプロパティの場合は sc-domain:example.com 形式

依存: requirements-ci.txt（google-auth, requests）と同じ
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GSC_QUERY_TMPL = "https://searchconsole.googleapis.com/v1/sites/{site_enc}/searchAnalytics/query"


def _access_token(creds_json: str) -> str:
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=[GSC_SCOPE],
    )
    creds.refresh(Request())
    if not creds.token:
        raise RuntimeError("Search Console 用トークン取得に失敗しました")
    return creds.token


def fetch_daily_clicks(
    *,
    creds_json: str,
    site_url: str,
    start: date,
    end: date,
) -> list[dict]:
    """
    日次の clicks / impressions を返す（GSC searchAnalytics/query）。
    """
    token = _access_token(creds_json)
    site_enc = urllib.parse.quote(site_url, safe="")
    url = GSC_QUERY_TMPL.format(site_enc=site_enc)
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["date"],
        "rowLimit": 25000,
        "dataState": "final",
    }
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=120,
    )
    if resp.status_code == 403:
        raise RuntimeError(
            "HTTP 403: Search Console へのアクセスが拒否されました。\n"
            "サービスアカウントのメール（client_email）を、GSC の該当プロパティに「ユーザー」として追加してください。\n"
            f"siteUrl={site_url!r}"
        )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"searchAnalytics/query HTTP {resp.status_code}: {resp.text[:500]}"
        )
    data = resp.json() or {}
    rows = data.get("rows") or []
    out: list[dict] = []
    for row in rows:
        keys = row.get("keys") or []
        day = keys[0] if keys else ""
        out.append(
            {
                "date": day,
                "clicks": float(row.get("clicks") or 0),
                "impressions": float(row.get("impressions") or 0),
                "ctr": float(row.get("ctr") or 0),
                "position": float(row.get("position") or 0),
            }
        )
    out.sort(key=lambda r: r["date"])
    return out


def _month_key(iso_day: str) -> str:
    return iso_day[:7] if len(iso_day) >= 7 else iso_day


def aggregate_by_month(rows: list[dict]) -> list[dict]:
    clicks_m: dict[str, float] = defaultdict(float)
    impr_m: dict[str, float] = defaultdict(float)
    for r in rows:
        mk = _month_key(str(r.get("date") or ""))
        if not mk:
            continue
        clicks_m[mk] += r["clicks"]
        impr_m[mk] += r["impressions"]
    months = sorted(clicks_m.keys())
    return [
        {
            "month": m,
            "clicks": round(clicks_m[m], 1),
            "impressions": round(impr_m[m], 1),
        }
        for m in months
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Console クリック推移レポート")
    parser.add_argument(
        "--months",
        type=int,
        default=16,
        help="何ヶ月分さかのぼるか（おおよそ 30日×months）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifact-out"),
        help="レポート JSON/TXT の出力先",
    )
    args = parser.parse_args()

    creds_json = os.environ.get("GA4_CREDENTIALS_JSON", "").strip()
    # Actions で Secret 未設定だと空文字になるため or で既定に落とす
    site_url = (
        os.environ.get("GSC_SITE_URL", "").strip()
        or "https://otaku.eidosfrontier.com/"
    )
    if not creds_json:
        print("GA4_CREDENTIALS_JSON が未設定です。", file=sys.stderr)
        return 2
    if not site_url:
        print("GSC_SITE_URL が空です。", file=sys.stderr)
        return 2

    end = date.today()
    approx_days = max(30, args.months * 31)
    start = end - timedelta(days=approx_days)

    print(f"Search Console 取得: {start} .. {end}  site={site_url!r}")
    try:
        rows = fetch_daily_clicks(
            creds_json=creds_json,
            site_url=site_url,
            start=start,
            end=end,
        )
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    by_month = aggregate_by_month(rows)
    total_clicks = sum(r["clicks"] for r in rows)
    total_impr = sum(r["impressions"] for r in rows)

    lines = [
        "=== Search Console クリック推移（日次集計の合算） ===",
        f"property: {site_url}",
        f"range: {start} .. {end} (approx {args.months} months lookback)",
        f"days_with_data: {len(rows)}",
        f"total_clicks: {total_clicks:.0f}",
        f"total_impressions: {total_impr:.0f}",
        "",
        "--- 月別クリック（参考） ---",
    ]
    for m in by_month:
        lines.append(f"  {m['month']}: clicks={m['clicks']:.0f}  impressions={m['impressions']:.0f}")
    lines.append("")
    lines.append("（先頭・末尾の日次サンプル）")
    for r in rows[:5]:
        lines.append(f"  {r['date']}: clicks={r['clicks']:.0f}  impr={r['impressions']:.0f}")
    if len(rows) > 10:
        lines.append("  ...")
    for r in rows[-5:]:
        lines.append(f"  {r['date']}: clicks={r['clicks']:.0f}  impr={r['impressions']:.0f}")

    text = "\n".join(lines) + "\n"
    print(text)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.out_dir / "gsc_clicks_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "site_url": site_url,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "days": len(rows),
                "total_clicks": total_clicks,
                "total_impressions": total_impr,
                "by_month": by_month,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "gsc_clicks_daily.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "gsc_clicks_report.txt").write_text(text, encoding="utf-8")
    print(f"Wrote: {summary_path}, gsc_clicks_daily.json, gsc_clicks_report.txt", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
