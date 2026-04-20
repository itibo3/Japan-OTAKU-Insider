#!/usr/bin/env python3
"""
translate_staging.py — staging JSON を英語化する（Google 優先、不備時は DeepL）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
UNTRANSLATED_PREFIX_RE = re.compile(r"^\s*\[未翻訳\]\s*")
JA_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")


def strip_untranslated_prefix(text: str) -> str:
    return UNTRANSLATED_PREFIX_RE.sub("", text or "").strip()


def looks_japanese(text: str) -> bool:
    return bool(JA_CHAR_RE.search(text or ""))


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def translation_deficient(source: str, translated: str) -> bool:
    s = (source or "").strip()
    if not s:
        return False
    t = (translated or "").strip()
    if not t:
        return True
    if looks_japanese(s) and looks_japanese(t):
        return True
    if s == t and looks_japanese(s):
        return True
    return False


def detect_deepl_endpoint(auth_key: str) -> str:
    if auth_key.strip().endswith(":fx"):
        return "https://api-free.deepl.com/v2/translate"
    return "https://api.deepl.com/v2/translate"


def deepl_translate_batch(*, auth_key: str, texts: List[str]) -> List[str]:
    import requests

    if not texts:
        return []
    primary = detect_deepl_endpoint(auth_key)
    secondary = (
        "https://api-free.deepl.com/v2/translate"
        if primary == "https://api.deepl.com/v2/translate"
        else "https://api.deepl.com/v2/translate"
    )

    def call(endpoint: str) -> List[str]:
        headers = {
            "Authorization": f"DeepL-Auth-Key {auth_key}",
            "Content-Type": "application/json",
        }
        payload = {"text": texts, "source_lang": "JA", "target_lang": "EN"}
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"DeepL error: HTTP {resp.status_code} {resp.text[:300]}")
        body = resp.json()
        out = []
        for tr in body.get("translations", []) or []:
            out.append((tr.get("text") or "").strip())
        if len(out) != len(texts):
            raise RuntimeError("DeepL response size mismatch")
        return out

    try:
        return call(primary)
    except Exception as e1:
        try:
            return call(secondary)
        except Exception as e2:
            raise RuntimeError(f"DeepL failed: primary={e1!r} secondary={e2!r}") from e2


def google_translate_each(texts: List[str], *, delay_sec: float) -> List:
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source="ja", target="en")
    out = []
    for i, raw in enumerate(texts):
        s = (raw or "").strip()
        if not s:
            out.append("")
            continue
        try:
            tr = translator.translate(s)
            out.append((tr or "").strip())
        except Exception as e:
            print(f"  [Google] 失敗 index={i}: {e}")
            out.append(None)
        if delay_sec > 0 and i < len(texts) - 1:
            time.sleep(delay_sec)
    return out


def translate_texts_with_fallback(
    texts: List[str],
    *,
    auth_key,
    delay_sec: float,
    deepl_batch: int,
) -> Tuple[List[str], int]:
    google_results = google_translate_each(texts, delay_sec=delay_sec)
    merged: List[str] = []
    need_indices: List[int] = []
    for i, s in enumerate(texts):
        s_clean = (s or "").strip()
        if not s_clean:
            merged.append("")
            continue
        g = google_results[i] if i < len(google_results) else None
        if g is None or translation_deficient(s_clean, g):
            need_indices.append(i)
            merged.append(g if g is not None else "")
        else:
            merged.append(g)

    deepl_count = 0
    if need_indices:
        if not auth_key:
            print(
                "  [WARN] Google 不備ありだが DEEPL_AUTH_KEY なし。Google の結果のまま進みます。"
            )
            for i in need_indices:
                if not (merged[i] or "").strip() and (texts[i] or "").strip():
                    raise SystemExit(
                        f"ERROR: 翻訳不能 index={i}（Google 失敗かつ DeepL キーなし）。"
                    )
        else:
            to_fix = [(texts[i] or "").strip() for i in need_indices]
            print(f"  [DeepL] フォールバック {len(to_fix)} 件を再翻訳します。")
            fixed_chunks: List[str] = []
            bs = max(1, deepl_batch)
            for chunk in chunked(to_fix, bs):
                fixed_chunks.extend(deepl_translate_batch(auth_key=auth_key, texts=chunk))
                time.sleep(0.2)
            deepl_count = len(to_fix)
            for idx, tr in zip(need_indices, fixed_chunks):
                merged[idx] = tr

    return merged, deepl_count


def _run_dry_run(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("ERROR: staging JSON must be a list")

    title_cnt = desc_cnt = tag_cnt = 0
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

    has_deepl = bool(os.getenv("DEEPL_AUTH_KEY", "").strip())
    print(f"[dry-run] {path}")
    print(f"  翻訳対象: タイトル {title_cnt} 件, 説明 {desc_cnt} 件, タグ {tag_cnt} 件")
    print(f"  DEEPL_AUTH_KEY: {'あり（Google 不備時にフォールバック）' if has_deepl else 'なし（Google のみ）'}")
    print("  実際の翻訳は実行していません（--dry-run なしで実行）")


def main() -> None:
    parser = argparse.ArgumentParser(description="staging JSON を英語化（Google 優先・DeepL フォールバック）")
    parser.add_argument("path", nargs="?", help="staging JSON path")
    parser.add_argument("--inplace", action="store_true", default=True, help="(default) overwrite")
    parser.add_argument("--batch", type=int, default=20, help="DeepL バッチサイズ")
    parser.add_argument("--delay", type=float, default=0.08, help="Google 各リクエスト間の待機秒")
    parser.add_argument("--dry-run", action="store_true", help="対象件数のみ表示")
    args = parser.parse_args()

    auth_key = os.getenv("DEEPL_AUTH_KEY", "").strip() or None

    path = Path(args.path) if args.path else None
    if not path or not path.exists():
        if args.dry_run:
            staging_dir = ROOT / "data" / "staging"
            if staging_dir.exists():
                files = sorted(staging_dir.glob("*.json"), reverse=True)
                path = files[0] if files else None
        if not path or not path.exists():
            raise SystemExit(f"ERROR: file not found: {path or 'path required'}")

    if args.dry_run:
        _run_dry_run(path)
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("ERROR: staging JSON must be a list")

    title_idx: List[Tuple[int, str]] = []
    desc_idx: List[Tuple[int, str]] = []
    tag_idx: List[Tuple[int, int, str]] = []

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

    total_deepl = 0

    def translate_pairs(pairs: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        nonlocal total_deepl
        texts = [t for _, t in pairs]
        merged, dc = translate_texts_with_fallback(
            texts, auth_key=auth_key, delay_sec=args.delay, deepl_batch=max(1, args.batch)
        )
        total_deepl += dc
        return [(idx, tr) for (idx, _), tr in zip(pairs, merged)]

    translated_titles = translate_pairs(title_idx)
    translated_descs = translate_pairs(desc_idx)

    translated_tags_map = {}
    if tag_idx:
        tag_texts = [t for _, _, t in tag_idx]
        merged, dc = translate_texts_with_fallback(
            tag_texts, auth_key=auth_key, delay_sec=args.delay, deepl_batch=max(1, args.batch)
        )
        total_deepl += dc
        for (ei, ti, _), tr in zip(tag_idx, merged):
            translated_tags_map[(ei, ti)] = tr

    for i, tr in translated_titles:
        data[i]["title"] = tr
    for i, tr in translated_descs:
        data[i]["description"] = tr
    for (ei, ti), tr in translated_tags_map.items():
        tags = data[ei].get("tags")
        if isinstance(tags, list) and 0 <= ti < len(tags):
            tags[ti] = tr

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"OK: translated titles={len(translated_titles)} descs={len(translated_descs)} "
        f"tags={len(translated_tags_map)} -> {path} (DeepL フォールバック文字列数: {total_deepl})"
    )


if __name__ == "__main__":
    main()
