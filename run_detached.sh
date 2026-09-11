#!/usr/bin/env bash
# Fully detached runner for the remaining fat-Kakeya jobs.
# Launched with setsid+nohup so it survives pi-session restarts.
# Logs to results/detached_run.log; marker file when done.
set -u
cd "$(dirname "$0")"
PY=/home/z/.venv/bin/python3
LOG=results/detached_run.log
echo "=== detached runner start $(date) ===" >> "$LOG"

run_job() {
  local desc="$1"; shift
  echo "--- $desc $(date) ---" >> "$LOG"
  nice -n 10 "$PY" "$@" 2>&1 | grep -v Warning >> "$LOG"
  echo "--- $desc done rc=${PIPESTATUS[0]} $(date) ---" >> "$LOG"
}

run_job "K=14 eps=0.05" optimize_v2.py --eps 0.05 --K_start 14 --K_end 14 \
    --seeds 3 --popsize 24 --maxiter 150 --n_theta 40 --workers 6 \
    --out results/v2_005_K14_multiseed.json

run_job "eps=0.01 K=6" optimize_v2.py --eps 0.01 --K_start 6 --K_end 6 \
    --seeds 3 --popsize 28 --maxiter 200 --n_theta 40 --workers 6 \
    --out results/v2_001.json

run_job "K=6 eps=0.05 extra seeds 3-5" optimize_v2.py --eps 0.05 --K_start 6 --K_end 6 \
    --seeds 3 --popsize 24 --maxiter 150 --n_theta 40 --workers 6 \
    --out results/v2_005_K6_more.json

run_job "K=10 eps=0.05 extra seeds 3-5" optimize_v2.py --eps 0.05 --K_start 10 --K_end 10 \
    --seeds 3 --popsize 28 --maxiter 150 --n_theta 40 --workers 6 \
    --out results/v2_005_K10_more.json

echo "=== detached runner done $(date) ===" >> "$LOG"
touch results/DETACHED_DONE
