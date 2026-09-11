#!/usr/bin/env bash
# Multi-seed fresh runs per K: area(K) = min over seeds.
# K in {6, 10, 14}, 3 seeds each, eps=0.05. Sequential, 6 workers.
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
for K in 6 10 14; do
  echo "=== K=$K ==="
  "$PY" optimize_v2.py --eps 0.05 --K_start "$K" --K_end "$K" \
      --seeds 3 --popsize 24 --maxiter 150 --n_theta 40 --workers 6 \
      --out "results/v2_005_K${K}_multiseed.json" 2>&1 | grep -v Warning
done
echo "MULTISEED-K DONE"
