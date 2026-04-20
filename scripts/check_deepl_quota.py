#!/usr/bin/env python3
"""
DeepL APIの利用枠を確認し、CSVに記録するスクリプト。
残枠（character_limit - character_count）が --require で指定した文字数を下回る場合は exit 1 を返す。

出力先: data/deepl_usage_log.csv
"""

import argparse
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# /v2/usage はFree/Pro共通で使えるエンドポイントのドメインが異なる
def detect_endpoint(auth_key: str) -> str:
    if auth_key.strip().endswith(":fx"):
        return "https://api-free.deepl.com/v2/usage"
    return "https://api.deepl.com/v2/usage"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require", type=int, default=0, help="最低限必要な残り文字数（これを下回るとエラー終了）")
    args = parser.parse_args()

    auth_key = os.environ.get("DEEPL_AUTH_KEY", "").strip()
    if not auth_key:
        print("DEEPL_AUTH_KEY is not set.")
        sys.exit(0)  # キーがない場合は無難に正常終了（翻訳処理自体がスキップされる仕組みに委ねる）

    url = detect_endpoint(auth_key)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"DeepL-Auth-Key {auth_key}")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Failed to fetch DeepL usage: {e}")
        # API障害などの場合は、一応正常終了扱いにして後続の翻訳処理自体でエラーを取らせるか判断
        # 今回は安全側に倒して正常終了扱いにし、実際に翻訳スクリプト側でエラーを出させる
        sys.exit(0)

    count = data.get("character_count", 0)
    limit = data.get("character_limit", 500000)
    remaining = limit - count

    print(f"DeepL Usage: {count} / {limit} (Remaining: {remaining})")

    # CSVへの記録
    csv_file = ROOT / "data" / "deepl_usage_log.csv"
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_exists = csv_file.exists()
    
    with open(csv_file, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "CharacterCount", "CharacterLimit", "Remaining"])
        
        # UTCで実行されているCIに合わせて、JST相当で可読性の高い日付を入れる
        now = datetime.now()
        writer.writerow([now.strftime("%Y-%m-%d %H:%M:%S"), count, limit, remaining])

    if args.require > 0 and remaining < args.require:
        print(f"Error: Remaining characters ({remaining}) is less than required ({args.require}).")
        sys.exit(1)

if __name__ == "__main__":
    main()
