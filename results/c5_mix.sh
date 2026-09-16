#!/usr/bin/env bash
set -u
cd /home/z/vibe/fat_kakeya_needle
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseC2.log
echo "=== C5a v2 K=8 @eps=0.005 $(date) ===" >> "$LOG"
nice -n 10 "$PY" optimize_v2.py --eps 0.005 --K_start 8 --K_end 8 --seeds 3 \
    --popsize 24 --maxiter 200 --n_theta 40 --workers 6 \
    --out results/v2_0005_K8.json >> "$LOG" 2>&1
echo "=== C5a rc=$? $(date) ===" >> "$LOG"
touch results/C5_DONE
