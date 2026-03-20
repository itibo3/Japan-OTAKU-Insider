#!/usr/bin/env python3
"""
weekly_report.py — Perplexity記事のカテゴリ別生存率を集計してMarkdown出力
"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

ENTRIES_FILE = Path("data/entries.json")
JST = timezone(timedelta(hours=9))
CATEGORIES = ["cafe", "vtuber", "figure", "game", "anime", "other"]

def main():
    data = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    now = datetime.now(JST)
    week_ago = now - timedelta(days=7)
    pplx_entries = [e for e in entries if e.get("_source") == "perplexity"]
    total = len(pplx_entries)
    active = len([e for e in pplx_entries if e.get("status") == "active"])
    cat_total = defaultdict(int)
    cat_active = defaultdict(int)
    for e in pplx_entries:
        cats = e.get("categories", ["other"])
        cat = cats[0] if cats else "other"
        cat_total[cat] += 1
        if e.get("status") == "active":
            cat_active[cat] += 1
    lines = [
        "## 📊 Weekly Perplexity Report",
        f"**期間:** {week_ago.strftime('%Y/%m/%d')} 〜 {now.strftime('%Y/%m/%d')}",
        "",
        "### カテゴリ別生存率",
        "| カテゴリ | 総記事数 | 生存 | 生存率 | 判定 |",
        "|---------|---------|------|--------|------|",
    ]
    for cat in CATEGORIES:
        t = cat_total.get(cat, 0)
        a = cat_active.get(cat, 0)
        rate = int(a / t * 100) if t > 0 else 0
        judge = "✅ 良好" if rate >= 70 else ("⚠️ 要観察" if rate >= 40 else "❌ 要見直し")
        lines.append(f"| {cat} | {t} | {a} | {rate}% | {judge} |")
    overall_rate = int(active / total * 100) if total > 0 else 0
    lines += [
        "",
        f"**総合生存率: {overall_rate}%** （{active}/{total}件）",
        "",
        "### アクションアイテム",
        "- ❌ 判定のカテゴリはPerplexity検索を見直し・一時停止を検討",
        "- ✅ 判定のカテゴリは検索件数・キーワード強化を検討",
        "",
        "*自動生成 by weekly_report.py*",
    ]
    print("\n".join(lines))

if __name__ == "__main__":
    main()