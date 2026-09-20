# fat_kakeya_needle

数值实验研究 **fat Kakeya needle 问题**：一根 1×ε 的细长矩形针，
在无限平面上完全自由地运动（平移 + 旋转），转过 180°，问它扫过的
最小面积 f(ε) 是多少？

## 愿景与最终目标

理论已知 f(ε) = Θ(1/log(1/ε))（Córdoba 1977 下界、Keich 1999 匹配
上界），但**乘性常数 A 至今无人给出数值**。本项目的最终目标：

1. 用大规模数值优化画出可信的 f(ε) 曲线（ε 从 0.8 压到 0.002）；
2. 从数据中反推**渐近常数**与修正结构；
3. 把每个数值结果配上**可复核的误差证书**，让"数值实验"升级为
   "计算辅助的严格上界"。

当前最佳估计（详见 docs/findings.md）：

> **f(ε) ≈ 2.27 / (ln(1/ε) + 1.60)**  （全域 0.002 ≤ ε ≤ 0.8，37 点，
> 除最小 ε 外偏差 < ±6.5%）

即渐近常数 **A ≈ 2.27**——据我们所知，这是该问题常数的首次数值估计。

## 实现方法

一根针的运动 = 一串关键帧位姿 (θ, x, y)；两个关键帧之间位姿线性
插值（或"绕枢轴旋转 + 沿针滑移"），扫掠面积 = 所有中间位姿矩形
的**精确多边形并集**（shapely，任意距离下精确，无光栅近似）。
搜索用差分进化（DE）+ Nelder-Mead 抛光，多进程并行。

四个运动族交叉验证（详见 docs/findings.md）：

| 族 | 特点 | 角色 |
|---|---|---|
| v1 keyframe | 光栅评估，有界窗口 | 中大 ε 基线 |
| v2 logspace keyframe | log 空间平移，可到任意远 | 小 ε |
| pivot+slide free | 每段绕针上某点枢转 + 沿针滑移 | 物理可解释族 |
| pivot+slide smooth | f(θ)、β(θ) 用少量控制点的光滑剖面 | 小 ε 主力（维数与 K 无关）|

方法论硬约束（踩坑换来的，见 docs/methodology.md）：
**min-over-≥3 fresh seeds** 是唯一可靠估计量；目标函数采样分辨率
必须随 ε 缩小而加密（n_theta=40 在 ε=0.005 时漏扫 21%）；所有跨 ε
结论必须经高分辨率复评。

## 已做什么 / 主要成果

- f̂(ε) 曲线 37 点（ε ∈ [0.002, 0.8]），四族交叉验证，
  全部结果与证书工具可复现（`results/`，`strict_bound.py`）。
- **A_eff = f̂·ln(1/ε) 单调上升**，与带修正项的 log 律完全一致；
  crossover 拟合给出 A ≈ 2.27, B ≈ 1.60。
- 阴性结果同样成体系：Perron 自相似层次参数化被证伪（塌缩为
  两站点运动）；结构种子与随机种子打平；盲 DE 维数诅咒普遍
  （三族皆 K=6–8 最优）。
- 完整过程记录：`results/morning_report.md`（含两次结论反转的
  证据链）。

## 没做什么 / 开放问题

- **ε=0.002 点 +16% 偏离** log+B 预测——是族表达边界还是更高阶
  修正？需 ε=0.001 + v2 族高分辨率交叉验证。
- **严格上界**尚未对所有已发表构造出证书（strict_bound.py 已就绪，
  枢转+滑移族几何干净可先行）。
- **f(ε) 的严格下界**完全没有——数值只能给上界。
- 理论 log 律的数值验证在 ε ≥ 0.002 内不可行（修正项衰减太慢，
  lnln(1/ε)/ln(1/ε) < 1% 需要 ε < 10⁻⁴⁰ 量级）。

## Roadmap

1. [ ] v2 族高分辨率评估器 polygon 化（raster 精度依赖 ε）
2. [ ] ε=0.001 + ε=0.002 交叉验证（裁决 +16% 偏离）
3. [ ] 对头条构造签发严格上界证书（strict_bound.py）
4. [ ] 跨优化器对比（CMA-ES / 贝叶斯 vs DE），标定搜索能力天花板
5. [ ] 族间不可达缺口成因（关键帧"切角" vs 枢转+滑移）

## 快速开始

```bash
uv pip install --python /home/z/.venv/bin/python3 shapely scipy numpy matplotlib

# 单点优化（例：eps=0.05, K=32, 光滑剖面族）
/home/z/.venv/bin/python3 smooth_run.py --eps 0.05 --K 32 --Nf 6 --Nb 6 \
    --seeds 3 --workers 6 --out results/demo.json

# 长任务请用 detached（见 WORKSPACE.md），分析绘图：
/home/z/.venv/bin/python3 analyze.py
```

## 文档导航

- `docs/findings.md` — 结论 SSOT（含证据链与数据表）
- `docs/methodology.md` — 优化方法论与教训
- `docs/research-plan.md` — 研究计划与未来方向
- `results/morning_report.md` — 完整过程日志（含两次结论反转）
- `basics.md` — 用户提供的背景资料（verbatim 源）
