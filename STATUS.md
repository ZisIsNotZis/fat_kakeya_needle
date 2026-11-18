# 当前状态（2026-11-12）

## 资源硬约束（用户09:31）

所有本地GPU依赖工作硬暂停，仅用户明确重新授权可恢复；GPU预约、排队、自动重试与定时唤醒均不得保留。本项目全树无GPU任务/PID/预约/待释放显存，唯一子reviewer已明确确认。CPU独立数学可继续，不作大型训练CPU替跑；不操作sys_gal或非本系统进程。

## 目标锚点

研究1×ε矩形针连续自由平移、旋转半周的扫掠面积下确界f(ε)。保留v3目标：可复现构造、预算→质量与严谨界，不用数值宣称真最优或渐近常数。目标历史见 `docs/philosophy.md`，结论见 `docs/findings.md`。

原始Θ(1/log(1/ε))的Keich文献前提及自由连续运动桥接见 `docs/continuous-motion-bridge.md`。允许角度回摆和中心远行；不由扫描推断，也不认证受限枢转族。本轮重取原PDF遇403，不冒称重新核验原文。

## 当前可交付结果

**`3141592653589/13596634733098 ≤ f(.005) ≤ 3006787/8388608`**，向外显示 **`[.23105663,.35843695]`**。

- 上界：固定正式ε=.005/K32预算网格源运动和q4096，细分旋转外包m16使严格上界从.38183391收紧6.1275%；不是运动优化。reviewer与root分别完整复验通过。见 `docs/rational-pivot-certificate.md`、`docs/certificate-review-2026-11-12.md`。
- 新下界：对**全体合格连续半转运动**，有限长矩形最大交叠+CS给 `f(ε)≥πε²/J(ε)≥π/[2log(1/ε)+3]`。BM证明任意平移交叠不超过中心重合值；角平分坐标精确积分给J；简洁式已作有理log外包认证。见 `docs/finite-rectangle-overlap.md` 及独立审查 `docs/finite-rectangle-overlap-review-2026-11-12.md`。未声称文献新颖性、锐常数或极限存在。
- 独立审查与检查：3098组精确中心交叠、500组平移、47组独立log夹逼通过；22项合并回归通过。有限测试不替代数学证明。
- 原v1外包本身面积≥.3784217834，说明旧差距不全是空间网格误差。此数仅为旧外包下界，非运动或f下界。旧证书和旧.22512335通用下界保留为有效但较弱证据。
- 精确中心交叠是Gram核：旋转平均/Jensen证明在“该核+加权CS”松弛中均匀方向已经最优。**本路线封口，不再扩方向网格、调方向权重或磨精确J的小数。**

## 当前交付范围

来源审计已完成。存档数值候选的配方使用 10+10 个控制量，正式 B480 证书源使用 6+6 个，对应不同运动。存档候选的扫掠面积仍只作数值估计，严格上界取自正式证书。三份源文件的 SHA-256、种子和控制布局见 [来源审计](results/incumbent_provenance_audit_20261112.json)。当前交付包含可复现构造、计算预算和有限宽度严格界。

真正突破当前下界须增加超出两两最大交叠+CS的全局几何信息；尚无经验证的新方法，不以增加算力替代缺失理论。旧有限扫描/预算数据不认证渐近常数、无限算力极限或全族最优。

## 最小复现（Python标准库，当前Windows/Python3.14.10）

```sh
python finite_rectangle_lower_bound.py --eps 0.005
python rational_pivot_certificate.py results/cert_source_grid_smooth_B480.json --seed 0 --q 4096 --subdivisions 16 --verify results/rational_pivot_grid_smooth_B480_q4096_m16.json
python -m unittest -v test_finite_rectangle_lower_bound.py test_direction_overlap_lower_bound.py test_rational_pivot_certificate.py
python certificate_review/centered_overlap_checks.py
python certificate_review/log_certificate_checks.py
```

`WORKSPACE.md`的Linux路径与sleep/nohup是历史环境；当前使用runtime process/reminder。初轮成果提交fe0b19a；最新阶段在上述证明/审查与本状态中定位，不覆写历史证据。
