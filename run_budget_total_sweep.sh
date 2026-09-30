#!/usr/bin/env bash
# Ticket 05: formal eps sweep over {0.8,0.4,0.2,0.1,0.05,0.02,0.01},
# protocol A (total-CPU), B=480, seeds {0,1,2}, 4 families, frozen R_f.
# Single core nice10, sequential; one cold retry per cell.
set -u
PY=/home/z/.venv/bin/python3
OUT=results/budget_total_sweep
LOG=.tmp/budget_total_sweep.log
DONE=.tmp/sweep_cells_done.txt
mkdir -p "$OUT" .tmp
: > "$LOG"; : > "$DONE"
declare -A RF=( [smooth]=39 [hierarchical]=23 [free_pivot]=36 [v2_repaired]=17 )
for eps in 0.8 0.4 0.2 0.1 0.05 0.02 0.01; do
  for family in smooth hierarchical free_pivot v2_repaired; do
    for seed in 0 1 2; do
      rf=${RF[$family]}
      tag="${family}_s${seed}_e${eps}"
      timeout --kill-after=10s 2400s \
        taskset -c 0 nice -n 10 "$PY" budget_total_integer.py --run \
          --family "$family" --seed "$seed" --eps "$eps" \
          --total-budget 480 --reserve "$rf" \
          --out "$OUT/${family}_seed${seed}_e${eps}.json" >> "$LOG" 2>&1
      rc=$?
      echo "$(date -Is) $tag rc=$rc" >> "$LOG"
      if [ $rc -eq 0 ]; then
        echo "$OUT/${family}_seed${seed}_e${eps}.json" >> "$DONE"
      else
        # one cold retry; remove the failed attempt first so the aggregator
        # never sees two files for the same (family, eps, seed) key
        rm -f "$OUT/${family}_seed${seed}_e${eps}.json"
        timeout --kill-after=10s 2400s \
          taskset -c 0 nice -n 10 "$PY" budget_total_integer.py --run \
            --family "$family" --seed "$seed" --eps "$eps" \
            --total-budget 480 --reserve "$rf" \
            --out "$OUT/${family}_seed${seed}_e${eps}.json" >> "$LOG" 2>&1
        rc2=$?
        echo "$(date -Is) $tag retry rc=$rc2" >> "$LOG"
        [ $rc2 -eq 0 ] && echo "$OUT/${family}_seed${seed}_e${eps}.json" >> "$DONE"
      fi
    done
  done
done
echo "$(date -Is) SWEEP COMPLETE cells=$(wc -l < "$DONE")" >> "$LOG"
