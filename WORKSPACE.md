# WORKSPACE.md — fat_kakeya_needle environment

## Runtime

- Python: `/home/z/.venv/bin/python3` (uv-managed venv). `pip` is absent;
  install with `uv pip install --python /home/z/.venv/bin/python3 <pkg>`.
- Packages: numpy, scipy, shapely, matplotlib (installed).
- Machine: 12 cores, 125 GB RAM. Shared with the owner's ML training
  jobs — long optimizer runs use `--workers 6` (not -1) and `nice -n 10`.

## Long-running jobs

`bg_run` children die when the pi session restarts (observed 3×, silent,
no exit code). Hour-long jobs must run detached:

```bash
setsid nohup ./run_detached.sh >/dev/null 2>&1 &
```

Progress: `tail results/detached_run.log`; completion marker
`results/DETACHED_DONE`. Never use bare `sleep` to wait — check the log.

## Known pitfalls

- Multiprocessing objectives must be picklable: define objective classes
  at module level, register dynamically loaded modules in `sys.modules`.
- Multiprocessing cannot spawn from a heredoc/stdin script (`<stdin>`
  main module) — write a temp .py file for smoke tests.
- numpy scalar → int casts must be guarded (checker + dtype edge cases).
- The old `basics.md` conversation replaces C·ε with a claimed Θ(1/log(1/ε))
  law. The cited Kakeya-neighborhood estimates have not yet been checked
  to imply a continuous half-turn motion with matching upper bound; do not
  state this as a verified theorem for the project's motion problem.
- arXiv:math/0008098 is by Terence Tao, not Bourgain (metadata checked
  2026-09-28).

## Conventions

- Results JSON: `results/<model>_<eps-tag>[_<variant>].json`, one file
  per run batch; each record carries eps, K, seed, area, model, keyframes.
- Commits: agent identity `agent <agent@local>`, message = result
  summary (see git log for examples).
