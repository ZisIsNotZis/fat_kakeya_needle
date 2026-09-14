#!/usr/bin/env bash
# Phase C: small-eps asymptotic test. Waits for Phase B marker, then runs
# smooth-profile K=32 with mixed init across eps, plus free-beta K=8 controls.
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseC.log

echo "phaseC waiting for PHASE_B_DONE ($(date))" >> "$LOG"
while [ ! -f results/PHASE_B_DONE ]; do sleep 120; done
echo "=== phaseC start $(date) ===" >> "$LOG"

prior=""
for eps in 0.02 0.01 0.005; do
  tag=$(echo "$eps" | tr -d '.')
  init_arg=""
  if [ -n "$prior" ] && [ -f "$prior" ]; then init_arg="--init-json $prior"; fi
  echo "--- smooth K=32 eps=$eps $init_arg start $(date) ---" >> "$LOG"
  nice -n 10 "$PY" smooth_run.py --eps "$eps" --K 32 --Nf 6 --Nb 6 \
      --seeds 4 --popsize 20 --maxiter 250 --workers 6 \
      $init_arg --out "results/smooth_${tag}_K32.json" >> "$LOG" 2>&1
  echo "--- smooth eps=$eps rc=$? $(date) ---" >> "$LOG"
  prior="results/smooth_${tag}_K32.json"

  echo "--- free-beta K=8 eps=$eps start $(date) ---" >> "$LOG"
  nice -n 10 "$PY" optimize_pivot.py --eps "$eps" --K 8 --seeds 3 \
      --popsize 24 --maxiter 150 --workers 6 \
      --out "results/pivot_${tag}_K8.json" >> "$LOG" 2>&1
  echo "--- free-beta eps=$eps rc=$? $(date) ---" >> "$LOG"
done

echo "=== phaseC done $(date) ===" >> "$LOG"
touch results/PHASE_C_DONE
