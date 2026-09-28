# fat_kakeya_needle

研究一根 1×ε 矩形针在平面上连续平移、旋转 180° 的扫掠面积。目标是寻找可随 ε 递推细化的构造，并比较有限算力预算下不同搜索方法取得的面积；失败、漏扫和不稳定结果同样需要可复核地记录。

## 当前状态（2026-09-28）

- 旧数值集合曾拟合 `2.27/(ln(1/ε)+1.60)`；新的统一复评和更低候选已**推翻该拟合作为当前曲线及渐近常数估计**的地位，见 `docs/findings.md` 历史拟合节。理论阶来自独立的集合构造与运动接合证明，不来自有限点拟合。
- 固定 K 段的枢转＋滑移运动，每段至少扫出面积 π/(8K)；对于项目中的等角枢转族，即使 K 增长，若始终使用固定分段线性控制曲线、每段滑移按指定的 1/K 规则缩放，真实连续扫掠面积仍有正下限（证明见 `docs/findings.md`）。该迁移族要突破此障碍，需改变控制形状或滑移规则；这不排除其他运动表示。
- 旧优化器评估有限姿态，可能严重漏扫：ε=0.001、K=1、每段 30 姿态中心旋转给出 0.058854，而解析面积约 0.785399。当前 ε=0.002 的最好**候选运动**为 K=256、73+73 控制点，n_sub=160 浮点数值区间 [0.310335345,0.310376103]；它继承历史盆地，三次局部搜索并非三个独立冷启动，不能称真实 minimum 或已认证上界。
- `strict_bound.py` 现提供 `numerical_pivot_enclosure`：用实际枢转圆弧的端点凸包、角点弧矢高和完整滑移条带，给出**浮点数值包络**。`make_certificates.py` 只生成 `results/pivot_numerical_enclosures.json`；旧泛用 `strict_upper` 已禁用，旧 `results/certificates.json` 不能当作证书。另有**有理数严格证书** `rational_pivot_certificate.py`，仅认证两条指定连续运动：ε=.05 的 f 上界为 `4489/8192≈0.547974`，ε=.002 的 q=128 初版为 `3057/8192≈0.373169`，加密到 q=2048 后为 `673359/2097152≈0.321083`。严格界仍高于相应浮点估计，不是估计值、全局最优或渐近定理。
- v2 关键帧旧评估器未强制镜像接缝连续；`v2_numerical_enclosure.py` 以末端横坐标作镜轴重算全部 34 条存档候选。ε=0.005 最好存档 v2 在 n_sub=320 的数值区间约 [0.37120,0.37385]，未击败同宽度已保存的光滑枢转候选；并非同预算方法排名。
- **严格渐近阶已核实为 Θ(1/log(1/ε))**：Keich 原文给出同一紧致 Kakeya 集的统一邻域上界；独立转场证明将其接成自由、连续的粗针半转，方向矩形重叠给出下界。证明允许临时角度回摆、中心随 ε 远行。Keich 有限三角形阶段还能给出**理论上有限有效的运动递推公式**，见 `docs/keich-explicit-motion.md`；`keich_motion.py` 可输出浮点展示轨迹，但不是严格证书或最优搜索器，也未确定乘性常数或给定预算下的最低数值。见 `docs/continuous-motion-bridge.md`。

## 模型和复现

运动族包括关键帧线性插值（`sweeper_v2.py`）、枢转＋滑移（`pivot_slide.py`）、少量控制点的光滑剖面（`smooth_pivot.py`）、二进层次滑移（`hierarchical_pivot.py`）。优化主要使用差分进化；每族的数值比较必须指定相同的评估精度、fresh seeds 和实测 CPU 核时预算。优化器所得的 sampled area 是数值估计，不是自动成立的面积上界。

理论递推展示：`/home/z/.venv/bin/python3 keich_motion.py 1/256 > motion.json`（n=2、17 个站点；输出浮点位姿仅用于检查，非面积证书）。环境见 `WORKSPACE.md`。最小回归检查：

```bash
/home/z/.venv/bin/python3 -m unittest -v test_pivot_enclosure test_v2_numerical_enclosure test_rational_pivot_certificate test_keich_motion
/home/z/.venv/bin/python3 make_certificates.py
/home/z/.venv/bin/python3 v2_numerical_enclosure.py --best-new --n-sub 80 \
    --out results/v2_best_repaired.json
```

`make_certificates.py` 会重生成枢转族的**数值**包络结果；不会修改历史 `results/certificates.json`。有理证书的证明假设、源文件哈希与两条逐条复算命令见 `docs/rational-pivot-certificate.md`。单点优化示例：

```bash
/home/z/.venv/bin/python3 smooth_run.py --eps 0.05 --K 32 --Nf 6 --Nb 6 \
    --seeds 3 --workers 6 --out results/demo.json
```

## 下一步

1. 已有粗网格严格上界；下一步细化有理网格，缩小它与浮点估计之间的差距，仍须独立审查每种新外包方法。
2. 继续寻找**控制形状随尺度增长且有跨层重叠证明**的递推；现有三层插结只有有限数值收益，对 ε=0.002 还需独立冷启动种子。
3. 固定候选族、机器并发、评估精度和 CPU 核时后，测量预算→质量曲线；“最优”只针对明确列出的已实现方法及预算。

`docs/philosophy.md` 是目标与证据层级的来源；`docs/findings.md` 记录结果、反例和未决问题；`docs/methodology.md` 记录评估器和优化器的已知陷阱。大型历史结果在 `results/`。
