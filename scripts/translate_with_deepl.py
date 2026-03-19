#!/usr/bin/env python3
"""
translate_with_deepl.py — staging JSONをDeepLで英語化する（ローカル検証用）

入力:
- data/staging/*.json（rss_fetch.pyが吐く配列JSON）

出力:
- 同じファイルを上書き（title/description/tags を英語化）

安全策:
- DEEPL_AUTH_KEY が無い場合は、何も変更せずに終了（設定方法だけ表示）
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Iterable, List, Tuple


UNTRANSLATED_PREFIX_RE = re.compile(r"^\s*\[未翻訳\]\s*")
JA_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")


def strip_untranslated_prefix(text: str) -> str:
    return UNTRANSLATED_PREFIX_RE.sub("", text or "").strip()


def looks_japanese(text: str) -> bool:
    return bool(JA_CHAR_RE.search(text or ""))


def detect_endpoint(auth_key: str) -> str:
    # Freeキーは末尾 :fx のことが多い。断定できないので「まず推定→失敗したら自動フォールバック」方針。
    if auth_key.strip().endswith(":fx"):
        return "https://api-free.deepl.com/v2/translate"
    return "https://api.deepl.com/v2/translate"


def deepl_translate_batch(
    *,
    auth_key: str,
    texts: List[str],
    source_lang: str = "JA",
    target_lang: str = "EN",
) -> List[str]:
    import requests  # venv前提

    if not texts:
        return []

    def call(endpoint: str) -> List[str]:
        headers = {
            "Authorization": f"DeepL-Auth-Key {auth_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "text": texts,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        if resp.status_code >= 400:
            raise RuntimeError(f"DeepL error: HTTP {resp.status_code} {resp.text[:200]}")
        payload = resp.json()
        out = []
        for tr in payload.get("translations", []) or []:
            out.append((tr.get("text") or "").strip())
        if len(out) != len(texts):
            raise RuntimeError("DeepL response size mismatch")
        return out

    primary = detect_endpoint(auth_key)
    secondary = "https://api-free.deepl.com/v2/translate" if primary == "https://api.deepl.com/v2/translate" else "https://api.deepl.com/v2/translate"
    try:
        return call(primary)
    except Exception as e1:
        # どっちのキーか不明なケース向けフォールバック
        try:
            return call(secondary)
        except Exception as e2:
            raise RuntimeError(f"DeepL failed on both endpoints. primary={e1} secondary={e2}")


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _run_dry_run(path: Path) -> None:
    """
    キー不要で staging JSON の翻訳対象を確認する。
    API を呼ばず、ファイルも変更しない。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("ERROR: staging JSON must be a list")

    title_cnt = 0
    desc_cnt = 0
    tag_cnt = 0
    for entry in data:
        if not isinstance(entry, dict):
            continue
        title = strip_untranslated_prefix(str(entry.get("title") or ""))
        desc = strip_untranslated_prefix(str(entry.get("description") or ""))
        if title and looks_japanese(title):
            title_cnt += 1
        if desc and looks_japanese(desc):
            desc_cnt += 1
        tags = entry.get("tags")
        if isinstance(tags, list):
            for t in tags:
                t = str(t or "").strip()
                if t and looks_japanese(t):
                    tag_cnt += 1

    print(f"[dry-run] {path}")
    print(f"  翻訳対象: タイトル {title_cnt} 件, 説明 {desc_cnt} 件, タグ {tag_cnt} 件")
    print("  実際の翻訳は実行していません（DEEPL_AUTH_KEY を設定して --dry-run なしで実行してください）")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", help="staging JSON path (e.g. data/staging/20260319_1153.json)")
    parser.add_argument("--inplace", action="store_true", default=True, help="(default) overwrite the file")
    parser.add_argument("--batch", type=int, default=20, help="DeepL request batch size")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="翻訳対象を確認するだけ（API呼び出しなし・キー不要）。ファイルは変更しない。",
    )
    args = parser.parse_args()

    auth_key = os.getenv("DEEPL_AUTH_KEY", "").strip()
    if not args.dry_run and not auth_key:
        print("DEEPL_AUTH_KEY が未設定なので、翻訳は実行しません。")
        print("例: export DEEPL_AUTH_KEY='your_key_here'  # その後にこのスクリプトを再実行")
        raise SystemExit(2)

    path = Path(args.path) if args.path else None
    if not path or not path.exists():
        # dry-run でパス未指定の場合は staging ディレクトリ内の最新ファイルを使用
        if args.dry_run:
            staging_dir = Path("data/staging")
            if staging_dir.exists():
                files = sorted(staging_dir.glob("*.json"), reverse=True)
                path = files[0] if files else None
        if not path or not path.exists():
            raise SystemExit(f"ERROR: file not found: {path or 'path required'}")

    if args.dry_run:
        _run_dry_run(path)
        return

    if not path.exists():
        raise SystemExit(f"ERROR: file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("ERROR: staging JSON must be a list")

    # --- collect texts to translate ---
    title_idx: List[Tuple[int, str]] = []
    desc_idx: List[Tuple[int, str]] = []
    tag_idx: List[Tuple[int, int, str]] = []  # entry_i, tag_i, text

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue

        title = strip_untranslated_prefix(str(entry.get("title") or ""))
        desc = strip_untranslated_prefix(str(entry.get("description") or ""))
        if title and looks_japanese(title):
            title_idx.append((i, title))
        if desc and looks_japanese(desc):
            desc_idx.append((i, desc))

        tags = entry.get("tags")
        if isinstance(tags, list):
            for j, t in enumerate(tags):
                t = str(t or "").strip()
                if t and looks_japanese(t):
                    tag_idx.append((i, j, t))

        # prefix除去だけはキー無しでもやりたくなるけど、事故防止で「キー無しは一切変更しない」方針

    # --- translate in batches ---
    def translate_pairs(pairs: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        out: List[Tuple[int, str]] = []
        texts = [t for _, t in pairs]
        translated: List[str] = []
        for chunk in chunked(texts, size=max(1, args.batch)):
            translated.extend(
                deepl_translate_batch(auth_key=auth_key, texts=chunk, source_lang="JA", target_lang="EN")
            )
        for (idx, _), tr in zip(pairs, translated):
            out.append((idx, tr))
        return out

    translated_titles = translate_pairs(title_idx)
    translated_descs = translate_pairs(desc_idx)

    # tags は短いのでまとめて翻訳
    translated_tags_map: dict[tuple[int, int], str] = {}
    if tag_idx:
        tag_texts = [t for _, _, t in tag_idx]
        tag_tr: List[str] = []
        for chunk in chunked(tag_texts, size=max(1, args.batch)):
            tag_tr.extend(deepl_translate_batch(auth_key=auth_key, texts=chunk, source_lang="JA", target_lang="EN"))
        for (ei, ti, _), tr in zip(tag_idx, tag_tr):
            translated_tags_map[(ei, ti)] = tr

    # --- apply ---
    for i, tr in translated_titles:
        data[i]["title"] = tr
    for i, tr in translated_descs:
        data[i]["description"] = tr
    for (ei, ti), tr in translated_tags_map.items():
        tags = data[ei].get("tags")
        if isinstance(tags, list) and 0 <= ti < len(tags):
            tags[ti] = tr

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: translated titles={len(translated_titles)} descs={len(translated_descs)} tags={len(translated_tags_map)} -> {path}")


if __name__ == "__main__":
    main()

