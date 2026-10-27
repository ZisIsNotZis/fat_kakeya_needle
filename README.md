<p align="center"><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>

<div align="center">
  <img src="assets/logo.svg" alt="fat_kakeya_needle logo" width="112">
</div>

<h1 align="center">fat_kakeya_needle</h1>

<p align="center"><strong>Find smaller needle sweeps. Know what the compute bought. Keep proof separate from the number.</strong></p>

<p align="center">A numerical-and-proof study of a 1×ε rectangle turning 180° under free planar motion.</p>

As ε→0, a needle can turn around in an arbitrarily small area. The hard questions are how fast the area decays, which finite-ε motions get closest, and what can actually be certified. This repository treats those as separate products: candidate motions, measured compute-to-quality scaling, and exact rational upper bounds for selected motions.

## At a glance

- **Best floating candidate at ε = 0.002:** `0.310335–0.310376` for a K=256 smooth pivot+slide motion (`n_sub=160`). This is a numerical candidate, **not** a certificate or a proven minimum.
- **Certified upper bounds for specified continuous motions:** ε = .05 → `4489/8192 ≈ 0.547974`; ε = .002 → `673359/2097152 ≈ 0.321083`; ε = .005 grid winner → `3203055/8388608 ≈ 0.381834`.
- **Theory:** for unrestricted continuous motion, `f(ε) = Θ(1/log(1/ε))`. Fixed-K pivot families have a positive-area obstruction: every uniform pivot segment sweeps at least `π/(8K)`.
- **Compute scaling:** `q(B) = q∞ + c/B`; the smooth family gives `q∞ = 0.3442` (R² = 0.975), within 0.04% of the archived best `0.344088`.
- **Status:** v1.0 research milestone reached; maintained for reproducibility and extension.

![Best-known swept area versus ε, and the log-law diagnostic](area_vs_eps.png)

*Early 37-point diagnostic: the theoretical log-law plateau does not appear in the computable range. The current 8-point, 84-cell sweep is documented in [docs/eps-sweep-condition1.md](docs/eps-sweep-condition1.md).*

## Quick start

Python 3.12. The proof path is standard-library only, so the first result needs no install:

```bash
# 1. Clone, then recompute an exact rational upper bound (stdlib only)
git clone https://github.com/ZisIsNotZis/fat_kakeya_needle.git
cd fat_kakeya_needle
python3 rational_pivot_certificate.py results/coarse_refine_0002_K256.json \
  --seed 0 --q 2048 \
  --verify results/rational_pivot_0002_K256_seed0_q2048.json
```

```bash
# 2. For the optimizers and enclosures, install the numerical stack
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install numpy scipy shapely matplotlib
python3 -m pip install pyclipper==1.4.0   # optional integer-polygon backend
```

The recorded environment uses Python 3.12 with `numpy`, `scipy`, `shapely`, `matplotlib`, and the optional `pyclipper==1.4.0`; see [`WORKSPACE.md`](WORKSPACE.md) for exact versions, hashes, and pitfalls.

```bash
# 3. Run the core regression set
python3 -m unittest -v test_pivot_enclosure test_v2_numerical_enclosure \
  test_rational_pivot_certificate test_keich_motion
```

## What it can do now

| Capability | What the repository provides | Start here |
| --- | --- | --- |
| Model continuous motions | Keyframe, pivot+slide, smooth-profile, and hierarchical families; explicit Keich theory recurrence | [`sweeper_v2.py`](sweeper_v2.py), [`pivot_slide.py`](pivot_slide.py), [`smooth_pivot.py`](smooth_pivot.py), [`hierarchical_pivot.py`](hierarchical_pivot.py), [`keich_motion.py`](keich_motion.py) |
| Score a motion | Floating Shapely enclosures, an integer-polygon backend, and continuous-motion adapters | [`strict_bound.py`](strict_bound.py), [`v2_numerical_enclosure.py`](v2_numerical_enclosure.py), [`integer_motion_area.py`](integer_motion_area.py), [`motion_adapters.py`](motion_adapters.py) |
| Prove an upper bound | Exact rational outer grid cover for a specified pivot+slide JSON motion, with source hashing and independent `--verify` recomputation | [`rational_pivot_certificate.py`](rational_pivot_certificate.py), [certificate notes](docs/rational-pivot-certificate.md) |
| Search under a budget | Differential evolution plus local polish, cold starts, total-process-CPU accounting, and grid aggregation that refuses incomplete cells | [`budget_total_integer.py`](budget_total_integer.py), [`aggregate_total_budget.py`](aggregate_total_budget.py), [`run_budget_total_grid.sh`](run_budget_total_grid.sh) |
| Keep evidence honest | Archived results, negative results, known evaluator pitfalls, and a three-tier evidence convention | [`results/`](results), [`docs/findings.md`](docs/findings.md), [`docs/methodology.md`](docs/methodology.md) |

## Evidence, in three layers

The repository deliberately keeps these apart:

1. **Strict theorem.** The `Θ(1/log(1/ε))` order for free continuous motion, fixed-K positive-area obstructions, and exact rational upper bounds for named motions. See [`docs/continuous-motion-bridge.md`](docs/continuous-motion-bridge.md) and [`docs/rational-pivot-certificate.md`](docs/rational-pivot-certificate.md).
2. **Numerical enclosure.** Continuous-motion envelopes computed with floating geometry or integer clipping. These are useful bounds on what a stored motion sweeps, but they are not outward-rounded proofs.
3. **Sampled estimate.** The optimizer's objective value. It can undercount if the angular resolution is too coarse, so it must never be quoted as a certified area.

A number without its layer is not a result.

## Architecture

The code follows a small pipeline:

```text
motion family  →  continuous-pose adapter  →  area evaluator  →  search / budget runner  →  archived evidence
```

| Layer | Responsibility | Main files |
| --- | --- | --- |
| Motion models | Define the first half-turn and close it by mirror reflection or an explicit theoretical connector | `sweeper_v2.py`, `pivot_slide.py`, `smooth_pivot.py`, `hierarchical_pivot.py`, `keich_motion.py`, `seed_lib.py` |
| Evaluation | Turn a motion into a swept set: sampled lower area, floating envelope, or integer-polygon outer area | `strict_bound.py`, `v2_numerical_enclosure.py`, `integer_motion_area.py`, `motion_adapters.py` |
| Certification | Rebuild a selected motion in exact rational arithmetic and count a closed grid cover | `rational_pivot_certificate.py` |
| Search and benchmarking | Differential evolution, local continuation, cold-start budget cells, cross-family quality gates | `optimize*.py`, `smooth_run.py`, `refine_*.py`, `budget_*.py`, `compare_integer_candidates.py`, `aggregate_*.py` |
| Diagnostics | Probes for specific hypotheses, plots, and refinement summaries | `probe_*.py`, `analyze*.py`, `reevaluate_*.py` |

`docs/` holds the project's memory: the goal, findings, methods, and accepted evidence boundaries. `results/` holds the raw JSON evidence and is intentionally kept, including negative and superseded results.

## How to develop

- **Environment:** install as in [Quick start](#quick-start); [`WORKSPACE.md`](WORKSPACE.md) holds the recorded machine, package hashes, and known pitfalls.
- **Before trusting an evaluator:** a centered half-turn must reproduce `π/4`. Every new family should pass that smoke test first.
- **Before comparing methods:** fix the evaluation resolution, use at least three fresh seeds, report the hit rate, and charge the full CPU budget. A family gap above 3% is treated as a non-convergence signal, not a win.
- **Before publishing a number:** say whether it is a sampled estimate, a numerical enclosure, or a strict bound. New numerical claims must carry enough metadata to be reproduced.
- **Tests:** there is no hosted CI. Run the regression set locally with the command above; the optional integer tests are `test_integer_motion_area`, `test_motion_adapters`, and `test_compare_integer_candidates`.
- **Docs:** read [`docs/methodology.md`](docs/methodology.md) before extending the optimizer, and record new evidence in its proper home under [`docs/`](docs).

## How to contribute

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first. In short: open an issue before adding a new motion family, keep claims inside their evidence tier, and include the seeds, resolution, CPU budget, and validation result with every new number.

## Roadmap

### Implemented

- [x] Four continuous motion families: v2 keyframes, free pivot+slide, smooth profiles, hierarchical slides
- [x] Floating numerical enclosures for pivot, smooth, and repaired-v2 motions
- [x] Integer-polygon evaluator and four-fold angular-step / integer-scale quality gate
- [x] Total-CPU protocol A runner, 48-cell budget grid, and 84-cell ε sweep
- [x] Exact rational certificates for three specified continuous motions
- [x] Strict `Θ(1/log(1/ε))` order and fixed-K / fixed-profile positive-area obstructions
- [x] Documented negative results: structured seeding, Keich-transition insertion, and blind K growth

### Planned

- [ ] Fresh-seed farms at ε ∈ {0.01, 0.05} for stable best-basin estimates
- [ ] Tighter rational certificates for the current best candidates
- [ ] A faithful mapping proof, or a clear impossibility result, for the restricted pivot+slide family
- [ ] A sharper asymptotic constant `A`, if the data ever enters the asymptotic regime
- [ ] Extension below ε = 0.005, where the compute cost grows superlinearly

## Future vision

Turn this archive into a reusable benchmark for Kakeya-type motion search: a place where a new construction can be scored on the same terms, a new optimizer can be compared under a frozen compute budget, and a headline number can be upgraded from estimate to certificate without rewriting the story. The long-term target is not a single best area, but a pipeline that makes each improvement reproducible, attributable, and honest about what it proves.

## License

AGPL-3.0-only. See [`LICENSE`](LICENSE).
