#!/usr/bin/env python3
"""Entrypoint for the review queue.

Resolves everything from this file's location rather than the process working
directory: the preview runner does not guarantee a cwd, and Flask's own CLI calls
os.getcwd() through python-dotenv, which fails outright under a restricted one.

Run:  python3 serve.py        (PORT env var respected, default 5001)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)  # data/rows.json is read relative to the repo root

from src.ui.app import app  # noqa: E402  (import must follow the sys.path fix)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5001")), debug=False)
