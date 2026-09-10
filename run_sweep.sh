#!/usr/bin/env bash
# Run the epsilon sweep: one process per (eps) with 4 seeds inside.
# Each optimize.py call uses workers=-1 (all cores) internally, so we
# stagger the runs by launching eps values sequentially with small budgets.
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
mkdir -p results
EPS_LIST="0.8 0.6 0.5 0.4 0.3 0.2 0.15 0.1 0.07 0.05"
for eps in $EPS_LIST; do
    tag=$(echo "$eps" | tr -d '.')
    echo "=== eps=$eps ==="
    "$PY" optimize.py --eps "$eps" --K 6 --seeds 4 --popsize 40 --maxiter 250 \
        --grid 420 --out "results/eps_${tag}.json" 2>&1
done
echo "SWEEP DONE"
