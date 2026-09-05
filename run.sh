#!/usr/bin/env bash
# The one command the judges execute. Keep it working on a clean clone.
set -euo pipefail

python3 -m pip install --quiet -r requirements.txt
python3 -m src.pipeline
python3 -m src.matcher.score
echo
echo "Review queue:  python3 serve.py"
