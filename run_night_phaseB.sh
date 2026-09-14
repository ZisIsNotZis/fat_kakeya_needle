#!/usr/bin/env bash
# Phase B: smooth-profile pivot+slide at eps=0.05.
# K in {12, 16, 32, 64} x 3 seeds (64 gets 2). Detached-safe.
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseB.log
echo "=== phaseB start $(date) ===" >> "$LOG"
for K in 12 16 32 64; do
  S=3
  [ "$K" = "64" ] && S=2
  echo "--- K=$K seeds=$S start $(date) ---" >> "$LOG"
  nice -n 10 "$PY" smooth_run.py --eps 0.05 --K "$K" --Nf 6 --Nb 6 \
      --seeds "$S" --popsize 20 --maxiter 200 --workers 6 \
      --out "results/smooth_005_K${K}.json" >> "$LOG" 2>&1
  echo "--- K=$K rc=$? $(date) ---" >> "$LOG"
done
echo "=== phaseB done $(date) ===" >> "$LOG"
touch results/PHASE_B_DONE
