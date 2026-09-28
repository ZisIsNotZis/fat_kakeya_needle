# fat_kakeya_needle

研究一根 1×ε 矩形针在平面上连续平移、旋转 180° 的扫掠面积。目标是寻找可随 ε 递推细化的构造，并比较有限算力预算下不同搜索方法取得的面积；失败、漏扫和不稳定结果同样需要可复核地记录。

## 当前状态（2026-09-28）

- 过去在 0.002≤ε≤0.8 的数值样本可用 `2.27/(ln(1/ε)+1.60)` 拟合。这只是**有限范围的拟合参数**，不是已证渐近常数，也不能证明构造在 ε→0 时达到理论阶。
- 固定 K 段的枢转＋滑移运动，每段至少扫出面积 π/(8K)；因此固定 K 的真实面积不能随 ε→0 趋零。必须研究 K 随 ε 增长且有足够跨段重叠的递推族。
- 旧优化器评估的是有限姿态采样的并集，可能低于真实连续扫掠面积。例：ε=0.001、K=1、每段 30 个姿态的中心旋转给出 0.058854，而解析面积约 0.785399。ε=0.002 的现有最小记录仅两个 fresh seeds，不能算通过项目的 ≥3 seeds 标准。
- `strict_bound.py` 现提供 `numerical_pivot_enclosure`：用实际枢转圆弧的端点凸包、角点弧矢高和完整滑移条带，给出**浮点数值包络**。`make_certificates.py` 只生成 `results/pivot_numerical_enclosures.json`；旧泛用 `strict_upper` 已禁用，旧 `results/certificates.json` 不能当作证书。Shapely 几何与面积没有严谨向外舍入，故目前**没有数学严格上界证书**。
- 关于文献中的对数阶是否直接适用于要求运动连续的这个问题，原始证明及连接步骤仍待核验；详见 `docs/findings.md`。

## 模型和复现

运动族包括关键帧线性插值（`sweeper_v2.py`）、枢转＋滑移（`pivot_slide.py`）、少量控制点的光滑剖面（`smooth_pivot.py`）、二进层次滑移（`hierarchical_pivot.py`）。优化主要使用差分进化；每族的数值比较必须指定相同的评估精度、fresh seeds 和实测 CPU 核时预算。优化器所得的 sampled area 是数值估计，不是自动成立的面积上界。

环境见 `WORKSPACE.md`。最小回归检查：

```bash
/home/z/.venv/bin/python3 -m unittest -v test_pivot_enclosure
/home/z/.venv/bin/python3 make_certificates.py
```

`make_certificates.py` 会重生成枢转族的**数值**包络结果；不会修改历史 `results/certificates.json`。单点优化示例：

```bash
/home/z/.venv/bin/python3 smooth_run.py --eps 0.05 --K 32 --Nf 6 --Nb 6 \
    --seeds 3 --workers 6 --out results/demo.json
```

## 下一步

1. 给数值包络增加中间姿态的几何包含回归；实现可审计的向外舍入面积算法后，才讨论严格证书。
2. 建立随 ε 增长的 K 的递推候选；用统一高分辨率重新评估，并对 ε=0.002 补足 fresh seeds。
3. 固定候选族、机器并发、评估精度和 CPU 核时后，测量预算→质量曲线；“最优”只针对明确列出的已实现方法及预算。

`docs/philosophy.md` 是目标与证据层级的来源；`docs/findings.md` 记录结果、反例和未决问题；`docs/methodology.md` 记录评估器和优化器的已知陷阱。大型历史结果在 `results/`。
