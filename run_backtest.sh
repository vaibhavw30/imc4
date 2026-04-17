#!/usr/bin/env bash
# Run prosperity4btest on Round 1 with a timestamped log.
# Forwards extra args to the underlying CLI, e.g.:
#   ./run_backtest.sh --match-trades worse --print
set -euo pipefail

mkdir -p logs
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT="logs/run_${TIMESTAMP}.log"

# PYTHONPATH=. so `from algo.* import ...` resolves when prosperity4btest
# imports algo/trader.py from inside its own working directory.
PYTHONPATH=. prosperity4btest algo/trader.py 1 --out "$OUT" "$@"

echo ""
echo "Log saved to: $OUT"
echo "Upload to https://prosperity.equirag.com/ to visualize."
