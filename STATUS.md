# 当前状态（2026-11-12）

## 资源硬约束（用户2026-11-12 09:31）

所有本地GPU依赖工作硬暂停，仅用户明确重新授权可恢复；GPU预约、排队、自动重试与定时唤醒均不得保留。本项目GPU任务/PID/预约均为无，全部现有计算只用标准库CPU。不操作sys_gal或非本系统进程；CPU数学可继续，不用大型训练CPU替跑。

## 目标锚点

研究 1×ε 矩形针连续自由平移、旋转半周的扫掠面积下确界 f(ε)。保留现行 v3 目标：可复现的构造、预算→质量关系及严谨上下界，不用数值宣称真最优或渐近常数；历史与证据等级见 `docs/philosophy.md`。

原始阶数 Θ(1/log(1/ε)) 的文献前提与仓内桥接证明见 `docs/continuous-motion-bridge.md`：Keich 1999 紧致全方向 Kakeya 集邻域界 + 低面积连续转场给上界，方向矩形重叠给下界。允许角度回摆和中心远行，不保证当前受限枢转族达到该阶，也不由范围扫描推断。本次重取原PDF遇HTTP403，保留此前来源与散列，未冒称新的原文核验。

## 本轮已完成

1. **严格上界收紧6.1275%**：固定 ε=.005 正式网格源运动及 q4096，仅细分旋转外包 m16，`f(.005)≤3006787/8388608≈.3584369421`，原界 `.3818339109`。独立数学审查及reviewer、根Manager各自完整复验通过。证明/最小复验命令见 `docs/rational-pivot-certificate.md`，最终审查见 `docs/certificate-review-2026-11-12.md`。
2. **定位外包误差原因**：原v1外包本身面积≥99201/262144≈.3784217834（严格整数内覆盖）；故旧缺口不能全称为空间网格误差，只加q不够。这是旧外包下界，不是运动或f的下界。
3. **通用有限 ε 下界**：均匀方向矩形+CS的显式下界适用于全体合格连续运动。有理实现给 ε=.005 下界2560000000000/11371543232201≈.225123358；与新上界组成严格区间（向外显示 `[.22512335,.35843695]`）。独立理论与实现审查通过，n1024完整重算及独立逐方向求和结果完全一致。推导与完整边界见 `docs/finite-eps-lower-bound.md`。
4. **回归与独立检查**：17项合并回归通过；独立100随机有理多边形内外覆盖、3780个有理圆角点及30组粗细三角区间检查通过。
5. **文档纠偏**：修正“旧7%全为网格开销”、有限预算拟合“命中无限算力极限”等过强论断；保留原数据、证书与全部有效负结果。

## 范围与下一步

旧有限范围扫描与预算网格里程碑继续保留；它们不认证渐近常数、无限算力极限或全局最优。2026-11-12 新授权覆盖旧维护态的停止投入策略，但不要求为了活跃扩大计算。

阶段成果已提交 `fe0b19a`，上下界独立验收已完成。下一检查点优先研究有限长矩形交叠能否改善条带下界；先证明平移下交叠最大化结论，再决定是否值得实现，不开新seed farm或更小ε扫描。

## 可复现入口

```sh
python rational_pivot_certificate.py results/cert_source_grid_smooth_B480.json --seed 0 --q 4096 --subdivisions 16 --verify results/rational_pivot_grid_smooth_B480_q4096_m16.json
python direction_overlap_lower_bound.py --eps 0.005 --directions 1024
python -m unittest -v test_direction_overlap_lower_bound.py test_rational_pivot_certificate.py
python certificate_review/independent_certificate_checks.py
```

均仅需Python标准库；当前Windows/Python3.14.10。`WORKSPACE.md` 主要是旧Linux环境，不照抄旧路径与sleep/nohup等待策略；使用当前runtime的process/reminder。旧导航：`FINDINGS.md`、`docs/findings.md`、`docs/budget-quality-scaling.md`、`docs/eps-sweep-condition1.md`。
