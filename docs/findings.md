# Findings — fat Kakeya needle, free 2D motion

One-line problem: minimize the area of the set swept by a 1×ε rectangle
turning 180° with unrestricted planar motion (translation + rotation).

（本文件部分小节为英文历史记录；最终结论见下方中文"主结论"节。）

## Theoretical ground truth (SOTA, from literature)

- Thin needle (ε→0), unconstrained region: infimum area = 0
  (Besicovitch 1928; regions can be arbitrarily small).
- Tao 的综述（arXiv:math/0008098，第 4 页）确认二维 Besicovitch 集的 δ-邻域面积下界 C/log(1/δ) 且 Keich 证明该**集合邻域**界尖锐；同文第 1–2 页确认零宽针可用任意小面积连续转向和平移。但这些陈述没有直接给出带厚度针在连续半圈运动下的同阶上界，连接步骤仍待查证；因此暂不把本项目 f(ε)=Θ(1/log(1/ε)) 当作已核验定理。
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
| 0.005 | 0.34265（浮点复评采样值） | smooth K=32, Nf=Nb=10；历史源文件无 n_arc 元数据，统一 n_sub=160 复评 |
| 0.002 | **0.3378（暂定）** | smooth K=32 (n_arc=60；仅 2 seeds，未满足项目 ≥3 seeds 规则) |

0.3424 smooth vs 0.3519 v2 @0.005 的约 3% 族间差距尚未从两份结果记录核实同一评估分辨率；不得作为已确证的同分辨率缺口。2026-09-28 在修复网格叠加后用 `reevaluate_smooth.py` 对 `smooth_0005_K32_v3.json` 统一 n_sub=160 重算，数值 lower=0.342648889、upper=0.342962359，仍优于同 ε 的 smooth_hr 最好参数数值 lower=0.349733275、upper=0.350052995；这是候选构造差异，不是同核时搜索比较，也非严格上下界。维数诅咒仍真实
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
- **2026-09-28 首次复评**：新增完整 Arc/Slide 数值包络（`results/pivot_numerical_enclosures.json`），中心旋转解析回归通过；但 Shapely 并集仍不具严格向外舍入。对 `smooth_hr_0005_K32.json` 最好参数，n_sub=40/80/160/320 的半圈加镜像采样面积分别为 0.3497321 / 0.3493582 / 0.3497333 / 0.3497335，出现本应不可能的 40→80 面积下降。各角度的 40 格点精确包含于 80 格点（浮点角差为零）、输入矩形均有效，但 GEOS 并集差集 40 格点并集减去 80 格点并集的面积约 0.0001873；这是布尔几何数值不稳定的实测反例，不能把细小 `upper-lower` 差值当作绝对误差保证。对应 ε=0.002 最好参数在 n_sub=320 时 sampled=0.3378498、numerical upper=0.3380324；仍仅两个 fresh seeds。
- **局部修复与边界**：在枢转评估器及数值包络的多边形叠加前按 `min(1e-10, ε·1e-8)` 固定精度网格贴合。同一 ε=0.005 解重跑 n_arc=40/80 得 0.3497321291/0.3497328727，不再出现上述非单调；新增回归测试。网格贴合会改变几何边界，既不保证所有实例单调，也不提供严格上界；已提交的历史优化结果未被悄悄改写，比较前须统一版本重评。下一步构造可审计的向外舍入/外包，并核查文献中的连续运动同阶上界。

## 2026-09-28 核时预算试点（失败诊断，不作方法排名）

`results/budget_pilot_0005_K32.json` 记录 ε=0.005、K=32、单核 DE、n_arc=80、两个族×{15,30} 进程 CPU 秒×3 fresh seeds，再用 n_sub=160 复评。层次族两档的最好浮点数值 upper 分别为 0.83423/0.82170；光滑族两档均为 1.07879。这些数字**不能说明层次族优于光滑族**：层次族 DE 初始种群 35 次评估，光滑族 65 次；12 个试验中只有 2 个超过初始种群，光滑族全部尚未完成初始化，且全都远差于存档光滑候选的约 0.343。试点仅测出每次评估的真实成本及预算下限。下一轮至少应保证两个族都完成初始种群并进入多代搜索，再谈有限预算质量；不得用这两个点外推无限算力。

## 2026-09-28 扩展预算试点（冷启动，两族均已进入搜索）

`results/budget_pilot_0005_K32_extended.json` 在相同机器、单核、n_arc=80 的 ε=0.005/K=32 试验中，层次族 DE 种群 35、光滑族 65，{60,120} 进程 CPU 秒×各 3 fresh seeds。所有 12 次完成初始种群并进入搜索。每格的最优浮点数值 upper：层次族 0.82170→0.71004，光滑族 0.97042→0.92379；实际每 seed 使用核时与目标函数调用次数均在 JSON。**这仅是该具体冷启动 DE 配置、预算和种子集合下的有限比较**，两族均远劣于此前投入大量未知历史算力发现的光滑族存档解 upper≈0.34296。历史解发现成本不可忽略，也不能把其作为免费初始条件后与冷启动公平比较；单凭两个预算点和 3 seeds 不能估计无限算力极限、稳定标度律或全体已知方法的胜者。下一步分开报告冷启动成本与利用已知 incumbent 的续搜成本。

## 2026-09-28 已知解续搜（发现成本不计入，不能与冷启动横比）

`results/incumbent_refine_0005.json` 对 ε=0.005 的历史最好光滑解进行 Nelder–Mead 局部续搜，预算 {60,120} 进程 CPU 秒×3 seeds；seed 0 从原参数开始，其余从小扰动开始。原参数在新目标函数 n_arc=80 的浮点采样面积 0.342648493；60 秒最好 0.342634753，120 秒最好 0.342612063，其余 2 seeds 没有改进。n_sub=320 数值区间从原参数 [0.342649080,0.342805710] 变为最好参数 [0.342612645,0.342770060]；n_sub=1024 分别为 [0.342649215,0.342698140] 与 [0.342612781,0.342661951]，区间仍略有重叠。再用 `compare_incumbent.py` 以 n_sub=2048 复评，原解 [0.342649247,0.342673707]、续搜解 [0.342612813,0.342637395]，浮点数值区间分离约 0.000011852（`results/incumbent_compare_n2048.json`）。这提供**同一数值几何实现下的较强经验改进证据**，但 GEOS 并集及精度网格均未向外舍入，不能据此证明真实扫掠面积严格下降；也没有稳定 budget→quality 标度。历史解发现成本未知，不能把本次续搜成本解释为从零找到该面积的总预算。

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

- Tao, "From rotating needles to stability of waves; emerging connections between combinatorics, analysis and PDE" (arXiv:math/0008098), PDF 第 1–4 页：明确提及零宽针可用任意小面积连续旋转、针可用任意小面积平移，并称平面 Besicovitch 集的 δ-邻域至少 C/log(1/δ)、Keich 证明该**邻域界**尖锐。PDF 没有在所引段落证明带厚度针的连续运动达到同阶；旧记录误署 Bourgain。
- Keich 1999, "On Lp Bounds for Kakeya Maximal Functions and the Minkowski Dimension in R²", DOI:10.1112/S0024609398005372（2026-09-28 经 Crossref 作者/标题/日期核对）；Tao 综述称其证明 Besicovitch 集 δ-邻域对数界尖锐。原文暂不可访问，尚不能把它直接当作本项目厚针连续运动的上界证明。
- Tao's Kakeya survey notes (teorth.github.io/tao-web/apps/kakeya.html)
  and arXiv:2608.22209 — problem landscape, fat-needle framing.
- Local verbatim source: `basics.md` (research transcript incl.
  corrections; superseded claims there are annotated in WORKSPACE.md).
