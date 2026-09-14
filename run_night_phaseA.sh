#!/usr/bin/env bash
# Phase A: pivot+slide free-parameter baseline at eps=0.05.
# K in {8,12,16} x 4 seeds. Detached-safe: writes log + DONE marker.
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseA.log
echo "=== phaseA start $(date) ===" >>"$LOG"
for K in 8 12 16; do
    echo "--- K=$K start $(date) ---" >>"$LOG"
    nice -n 10 "$PY" optimize_pivot.py --eps 0.05 --K "$K" --seeds 4 \
        --popsize 24 --maxiter 150 --workers 6 \
        --out "results/pivot_005_K${K}_night.json" >>"$LOG" 2>&1
    echo "--- K=$K rc=$? $(date) ---" >>"$LOG"
done
echo "=== phaseA done $(date) ===" >>"$LOG"
touch results/PHASE_A_DONE
