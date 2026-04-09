#!/usr/bin/env python3
"""
外部API接続のスモークテスト（Secrets検証用）。

目的:
- GitHub Secrets に入れた各キーが「最低限使えるか」を手動で確認する
- データ更新・投稿などの副作用は起こさない（読み取り/短文生成のみ）

チェック対象:
- GEMINI_API_KEY
- ANTHROPIC_API_KEY
- GA4_CREDENTIALS_JSON (+ GA4_PROPERTY_ID があれば runReport まで)
- YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from typing import Tuple

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


def _env_or_default(name: str, default: str) -> str:
    val = os.getenv(name, "").strip()
    return val if val else default


def _ok(name: str, msg: str) -> Tuple[bool, str]:
    return True, f"✅ {name}: {msg}"


def _ng(name: str, msg: str) -> Tuple[bool, str]:
    return False, f"❌ {name}: {msg}"


def check_gemini() -> Tuple[bool, str]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return _ng("Gemini", "GEMINI_API_KEY が未設定")

    model = _env_or_default("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    resp = requests.post(
        url,
        params={"key": key},
        json={
            "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
            "generationConfig": {"maxOutputTokens": 8},
        },
        timeout=45,
    )
    if resp.status_code >= 400:
        return _ng("Gemini", f"HTTP {resp.status_code} {resp.text[:160]}")
    return _ok("Gemini", f"APIキーで generateContent 成功 ({model})")


def check_anthropic() -> Tuple[bool, str]:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return _ng("Anthropic", "ANTHROPIC_API_KEY が未設定")

    model = _env_or_default("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 8,
            "messages": [{"role": "user", "content": "ping"}],
        },
        timeout=45,
    )
    if resp.status_code >= 400:
        return _ng("Anthropic", f"HTTP {resp.status_code} {resp.text[:160]}")
    return _ok("Anthropic", f"APIキーで messages 成功 ({model})")


def _ga4_access_token(creds_json: str) -> str:
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    creds.refresh(Request())
    token = creds.token or ""
    if not token:
        raise RuntimeError("アクセストークンを取得できませんでした")
    return token


def check_ga4() -> Tuple[bool, str]:
    creds_json = os.getenv("GA4_CREDENTIALS_JSON", "").strip()
    if not creds_json:
        return _ng("GA4", "GA4_CREDENTIALS_JSON が未設定")

    try:
        token = _ga4_access_token(creds_json)
    except Exception as e:
        return _ng("GA4", f"認証失敗: {e}")

    property_id = os.getenv("GA4_PROPERTY_ID", "").strip()
    if not property_id:
        return _ok("GA4", "認証成功（GA4_PROPERTY_ID 未設定のため runReport はスキップ）")

    today = date.today()
    start = (today - timedelta(days=2)).isoformat()
    end = (today - timedelta(days=1)).isoformat()
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "dateRanges": [{"startDate": start, "endDate": end}],
            "metrics": [{"name": "activeUsers"}],
            "dimensions": [{"name": "date"}],
            "limit": 3,
        },
        timeout=45,
    )
    if resp.status_code >= 400:
        return _ng("GA4", f"runReport 失敗: HTTP {resp.status_code} {resp.text[:160]}")
    return _ok("GA4", "認証 + runReport 成功")


def _youtube_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
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
        raise RuntimeError(f"トークン更新失敗: HTTP {resp.status_code} {resp.text[:160]}")
    token = resp.json().get("access_token", "")
    if not token:
        raise RuntimeError("access_token が空です")
    return token


def check_youtube() -> Tuple[bool, str]:
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()
    if not (client_id and client_secret and refresh_token):
        return _ng("YouTube", "YOUTUBE_CLIENT_ID / SECRET / REFRESH_TOKEN のいずれか未設定")

    try:
        token = _youtube_access_token(client_id, client_secret, refresh_token)
    except Exception as e:
        return _ng("YouTube", str(e))

    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id", "mine": "true"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=45,
    )
    if resp.status_code >= 400:
        return _ng("YouTube", f"channels.mine 失敗: HTTP {resp.status_code} {resp.text[:160]}")
    items = (resp.json() or {}).get("items") or []
    if not items:
        return _ng("YouTube", "channels.mine が0件（権限スコープ or チャンネル紐付け要確認）")
    return _ok("YouTube", "refresh_token + channels.mine 成功")


def main() -> None:
    checks = [check_gemini, check_anthropic, check_ga4, check_youtube]
    all_ok = True
    print("=== API Secrets Smoke Test ===")
    for fn in checks:
        ok, msg = fn()
        print(msg)
        all_ok = all_ok and ok

    if not all_ok:
        print("\n結果: 失敗あり（上の ❌ を確認）")
        sys.exit(1)
    print("\n結果: すべて成功")


if __name__ == "__main__":
    main()
