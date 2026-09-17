# Methodology — hard-won optimizer lessons

Procedural lessons from this experiment; each one cost a failed run to
learn. Read before extending the optimization pipeline.

## Search landscape

- **Warm-starting underperforms fresh search.** Warm-started DE chains
  (continuation pass 1, growing-K) consistently locked into worse
  basins: pass-1 small-ε sat +5% above independent results; growing-K
  stuck at 0.56–0.59 while a fresh single-K run hit 0.46. Use fresh
  independent seeds and take the min; track basins post-hoc instead.
- **Seed variance dominates.** Identical configs (same K, popsize,
  maxiter) differ up to 46% across RNG streams; the good basin is hit
  in ~1 of 3–4 seeds. Any single-seed area-vs-parameter comparison is
  meaningless — measure min over ≥3 seeds, and prefer more seeds over
  more K or more iterations.
- **Blind DE degrades with dimension.** K=6 (12–14 params) beats K=10
  and K=14 at the same budget. More keyframes only help with
  structure-aware initialization — which was tested and failed: see
  the structure-seed finding in docs/findings.md. The landscape's good
  basin is not reachable by geometric intuition; only broad random
  search finds it.

## Model geometry

- **Bounded-motion myth:** the optimal construction family (Perron
  trees / Pál joins) is spatially bounded; travel distance is not the
  resource that buys small area — overlapping rotation stations are.
  A log-space reach parametrization is cheap insurance (v2 keeps it)
  but the winning motions stayed compact.
- **Mirror closure is valid and halves the search:** keyframes over
  θ ∈ [0, π/2] with pose(π/2) = mirror(pose(0)); swept set = S1 ∪
  mirror_x(S1). Matches the symmetry of every known construction.
- **Exact polygon union (shapely) over rasterization:** no raster
  window to cap the reach, no grid-convergence error tax on every
  evaluation, ~10 ms/eval at K=14. Rasterization (v1) is fine at
  bounded reach but silently biased near window edges.

## Process

- **bg_run children die on pi-session restart** (silent, 3× observed).
  Hour-long jobs: `setsid nohup … &` detached runner writing a log +
  done-marker; check the log, never sleep-poll.
- **Multiprocessing pitfalls:** objective classes at module level
  (picklable); dynamically imported modules registered in
  `sys.modules`; no spawn from heredoc/stdin scripts.
- **Validate the evaluator first:** the centered half-turn must give
  π/4 to <1% before trusting anything downstream (caught a mirrored
  Y-axis bug and a 12% raster bias this way).
- **评估器分辨率必须匹配 ε**：n_theta=40 的目标函数在 ε=0.005 时
  漏扫 21%——DE 优化的不是真实面积。所有跨 ε 比较必须用同
  高分辨率复评（area_hi 必须落盘！growing 路径曾漏掉）。这是
  本项目最贵的教训：它制造了"A_eff 峰值回落"的假发现。
- **Forensics before rewrites:** when a construction underperforms,
  dump per-segment swept areas before blaming the idea (caught mirror-
  closure violations, chain drift, and the endpoint-pivot sector cost
  this way; each produced a different fix or conclusion).
- **Pivot+slide evaluator checks:** a center-pivot 180° motion must
  reproduce π/4; an arc evaluator must include both opposite arms of
  the rectangle; a continuous along-axis slide must be represented by
  the exact enlarged rectangle, not only its endpoint poses. These
  checks caught a factor-of-two sector bug and slide undercoverage.
