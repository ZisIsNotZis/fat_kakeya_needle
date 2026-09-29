#!/usr/bin/env bash
# RF calibration phase: real DE-selected candidates, measure true validation cost.
# B=240, reserve=0 (pilot only, never ranked); seeds {0,1} x 4 families.
set -u
PY=/home/z/.venv/bin/python3
OUT=results/rf_calibration_0005
LOG=.tmp/rf_calibration.log
mkdir -p "$OUT" .tmp
: > "$LOG"
for family in smooth hierarchical free_pivot v2_repaired; do
  for seed in 0 1; do
    timeout --kill-after=10s 2400s \
      taskset -c 0 nice -n 10 "$PY" budget_total_integer.py --run \
        --family "$family" --seed "$seed" --eps 0.005 \
        --total-budget 240 --reserve 0 \
        --out "$OUT/${family}_seed${seed}_B240_r0.json" >> "$LOG" 2>&1
    echo "$(date -Is) $family seed$seed rc=$?" >> "$LOG"
  done
done
echo "$(date -Is) CALIBRATION COMPLETE" >> "$LOG"
