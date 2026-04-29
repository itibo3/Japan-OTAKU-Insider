#!/usr/bin/env python3
"""
JSONエントリーをメインDBに追加するスクリプト
"""

import json
import sys
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
import requests

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
ENTRIES_FILE = ROOT / "data" / "entries.json"
ENTRIES_JA_FILE = ROOT / "data" / "entries_ja.json"
URL_CHECK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JOI-AddEntryVerifier/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}
_PPLX_URL_CHECK_CACHE = {}
_MOJIBAKE_HINT_RE = re.compile(
    r"(?:Ã.|ã.|â.|ï½|ï¼|ã[ァ-ヶぁ-ん一-龯]|ï¿½|Â|¢|£|¥)"
)


def detect_mojibake(text: str) -> bool:
    """UTF-8/Latin-1 取り違えで出やすい文字列断片を検出する。"""
    t = (text or "").strip()
    if not t:
        return False
    if _MOJIBAKE_HINT_RE.search(t):
        return True
    # ASCII 比率が低いのに拗音崩れ記号が多いケースを補足
    weird = sum(1 for ch in t if ch in "ÃãâïÂ�")
    return weird >= 3


def has_mojibake(entry: dict) -> tuple[bool, str]:
    fields = (
        ("title", entry.get("title", "")),
        ("description", entry.get("description", "")),
        ("title_ja", entry.get("title_ja", "")),
        ("description_ja", entry.get("description_ja", "")),
    )
    for name, val in fields:
        if detect_mojibake(str(val or "")):
            return True, name
    return False, ""

def load_entries_file(path: Path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_updated": "", "total_entries": 0, "entries": []}


def save_entries_file(db, path: Path):
    db["last_updated"] = datetime.now(JST).isoformat()
    db["total_entries"] = len(db["entries"])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def load_entries():
    return load_entries_file(ENTRIES_FILE)


def save_entries(db):
    save_entries_file(db, ENTRIES_FILE)


def load_entries_ja():
    return load_entries_file(ENTRIES_JA_FILE)


def save_entries_ja(db):
    save_entries_file(db, ENTRIES_JA_FILE)

def normalize_categories(entry):
    """
    category（単数）を categories（配列）に正規化する。
    後方互換のため、category が混入していても categories に統一する。
    """
    if "category" in entry:
        cat = entry.pop("category", None)
        entry["categories"] = [cat] if cat else ["event"]
    elif "categories" in entry and isinstance(entry["categories"], list):
        return
    else:
        entry["categories"] = entry.get("categories", ["event"])
    if not isinstance(entry["categories"], list):
        entry["categories"] = [entry["categories"]] if entry["categories"] else ["event"]


def check_duplicate(new_entry, existing_entries):
    """
    重複チェック
    Returns: (is_duplicate: bool, reason: str, is_warning: bool)
    """
    new_id = new_entry.get("id", "")
    new_title = new_entry.get("title", "")
    new_title_ja = new_entry.get("title_ja", "")
    new_source_url = new_entry.get("source", {}).get("url", "")

    for existing in existing_entries:
        ex_id = existing.get("id", "")
        ex_title = existing.get("title", "")
        ex_title_ja = existing.get("title_ja", "")
        ex_source_url = existing.get("source", {}).get("url", "")

        # チェック1: ID完全一致
        if new_id and new_id == ex_id:
            return True, f"ID一致", False

        # チェック2: 英語タイトル完全一致
        if new_title and new_title == ex_title:
            return True, f"タイトル一致", False

        # チェック3: 日本語タイトル完全一致
        if new_title_ja and new_title_ja == ex_title_ja:
            return True, f"日本語タイトル一致", False

        # チェック4: ソースURL完全一致
        if new_source_url and new_source_url == ex_source_url:
            return True, f"ソースURL一致", False

        # チェック5: タイトル類似（包含関係）→ 警告のみ
        if new_title and ex_title:
            new_lower = new_title.lower()
            ex_lower = ex_title.lower()
            if len(new_lower) > 10 and len(ex_lower) > 10:  # 短すぎる場合は除外
                if new_lower in ex_lower or ex_lower in new_lower:
                    return False, f"既存「{ex_title}」", True

    return False, "", False

UNTRANSLATED_PREFIX = "[未翻訳]"


def has_untranslated_marker(entry):
    """title または description に [未翻訳] プレースホルダが残っているか確認する"""
    title = entry.get("title", "") or ""
    description = entry.get("description", "") or ""
    return title.strip().startswith(UNTRANSLATED_PREFIX) or description.strip().startswith(UNTRANSLATED_PREFIX)


def has_low_quality_source_url(entry):
    """トップページ等の中身が薄いURLを簡易判定で弾く（主に Perplexity 由来）。"""
    source_url = ((entry.get("source") or {}).get("url") or "").strip()
    if not source_url:
        return False
    if entry.get("_source_id") == "joi-weekly" and source_url.startswith("/weekly.html"):
        return False
    try:
        parsed = urlparse(source_url)
    except Exception:
        return True
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return True
    # Perplexity はトップURLをでっち上げる傾向があるため、root / index は登録しない
    if entry.get("_source") == "perplexity":
        path = (parsed.path or "").strip().lower()
        if path in ("", "/", "/index.html", "/index.php", "/home", "/top"):
            return True
        depth = len([x for x in path.split("/") if x])
        if depth <= 1 and not parsed.query:
            return True
    return False


def get_unreachable_perplexity_reason(entry):
    """Perplexity 由来URLの実在チェック。問題なければ空文字。"""
    if entry.get("_source") != "perplexity":
        return ""
    source_url = ((entry.get("source") or {}).get("url") or "").strip()
    if not source_url:
        return "URLが空"
    if source_url in _PPLX_URL_CHECK_CACHE:
        return _PPLX_URL_CHECK_CACHE[source_url]
    try:
        r = requests.get(source_url, headers=URL_CHECK_HEADERS, timeout=12, allow_redirects=True)
        if r.status_code != 200:
            reason = f"HTTP {r.status_code}"
        else:
            reason = ""
    except Exception as e:
        reason = f"疎通失敗: {type(e).__name__}"
    _PPLX_URL_CHECK_CACHE[source_url] = reason
    return reason


def add_single_entry(entry: dict) -> dict:
    """
    dict 1件を entries.json に追加する。
    既存の validate/重複チェックロジックをそのまま通す。
    戻り値: {"ok": True/False, "message": str, "entry_id": str or None}
    """
    db = load_entries()
    existing_entries = db["entries"]

    normalize_categories(entry)

    if entry.get("_source_id") == "joi-weekly":
        for e in db["entries"]:
            if e.get("_source_id") == "joi-weekly" or e.get("_source") == "joi-weekly":
                if e.get("pinned_top"):
                    e["pinned_top"] = False
                e["_weekly_archived"] = True
        entry["pinned_top"] = True
        entry["_weekly_archived"] = False

    title = (entry.get("title") or "").strip()
    desc = (entry.get("description") or "").strip()
    if not title or not desc:
        return {"ok": False, "message": "title または description が空です", "entry_id": None}

    if has_untranslated_marker(entry):
        return {"ok": False, "message": "title/description に [未翻訳] マーカーが残っています", "entry_id": None}
    mojibake, field = has_mojibake(entry)
    if mojibake:
        return {"ok": False, "message": f"文字化け疑いを検出: {field}", "entry_id": None}

    if has_low_quality_source_url(entry):
        return {"ok": False, "message": "URL がトップページ/不正形式の可能性があります", "entry_id": None}

    pplx_bad = get_unreachable_perplexity_reason(entry)
    if pplx_bad:
        return {"ok": False, "message": f"URL の疎通チェック失敗: {pplx_bad}", "entry_id": None}

    is_dup, reason, is_warn = check_duplicate(entry, existing_entries)
    if is_dup:
        return {"ok": False, "message": f"重複エントリーです（{reason}）", "entry_id": None}

    db["entries"].insert(0, entry)
    save_entries(db)
    entry_id = entry.get("id", "")
    return {"ok": True, "message": f"追加しました: {title}", "entry_id": entry_id}


def add_single_entry_dual(entry_en: dict, *, title_ja: str, description_ja: str) -> dict:
    """
    JP正本を基準に entries.json(EN) / entries_ja.json(JP) を同時追加する。
    どちらかの検証で失敗した場合は何も保存しない。
    """
    db_en = load_entries()
    db_ja = load_entries_ja()

    # 失敗時ロールバック用スナップショット
    snapshot_en = json.loads(json.dumps(db_en))
    snapshot_ja = json.loads(json.dumps(db_ja))

    normalize_categories(entry_en)

    title_en = (entry_en.get("title") or "").strip()
    desc_en = (entry_en.get("description") or "").strip()
    title_ja = (title_ja or "").strip() or (entry_en.get("title_ja") or "").strip()
    description_ja = (description_ja or "").strip() or (entry_en.get("description_ja") or "").strip()

    if not title_ja or not description_ja:
        return {"ok": False, "message": "日本語タイトル/日本語概要が空です", "entry_id": None}
    if not title_en or not desc_en:
        return {"ok": False, "message": "英語タイトル/英語概要が空です", "entry_id": None}

    entry_en["title_ja"] = title_ja
    entry_en["description_ja"] = description_ja

    # JP表示用エントリを生成（IDはENと同一）
    entry_ja = json.loads(json.dumps(entry_en))
    entry_ja["title"] = title_ja
    entry_ja["title_ja"] = title_ja
    entry_ja["description"] = description_ja
    entry_ja["description_ja"] = description_ja

    # 品質チェック（EN側に適用）
    if has_untranslated_marker(entry_en):
        return {"ok": False, "message": "title/description に [未翻訳] マーカーが残っています", "entry_id": None}
    mojibake, field = has_mojibake(entry_en)
    if mojibake:
        return {"ok": False, "message": f"文字化け疑いを検出: {field}", "entry_id": None}
    if has_low_quality_source_url(entry_en):
        return {"ok": False, "message": "URL がトップページ/不正形式の可能性があります", "entry_id": None}
    pplx_bad = get_unreachable_perplexity_reason(entry_en)
    if pplx_bad:
        return {"ok": False, "message": f"URL の疎通チェック失敗: {pplx_bad}", "entry_id": None}

    # 重複チェック（EN/JP両方）
    is_dup_en, reason_en, _ = check_duplicate(entry_en, db_en["entries"])
    if is_dup_en:
        return {"ok": False, "message": f"重複エントリーです（EN: {reason_en}）", "entry_id": None}
    is_dup_ja, reason_ja, _ = check_duplicate(entry_ja, db_ja["entries"])
    if is_dup_ja:
        return {"ok": False, "message": f"重複エントリーです（JP: {reason_ja}）", "entry_id": None}

    db_en["entries"].insert(0, entry_en)
    db_ja["entries"].insert(0, entry_ja)
    try:
        save_entries(db_en)
        save_entries_ja(db_ja)
    except Exception:
        # 片側だけ保存された場合の保険
        save_entries(snapshot_en)
        save_entries_ja(snapshot_ja)
        raise

    return {
        "ok": True,
        "message": f"追加しました: {title_ja}",
        "entry_id": entry_en.get("id", ""),
    }


def add_entries_from_file(filepath, reset=False):
    """Geminiの出力JSONファイルからエントリーを追加。reset=True のときは既存を空にしてから追加"""
    with open(filepath, 'r', encoding='utf-8') as f:
        new_entries = json.load(f)

    # 配列でない場合（単一エントリー）は配列に変換
    if isinstance(new_entries, dict):
        new_entries = [new_entries]

    db = load_entries()
    if reset:
        db["entries"] = []
        print("  (reset: entries を空にしました)")
    existing_entries = db["entries"]

    added = 0
    for entry in new_entries:
        normalize_categories(entry)
        # 週刊JOIを追加する場合、既存JOIは archive 扱いにして pinned_top を外す
        if entry.get("_source_id") == "joi-weekly":
            for e in db["entries"]:
                if e.get("_source_id") == "joi-weekly" or e.get("_source") == "joi-weekly":
                    if e.get("pinned_top"):
                        e["pinned_top"] = False
                    e["_weekly_archived"] = True
            entry["pinned_top"] = True
            entry["_weekly_archived"] = False
        title = (entry.get("title") or "").strip()
        desc = (entry.get("description") or "").strip()
        if not title or not desc:
            title_disp = entry.get('title_ja', title or 'Unknown')
            print(f"  SKIP (empty field): {title_disp[:60]} — title/description が空")
            continue
        # 翻訳未完了チェック: [未翻訳] プレースホルダが残っている記事は登録しない
        if has_untranslated_marker(entry):
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (未翻訳): {title_disp[:60]} — title/description に [未翻訳] が残っています")
            continue
        # 文字化けチェック: mojibakeらしきタイトル/本文は登録しない
        mojibake, field = has_mojibake(entry)
        if mojibake:
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (mojibake): {title_disp[:60]} — 文字化け疑い({field})")
            continue
        # 品質チェック: トップページ等の薄いURLは除外
        if has_low_quality_source_url(entry):
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (source quality): {title_disp[:60]} — URL がトップ/不正形式の可能性")
            continue
        # 品質チェック: Perplexity由来は URL 実在性を最終ゲートで担保
        pplx_bad_reason = get_unreachable_perplexity_reason(entry)
        if pplx_bad_reason:
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (source unreachable): {title_disp[:60]} — {pplx_bad_reason}")
            continue
        is_dup, reason, is_warn = check_duplicate(entry, existing_entries)
        
        if is_dup:
            title_disp = entry.get('title_ja', entry.get('title', 'Unknown'))
            print(f"  SKIP (duplicate): {title_disp} — 理由: {reason}")
        else:
            if is_warn:
                print(f"  ⚠ WARNING: \"{entry.get('title', 'Unknown')}\" may be similar to {reason} — 確認してください")
            
            db["entries"].insert(0, entry)
            added += 1
            print(f"  Added: {entry.get('title', 'Unknown')}")

    save_entries(db)
    print(f"\n{added} entries added. Total: {db['total_entries']}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python add_entry.py [--reset] <gemini_output.json>")
        print("  --reset : entries を空にしてから追加（リセット後の再構築用）")
        sys.exit(1)

    reset = "--reset" in args
    if reset:
        args = [a for a in args if a != "--reset"]
    filepath = args[-1] if args else ""
    if not filepath or filepath.startswith("--"):
        print("ERROR: ファイルパスを指定してください")
        sys.exit(1)

    add_entries_from_file(filepath, reset=reset)
