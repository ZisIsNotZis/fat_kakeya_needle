#!/usr/bin/env bash
# Phase C5b: high-res small eps, reduced n_arc, incremental checkpointing.
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseC5.log
echo "=== phaseC5b start $(date) ===" >> "$LOG"
for cfg in "0.01 80 3" "0.005 80 3" "0.002 60 2"; do
  set -- $cfg
  eps=$1; narc=$2; seeds=$3
  tag=$(echo "$eps" | tr -d '.')
  echo "--- smooth n_arc=$narc eps=$eps seeds=$seeds start $(date) ---" >> "$LOG"
  nice -n 10 "$PY" smooth_run.py --eps "$eps" --K 32 --Nf 8 --Nb 8 \
      --seeds "$seeds" --popsize 20 --maxiter 150 --workers 6 --n_arc "$narc" \
      --out "results/smooth_hr_${tag}_K32.json" >> "$LOG" 2>&1
  echo "--- eps=$eps rc=$? $(date) ---" >> "$LOG"
done
echo "=== phaseC5b done $(date) ===" >> "$LOG"
touch results/PHASE_C5B_DONE
