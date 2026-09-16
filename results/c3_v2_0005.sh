#!/usr/bin/env bash
set -u
cd /home/z/vibe/fat_kakeya_needle
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseC2.log
echo "=== C3 v2 cross-check eps=0.005 $(date) ===" >> "$LOG"
nice -n 10 "$PY" optimize_v2.py --eps 0.005 --K_start 6 --K_end 6 --seeds 3 \
    --popsize 24 --maxiter 200 --n_theta 40 --workers 6 \
    --out results/v2_0005.json >> "$LOG" 2>&1
echo "=== C3 rc=$? $(date) ===" >> "$LOG"
touch results/C3_DONE
