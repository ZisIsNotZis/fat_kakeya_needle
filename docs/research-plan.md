# 过夜自主研究计划（2026-09-11 晚 → 09-12 早）

用户已授权全夜自主研究。本文件是 **SSOT**：任何新会话/子代理先读本文件

+ `docs/findings.md` + `docs/methodology.md` + `WORKSPACE.md` 即可接续。

## 主问题

f(ε) = 1×ε 矩形针自由平面运动旋转 180° 的最小扫掠面积。理论上
Θ(1/log(1/ε))，常数 A 开放。数值上当前 f̂·ln(1/ε) 仍在上升
（1.38 @ε=0.05 → 1.58 @ε=0.01），log 律未显现。

## 核心瓶颈（已证实的结论）

+ 最优构造（Perron 树）需要 K 很大的分段，但盲 DE 随维数崩盘
  （K=6: 0.461 < K=10: 0.583 < K=14: 0.608，ε=0.05）。
+ 纯 warm-start 失败两次；**min-over-≥3 fresh seeds** 是唯一可靠估计量。
+ 结构种子在关键帧模型失败（好盆地非经典枢轴链族）。
+ 新枢转+滑移模型（`pivot_slide.py`，物理忠实，π/4 校验通过）：
  K=6→0.4925, K=8→0.4880，随 K 下降，尚未超过 0.4614。

## 今晚三阶段

### Phase A（已启动，detached）

枢转+滑移自由参数基线：ε=0.05，K ∈ {8,12,16} × 4 seeds，
`results/pivot_005_K*_night.json`，完成标记 `results/PHASE_A_DONE`。
判据：K 趋势是否延续下降、能否越过 v2 的 0.4614。

### Phase B（核心创新）：层次化滑移参数化

Perron 树自相似：对半分裂 → 对的对… 用 **log₂K 个尺度参数 s₁..s_m**
生成 K 站点的滑移序列（ruler sequence 模式：β_j = σ_j·s_{r(j)}，
r(j) = j 的 2-adic 赋值 +1），参数向量 [y0, s₁..s_m]，K = 2^m。
低维 → DE 可用大 K（16/32/64）。判据：ε=0.05 下能否显著 < 0.461。
实现：`hierarchical_pivot.py`（新文件，不改 pivot_slide.py——A 在跑），
`run_night_phaseB.sh`。控制组：hierarchical K=8（m=3+1=4 维）对比
自由 β K=8（17 维，0.4880）——若 4 维能达到 ~0.49 则族损失可忽略。

### Phase C（渐近区检验，主问题判据）

ε ∈ {0.02, 0.01, 0.005}，双族并跑：
+ hierarchical K=32 × 4 seeds，**mixed-init**：初值矩阵含上一档较大 ε
  最优解的扰动副本 + 随机行（层次参数与 ε 无关，可直接跨 ε 迁移——
  这实现用户"从大 ε 学习、逐步缩小"的建议；纯 warm-start 已证伪，
  mixed-init 保留随机主导）。
+ 自由 β K=8 × 3 seeds（交叉验证）。
判据：A_eff = f̂·ln(1/ε) 是否开始平台化。

### Phase D（晨间交付）

合并绘图（三模型 + A_eff 面板）、`docs/findings.md` 更新、
`results/morning_report.md`、ticket 收尾、commit。

## 执行协议（硬约束）

1. 长任务一律 `setsid nohup` detached（bg_run 子进程会随会话重启死亡，
   已发生 3 次），日志 + per-run JSON + DONE 标记文件。
2. 计算负载：单任务 workers ≤ 6，`nice -n 10`；Phase 间用标记文件串行
   （master runner 内 `while [ ! -f marker ]; do sleep 120; done`）。
3. 一切"完成"声明必须引用命令+观测结果（证据在 results/）。
4. 评估器先过冒烟：全零参数 → π/4（0.787±0.003）。
5. 文档先行：每阶段结束立刻更新 findings/methodology/morning_report
   （中文），防 auto-compact 丢失。
6. commit 规范：agent <agent@local>，message = 结果摘要。

## 自主决策规则（用户不在场）

+ 可逆操作（跑实验、改代码、写文档）→ 直接做并记录。
+ 不可逆/删除性操作 → 不做，记录到 ticket。
+ 夜间无用户可问：卡住 >2 次尝试 → park 并记录状态与下一步。

## 未来研究方向（2026-09-17 与用户过，按推荐序）

1. **族间不可达缺口成因**：ε=0.005 处关键帧族 0.2917 vs 枢转+滑移族
   0.342（15% 缺口，各自充分搜索）。假设：关键帧的线性位姿插值
   "切角"等价于混合运动，可能是优势来源。实验：三元插值模型
   （枢转+滑移+切角系数），看缺口是否关闭。
2. **ε=0.001 挑战**：A_eff 峰值右侧只有 2 个点，且 0.005 点来自另一族
   （族切换 artifact 风险）。前置工作：v2 评估器 raster→polygon 化
   （ε=0.001 时 raster 精度不足）。判据：A_eff 是否稳定在 1.55–1.58。
3. **常数 A 的修正结构**：小 ε 拟合 A_eff = A + c·lnln(1/ε)/ln(1/ε)
   vs A + b/ln^α，判断次级修正形态。当前残余斜率 0.067 仍显著。
4. **严格上界机器**：枢转+滑移模型采样误差有解析界（凸体旋转
   内接多边形 O(1/n²)），把数值结果升级为严格数学上界
   （计算辅助证明）。
5. **DE 维数诅咒机制**：跨优化器（DE/CMA-ES/贝叶斯）× K 网格的
   算法-维数-面积曲面，标定所有数值结论的可信度上限。

## 文件清单（夜间产物）

+ `run_night_phaseA.sh` / `results/night_phaseA.log` / `PHASE_A_DONE`
+ `hierarchical_pivot.py`、`run_night.sh`（master：等 A → 冒烟 → B →
  `PHASE_B_DONE` → C → `PHASE_C_DONE`）、`results/night_*.log`
+ `results/hier_005_K*.json`、`results/hier_0*.json`、`results/pivot_0*.json`
+ `results/hier_smoke.log`（冒烟证据）
+ `results/morning_report.md`（追加式晨报）
