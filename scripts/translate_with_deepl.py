#!/usr/bin/env python3
"""後方互換: 旧ファイル名。本体は translate_staging（Google 優先、不備時 DeepL）。"""
import sys
from pathlib import Path
_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
from translate_staging import main
if __name__ == "__main__":
    main()
