# 连续运动的数值整数多边形评估（非数学证书）

`integer_motion_area.py` 是可选的 `pyclipper==1.4.0` 数值后端，首版只接入 `keich_motion.py` 输出的 `slide` 和绕当前中心的 `center_rotate` 原语。它补上旧 GEOS 在远距细针上的拓扑失败，但不应被称为严格上界：原始位姿、三角函数和浮点→整数时的外扩垫片没有逐步向外舍入的证明。严格证书仍由独立的 `rational_pivot_certificate.py` 负责。

## 评分规则

- 轴向滑移：核对起终角、声明的有符号长度、轴向残差及相邻原语接点；取起终矩形角点凸包，包含整个平移条带。中心旋转：核对声明转角与两端，允许负角和临时回摆；角度分段不超过 π/2，每段端点矩形角点凸包以 `r·2sin²(|Δθ|/4)` 作 L∞ 方形外扩，`r=hypot(1/2,ε/2)`。任一运动无效或后端失败都不返回面积。
- 统一整数尺度默认为 `2^40`；浮点乘尺度前以整数比值做 floor/ceil、启发式 ulp 垫片，拒绝非有限值与 `|坐标·尺度|≥2^53`，并检查 Clipper 6.4.2 的 `hiRange`。整数凸包并集按孔洞符号和 Python 整数鞋带公式求面积。**只对量化后的整数多边形裁剪是精确的**；整个输入运动的 `numeric_outer_area` 仍是数值近似。
- `evaluate_keich(5)` 在目标外扩矢高≤0.1ε 与≤0.05ε 的两档角步之间比较；差异>2%、任一失败或预算耗尽时移除面积并返回 `quality_limited`／`resource_limited`／`error`。原生 Clipper 并集不能在进程内部抢占；长跑必须加外部 `timeout`。没有稳定通过这道闸门的面积不得参加排名。

## 首轮回归与边界

`PYTHONDONTWRITEBYTECODE=1 /home/z/.venv/bin/python3 -m unittest -v test_integer_motion_area` 覆盖中心旋转解析圆盘、远距正负滑移、负角、多圈、内点外包、孔洞、矛盾原语和断链、n4/5 资源界。`timeout 180 nice -n 10 /home/z/.venv/bin/python3 integer_motion_area.py --n 5 --max-wall-s 120 --out results/integer_keich_n5_smoke.json` 独立写结果，文件存在时拒绝覆盖。

首次固定尺度 `2^40`：Keich n=4 (`ε=2^-16`) 数值外包约 **1.241886**（984 多边形、0.44 秒）；n=5 (`ε=2^-20`) 数值外包约 **0.940920**（3236 多边形、19.1 秒），更细角步约 0.932155、相差 0.93%。另以 `2^38` 尺度得 n4≈1.241886018、n5≈0.940920748，相对差约 `9.68e-8`、`1.16e-6`。证据在 `results/integer_keich_n{4,5}_{smoke,scale38_smoke}.json`。它们**高于**固定中心约 π/4，也不能从这些尺度判定递推的渐近常数；旧稀疏采样 n4≈0.446 是漏扫诱导的假低，n5 旧 GEOS 则失败。结果不包括发现该理论递推或其他优化族的同预算搜索成本。

## 后续门槛

当前接口尚未把 `PivotSlideModel` 的非中心枢转圆弧或 v2 的线性中心／线性角度段适配到同一整数后端。各自需要正确的角点半径、完整滑移或零角平移，以及 v2 的末端中心镜轴；不得把所有运动强行视为中心旋转。三族经过同一后端的解析、接合、密采样包含和双尺度回归后，才冻结 `.scratch/01-fat-kakeya-experiment/issues/03-budget-quality-benchmark.md` 的预算实验。可选依赖的版本、MIT 包装层与 Boost 1.0 内核许可及安装命令见 `WORKSPACE.md`。
