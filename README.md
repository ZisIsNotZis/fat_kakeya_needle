# fat_kakeya_needle

Numerical exploration of the fat Kakeya needle problem: find the minimal
area swept by a 1×ε rectangle rotating 180° under fully free planar
motion, as a function of ε ∈ (0, 1].

## Status

- `f̂(ε)` sampled at 30+ points on ε ∈ [0.01, 0.8] via differential
  evolution over keyframe motions (exact polygon-union swept area).
- Measured decay on [0.035, 0.8]: power law ε^0.32; the theoretical
  asymptotic A/(log(1/ε)+B) (Bourgain–Córdoba lower bound, Keich 1999
  matching upper bound) has not visibly set in by ε = 0.01 — the
  effective constant f̂·ln(1/ε) still rises (1.38 → 1.58).
- Key numbers: f̂(0.8) ≈ 1.25 (> π/4: sliding hurts fat needles),
  f̂(0.05) ≈ 0.461, f̂(0.01) ≈ 0.344. Open: the multiplicative
  constant of the 1/log law — the central open question of the problem.

## Quickstart

```bash
# environment (uv-managed venv with numpy/scipy/shapely/matplotlib)
uv pip install --python /home/z/.venv/bin/python3 shapely scipy numpy matplotlib

# single optimization run (K = keyframes, log-space motion model)
/home/z/.venv/bin/python3 optimize_v2.py --eps 0.05 --K_start 6 --K_end 6 \
    --seeds 3 --popsize 24 --maxiter 150 --workers 6 \
    --out results/v2_005.json

# long jobs: detached so they survive agent-session restarts
setsid nohup ./run_detached.sh >/dev/null 2>&1 &

# analysis + plot
/home/z/.venv/bin/python3 analyze.py
```

## Layout

- `sweeper.py` / `optimize.py` — v1: raster-window model (bounded reach)
- `sweeper_v2.py` / `optimize_v2.py` — v2: exact polygon union,
  log-space translations, uniform-θ keyframes
- `continuation.py` — warm-started fine-grid pass (kept for reference;
  warm-starting underperforms fresh search here, see docs/methodology.md)
- `results/` — JSON results per run, `area_vs_eps.png` plot
- `basics.md` — user-supplied background (verbatim source, docs/sources role)
- `docs/` — findings and methodology (start there)
