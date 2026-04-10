#!/usr/bin/env python3
"""
GA4 / YouTube Analytics の共通クライアント。

目的:
- 日次通知や週次分析で使う API 呼び出しを1か所に集約する
- 取得できない指標は例外を握りつぶさず、呼び出し元で「取得不可」を扱える形にする
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account


def ga4_access_token(creds_json: str) -> str:
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    creds.refresh(Request())
    if not creds.token:
        raise RuntimeError("GA4 token 取得失敗")
    return creds.token


def fetch_ga4_daily(
    *,
    creds_json: str,
    property_id: str,
    target_date: date,
) -> dict[str, float]:
    if not (creds_json and property_id):
        raise RuntimeError("GA4 credentials/property_id が不足")
    token = ga4_access_token(creds_json)
    day = target_date.isoformat()
    resp = requests.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "dateRanges": [{"startDate": day, "endDate": day}],
            "metrics": [
                {"name": "activeUsers"},
                {"name": "sessions"},
                {"name": "screenPageViews"},
            ],
        },
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"GA4 runReport HTTP {resp.status_code}: {resp.text[:200]}")
    rows = (resp.json() or {}).get("rows") or []
    if not rows:
        return {"activeUsers": 0.0, "sessions": 0.0, "screenPageViews": 0.0}
    vals = rows[0].get("metricValues") or []
    names = ("activeUsers", "sessions", "screenPageViews")
    out: dict[str, float] = {}
    for i, n in enumerate(names):
        try:
            out[n] = float((vals[i] or {}).get("value") or 0)
        except Exception:
            out[n] = 0.0
    return out


def youtube_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=45,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"YouTube token refresh HTTP {resp.status_code}: {resp.text[:200]}")
    token = (resp.json() or {}).get("access_token") or ""
    if not token:
        raise RuntimeError("YouTube access_token が空")
    return token


def youtube_channel_id(token: str) -> str:
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id", "mine": "true"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=45,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"YouTube channels.mine HTTP {resp.status_code}: {resp.text[:200]}")
    items = (resp.json() or {}).get("items") or []
    if not items:
        raise RuntimeError("YouTube channels.mine が0件")
    return items[0].get("id") or ""


def _youtube_reports_query(
    *,
    token: str,
    channel_id: str,
    start_date: date,
    end_date: date,
    metrics: str,
    dimensions: str | None = None,
    filters: str | None = None,
) -> dict[str, Any]:
    params: dict[str, str] = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "metrics": metrics,
    }
    if dimensions:
        params["dimensions"] = dimensions
    if filters:
        params["filters"] = filters
    resp = requests.get(
        "https://youtubeanalytics.googleapis.com/v2/reports",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"YouTube Analytics HTTP {resp.status_code}: {resp.text[:220]}")
    return resp.json() or {}


def fetch_youtube_daily(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    target_date: date,
) -> dict[str, float]:
    if not (client_id and client_secret and refresh_token):
        raise RuntimeError("YouTube credentials が不足")
    token = youtube_access_token(client_id, client_secret, refresh_token)
    cid = youtube_channel_id(token)
    data = _youtube_reports_query(
        token=token,
        channel_id=cid,
        start_date=target_date,
        end_date=target_date,
        metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost",
    )
    rows = data.get("rows") or []
    if not rows:
        return {
            "views": 0.0,
            "estimatedMinutesWatched": 0.0,
            "subscribersDelta": 0.0,
        }
    row = rows[0]
    try:
        views = float(row[0] or 0)
        mins = float(row[1] or 0)
        gained = float(row[2] or 0)
        lost = float(row[3] or 0)
    except Exception:
        views, mins, gained, lost = 0.0, 0.0, 0.0, 0.0
    return {
        "views": views,
        "estimatedMinutesWatched": mins,
        "subscribersDelta": gained - lost,
    }


def fetch_youtube_shorts_views_daily(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    target_date: date,
) -> dict[str, Any]:
    """
    Shorts 再生数取得。
    API仕様差に備えて複数パターンを試し、失敗したら unavailable を返す。
    """
    if not (client_id and client_secret and refresh_token):
        return {"available": False, "reason": "credentials_missing"}
    try:
        token = youtube_access_token(client_id, client_secret, refresh_token)
        cid = youtube_channel_id(token)
    except Exception as e:
        return {"available": False, "reason": str(e)}

    # videoType をディメンションに含めると環境によっては弾かれる。day + フィルタのみを先に試す。
    tries = [
        {"dimensions": "day", "filters": "videoType==SHORTS"},
        {"dimensions": "day", "filters": "creatorContentType==SHORTS"},
        {"dimensions": "day,videoType", "filters": "videoType==SHORTS"},
        {"dimensions": "day,creatorContentType", "filters": "creatorContentType==SHORTS"},
    ]
    for t in tries:
        try:
            data = _youtube_reports_query(
                token=token,
                channel_id=cid,
                start_date=target_date,
                end_date=target_date,
                metrics="views",
                dimensions=t["dimensions"],
                filters=t["filters"],
            )
            rows = data.get("rows") or []
            if not rows:
                return {"available": True, "views": 0.0, "source": t["dimensions"]}
            total = 0.0
            for r in rows:
                try:
                    total += float(r[-1] or 0)
                except Exception:
                    pass
            return {"available": True, "views": total, "source": t["dimensions"]}
        except Exception:
            continue
    return {"available": False, "reason": "shorts_dimension_not_supported"}


def previous_dates(*, base: date | None = None) -> tuple[date, date]:
    d = base or date.today()
    return d - timedelta(days=1), d - timedelta(days=2)
