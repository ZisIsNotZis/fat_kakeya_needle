# Findings — fat Kakeya needle, free 2D motion

One-line problem: minimize the area of the set swept by a 1×ε rectangle
turning 180° with unrestricted planar motion (translation + rotation).

（本文件部分小节为英文历史记录；最终结论见下方中文"主结论"节。）

## Theoretical ground truth (SOTA, from literature)

- Thin needle (ε→0), unconstrained region: infimum area = 0
  (Besicovitch 1928; regions can be arbitrarily small).
- 历史文献记录称细针方向覆盖集合的 δ-邻域具有约 1/log(1/δ) 的上下阶；此处引用尚未核对原文，也尚未证明小面积方向覆盖集合中的线段能以同阶扫掠面积连接成连续半圈运动。因此暂不把自由运动问题的 Θ(1/log(1/ε)) 当作已核验定理。
- 即使针对方向覆盖集合的对数阶成立，其最佳常数也未由现有实验确定；本项目的数值拟合只探索有限范围的候选系数。
- Perron 树、Pál 接合是候选几何灵感；它们是否给出本项目所需、同阶面积的连续运动及具体 K 标度仍需证明。
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

## 主结论（2026-09-19 crossover 拟合后定稿）

1. **有限数据可被修正 log 律拟合**：两参数 log 律
   **f(ε) ≈ 2.27/(ln(1/ε)+1.60)**
   全域（0.002–0.8，37 点）拟合残差与 4 参数混合模型同水平，
   除 ε=0.002（+16%）外全部偏差 <±6.5%；幂律修正项在混合模型中
   系数趋于 0（被弃用）。
2. **有限区间拟合参数：A ≈ 2.27，并非已确认的渐近常数**。早期估计 1.56（无修正项拟合）与 2.1（低分辨率数据推论）均不可靠；固定 K 的枢转族有正面积下限，不能据此外推 ε→0。
3. **A_eff 形状尚不能支持渐近断言**：令 L=ln(1/ε)，拟合式 A_eff=A·L/(L+B) 对 L 单调上升但二阶导数 -2AB/(L+B)^3<0，即上升减速；若实测确实上升加速，则与该形状诊断冲突，须检验取点、优化和评估分辨率。
4. **未决**：ε=0.002 点报告 +16% 偏离，但仅有两个 fresh seeds，且采样分辨率低于 ε=0.005；尚不能排除评估/搜索差异。先统一复评和增加种子，再考虑更小 ε。

## 全局最优序列（各族最优，2026-09-19 修订）

| ε | f̂ | 族/模型 |
|---|---|---|
| 0.8 | 1.2516 | pivot+slide |
| 0.1 | 0.5897 | v1 keyframe |
| 0.05 | 0.4720 | pivot+slide K=16 |
| 0.02 | 0.3952 | smooth K=32 |
| 0.01 | 0.3654 | smooth K=32 (n_arc=80) |
| 0.005 | 0.3494 | smooth K=32 (n_arc=80) |
| 0.002 | **0.3378（暂定）** | smooth K=32 (n_arc=60；仅 2 seeds，未满足项目 ≥3 seeds 规则) |

0.3424 smooth vs 0.3519 v2 @0.005 的约 3% 族间差距尚未从两份结果记录核实同一评估分辨率；不得作为已确证的同分辨率缺口。维数诅咒仍真实
（free-β K=6 vs K=16 同分辨率对比）。

## 早期历史数值结果（低分辨率记录，不应与上表直接混用）

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

## 2026-09-28 证据审查：构造与证书边界

- **解析反例（针对固定 K 枢转族，而非一般运动）**：`pivot_slide.py` 每段转角 Δ=π/(2K)，针臂长度 (1±f_i)/2 扫过两个扇形，仅此一段零宽针的面积就是 Δ(1+f_i²)/4≥π/(8K)。实际宽针包含零宽针，故固定 K 的真实扫掠面积不能随 ε→0 趋于零；K 至少需要随 log(1/ε) 增长，且这只是必要条件，不保证上界。`smooth_pivot.py` 固定 K 的有限 ε 拟合不能充当渐近递推公式。
- **证书尚非严格定理**：`make_certificates.py` 的 pivot 姿态使用端点中心直线插值，而实际模型是枢轴圆弧加段间滑移；`strict_bound.py` 的端点位移速度界仅适用线性段，Shapely 浮点 buffer 与并集面积也未向外舍入。`results/certificates.json` 只可视为未验证的数值候选，不能引用 `certified_upper` 作为数学上界；其中 v2 的 `claimed` 旧低分辨率值小于同文件的 `lower`，尤须停用。
- **待做**：构造包含完整 Arc/Slide 的连续运动证书及保守外包；先作中心旋转解析回归与跨分辨率复评，再谈预算比较及新递推。文献中的连续运动同阶上界须核对原始证明。

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
