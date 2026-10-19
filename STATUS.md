# STATUS

路由文件：只记「它是什么、现在什么状态、进展落在哪、下一步」。结论与数字见 `FINDINGS.md`（每条带 `文件:行`）；目标与证据层级的权威是 `docs/philosophy.md`。
`文件:行` 引用绑定该提交之前的 revision `35b721a`。

## 它是什么

研究**一根 1×ε 矩形针在平面上连续平移、旋转 180° 的扫掠面积**：**minimize** 该面积（ε 是针宽）。目标是找可随 ε 递推细化的构造，并在有限算力预算下比较不同搜索方法取得的面积；失败、漏扫与不稳定结果同样要可复核地记录。（`README.md:3`）

## 当前状态

**维护态（归档）**，自 2026-09-30 起；最后一次代码/文档提交 2026-10-15（HEAD `35b721a`）。

- v3 终局判定三条全部达成，项目进入维护态。（`README.md:43-45`、`docs/philosophy.md:79-91`）
- 重启条件写在 `docs/philosophy.md:91`：质疑任一证书、需要新的严格界，或要用别的运动族重测。**除这些条件外不主动投入。**
- 全部结论都停在**数值估计层**，除两条有理证书外没有严格面积上界；这是仓库自己反复写明的边界（`README.md:7-13`、`FINDINGS.md` 的"部分"行）。

## 最新进展落在哪个文件

1. 结果、反例与未决问题：`docs/findings.md`（最近三节：`2026-09-29` budget→quality 标度律、`2026-09-30` f̂(ε) 全程扫描、以及更早的严格命题与证书边界）。
2. 终局三条判定的结论：`README.md:43-63`、`docs/philosophy.md:79-91`。
3. 三条判定各自的细节：`docs/budget-quality-scaling.md`、`docs/eps-sweep-condition1.md`、`docs/rational-pivot-certificate.md`。
4. 理论侧：`docs/continuous-motion-bridge.md`（严格阶）、`docs/keich-explicit-motion.md`（有限递推）、`docs/numerical-motion-evaluator.md`（评估器陷阱）。
5. 环境与已知陷阱：`WORKSPACE.md`；评估器/优化器陷阱：`docs/methodology.md`。

## 下一步

维护态下**没有在办工作**；仓内写明的可重启方向只有这些，未新增判断：

1. `docs/findings.md:167-188` 的 5 个 open questions（log 律是否显现、pivot+slide 表示是否有忠实映射证明、真最优的 sharp 常数 A、ε∈{0.01,0.05} 的 ≥10 seed farm、pivot+slide 族的初值）。
2. `README.md:37-39` 的"下一步"三条：修复 v2 的优化目标后再谈公平预算搜索与更紧的有理证书；找控制形状随尺度增长且有跨层重叠证明的递推；固定候选族/并发/精度/核时后测预算→质量曲线。
3. `.wrapup`-类未决项：无（本仓库无未决阻塞登记）。
