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
from pathlib import Path

import requests

# Discord: 通常メッセージ content は最大2000文字。長文は embed description（最大4096）へ逃がす。
# 1メッセージあたり embed 全体で実質6000文字上限のため、超えそうなら2回に分割して POST する。
_EMBED_DESC_SAFE = 3800
_MAX_SINGLE_EMBED_DESC = 4000


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


def _truncate(s: str, max_len: int) -> str:
    """Discord 表示用に安全に省略（文字数上限対策）。"""
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _build_discord_payloads(
    *,
    header_lines: str,
    report_text: str,
    proposals_summary: str,
) -> list[dict]:
    """1〜2件の webhook JSON ボディを組み立てる。"""
    rep = (report_text or "").strip() or "（レポートなし）"
    prop = (proposals_summary or "").strip() or "（なし）"
    combined = f"**週次レポート（抜粋）**\n{rep}\n\n**改善案サマリ**\n{prop}"
    if len(combined) <= _MAX_SINGLE_EMBED_DESC:
        return [
            {
                "content": header_lines,
                "embeds": [{"title": "JOI 週次サマリ", "description": combined}],
            }
        ]
    return [
        {
            "content": header_lines,
            "embeds": [{"title": "週次レポート（抜粋）", "description": _truncate(rep, _EMBED_DESC_SAFE)}],
        },
        {
            "embeds": [{"title": "改善案サマリ", "description": _truncate(prop, _EMBED_DESC_SAFE)}],
        },
    ]


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
    proposals_summary = _build_summary(proposals)

    run_url = ""
    if args.repo and args.run_id:
        run_url = f"{args.server_url}/{args.repo}/actions/runs/{args.run_id}"

    header = "📊 JOI 週次改善レポートが更新されました"
    if run_url:
        header += f"\n\n実行ログ / Artifact: {run_url}"

    payloads = _build_discord_payloads(
        header_lines=header,
        report_text=report_text,
        proposals_summary=proposals_summary,
    )
    for body in payloads:
        resp = requests.post(args.webhook_url, json=body, timeout=20)
        if resp.status_code >= 400:
            raise RuntimeError(f"Discord通知失敗 HTTP {resp.status_code}: {resp.text[:200]}")
    print(f"Discord通知: 送信成功（{len(payloads)}件）")


if __name__ == "__main__":
    main()
