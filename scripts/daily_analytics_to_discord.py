#!/usr/bin/env python3
"""
GA4 + YouTube の前日比を Discord に日次通知する。
"""

from __future__ import annotations

import argparse
import os
from datetime import date

import requests

from analytics_clients import (
    fetch_ga4_daily,
    fetch_youtube_daily,
    fetch_youtube_shorts_views_daily,
    previous_dates,
)


def _fmt_delta(curr: float, prev: float) -> str:
    diff = curr - prev
    sign = "+" if diff >= 0 else "-"
    return f"{curr:.0f} ({sign}{abs(diff):.0f})"


def _line(name: str, curr: float, prev: float) -> str:
    return f"- {name}: {_fmt_delta(curr, prev)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="日次アナリティクスをDiscord通知")
    parser.add_argument("--webhook-url", default=os.getenv("DISCORD_WEBHOOK_URL", "").strip())
    parser.add_argument("--base-date", help="YYYY-MM-DD（省略時は今日基準で前日/前々日）")
    args = parser.parse_args()

    if not args.webhook_url:
        print("DISCORD_WEBHOOK_URL 未設定のため通知スキップ")
        return

    base = date.fromisoformat(args.base_date) if args.base_date else None
    day1, day2 = previous_dates(base=base)

    notes: list[str] = []
    ga4_curr = ga4_prev = None
    yt_curr = yt_prev = None
    shorts_curr = shorts_prev = None

    try:
        ga4_curr = fetch_ga4_daily(
            creds_json=os.getenv("GA4_CREDENTIALS_JSON", "").strip(),
            property_id=os.getenv("GA4_PROPERTY_ID", "").strip(),
            target_date=day1,
        )
        ga4_prev = fetch_ga4_daily(
            creds_json=os.getenv("GA4_CREDENTIALS_JSON", "").strip(),
            property_id=os.getenv("GA4_PROPERTY_ID", "").strip(),
            target_date=day2,
        )
    except Exception as e:
        err = str(e)
        if "credentials/property_id が不足" in err:
            notes.append(
                "GA4 取得不可: GitHub の Repository secrets に "
                "`GA4_CREDENTIALS_JSON`（サービスアカウントJSON全文）と "
                "`GA4_PROPERTY_ID`（数値のプロパティID）が未設定です。"
            )
        else:
            notes.append(f"GA4 取得不可: {e}")

    try:
        c_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
        c_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
        r_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()
        yt_curr = fetch_youtube_daily(
            client_id=c_id,
            client_secret=c_secret,
            refresh_token=r_token,
            target_date=day1,
        )
        yt_prev = fetch_youtube_daily(
            client_id=c_id,
            client_secret=c_secret,
            refresh_token=r_token,
            target_date=day2,
        )
        s1 = fetch_youtube_shorts_views_daily(
            client_id=c_id,
            client_secret=c_secret,
            refresh_token=r_token,
            target_date=day1,
        )
        s2 = fetch_youtube_shorts_views_daily(
            client_id=c_id,
            client_secret=c_secret,
            refresh_token=r_token,
            target_date=day2,
        )
        if s1.get("available") and s2.get("available"):
            shorts_curr = float(s1.get("views") or 0)
            shorts_prev = float(s2.get("views") or 0)
        else:
            notes.append(f"YouTube Shorts 取得不可: {s1.get('reason') or s2.get('reason')}")
    except Exception as e:
        err = str(e)
        if "invalid_grant" in err or "token refresh HTTP 400" in err:
            notes.append(
                "YouTube 取得不可: Refresh Token が失効/無効化。"
                "Google Cloud で再認可して `YOUTUBE_REFRESH_TOKEN` を更新してください。"
            )
        else:
            notes.append(f"YouTube 取得不可: {e}")

    lines = [
        f"📈 日次アナリティクス（{day1.isoformat()} vs {day2.isoformat()}）",
        "",
        "**GA4 前日比**",
    ]
    if ga4_curr and ga4_prev:
        lines += [
            _line("ユーザー", ga4_curr["activeUsers"], ga4_prev["activeUsers"]),
            _line("セッション", ga4_curr["sessions"], ga4_prev["sessions"]),
            _line("PV", ga4_curr["screenPageViews"], ga4_prev["screenPageViews"]),
        ]
    else:
        lines.append("- 取得不可")

    lines += ["", "**YouTube 前日比**"]
    if yt_curr and yt_prev:
        lines += [
            _line("視聴回数", yt_curr["views"], yt_prev["views"]),
            _line("総再生時間(分)", yt_curr["estimatedMinutesWatched"], yt_prev["estimatedMinutesWatched"]),
            _line("登録者増減", yt_curr["subscribersDelta"], yt_prev["subscribersDelta"]),
        ]
        if shorts_curr is not None and shorts_prev is not None:
            lines.append(_line("Shorts再生数", shorts_curr, shorts_prev))
        else:
            lines.append("- Shorts再生数: 取得不可")
    else:
        lines.append("- 取得不可")

    if notes:
        lines += ["", "**注記**"] + [f"- {n}" for n in notes[:5]]

    content = "\n".join(lines)
    resp = requests.post(args.webhook_url, json={"content": content}, timeout=20)
    if resp.status_code >= 400:
        raise RuntimeError(f"Discord通知失敗 HTTP {resp.status_code}: {resp.text[:200]}")
    print("Discord通知: 日次分析を送信")


if __name__ == "__main__":
    main()
