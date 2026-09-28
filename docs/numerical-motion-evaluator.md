# 连续运动的数值整数多边形评估（非数学证书）

`integer_motion_area.py` 是可选的 `pyclipper==1.4.0` 数值后端；Keich `slide`/中心转动、非中心枢转及 v2 线性中心／角度段均已接入，`motion_adapters.py` 负责历史运动的连续镜像接合与模型解码。它补上旧 GEOS 在远距细针上的拓扑失败，但不应被称为严格上界：原始位姿、三角函数和浮点→整数时的外扩垫片没有逐步向外舍入的证明。严格证书仍由独立的 `rational_pivot_certificate.py` 负责。

## 评分规则

- 轴向滑移：核对起终角、有符号长度、轴向残差及接点；取起终矩形角点凸包，包含完整平移。中心转动、固定枢轴转动、世界中心与角度线性插值分别计算正确的角点半径；每段角差≤π/2，端点矩形凸包按 `r·2sin²(|Δθ|/4)` 作 L∞ 方形外扩。`evaluate()` 以全路径最大半径选角步，避免偏心枢转超出名义矢高比例。正负转角、v2 零角平移、pivot 段间正负滑移及末端横坐标镜像均经接合校验；无效运动不返回面积。
- 统一整数尺度默认为 `2^40`；浮点乘尺度前以整数比值做 floor/ceil、启发式 ulp 垫片，拒绝非有限值与 `|坐标·尺度|≥2^53`，并检查 Clipper 6.4.2 的 `hiRange`。整数凸包并集按孔洞符号和 Python 整数鞋带公式求面积。**只对量化后的整数多边形裁剪是精确的**；整个输入运动的 `numeric_outer_area` 仍是数值近似。
- `evaluate_keich(5)` 在目标外扩矢高≤0.1ε 与≤0.05ε 的两档角步之间比较；差异>2%、任一失败或预算耗尽时移除面积并返回 `quality_limited`／`resource_limited`／`error`。原生 Clipper 并集不能在进程内部抢占；长跑必须加外部 `timeout`。没有稳定通过这道闸门的面积不得参加排名。

## 首轮回归与边界

`PYTHONDONTWRITEBYTECODE=1 /home/z/.venv/bin/python3 -m unittest -v test_integer_motion_area` 覆盖中心旋转解析圆盘、远距正负滑移、负角、多圈、内点外包、孔洞、矛盾原语和断链、n4/5 资源界。`timeout 180 nice -n 10 /home/z/.venv/bin/python3 integer_motion_area.py --n 5 --max-wall-s 120 --out results/integer_keich_n5_smoke.json` 独立写结果，文件存在时拒绝覆盖。

首次固定尺度 `2^40`：Keich n=4 (`ε=2^-16`) 数值外包约 **1.241886**（984 多边形、0.44 秒）；n=5 (`ε=2^-20`) 数值外包约 **0.940920**（3236 多边形、19.1 秒），更细角步约 0.932155、相差 0.93%。另以 `2^38` 尺度得 n4≈1.241886018、n5≈0.940920748，相对差约 `9.68e-8`、`1.16e-6`。证据在 `results/integer_keich_n{4,5}_{smoke,scale38_smoke}.json`。它们**高于**固定中心约 π/4，也不能从这些尺度判定递推的渐近常数；旧稀疏采样 n4≈0.446 是漏扫诱导的假低，n5 旧 GEOS 则失败。结果不包括发现该理论递推或其他优化族的同预算搜索成本。

## 后续门槛

`motion_adapters.py` 已接入 pivot-slide、历史 smooth 控制点（显式 Nf/Nb 或标记推断等量控制点）、修复镜像轴的 v2 关键帧，`test_motion_adapters.py` 覆盖解析、接点、密采样内点及存档交叉复评。`compare_integer_candidates.py` 对每条**已发现候选**做两档角步×两档整数尺度的四重门槛，全部成功且相对面积分散≤0.5% 才给可比较数值区间；单档存档值不是排名。即使通过也仅比较保存的运动，不等于从零同核时搜索。`results/integer_saved_crossfamily_quality.json` 已完成四条已保存候选的四重闸门：全部 `ok`，相对分散在 0.123%–0.169%。在 ε=.005，pivot K8 区间 [0.367380,0.367921]、smooth K32 [0.344088,0.344669]、修复 v2 K6 [0.374629,0.375177]；ε=.002 当前 smooth K256 [0.311277,0.311661]。区间是**四次数值近似的范围，不是数学置信区间或严格上下界**；三族旧解的发现成本不同或未知，因此只是同后端存档构造对比。修复 v2 **优化目标**、测候选搜索的目标函数成本并预注册独立种子/核时后，才能冻结 `.scratch/01-fat-kakeya-experiment/issues/03-budget-quality-benchmark.md` 的正式排名。可选依赖的版本、MIT 包装层与 Boost 1.0 内核许可及安装命令见 `WORKSPACE.md`。
