# 04 — Keich 转场在可计算 ε 的实扫掠优势探针

Status: claimed
Need-review: yes
Need-test-cases: yes
Blocked by: none（theory 文档 01/已合并；carrier 结果已存档）。
Claimed by: agent-04-theory-bridge worktree, branch agent/04-theory-bridge-probe, 2026-09-29。

## 问题
docs/continuous-motion-bridge.md 与 docs/keich-explicit-motion.md 的 Keich 型转场
（远滑 → 小转 → 滑回，中心位移恒等式 sigma*R*(u(θ)-u(θ+α))+t*u(θ)）在理论上给出
f(ε)=Θ(1/log(1/ε))，但在可计算 ε（本项目 incumbent 链所在尺度）是否产生**真实
并集扫掠面积优势**，从未做过同分辨率数值对照。本票据只回答这个物理问题
（excursion 成本 vs overlap 收益），用数值估计层，**不是证书、不是定理**。

## 实验设计（预注册）
- Carrier：`results/coarse_refine_0002_K256.json` record 0（ε=0.002, K=256,
  pivot-slide-smooth, Nf=Nb=73, seed0；存档整数外包 0.31166075884960276,
  step_fraction=1e-4）。若 smooth 链适配器构建超时，降级载体：
  v2_repaired K6 链或 3 站手造运动——物理问题优先于载体。
- 对照：baseline 与全部变体用 `integer_motion_area.evaluate` + pyclipper，
  **同一 step_fraction 口径**（变体按其 max_corner_radius 折算 step_fraction
  使 max_step 与 baseline 完全一致，分辨率只严不松）。
- 变体：在若干相邻站点 gap 处，把原地 pivot_rotate 换成简化 excursion：
  沿当前针轴滑出 R、绕针中心转同一小角 δ、沿新轴滑回 R。
  R ∈ {2,4,8,16}（**单位 = 半针长 0.5**，即绝对距离 {1,2,4,8} 针长），
  连续窗口 m ∈ {1,4,16}×3 个位置（早/中/晚），另加全站点 m=256 对照组。
- 预算：<30 CPU 分钟总量；`taskset -c 0 nice -n 10` 串行；每次评估外层
  `timeout --kill-after=10s 600s`。

## 验收
- probe 脚本 + 测试（连续性、镜像还原、step 换算、未补丁重建与 motion_adapters
  一致）+ results JSON + 票据结论（numerical estimate 层级措辞）。
- 逐变体记录 delta vs baseline，报告是否有任何 (position, R) 组合胜出及最佳 delta。
- 明确限制：浮点位姿/三角函数无严格外证（integer_motion_area.LIMITATION），
  结论只在该 carrier、该分辨率、该 excursion 简化形式内成立，不外推渐近。

## Comments
- 2026-09-29 (agent-04 worker): 票据创建即 claim。前次超时 worker 未留提交，
  本 worktree 从 b57b6e1 重新开始；按 commit-early 纪律分三次提交
  （ticket / probe+test / results+verdict）。
## Result (2026-09-29, main-session implementation after 4 subagent timeouts)
- Implementation: `probe_theory_bridge.py` + `test_probe_theory_bridge.py`
  (6 tests OK). Rebuild pipeline verified byte-identical to
  `motion_adapters.evaluate_saved` (rel_tol 1e-12). Two real bugs found and
  fixed during TDD: boundary-check operator precedence; missing
  inter-station beta slide in the excursion branch (would have changed the
  motion itself); plus one design fix: post-excursion chain must anchor
  pivots to the actual chain position, not the nominal lattice.
- Sweep: 40/40 variants evaluated ok at step_fraction=1e-3, K256 carrier,
  eps=0.002 (results/theory_bridge_probe_0002_K256.json).
- VERDICT: **no advantage at computable scale.** Every variant is worse.
  Best = mid_m1_R2 at +3.460% (single station, R=1); monotone degradation
  with window size m and radius R (full replacement R=8: +1414%).
  High-resolution confirm (1e-4) on the best variant: +3.25% (baseline
  0.31166075884960276 vs variant 0.3217736810300932). Consistent with the
  strict fixed-profile positive-floor theorem (db581e7): the excursion's
  slide-out/slide-back sweep always exceeds its overlap gain on this
  carrier. The theory's log-order advantage relies on asymptotic regimes
  (R ~ eps^{-1/2} ~ 22 here) and set-theoretic bookkeeping, not on local
  finite-eps gains.
- Evidence tier: numerical estimate only (integer evaluator, same
  resolution baseline vs variant; NOT a certificate, NOT asymptotic).
