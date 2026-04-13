#!/usr/bin/env python3
"""
entries.json 内で週次レポートが検知する [未翻訳] マーカーを除去する。

目的: title / description 先頭の [未翻訳] を translate_staging と同じ規則で剥がす。
入力・出力: data/entries.json（上書き）
補足: description が空になる場合は英語 title を流用（既に英語タイトルのRSS取り込み想定）。

触っていい所: 本スクリプト単体。危ない所: 常にバックアップ推奨。
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_PATH = ROOT / "data" / "entries.json"
UNTRANSLATED_PREFIX_RE = re.compile(r"^\s*\[未翻訳\]\s*")
JST = timezone(timedelta(hours=9))


def strip_prefix(text: str) -> str:
    return UNTRANSLATED_PREFIX_RE.sub("", text or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="entries.json から [未翻訳] プレフィックスを除去")
    parser.add_argument("--dry-run", action="store_true", help="変更せず件数だけ表示")
    args = parser.parse_args()

    raw = ENTRIES_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)
    entries = data.get("entries") or []
    changed_ids: list[str] = []

    for e in entries:
        if not isinstance(e, dict):
            continue
        tid = e.get("id", "")
        mod = False
        for key in ("title", "description"):
            if key not in e:
                continue
            v = e.get(key) or ""
            if not v.strip().startswith("[未翻訳]"):
                continue
            nv = strip_prefix(v)
            if key == "description" and not nv:
                nv = strip_prefix(e.get("title") or "")
            if nv != v:
                e[key] = nv
                mod = True
        if mod:
            changed_ids.append(tid)

    print(f"対象 {len(changed_ids)} 件")
    for i in changed_ids:
        print(f"  - {i}")

    if args.dry_run:
        return

    data["last_updated"] = datetime.now(JST).isoformat()
    ENTRIES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"書き込み: {ENTRIES_PATH}")


if __name__ == "__main__":
    main()
