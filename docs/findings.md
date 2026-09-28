# Findings — fat Kakeya needle, free 2D motion

Budget: 200 lines / 18000 characters; exception retains historical numeric claims and their explicit supersession alongside current evidence until old result files are migrated into an archive.

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

## 存档与迁移后候选序列（非全局最优证明；2026-09-28 更新）

| ε | f̂ | 族/模型 |
|---|---|---|
| 0.8 | 1.2516 | pivot+slide |
| 0.1 | 0.5897 | v1 keyframe |
| 0.05 | 0.4720 | pivot+slide K=16 |
| 0.02 | 0.3952 | smooth K=32 |
| 0.01 | 0.3654 | smooth K=32 (n_arc=80) |
| 0.005 | **0.33928（暂定浮点复评采样值）** | ε=.005 源解从 K32 按 β·32/K 迁移到 smooth K64，n_sub=320；源解发现成本未知 |
| 0.002 | **0.31034（暂定浮点复评采样值）** | K256 73+73 控制，继承节点同层优化后 n_sub=160；源盆地复用 |
| 0.001 | **0.30637（暂定浮点复评采样值）** | ε=.002 的 K256/73+73 控制解直接迁移，不在本 ε 优化；n_sub=160 |

历史所称 0.3424 smooth vs 0.3519 v2 @0.005 的约 3% 族间差距未核实同一分辨率，不作为同预算胜负证据。2026-09-28 统一复评及分段数迁移刷新了上述候选；这些数值都是**同一浮点几何实现下的候选构造值**，未认证严格面积，也未满足每 ε 的 fresh seeds 估计量规则。维数诅咒仍真实
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
  triangle-overlap packing. A pivot+slide segment representation is one
  candidate test, but its restricted axial slides and fixed angle grid
  have not been proved expressive enough to reproduce Perron packing.

## 2026-09-28 证据审查：构造与证书边界

- **解析反例（针对固定 K 枢转族，而非一般运动）**：`pivot_slide.py` 每段转角 Δ=π/(2K)，针臂长度 (1±f_i)/2 扫过两个扇形，仅此一段零宽针的面积就是 Δ(1+f_i²)/4≥π/(8K)。实际宽针包含零宽针，故固定 K 的真实扫掠面积不能随 ε→0 趋于零；K 至少需要随 log(1/ε) 增长，且这只是必要条件，不保证上界。`smooth_pivot.py` 固定 K 的有限 ε 拟合不能充当渐近递推公式。
- **旧版证书尚非严格定理**：`make_certificates.py` 的 pivot 姿态使用端点中心直线插值，而实际模型是枢轴圆弧加段间滑移；`strict_bound.py` 的端点位移速度界仅适用线性段，Shapely 浮点 buffer 与并集面积也未向外舍入。`results/certificates.json` 只可视为未验证的数值候选，不能引用 `certified_upper` 作为数学上界；其中 v2 的 `claimed` 旧低分辨率值小于同文件的 `lower`，尤须停用。
- **2026-09-28 首次复评**：新增完整 Arc/Slide 数值包络（`results/pivot_numerical_enclosures.json`），中心旋转解析回归通过；但 Shapely 并集仍不具严格向外舍入。对 `smooth_hr_0005_K32.json` 最好参数，n_sub=40/80/160/320 的半圈加镜像采样面积分别为 0.3497321 / 0.3493582 / 0.3497333 / 0.3497335，出现本应不可能的 40→80 面积下降。各角度的 40 格点精确包含于 80 格点（浮点角差为零）、输入矩形均有效，但 GEOS 并集差集 40 格点并集减去 80 格点并集的面积约 0.0001873；这是布尔几何数值不稳定的实测反例，不能把细小 `upper-lower` 差值当作绝对误差保证。对应 ε=0.002 最好参数在 n_sub=320 时 sampled=0.3378498、numerical upper=0.3380324；仍仅两个 fresh seeds。
- **局部修复与边界**：在枢转评估器及数值包络的多边形叠加前按 `min(1e-10, ε·1e-8)` 固定精度网格贴合。同一 ε=0.005 解重跑 n_arc=40/80 得 0.3497321291/0.3497328727，不再出现上述非单调；新增回归测试。网格贴合会改变几何边界，既不保证所有实例单调，也不提供严格上界；已提交的历史优化结果未被悄悄改写，比较前须统一版本重评。下一步构造可审计的向外舍入/外包，并核查文献中的连续运动同阶上界。

## 2026-09-28 首个有理数面积上界（仅指定连续运动）

`rational_pivot_certificate.py` 对 JSON 十进制输入构造 Machin π/Taylor 三角有理区间，外舍入枢转全弧与完整滑移，闭网格精确计数，镜像接合形成连续半转。`docs/rational-pivot-certificate.md` 给出证明及重算命令；此处不复用 Shapely 数值包络。q=128 时 `results/rational_pivot_005_K16_seed1_q128.json` 得 ε=.05/K16 seed1 的 **严格构造上界** 8978/16384≈0.548；`results/rational_pivot_0002_K256_seed0_q128.json` 得 ε=.002/K256 seed0 的 **严格构造上界** 6114/16384≈0.373。对应历史浮点候选约 0.472 / 0.310 **仍不是严格上界**；两个有限实例不证明真最小值或渐近标度。两份证书均从 SHA-256 固定的源 JSON 重算验证；独立数学审查确认外包推导和整数闭格计数，代码审查入口漏洞修复后复核通过。证书仅证明指定的精确十进制有理参数运动，不能把浮点优化器内部运动、0.310335 数值估计或渐近律一并认证。对同一 ε=.002/K256 指定运动细化网格，q=256 时 N=22662、严格上界 11331/32768≈0.345795；q=512 时 N=87022、严格上界 43511/131072≈0.331963（`results/rational_pivot_0002_K256_seed0_q{256,512}.json`，均由源哈希相同的 `--verify` 重算）。细化缩小了与浮点候选的差距，但仍未认证约 0.310335。

## 2026-09-28 核时预算试点（失败诊断，不作方法排名）

`results/budget_pilot_0005_K32.json` 记录 ε=0.005、K=32、单核 DE、n_arc=80、两个族×{15,30} 进程 CPU 秒×3 fresh seeds，再用 n_sub=160 复评。层次族两档的最好浮点数值 upper 分别为 0.83423/0.82170；光滑族两档均为 1.07879。这些数字**不能说明层次族优于光滑族**：层次族 DE 初始种群 35 次评估，光滑族 65 次；12 个试验中只有 2 个超过初始种群，光滑族全部尚未完成初始化，且全都远差于存档光滑候选的约 0.343。试点仅测出每次评估的真实成本及预算下限。下一轮至少应保证两个族都完成初始种群并进入多代搜索，再谈有限预算质量；不得用这两个点外推无限算力。

## 2026-09-28 扩展预算试点（冷启动，两族均已进入搜索）

`results/budget_pilot_0005_K32_extended.json` 在相同机器、单核、n_arc=80 的 ε=0.005/K=32 试验中，层次族 DE 种群 35、光滑族 65，{60,120} 进程 CPU 秒×各 3 fresh seeds。所有 12 次完成初始种群并进入搜索。每格的最优浮点数值 upper：层次族 0.82170→0.71004，光滑族 0.97042→0.92379；实际每 seed 使用核时与目标函数调用次数均在 JSON。**这仅是该具体冷启动 DE 配置、预算和种子集合下的有限比较**，两族均远劣于此前投入大量未知历史算力发现的光滑族存档解 upper≈0.34296。历史解发现成本不可忽略，也不能把其作为免费初始条件后与冷启动公平比较；单凭两个预算点和 3 seeds 不能估计无限算力极限、稳定标度律或全体已知方法的胜者。下一步分开报告冷启动成本与利用已知 incumbent 的续搜成本。

## 2026-09-28 已知解续搜（发现成本不计入，不能与冷启动横比）

`results/incumbent_refine_0005.json` 对 ε=0.005 的历史最好光滑解进行 Nelder–Mead 局部续搜，预算 {60,120} 进程 CPU 秒×3 seeds；seed 0 从原参数开始，其余从小扰动开始。原参数在新目标函数 n_arc=80 的浮点采样面积 0.342648493；60 秒最好 0.342634753，120 秒最好 0.342612063，其余 2 seeds 没有改进。n_sub=320 数值区间从原参数 [0.342649080,0.342805710] 变为最好参数 [0.342612645,0.342770060]；n_sub=1024 分别为 [0.342649215,0.342698140] 与 [0.342612781,0.342661951]，区间仍略有重叠。再用 `compare_incumbent.py` 以 n_sub=2048 复评，原解 [0.342649247,0.342673707]、续搜解 [0.342612813,0.342637395]，浮点数值区间分离约 0.000011852（`results/incumbent_compare_n2048.json`）。这提供**同一数值几何实现下的较强经验改进证据**，但 GEOS 并集及精度网格均未向外舍入，不能据此证明真实扫掠面积严格下降；也没有稳定 budget→quality 标度。历史解发现成本未知，不能把本次续搜成本解释为从零找到该面积的总预算。

## 2026-09-28 固定剖面跨 ε 压力测试

对上节 ε=0.005 续搜的**同一套 K=32 参数**不再优化，只缩小针宽（`probe_fixed_profile.py`，`results/fixed_profile_eps_probe.json`，每段 n_sub=320）：ε=0.005、0.002、0.001、0.0005、0.0002 的浮点数值 lower 依次为 0.342613、0.326618、0.321296、0.318636、0.317040，已显现正面积平台的方向。此实验仅描述**这一个固定运动**，不等于对每个 ε 重新选择最佳参数，也不能数值证明任何固定 K 族的精确极限；固定 K 不趋零的严谨结论仍来自前述 π/(8K) 扇形下界。要满足理论对数阶候选，必须构造随 ε 增长的复杂度并证明有效重叠。

## 2026-09-28 层次递推候选的反证与未决引理

`hierarchical_pivot.py` 定义连续的 ruler 滑移运动：令 K=2^m、θ_j=jπ/(2K)、f_i=0，r(j)=1+v₂(j)、β_{j-1}=(-1)^{⌊j/2^{r(j)}⌋}s_{r(j)}；各段绕中心枢转，边界沿针轴完整滑移，最后镜像接合。**解析反例**：任取 m≥1，只令 s_m=a≠0、其余 s_r=0；前 K/2 段共享一枢轴，零宽针从 0 转到 π/4，单这部分扫掠面积就是 π/16，任意增大 K 仍不趋零。因此“ruler 参数化＋K 增长”本身不足以得到对数阶，虽然不排除另选 s_r 的有效递推。

更具体的未经优化尺度 s_r=2^{-r}、ε=2^{-m}，在 `probe_ruler.py` / `results/ruler_recurrence_probe.json` 的 m=2…7（K=4…128）得到浮点数值 lower 1.4102→1.1947，m·lower 2.82→8.36，未显示 O(1/m) 下降；有限数据不能排除某个更大常数下的最终渐近。证明所缺的是不同层级圆弧扇形及完整滑移条带的并集足够重叠，使面积 ≤C/m；仅证明每个方向各存在一条针，未给出**方向间连续、低面积的转场**。在文献原始证明或新构造给出此引理前，不把集合邻域上界升级为本问题的运动上界。

## 2026-09-28 分段数迁移：缩放滑移比盲目加 K 更有效

把 ε=0.005 续搜 K=32 的 10+10 控制点**原样**带到 K=8/16/32/64/128、不重新优化（`results/transfer_k_probe.json`），n_sub=80 的浮点数值 lower 分别为 0.70166/0.57674/0.34261/0.61173/0.90706：盲目加密 K 明显恶化。原因是每个边界的滑移 β 仍保持原大小，累计滑移随 K 增长。按 β_new=β_old·32/K 缩放，ε=0.005、n_sub=320 的 K=16/32/64/128 数值区间分别为 [0.376147,0.376433] / [0.342613,0.342770] / **[0.339283,0.339363]** / [0.341060,0.341098]（`results/transfer_k_scaled_probe.json`）。这一确定性迁移在 K=64 时比原 K=32 解有约 1% 的经验改进；K=128 再次恶化，故不是收敛递推证明。

同样从 ε=0.005 的源参数迁移到 ε=0.002、K=64（并非 ε=0.002 的新随机种子），n_sub=640 数值区间 **[0.323239389,0.323279447]**，优于此前该 ε 的 smooth_hr 候选 0.33785（`results/transfer_k_scaled_0002_dense.json`）；ε=0.001、K=64、n_sub=320 区间 [0.317884,0.317964]（`results/transfer_k_scaled_0001.json`）。这些都是**候选构造的浮点数值复评**，不是严格上界证书，也不满足每档 ε 至少三个 fresh seeds 的估计量规则；迁移并没有计入源解发现成本。下一步应在 K=64、ε=0.002 上做同核时预算的局部优化与更多独立盆地测试。

## 2026-09-28 ε=0.002 迁移解续搜

`results/incumbent_refine_0002_K64.json` 在 ε=0.002、K=64 的迁移解上追加 {60,120} 核秒×3 扰动种子 Nelder–Mead：仅 seed 0 改进，n_arc=80 的基线 0.323239268→120 秒 0.322073441。最佳解 n_sub=640 的浮点数值区间 [0.322073553,0.322115423]（`results/refined_0002_K64_dense.json`），与迁移基线 [0.323239389,0.323279447] 明显分离。改进局限于这套模型和既有盆地；另外两种子均未超过基线，历史发现成本和严格误差界仍缺失。不可把该有限续搜视为同预算全方法最低值。

ε=0.002 续搜后的 K64 解不重优化直接缩宽（`probe_fixed_profile.py`、`results/refined_fixed_K64_eps_probe.json`），ε=0.002→0.0001 的浮点 lower 从 0.322074→0.311834，进一步显示**该固定运动**存在正面积平台趋势。ε=0.001 的新迁移候选浮点区间 [0.316684,0.316768] 优于先前同宽度 K64 候选 [0.317884,0.317964]，但两者都不是独立 fresh-seed 估计，也不是严格面积证书。

## 2026-09-28 严格命题：固定分段线性控制曲线在指定迁移规则下不能趋零

令 L=π/2，K₀ 为固定正数；取**固定**有界分段线性控制曲线 f:[0,L]→[-1,1]、b:[0,L]→R，在 K 等分角网格 θ_i=iL/K 上令枢轴分数 f_i=f(θ_i)、段间滑移 β_i=(K₀/K)b(θ_{i+1})，并按 `pivot_slide.py` 完整执行每段枢转、完整滑移及镜像闭合。此处 f 是裁剪控制点后实际插值得到的曲线；允许整体竖直平移，因为面积不变。**严格结论**：存在只依赖 f、b、K₀ 的常数 c>0，使所有充分大的 K、任意 0<ε≤1 的**真实连续扫掠面积**至少 c。因此，这个**等角网格、固定分段线性 f/b、β_i=(K₀/K)b(θ_{i+1})** 的特定迁移族不可能给出趋零的对数阶上界；并未排除别的滑移缩放规则、控制形状随 K 变化或其他运动表示，也不把浮点 `swept_area()` 值当成定理。

证明要点：枢轴递推 `P_{i+1}-P_i=[β_i+(f_{i+1}-f_i)/2]u(θ_{i+1})` 的黎曼和收敛，归一化中心路径的极限 c(θ) 满足 `c'(θ)=(K₀/L)b(θ)u(θ)-f(θ)u⊥(θ)/2`。令 F(θ,t)=c(θ)+t u(θ)、t∈(-1/2,1/2)，其雅可比行列式（差一个符号）为 `t-f(θ)/2`；在任意内部角度选 t=±1/4 且避开枢轴值，即有局部逆映射及像中的开圆盘。不能直接把有滑移跳跃的“角度→中心”作为连续映射；应将每个角网格时间段前半分给枢转、后半分给完整滑移（末格保持终点），形成连续的零宽针映射 G_K(s,t)。最大角度偏差与单次滑移均为 O(1/K)，中心黎曼和亦一致收敛，所以 G_K→F 一致。在局部小圆盘的边界上，以绕数稳定性保证某个固定正半径圆盘包含于所有足够大 K 的 G_K 像；真实宽针扫掠包含这些零宽针，故面积有与 K、ε 无关的正下界。此为几何/拓扑论证，不依赖 Shapely；数值上 K64 固定剖面在 ε→0 的平台只是佐证。

## 2026-09-28 加密控制形状：三次局部攻击均改善

`refine_midpoints.py` 将 ε=0.002/K64 的已知解两组控制点各 10→19 个，插结前后的**原始运动逐姿态不变**；仅优化新增的 18 个中点。180 进程 CPU 秒×3 个随机坐标顺序，在 n_arc=80 下全部由基线 sampled 0.322073441 降到 0.318201764、0.318297664、0.318273413。n_sub=640 的浮点数值区间分别为 **[0.318201882,0.318243177]**、[0.318297789,0.318337757]、[0.318273542,0.318312697]（`results/midpoint_refine_0002_K64_dense.json`；第一次两 seed 的批量复评 120s 超时，第三 seed 随后独立补跑完成）。这说明**增加控制形状自由度**在当前盆地有可重复的有限数值收益，且远大于数值包络间隙；但三次都从同一历史解出发，不是三个独立 cold-start 盆地，更不能由此证明任意 K 依赖形状能达到对数阶。

继续将上节 19+19 控制解从 K64→K128、每段滑移缩半，不优化新参数，n_sub=320 浮点区间 **[0.317332207,0.317373436]**，低于 K64 最好数值区间 [0.318201882,0.318243177]（`results/midpoint_transfer_K128_0002_dense.json`）。但在这个 K128 的固定控制数下，前述严格命题仍排除无止境地只加 K/缩 β 而趋零。已将同一插结算法泛化为 19→37 控制点，进行第二层局部攻击；这是有限尺度方法探索，不是已经找到对数阶递推。

第二层 K128 的 19+19→37+37 精确插结续搜中，三种子均从迁移基线 sampled 0.317332080 改善到 0.314321134/0.314462121/0.314706322；n_sub=320 浮点数值区间分别为 **[0.314321259,0.314363895]**、[0.314462250,0.314503124]、[0.314706450,0.314747332]（`results/midpoint_refine_0002_K128_dense.json`）。再将最好 K128 解迁移 K256、β 缩半、不重新优化，n_sub=160 得 **[0.314024437,0.314067082]**（`results/midpoint_transfer_K256_0002_dense.json`）。连续两层都有有限改善，却不能只凭三层将面积外推到零或证明 O(1/log)；后续必须检验第三层新增控制的收益、评估器精度与计算成本标度。

第三层 K256 的 37+37→73+73 精确插结续搜也全部改善：三次 sampled 0.314024302→0.311840149/0.312061115/0.312011150；n_sub=160 浮点数值区间分别为 **[0.311840284,0.311882752]**、[0.312061253,0.312102605]、[0.312011283,0.312054045]（`results/midpoint_refine_0002_K256_dense.json`）。在固定 ε=0.002 的最佳继承链上，K64→K128→K256 的数值 upper 0.318243177→0.314363895→0.311882752；若 K256 再优化**原有** 37+37 控制节点（此前只动新中点），三次从同一源盆地均改善。n_sub=160 的数值区间分别为 **[0.310335345,0.310376103]**、[0.310537028,0.310578272]、[0.310742094,0.310784328]（`results/coarse_refine_0002_K256_dense.json`），表明前一阶段并非局部完全收敛。自 K64 迁移后的首次局部续搜起，最佳继承链累计优化进程 CPU 约 **1082 秒**，所有相关 seed/预算共约 **3432 秒**（`results/refinement_scaling_0002.json`），均不含历史源解发现和验证计算。每层收益变小、参数维度与验证成本增长；不能从这串数据外推出零极限或稳定预算标度。

在 ε=0.002 将第三层 K256 解直接搬到 K512、β 缩半时，n_sub=80 浮点区间 [0.311859474,0.311901406]，与 K256 最好 [0.311840284,0.311882752] 重叠，**盲目加 K 已无确定收益**。把相同形状搬到 ε=0.001，在 n_sub=160 下 K256 [0.306372597,0.306414908]、K512 [0.306394063,0.306414958]（`results/midpoint_transfer_0001_K256_K512_dense.json`），同样无法区分哪个连续运动的真实面积较小。新宽度下这些值均未通过三个独立冷启动种子或数学证书。

## 2026-09-28 v2 关键帧族连续性审查（独立跨族攻击的前提）

`sweeper_v2.py` 将第一半圈的有限采样矩形与**关于 x=0 的镜像**并集，但并未约束末端中心 `x_end=0` 或计入接缝转场。存档 `v2_0005.json` 的 seed 0 末端 `z_x≈-0.906`、实际 x≈-0.596，镜像前后差约 1.192，故旧并集**不是这条候选的连续半转扫掠面积**。seed 1 的 x_end≈0.00008165 虽差很小，仍须明确补全运动并重算；其 `0.291736` 又是漏扫的稀疏采样值。独立 reviewer 指出一个无额外转场的有效修复：保留整个第一半段，改以**末端中心横坐标 x_end 为镜轴**反射、时间倒序执行第二半段，接点自动连续；新并集一般不同于旧记录，必须单独数值复评。起点与终点不必同位置（问题只要求半转，不要求闭合回路）。新的独立评估器 `v2_numerical_enclosure.py` 默认对 16 个存档 JSON 的**全部 34 条候选**复评，再选择修复后数值最优，避免按旧面积预筛导致漏选；零角度平移亦完整计入。`results/v2_numerical_enclosures.json` 以每关键帧段 n_sub=80 复评，ε=.005 的 v2 K6 三 seed 中最好 seed1 区间 [0.365034574,0.375485710]，其旧值仅 0.291736195。再以 n_sub=320 加密，最好 K6 [0.371195809,0.373850754]、K8 [0.386494298,0.388357858]（`results/v2_0005_repaired_dense.json`）。同 ε 的已保存 smooth K64 迁移候选区间 [0.339282569,0.339363108]（n_sub=320）与 K6 v2 数值区间明显分离，说明**这些存档 v2 候选**未击败当前枢转族候选；不代表全部可能 v2 搜索或同预算算法排名。两族使用同一精度网格几何但每段角度步长不同；两处数值区间均无严格向外舍入，不能宣称严格面积比较。

## Open questions

1. Does f̂·ln(1/ε) flatten (log law, constant A) below ε = 0.01, or
   does the measured curve keep its power-law character? Needs both
   smaller ε and better search at fixed ε.
2. ~~Structure-seeded initialization~~ — tested, negative result (see
   findings above). The successor question: does a **pivot+slide
   segment representation** (each keyframe interval = rotate about a
   chosen cross-section point, then slide along the needle), which can
   potentially express more of Perron-tree packing than the keyframe-
   interpolation model, and find smaller areas? No faithful mapping proof exists.
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
