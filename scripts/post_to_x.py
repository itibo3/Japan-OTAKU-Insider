"""
X (Twitter) 自動投稿スクリプト

目的: 新しく追加されたエントリーを X に自動ポストする
入力: data/entries.json（前回コミットとの差分で新着を検出）
出力: X API v2 経由でツイート投稿
前提: 環境変数に X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET が設定済み

触っていい所: ツイート文面テンプレート（format_tweet 内）
危ない所: OAuth 認証周り（変更すると投稿できなくなる）
"""
import json
import os
import sys
import hashlib
import hmac
import time
import urllib.request
import urllib.parse
import base64
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRIES_FILE = PROJECT_ROOT / "data" / "entries.json"
POSTED_FILE = PROJECT_ROOT / "data" / ".x_posted_ids"
SITE_URL = "https://itibo3.github.io/Japan-OTAKU-Insider/"
MAX_POSTS_PER_RUN = 3

CATEGORY_EMOJI = {
    "cafe": "\u2615",
    "figure": "\U0001F9F8",
    "event": "\U0001F3AA",
    "anime": "\U0001F4FA",
    "vtuber": "\U0001F3A4",
    "game": "\U0001F3AE",
    "otaku-news": "\U0001F4E2",
}

# カテゴリ毎のハッシュタグ（最大2個）。未定義は #CategoryName #JapanOtaku
CATEGORY_HASHTAGS = {
    "cafe": ["#CollabCafe", "#JapanOtaku"],
    "figure": ["#Figure", "#JapanOtaku"],
    "event": ["#Event", "#JapanOtaku"],
    "anime": ["#AnimeNews", "#JapanOtaku"],
    "vtuber": ["#VTuber", "#JapanOtaku"],
    "game": ["#GameNews", "#JapanOtaku"],
    "otaku-news": ["#OtakuNews", "#JapanOtaku"],
    "other": ["#JapanOtaku", "#Otaku"],
}


def get_credentials():
    keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
    creds = {k: os.environ.get(k, "") for k in keys}
    missing = [k for k, v in creds.items() if not v]
    if missing:
        print(f"X API credentials not set: {', '.join(missing)}. Skipping.")
        sys.exit(0)
    return creds


def load_posted_ids():
    if POSTED_FILE.exists():
        return set(POSTED_FILE.read_text().strip().splitlines())
    return set()


def save_posted_ids(ids):
    POSTED_FILE.write_text("\n".join(sorted(ids)) + "\n")


def format_tweet(entry):
    cats = entry.get("categories", [])
    emoji = " ".join(CATEGORY_EMOJI.get(c, "") for c in cats[:2]).strip()
    title = entry.get("title", "")
    if len(title) > 120:
        title = title[:117] + "..."

    source = entry.get("source", {})
    source_url = source.get("url", "") if isinstance(source, dict) else source

    parts = []
    if emoji:
        parts.append(emoji)
    parts.append(title)

    primary = (cats[0] if cats else "other")
    tags = CATEGORY_HASHTAGS.get(primary)
    if not tags:
        tags = [f"#{primary.replace('-', '').capitalize()}", "#JapanOtaku"]
    tags = tags[:2]

    parts.append(" ".join(tags))
    if source_url:
        parts.append(source_url)
    else:
        parts.append(SITE_URL)

    return "\n\n".join(parts)


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


def post_tweet(text, creds):
    url = "https://api.twitter.com/2/tweets"
    body = json.dumps({"text": text}).encode()
    auth_header = oauth_sign("POST", url, {}, creds)

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", auth_header)
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            tweet_id = result.get("data", {}).get("id", "?")
            print(f"  Posted tweet: {tweet_id}")
            return True
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"  ERROR posting tweet: {e.code} {body_text[:200]}")
        return False
    except Exception as e:
        print(f"  ERROR posting tweet: {e}")
        return False


def main():
    creds = get_credentials()

    if not ENTRIES_FILE.exists():
        print("entries.json not found. Skipping.")
        sys.exit(0)

    with open(ENTRIES_FILE) as f:
        data = json.load(f)
    entries = data.get("entries", []) if isinstance(data, dict) else data

    posted_ids = load_posted_ids()
    new_entries = [e for e in entries if isinstance(e, dict) and e.get("id") and e["id"] not in posted_ids]

    if not new_entries:
        print("No new entries to post.")
        return

    print(f"Found {len(new_entries)} new entries, posting up to {MAX_POSTS_PER_RUN}.")
    posted_count = 0

    for entry in new_entries[:MAX_POSTS_PER_RUN]:
        text = format_tweet(entry)
        print(f"Posting: {entry['id']}")
        if post_tweet(text, creds):
            posted_ids.add(entry["id"])
            posted_count += 1
            time.sleep(2)

    save_posted_ids(posted_ids)
    print(f"Done. Posted {posted_count} tweet(s).")


if __name__ == "__main__":
    main()
