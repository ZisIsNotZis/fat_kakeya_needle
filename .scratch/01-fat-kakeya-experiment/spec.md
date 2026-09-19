# 01 — fat Kakeya needle numerical experiment

Parent spec for the numerical exploration. Working state; results are
recorded in docs/findings.md (SSOT for findings).

## Objective

Sample f̂(ε) = minimal swept area of a 1×ε needle turning 180° under
free planar motion, on ε ∈ [0.01, 0.8]; characterize the decay law and
probe the (open) constant of the theoretical Θ(1/log(1/ε)) asymptotic.

## Done

- [x] v1 raster model + coarse sweep ε ∈ [0.07, 0.8] (results/eps_*.json)
- [x] v2 exact-polygon log-space model (sweeper_v2.py, optimize_v2.py)
- [x] Continuation passes 1–2 (results/cont1/, results/cont_*.json)
- [x] K study at ε=0.05: K=6 beats K=10, K=14 under blind DE
- [x] ε=0.01 first point: f̂ ≈ 0.344
- [x] Findings + methodology docs

## Open (see docs/findings.md "Open questions")

- [ ] 01-smaller-eps-asymptotics: does f̂·ln(1/ε) flatten below ε=0.01?
- [x] 01-structure-seeded-init: tested, negative result (see findings)
- [ ] 01-seed-farm: min-of-N seeds at ε ∈ {0.01, 0.05} for stable minima
- [ ] 01-night-plan: 过夜自主研究 Phase A–D，见 docs/research-plan.md
  （SSOT）。Phase A 已 detached 启动；Phase B/C 由子代理实现 +
  master runner 串行执行。

## Comments

- 2026-09-11 (agent, pi harness): bg_run children died 3× on pi-session
  restarts; switched to setsid-detached runner (run_detached.sh).
  Result files committed as evidence per Repository files 3.

## Comments

- 2026-09-19 (agent, pi harness): 过夜自主研究完成。方向4审计发现
  n_theta=40 目标函数在 ε=0.005 漏扫 21%，0.2917 假值已剔除；
  高分辨率（n_arc 80-160）小 ε 序列：0.01→0.3654, 0.005→0.3494,
  0.002→0.3378。A_eff 单调加速上升无平台，log 律 vs 幂律在
  ε≥0.002 无法裁决。全部证据在 results/ 与 morning_report.md。
  模型：agent (pi harness), 主会话直接实现（子代理环境两次零产出不可用）。
