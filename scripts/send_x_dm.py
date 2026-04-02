#!/usr/bin/env python3
"""
X (Twitter) DM 自動送信スクリプト

目的: Japan OTAKU Insider の公式アカウントから、指定した管理者アカウントへDMを送信する。
用途: 週間レポートの通知など（旧 DeepL 枠警告は廃止）。

必要な環境変数:
- X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
- X_TARGET_USERNAME (通知先のTwitter ID, 例: "itibo3_123")
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid

def get_credentials():
    keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
    creds = {k: os.environ.get(k, "") for k in keys}
    missing = [k for k, v in creds.items() if not v]
    if missing:
        print(f"X API credentials not set: {', '.join(missing)}. Skipping DM.")
        sys.exit(0)
    return creds

def oauth_sign(method, url, params, creds):
    """OAuth 1.0a 署名を生成"""
    oauth_params = {
        "oauth_consumer_key": creds["X_API_KEY"],
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": creds["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    all_params = {**oauth_params, **params}
    sorted_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )
    base_string = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(sorted_params, safe=""),
    ])
    signing_key = (
        urllib.parse.quote(creds["X_API_SECRET"], safe="")
        + "&"
        + urllib.parse.quote(creds["X_ACCESS_SECRET"], safe="")
    )
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = signature
    auth_header = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return auth_header

def get_user_id_by_username(username, creds):
    """ユーザー名から numeric ID を取得 (v2 API)"""
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    auth_header = oauth_sign("GET", url, {}, creds)
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", auth_header)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            return result.get("data", {}).get("id")
    except urllib.error.HTTPError as e:
        print(f"Failed to get user ID: {e.code} {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Failed to get user ID: {e}")
        return None

def send_dm(target_user_id, text, creds):
    """v2 API で DM を送信 (Participant ID 方式)"""
    url = f"https://api.twitter.com/2/dm_conversations/with/{target_user_id}/messages"
    body = json.dumps({
        "message": {
            "text": text
        }
    }).encode("utf-8")
    
    auth_header = oauth_sign("POST", url, {}, creds)
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", auth_header)
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            print("Successfully sent DM.")
            return True
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"ERROR sending DM: {e.code} {body_text[:200]}")
        return False
    except Exception as e:
        print(f"ERROR sending DM: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", required=True, help="DMとして送信するテキスト")
    parser.add_argument("--target", help="送信先のXユーザー名（@マークなし）。指定がなければ環境変数 X_TARGET_USERNAME を使用")
    args = parser.parse_args()

    creds = get_credentials()
    
    target_username = args.target or os.environ.get("X_TARGET_USERNAME", "").strip()
    if not target_username:
        print("X_TARGET_USERNAME is not set. Skipping DM.")
        sys.exit(0)
    
    # '@' がついていたら除去
    target_username = target_username.lstrip('@')
    
    target_user_id = os.environ.get("X_TARGET_USER_ID", "").strip()
    if not target_user_id:
        print(f"Looking up User ID for @{target_username}...")
        target_user_id = get_user_id_by_username(target_username, creds)
        
    if not target_user_id:
        print("Could not resolve Target User ID. Skipping DM.")
        sys.exit(1)
        
    print(f"Sending DM to User ID {target_user_id} (@{target_username})...")
    send_dm(target_user_id, args.message, creds)

if __name__ == "__main__":
    main()
