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
import argparse
import hashlib
import hmac
import time
import urllib.request
import urllib.parse
import base64
import uuid
from pathlib import Path
import re
from datetime import datetime, timedelta

JA_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")

def looks_japanese(text: str) -> bool:
    return bool(JA_CHAR_RE.search(text or ""))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRIES_FILE = PROJECT_ROOT / "data" / "entries.json"
POSTED_FILE = PROJECT_ROOT / "data" / ".x_posted_ids"
SITE_URL = "https://otaku.eidosfrontier.com/"
CATEGORY_EMOJI = {
    "cafe": "\u2615",
    "figure": "\U0001F9F8",
    "cosplay": "\U0001F457",
    "event": "\U0001F3AA",
    "anime": "\U0001F4FA",
    "vtuber": "\U0001F3A4",
    "game": "\U0001F3AE",
    "otaku-news": "\U0001F4E2",
    "other": "\U0001F1EF\U0001F1F5",
}

# カテゴリ毎の固定ハッシュタグ（最大2個）+ 全投稿共通タグ
# 集客見直し時: 検索ボリュームの大きい汎用タグとニッチタグのバランスを取る（例: VTuber枠で #Hololive だけだにじさんじ層に届きにくい）
COMMON_HASHTAG = "#JapanOTAKUInsider"
CATEGORY_HASHTAGS = {
    "cafe":       ["#CollabCafe",   "#JapanAnime"],
    "figure":     ["#AnimeFigure",  "#JapanFigure"],
    "cosplay":    ["#Cosplay",      "#Cosplayer"],
    "event":      ["#AnimeEvent",   "#JapanEvent"],
    "anime":      ["#Anime",        "#AnimeSeason"],
    "vtuber":     ["#VTuber",       "#VTuberEN"],
    "game":       ["#JapanGames",   "#GameNews"],
    "otaku-news": ["#Otaku",        "#JapanCulture"],
    "other":      ["#JapanOtaku",   "#Otaku"],
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


def normalize_public_url(raw_url: str) -> str:
    """
    source.url を公開用URLへ正規化する。
    - /weekly.html?... のような相対URLは SITE_URL 基準で絶対化
    - http/https 以外（空・不正）は SITE_URL にフォールバック
    """
    u = (raw_url or "").strip()
    if not u:
        return SITE_URL
    if u.startswith("/"):
        return urllib.parse.urljoin(SITE_URL, u)
    p = urllib.parse.urlparse(u)
    if p.scheme in ("http", "https") and p.netloc:
        return u
    return SITE_URL


def is_weekly_like_entry(entry: dict) -> bool:
    """
    週刊レポート（週刊JOI通信 / weekly.html）っぽい投稿を X 自動投稿から除外する。
    理由: 通常ニュースと混ざるとタイムラインが「週報」だらけに見えやすい。
    """
    try:
        src = entry.get("_source")
        if src in ("joi-weekly", "weekly"):
            return True
        tags = entry.get("tags") or []
        if isinstance(tags, list) and any(t in ("weekly-joi", "weekly", "weekly-report") for t in tags):
            return True
        source = entry.get("source", {})
        raw = source.get("url", "") if isinstance(source, dict) else str(source or "")
        u = (raw or "").strip()
        if u.startswith("/weekly.html") or "/weekly.html" in u:
            return True
        eid = str(entry.get("id") or "")
        if "-joi-" in eid or eid.startswith("otaku-news-") and "joi" in eid:
            return True
    except Exception:
        return False
    return False


def format_tweet(entry, lang="en"):
    cats = entry.get("categories", [])
    if not cats and entry.get("category"):
        cats = [entry["category"]]
    primary = cats[0] if cats else "other"
    emoji = CATEGORY_EMOJI.get(primary, "")
    
    if lang == "ja":
        title = entry.get("title_ja", "") or entry.get("title", "")
    else:
        title = entry.get("title", "")
        if title.startswith("[未翻訳] "):
            title = title.replace("[未翻訳] ", "")
        
        # 英語投稿時にタイトルが日本語の場合はスキップフラグを返す
        if looks_japanese(title):
            return "[SKIP_EN_TWEET]"

    if len(title) > 110:
        title = title[:107] + "..."

    source = entry.get("source", {})
    source_url_raw = source.get("url", "") if isinstance(source, dict) else source
    source_url = normalize_public_url(source_url_raw)

    tags = CATEGORY_HASHTAGS.get(primary, ["#JapanOtaku", "#Otaku"])
    hashtag_line = " ".join(tags) + " " + COMMON_HASHTAG

    parts = []
    if emoji:
        parts.append(emoji)
    parts.append(title)
    parts.append(hashtag_line)
    parts.append(source_url)

    return "\n\n".join(parts)


def _id_date(entry: dict) -> datetime | None:
    m = re.search(r"-(\d{8})(?:\d{4})?-", str(entry.get("id") or ""))
    if not m:
        return None
    ds = m.group(1)
    try:
        return datetime(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
    except Exception:
        return None


def build_weekly_top5(entries: list[dict], *, limit: int = 5, lang: str = "en") -> str:
    """週次ハイライト投稿（Top5）本文を作る。"""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=7)
    picked: list[dict] = []
    seen: set[str] = set()
    for e in entries:
        if not isinstance(e, dict):
            continue
        if is_weekly_like_entry(e):
            continue
        dt = _id_date(e)
        if dt and dt < cutoff:
            continue
        title = (e.get("title_ja") if lang == "ja" else e.get("title")) or e.get("title") or ""
        title = str(title).strip()
        if not title or title in seen:
            continue
        seen.add(title)
        picked.append(e)
        if len(picked) >= limit:
            break

    if not picked:
        return ""

    if lang == "ja":
        lines = ["【今週のJOI Top5】", "今週の注目記事まとめ！"]
        for i, e in enumerate(picked, start=1):
            t = (e.get("title_ja") or e.get("title") or "").strip()
            if len(t) > 56:
                t = t[:53] + "..."
            lines.append(f"{i}. {t}")
        lines.append("#オタクニュース #JapanOTAKUInsider")
    else:
        lines = ["JOI Weekly Top 5", "This week's must-read picks:"]
        for i, e in enumerate(picked, start=1):
            t = (e.get("title") or "").strip()
            if len(t) > 56:
                t = t[:53] + "..."
            lines.append(f"{i}. {t}")
        lines.append("#AnimeNews #JapanOTAKUInsider")
    lines.append(SITE_URL)
    return "\n".join(lines)


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
    parser = argparse.ArgumentParser(description="X自動投稿")
    parser.add_argument("--weekly-top5", action="store_true", help="週1ハイライトTop5投稿を実行")
    parser.add_argument("--limit", type=int, default=5, help="Top5投稿時の件数")
    args = parser.parse_args()

    creds = get_credentials()

    if not ENTRIES_FILE.exists():
        print("entries.json not found. Skipping.")
        sys.exit(0)

    with open(ENTRIES_FILE) as f:
        data = json.load(f)
    entries = data.get("entries", []) if isinstance(data, dict) else data

    if args.weekly_top5:
        text_en = build_weekly_top5(entries, limit=max(1, args.limit), lang="en")
        text_ja = build_weekly_top5(entries, limit=max(1, args.limit), lang="ja")
        if not text_en and not text_ja:
            print("No entries for weekly top5 post.")
            return
        posted = 0
        if text_en:
            print("Posting weekly top5 (EN)")
            if post_tweet(text_en, creds):
                posted += 1
            time.sleep(3)
        if text_ja:
            print("Posting weekly top5 (JA)")
            if post_tweet(text_ja, creds):
                posted += 1
        print(f"Weekly top5 done. Posted {posted} tweet(s).")
        return

    posted_ids = load_posted_ids()
    new_entries = []
    skipped_weekly = 0
    for e in entries:
        if not (isinstance(e, dict) and e.get("id")):
            continue
        if e["id"] in posted_ids:
            continue
        if is_weekly_like_entry(e):
            # スキップしたものは「未投稿のまま残る」と毎回引っかかるので、投稿済み扱いにして追跡から外す
            posted_ids.add(e["id"])
            skipped_weekly += 1
            continue
        new_entries.append(e)

    if not new_entries:
        if skipped_weekly:
            save_posted_ids(posted_ids)
            print(f"No new entries to post. (skipped weekly-like: {skipped_weekly})")
        else:
            print("No new entries to post.")
        return

    # カテゴリ別にグループ化し、各カテゴリから最新1件を選択
    cat_best: dict[str, dict] = {}
    for entry in new_entries:
        cats = entry.get("categories", [])
        if not cats and entry.get("category"):
            cats = [entry["category"]]
        primary = cats[0] if cats else "other"
        if primary not in cat_best:
            cat_best[primary] = entry  # entries は新着順なので最初が最新

    to_post = list(cat_best.values())
    print(f"Found {len(new_entries)} new entries → {len(to_post)} categories → posting 1 per category.")
    posted_count = 0

    for entry in to_post:
        primary_cat = entry.get('categories', ['?'])[0]
        
        # 英語ポスト
        text_en = format_tweet(entry, lang="en")
        if text_en == "[SKIP_EN_TWEET]":
            print(f"  WARNING: 英語タイトルが日本語のため投稿スキップ: {entry.get('title', '')[:50]}...")
            success_en = False
        else:
            print(f"Posting [{primary_cat}] (EN): {entry['id']}")
            success_en = post_tweet(text_en, creds)
            if success_en:
                posted_count += 1
        
        time.sleep(3)
        
        # 日本語ポスト
        text_ja = format_tweet(entry, lang="ja")
        print(f"Posting [{primary_cat}] (JA): {entry['id']}")
        success_ja = post_tweet(text_ja, creds)
        if success_ja:
            posted_count += 1
            
        # 少なくともどちらかが成功したら記録する
        if success_en or success_ja:
            posted_ids.add(entry["id"])
            
        time.sleep(10)

    save_posted_ids(posted_ids)
    print(f"Done. Posted {posted_count} tweet(s).")


if __name__ == "__main__":
    main()
