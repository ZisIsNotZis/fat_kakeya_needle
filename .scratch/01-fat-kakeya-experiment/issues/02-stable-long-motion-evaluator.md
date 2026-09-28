# 02 — 稳定的远距细针连续扫掠评估器

Status: claimed
Need-review: yes
Need-test-cases: yes
Blocked by: none

## 目标
把 `keich_motion.py` 的连续 slide/center_rotate 原语、现有 pivot-slide 和修复接缝后的 v2 运动放到一个能处理细针与远距中心的数值几何评分口径；不得把近似浮点输出称为严格证书。当前 `probe_keich_demo.py` 在 n=4 的 sampled≈0.446 与 numerical_outer≈1.271 差距过大，n=5 GEOS 并集拓扑失败，属于必须先复现并解决的回归。

## 验收
- 统一原语路径与有效性：轴向滑移全条带、固定中心弧经解析矢高保守外包、v2 线性段及镜像接缝；不因平移中心很远或 eps 很小而产生虚假低值。
- 通过 K=1 中心旋转解析面积、正/负滑移、嵌套角采样、v2 末端轴、Keich n=4/5 的有界运行。n=5 可以明确给出质量/资源限制而不是崩溃或假值。
- 评分附输入来源、ε、几何后端/版本、格点缩放、分辨率、壁钟/CPU 时间和浮点误差边界性质；独立验证复现关键值。
- 不改写旧 results；若加入可选依赖，核验许可、版本、安装与快速开始，避免污染共享服务。测试、`git diff --check`、独立 fresh review 通过才集成。

## 方案与门槛
先并行只读设计：比较现有 GEOS 精度网格、整数 polygon clipping（如 pyclipper）和自适应有理网格在 n=5 的性能/面积偏差。以单核 nice10 的短冒烟先证实后端可用；再只实现一条最小可行评分路径。若任何方法在 ε=2^-20 的长距薄条上无法给出可解释保守误差，记录资源/表示边界，不开始预算排名。

## Comments
- 2026-09-28 19:50 +08 (agent): 用户确认自动推进；从 `WORKSPACE.md`、`docs/philosophy.md`、01 票据及 master@c5f7e17 重启。主仓库四个 `.pi-glla` 跟踪运行态文件删除仍在，来源不明，保留不恢复/不提交。已验证当前 venv 无 pyclipper。下一步只读专门设计与后端风险审查。
