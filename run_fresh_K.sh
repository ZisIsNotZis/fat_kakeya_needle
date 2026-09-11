#!/usr/bin/env bash
# Fresh (no warm-start) v2 runs at increasing K, one at a time.
# Question: does f(0.05) keep dropping as K grows, or saturate?
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
for K in 6 8 10 12 14 16; do
  echo "=== K=$K ==="
  "$PY" optimize_v2.py --eps 0.05 --K_start "$K" --K_end "$K" \
      --seeds 1 --popsize 24 --maxiter 150 --n_theta 40 --workers 6 \
      --out "results/v2_005_fresh_K${K}.json" 2>&1 | grep -v Warning
done
echo "FRESH-K DONE"
