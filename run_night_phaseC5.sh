#!/usr/bin/env bash
# Phase C5: re-run small eps with high-res objectives (n_arc=160).
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseC5.log
echo "=== phaseC5 start $(date) ===" >> "$LOG"
for cfg in "0.01 32 4" "0.005 32 4" "0.002 32 3"; do
  set -- $cfg
  eps=$1; K=$2; seeds=$3
  tag=$(echo "$eps" | tr -d '.')
  echo "--- smooth hi-res eps=$eps K=$K seeds=$seeds start $(date) ---" >> "$LOG"
  nice -n 10 "$PY" smooth_run.py --eps "$eps" --K "$K" --Nf 8 --Nb 8 \
      --seeds "$seeds" --popsize 24 --maxiter 250 --workers 6 --n_arc 160 \
      --out "results/smooth_hr_${tag}_K${K}.json" >> "$LOG" 2>&1
  echo "--- eps=$eps rc=$? $(date) ---" >> "$LOG"
done
echo "=== phaseC5 done $(date) ===" >> "$LOG"
touch results/PHASE_C5_DONE
