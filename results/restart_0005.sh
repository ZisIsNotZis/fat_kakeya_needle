#!/usr/bin/env bash
set -u
cd /home/z/vibe/fat_kakeya_needle
PY=/home/z/.venv/bin/python3
LOG=results/night_phaseC2.log
echo "=== restart 0005 $(date) ===" >> "$LOG"
nice -n 10 "$PY" smooth_run.py --eps 0.005 --K 32 --Nf 8 --Nb 8 \
    --seeds 2 --popsize 20 --maxiter 200 --workers 3 \
    --init-json results/smooth_0005_K32.json \
    --out results/smooth_0005_K32_more.json >> "$LOG" 2>&1
echo "=== restart 0005 rc=$? $(date) ===" >> "$LOG"
touch results/RESTART_0005_DONE
