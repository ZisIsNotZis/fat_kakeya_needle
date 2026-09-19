# Findings — fat Kakeya needle, free 2D motion

One-line problem: minimize the area of the set swept by a 1×ε rectangle
turning 180° with unrestricted planar motion (translation + rotation).

## Theoretical ground truth (SOTA, from literature)

- Thin needle (ε→0), unconstrained region: infimum area = 0
  (Besicovitch 1928; regions can be arbitrarily small).
- Fat needle 1×ε: minimum swept area is Θ(1/log(1/ε)).
  Lower bound: Bourgain/Córdoba (δ-neighborhood of any Besicovitch set
  has area ≳ 1/log(1/δ)). Matching upper bound: Keich 1999 (Perron-tree
  constructions; no Besicovitch set of n triangles beats ~1/log n).
- The multiplicative constant in front of 1/log(1/ε) is **open** — this
  is what the numerical experiment probes.
- Optimal constructions (Perron trees, Pál joins) live inside a bounded
  region (~unit disk): they use MANY overlapping rotation stations
  (K ~ log(1/ε)), NOT travel to infinity. Moving far away adds area.
- Fixed-center rotation reference: π/4 ≈ 0.785 (disk of radius ½).
- Scaling: f(ε) = ε²·f(1/ε) for ε > 1 (similarity argument, exact) —
  so ε ∈ (0,1] covers the whole problem.

## Numerical setup (what we optimize)

Motion = keyframes (θᵢ, xᵢ, yᵢ), θ monotone 0→π/2, second half of the
turn = x-mirror of the first (mirror closure, exact). Between keyframes
poses interpolate linearly. Swept set = exact union of oriented-box
polygons (shapely), area computed exactly at any distance. v2
(`sweeper_v2.py`) parametrizes translations in signed log space
(center = σ(e^z − 1), σ = max(1, 8ε)) so exponential reach costs
O(log) parameters. Search: differential evolution + Nelder-Mead polish.

## 主结论（2026-09-19 高分辨率重跑后定稿）

研究过程经历两次反转（09-17 早"峰值回落"→ 09-17 晚"反转上升"→
09-19 高分辨率验证），最终图景以 smooth 族高分辨率序列为准：

1. **高分辨率（n_arc 80–160）下 A_eff 单调上升且加速度在增大**：
   1.414 (0.05) → 1.546 (0.02) → 1.683 (0.01) → 1.851 (0.005) →
   2.100 (0.002)。每倍半程增量 +0.13→+0.14→+0.17→+0.25。
   **log 律平台在 ε≥0.002 内未出现**。

2. **数据质量**：smooth 族高低分辨率一致（无采样低估）；v2 关键帧
   族 n_theta=40 假值已剔除（0.2917 实为 0.3519，低估 21%）。当前
   小-ε 数据可信。

3. **两种未决解释**：(a) 可测范围内真实曲线为幂律 f≈1.16·ε^0.28，
   log 律是更远渐近行为；(b) 现有运动族的共同表达边界限制面积下降。
   smooth 族高低分辨率一致已排除采样因素，指向族表达能力
   （或真实曲线形态）。区分两者需要 ε=0.001+ 与高分辨率评估。

4. **实验常数下界**：若 log 律最终成立，A > 2.1（比早期估计 1.56
   大得多——早期值是低分辨率 artifact）。

5. **历史教训**：早期 0.2917 "突破" 与 1.56 常数估计均为低分辨率
   artifact；n_theta=40 目标函数在 ε=0.005 漏扫 21%。

## 全局最优序列（各族最优，2026-09-19 修订）

| ε | f̂ | 族/模型 |
|---|---|---|
| 0.8 | 1.2516 | pivot+slide |
| 0.1 | 0.5897 | v1 keyframe |
| 0.05 | 0.4720 | pivot+slide K=16 |
| 0.02 | 0.3952 | smooth K=32 |
| 0.01 | 0.3654 | smooth K=32 (n_arc=80) |
| 0.005 | 0.3494 | smooth K=32 (n_arc=80) |
| 0.002 | **0.3378** | smooth K=32 (n_arc=60) |

族间真实缺口（同 ε 高分辨率对比）：~3%（0.3424 smooth vs 0.3519 v2
@0.005）——早期 15% 缺口大部分是低分辨率 artifact。维数诅咒仍真实
（free-β K=6 vs K=16 同分辨率对比）。

## 数值结果（best-known f̂(ε)，min over seeds/families）

| ε | f̂ | note |
|---|---|---|
| 0.8 | 1.252 | > π/4: sliding hurts fat needles (crossover ~ε=0.25) |
| 0.5 | 0.957 | |
| 0.3 | 0.828 | |
| 0.2 | 0.742 | |
| 0.1 | 0.590 | |
| 0.05 | 0.461 | best over 4 seeds; seed spread 0.46–0.67 |
| 0.035 | 0.438 | continuation pass 2 |
| 0.01 | 0.344 | best of 3 seeds; spread 0.34–0.42 |

- On [0.035, 0.8] the sampled curve fits power law ε^0.32 far better
  than A/(log(1/ε)+B). The log asymptotic has NOT set in by ε = 0.01:
  f̂·ln(1/ε) = 1.38 (ε=0.05) → 1.47 (ε=0.035) → 1.58 (ε=0.01), still
  rising. Both the pre-asymptotic regime and optimizer under-
  convergence are live explanations (see methodology).
- Sampled f̂ is smooth/monotone in ε (continuity hypothesis confirmed
  at ~5% level); 3 sampling strategies (independent sweep, warm
  continuation, batch-min) agree within noise on [0.08, 0.8].
- Seed variance is the dominant error source at small ε: identical
  configs differ up to 46% across RNG streams; good basins are found
  in ~1 of 3–4 seeds. Estimator must be min-over-seeds.
- K (keyframe count) study at ε=0.05: min-area K=6 (0.461) < K=10
  (0.583) < K=14 (0.608) — blind DE degrades with more parameters;
  extra stations only help with structure-aware initialization.
- Structure-seeded DE (Pál-join/Perron pivot-chain seeds, `seed_lib.py`):
  **negative result.** Geometric analysis shows endpoint-pivot fans
  sweep quarter-sectors (~0.15–0.33/segment) and inter-pivot slides add
  ε per line change — the fan gets WORSE with K (0.74 @K=4 → 1.58
  @K=16), opposite to the intended 1/log behavior; all parameterized
  pivot-profile seeds collapse to the fixed-center disk (≈0.784).
  Controlled A/B (same budget, same RNG): seeded-init DE 0.463 vs
  random-init 0.461 — a tie. Conclusion: the good basin DE finds is
  NOT the classical pivot-chain family; the uniform-θ keyframe model
  with interpolated poses cannot faithfully express Perron-tree
  triangle-overlap packing. A faithful test of the construction family
  needs a pivot+slide segment representation (open).

## Open questions

1. Does f̂·ln(1/ε) flatten (log law, constant A) below ε = 0.01, or
   does the measured curve keep its power-law character? Needs both
   smaller ε and better search at fixed ε.
2. ~~Structure-seeded initialization~~ — tested, negative result (see
   findings above). The successor question: does a **pivot+slide
   segment representation** (each keyframe interval = rotate about a
   chosen cross-section point, then slide along the needle), which can
   faithfully express Perron-tree packing, find areas the keyframe-
   interpolation model cannot?
3. Sharp A for the true optimum: theory gives no candidate value.
4. Seed-farm: min over N≥10 seeds at ε ∈ {0.01, 0.05} for a stable
   estimate of the good-basin value and its hit rate.
5. Pivot+slide representation (`pivot_slide.py`): first valid model,
   with each angle interval an exact pivot arc and each boundary an
   along-needle slide. At ε=0.05, preliminary DE gives 0.4925 (K=6)
   and 0.4880 (K=8), close to but above the v2 keyframe best 0.461.
   This is a physically interpretable family; the initial sector-only
   implementation was rejected because it undercounted the two arms of
   the needle and omitted continuous slide area. The corrected model
   passes the fixed-center π/4 smoke test within 0.2%.

## References

- Bourgain, "From rotating needles to stability of waves…"
  (arXiv:math/0008098) — δ-neighborhood lower bound discussion.
- Keich 1999, "On Lp bounds for Kakeya maximal functions and the
  Minkowski dimension" — matching 1/log upper bound construction.
- Tao's Kakeya survey notes (teorth.github.io/tao-web/apps/kakeya.html)
  and arXiv:2608.22209 — problem landscape, fat-needle framing.
- Local verbatim source: `basics.md` (research transcript incl.
  corrections; superseded claims there are annotated in WORKSPACE.md).
