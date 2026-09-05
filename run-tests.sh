#!/usr/bin/env bash
# Every test suite, failing on the first one that fails.
set -euo pipefail
for suite in tests/test_*.py; do
  python3 "$suite"
done
echo "all suites pass"
