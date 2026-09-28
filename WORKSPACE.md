# WORKSPACE.md — fat_kakeya_needle environment

## Runtime

- Python: `/home/z/.venv/bin/python3` (uv-managed venv). `pip` is absent;
  install with `uv pip install --python /home/z/.venv/bin/python3 <pkg>`.
- Packages: numpy, scipy, shapely, matplotlib; optional numeric integer-geometry
  backend `pyclipper==1.4.0` (installed 2026-09-28 with uv). The PyPI sdist
  SHA-256 `9882bd889f27da78add4dd6f881d25697efc740bf840274e749988d25496c8e1`
  contains an MIT wrapper license and bundled Clipper 6.4.2 under Boost 1.0;
  CPython 3.12 manylinux x86_64 wheel SHA-256
  `d1f807e2b4760a8e5c6d6b4e8c1d71ef52b7fe1946ff088f4fa41e16a881a5ca`;
  installed extension bytes match that wheel (verified 2026-09-28). Reinstall:
  `uv pip install --python /home/z/.venv/bin/python3 pyclipper==1.4.0`. Integer
  clipping after floating-point pose quantization remains numerical, not a
  mathematical certificate.
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
- For unrestricted continuous 180-degree motion (temporary angle reversals
  and distant excursions allowed), f(eps)=Theta(1/log(1/eps)) is verified:
  Keich 1999 Lemma 1 provides one compact all-direction Kakeya set with a
  uniform neighborhood upper bound; docs/continuous-motion-bridge.md proves
  low-area continuous connectors and the direction-tube overlap lower bound.
  This does not certify the project's restricted numerical family, a sharp
  constant, or a practical finite-precision optimizer. Keich's finite
  triangle stages plus connectors do give a theoretical finite recursion;
  see docs/keich-explicit-motion.md.
- arXiv:math/0008098 is by Terence Tao, not Bourgain (metadata checked
  2026-09-28).

## Conventions

- Results JSON: `results/<model>_<eps-tag>[_<variant>].json`, one file
  per run batch; each record carries eps, K, seed, area, model, keyframes.
- Commits: agent identity `agent <agent@local>`, message = result
  summary (see git log for examples).
