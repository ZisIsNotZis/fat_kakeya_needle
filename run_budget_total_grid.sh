#!/usr/bin/env bash
# Driver for the formal 48-cell total-CPU budget grid (protocol A).
# 4 families x budgets {60,120,240,480} x seeds {0,1,2}, sequential, single core.
# Frozen reserves R_f (ticket 03, 2026-09-29): smooth=10 hier=18 free_pivot=44 v2=2.
# One cold infra-failure retry per cell (ticket 03 frozen policy).
set -u
PY=/home/z/.venv/bin/python3
OUT=results/budget_total_grid_0005
LOG=.tmp/budget_total_grid_0005.log
mkdir -p "$OUT" .tmp
declare -A RF=( [smooth]=39 [hierarchical]=23 [free_pivot]=36 [v2_repaired]=17 )
CELLS_DONE=.tmp/grid_cells_done.txt
: > "$LOG"; : > "$CELLS_DONE"
for family in smooth hierarchical free_pivot v2_repaired; do
  for seed in 0 1 2; do
    for budget in 60 120 240 480; do
      rf=${RF[$family]}
      run_one () {
        local tag="$1" attempt="$2"
        local out="$OUT/${family}_seed${seed}_B${budget}${attempt}.json"
        # external wall timeout well beyond any expected cell (CPU<=480+slack)
        timeout --kill-after=10s 2400s \
          taskset -c 0 nice -n 10 "$PY" budget_total_integer.py --run \
            --family "$family" --seed "$seed" --eps 0.005 \
            --total-budget "$budget" --reserve "$rf" \
            --out "$out" >> "$LOG" 2>&1
        local rc=$?
        echo "$(date -Is) $tag rc=$rc out=$out" >> "$LOG"
        [ $rc -eq 0 ] && echo "$out" >> "$CELLS_DONE"
        return $rc
      }
      run_one "${family}_s${seed}_B${budget}" _a1
      rc=$?
      if [ $rc -ne 0 ]; then
        # single cold retry allowed for infrastructure failure
        timeout --kill-after=10s 2400s \
          taskset -c 0 nice -n 10 "$PY" budget_total_integer.py --run \
            --family "$family" --seed "$seed" --eps 0.005 \
            --total-budget "$budget" --reserve "$rf" \
            --out "$OUT/${family}_seed${seed}_B${budget}_retry.json" >> "$LOG" 2>&1
        rc2=$?
        echo "$(date -Is) ${family}_s${seed}_B${budget} retry rc=$rc2" >> "$LOG"
        [ $rc2 -eq 0 ] && echo "$OUT/${family}_seed${seed}_B${budget}_retry.json" >> "$CELLS_DONE"
      fi
    done
  done
done
echo "$(date -Is) GRID COMPLETE cells=$(wc -l < "$CELLS_DONE")" >> "$LOG"
