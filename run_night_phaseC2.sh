#!/usr/bin/env bash
# Phase C2: strengthen small-eps results (more seeds, bigger budget).
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseC2.log
echo "=== phaseC2 start $(date) ===" >> "$LOG"
for eps in 0.01 0.005; do
  tag=$(echo "$eps" | tr -d '.')
  echo "--- smooth K=32 eps=$eps seeds 4-7 start $(date) ---" >> "$LOG"
  nice -n 10 "$PY" smooth_run.py --eps "$eps" --K 32 --Nf 8 --Nb 8 \
      --seeds 4 --popsize 24 --maxiter 350 --workers 6 \
      --init-json "results/smooth_${tag}_K32.json" \
      --out "results/smooth_${tag}_K32_more.json" >> "$LOG" 2>&1
  echo "--- eps=$eps rc=$? $(date) ---" >> "$LOG"
done
echo "=== phaseC2 done $(date) ===" >> "$LOG"
touch results/PHASE_C2_DONE
