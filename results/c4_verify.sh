#!/usr/bin/env bash
set -u
cd /home/z/vibe/fat_kakeya_needle
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseC2.log
echo "=== C4 verify v2@0.005 more seeds $(date) ===" >> "$LOG"
nice -n 10 "$PY" optimize_v2.py --eps 0.005 --K_start 6 --K_end 6 --seeds 3 \
    --popsize 24 --maxiter 200 --n_theta 40 --workers 6 \
    --out results/v2_0005_more.json >> "$LOG" 2>&1
echo "=== C4a rc=$? $(date) ===" >> "$LOG"
echo "=== C4 smooth@0.005 higher budget Nf=Nb=10 $(date) ===" >> "$LOG"
nice -n 10 "$PY" smooth_run.py --eps 0.005 --K 32 --Nf 10 --Nb 10 \
    --seeds 2 --popsize 24 --maxiter 300 --workers 6 \
    --init-json results/smooth_0005_K32.json \
    --out results/smooth_0005_K32_v3.json >> "$LOG" 2>&1
echo "=== C4b rc=$? $(date) ===" >> "$LOG"
touch results/C4_DONE
