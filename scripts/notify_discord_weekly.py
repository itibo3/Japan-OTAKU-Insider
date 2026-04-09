#!/usr/bin/env python3
"""
週次の改善案サマリを Discord Webhook に通知する。

入力:
  - 改善案JSON（claude_prompt_proposals.json）
  - 週次レポート（weekly_report_ja.md）
出力:
  - Discord通知（Webhook）
"""

from __future__ import annotations

import argparse
import json
import os
import textwrap
from pathlib import Path

import requests


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _build_summary(proposals: dict) -> str:
    if not proposals:
        return "今回は改善案JSONが空でした。"
    lines = []
    for k, v in proposals.items():
        text = " ".join(str(v).split())
        if len(text) > 140:
            text = text[:137] + "..."
        lines.append(f"- `{k}`: {text}")
    return "\n".join(lines[:8])


def main() -> None:
    parser = argparse.ArgumentParser(description="Discordへ週次改善案を通知")
    parser.add_argument("--webhook-url", default=os.getenv("DISCORD_WEBHOOK_URL", "").strip())
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", ""))
    parser.add_argument("--server-url", default=os.getenv("GITHUB_SERVER_URL", "https://github.com"))
    args = parser.parse_args()

    if not args.webhook_url:
        print("DISCORD_WEBHOOK_URL 未設定のため通知スキップ")
        return

    proposals = _load_json(args.proposals)
    report_text = args.report.read_text(encoding="utf-8") if args.report.exists() else ""
    report_preview = " ".join(report_text.split())
    if len(report_preview) > 220:
        report_preview = report_preview[:217] + "..."
    if not report_preview:
        report_preview = "(週次レポート本文なし)"

    run_url = ""
    if args.repo and args.run_id:
        run_url = f"{args.server_url}/{args.repo}/actions/runs/{args.run_id}"

    content = textwrap.dedent(
        f"""
        📊 JOI 週次改善レポートが更新されました

        **改善案サマリ**
        {_build_summary(proposals)}

        **レポート冒頭**
        {report_preview}
        """
    ).strip()
    if run_url:
        content += f"\n\n実行ログ/Artifact: {run_url}"

    resp = requests.post(args.webhook_url, json={"content": content}, timeout=20)
    if resp.status_code >= 400:
        raise RuntimeError(f"Discord通知失敗 HTTP {resp.status_code}: {resp.text[:200]}")
    print("Discord通知: 送信成功")


if __name__ == "__main__":
    main()
