# AGENTS.md — fat_kakeya_needle 项目约定

## 接手入口

先读 `STATUS.md` 恢复当前状态与下一项工作。目标及历史承诺以 `docs/philosophy.md` 为准；数学/数值结论在 `docs/findings.md`。旧维护态不自动覆盖 2026-11-12 的恢复推进授权。

## 语言

- 与用户对话、报告、总结用简体中文。
- 代码、注释、commit message、results JSON 字段用英文。

## 研究与证据

研究 1×ε 矩形针自由连续半转的扫掠面积下确界；目标是可复现构造、预算→质量关系及严谨界，不把数值最小值写成真最优。

- 报告区分数值估计、经验包络、严格定理。
- 严格证书修改时读 `docs/rational-pivot-certificate.md` 与 `docs/certificate-review-2026-11-12.md`；有限ε通用下界见 `docs/finite-eps-lower-bound.md`。
- 数值族比较时读 `docs/methodology.md` 与 `docs/budget-quality-scaling.md`，保持源运动、分辨率、种子、计费口径可比。

## 执行

长任务使用当前 runtime 的 process 进度与 reminder 检查点；旧环境的 sleep/nohup 方案仅是历史记录。运行前核实实际平台，`WORKSPACE.md` 中 Linux 路径不代表当前机器。
