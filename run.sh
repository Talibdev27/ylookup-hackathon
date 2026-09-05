#!/usr/bin/env bash
# The one command the judges execute. Keep it working on a clean clone.
set -euo pipefail

python3 -m pip install --quiet -r requirements.txt
python3 -m src.spine.build
python3 -m src.matcher.run
python3 -m src.matcher.score data/rows.json
echo
echo "Review queue:  flask --app src.ui.app run --port 5001"
