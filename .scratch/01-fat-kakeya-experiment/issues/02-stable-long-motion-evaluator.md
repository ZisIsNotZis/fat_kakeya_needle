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
- 2026-09-28 19:50 +08 (agent): 用户确认自动推进；从 `WORKSPACE.md`、`docs/philosophy.md`、01 票据及 master@c5f7e17 重启。主仓库四个 `.pi-glla` 跟踪运行态文件删除仍在，来源不明，保留不恢复/不提交。已验证当前 venv 无 pyclipper。
- 2026-09-28 20:00 +08 (agent): 双只读设计/风险工作流 477a5edf-7533-4737-a23e-500cc96f6d48：推荐最小可选整数裁剪后端，先对 Keich n4/5 连续 slide/center_rotate 保守浮点外包做质量门槛，再加 pivot/v2 适配；整数裁剪只对输入整数多边形精确，不构成浮点运动严格证书。风险审查要求高远坐标范围/浮点乘尺度安全检查、显式正负滑移整条带、圆弧端点凸包+L∞方形外扩、孔洞面积处理、n5 双角分辨率≤2% 差异或标 `quality_limited`。设计阶段已由 PyPI API 识别 `pyclipper 1.4.0` CPython3.12 manylinux wheel、MIT 许可；下载 sdist SHA256 9882bd889f27da78add4dd6f881d25697efc740bf840274e749988d25496c8e1，检查 LICENSE MIT、捆绑 Clipper 6.4.2 头注 Boost 1.0、头文件 hiRange=0x3FFFFFFFFFFFFFFF。`uv pip install --python /home/z/.venv/bin/python3 pyclipper==1.4.0` exit0，import/version/simple-union 冒烟成功，已记录 WORKSPACE。独立工作树 `/home/z/vibe/worktrees/fat_kakeya_needle/agent-02-int-geom-source` 从 master@94cb466 创建、工作树干净、仅一 writer；async workflow b466f6ec-2e50-494b-9c46-78bf43c51367 已串行安排 worker 实现 Keich n4/5 窄版整数并集/矢高外包、fresh reviewer 复核，30min 截止。安全整数尺度起点 2^40（n5 最大坐标约1025→整数1.13e15，仍低于2^53），超范围明确拒绝；后续适配其他族前不排名。writer 2d5022d7-2404-4b4f-b3e2-89292ebbce36 提交 1d97ec7 实现新 `integer_motion_area.py`/测试，n4/5 首轮冒烟可执行；串行独立 reviewer 79adbac9-6e38-41f2-b9a6-01a7c26a6ae5 判 BLOCK：不校验 `length`/`angle` 与端点、原语链不连续也能返回虚低；公开角外包在整圈 max_step=4π 时矢高周期性归零。父会话仅在专用工作树修正：长度/角度一致与严格接点检查、单弧≤π/2，增加矛盾长度/角度/断链及 ±4π 回归；11 项后端测试 exit0、diff check 通过，修复提交 62017fc。fresh reviewer 648b807e-c1b8-40a6-aa03-ce6e1578f3c1 正进行最终复核；后台 task be68087df exit0：n4 数值外包 1.2418858977（0.44s，984 多边形），n5 0.9409196524（19.1s，3236 多边形），n5 加密角步 0.9321554594、相对差 0.9314% <2%，无 GEOS 崩溃；均高于固定中心≈0.785，不可宣称本理论族此尺度获胜。整数尺度敏感性 task b39bd1b4d exit0：2^38 下 n4=1.2418860179、n5=0.9409207481，相对 2^40 分别差 9.68e-8/1.16e-6。结果分别落在专用工作树 `results/integer_keich_n{4,5}_{smoke,scale38_smoke}.json`；最终 reviewer 648b807e-c1b8-40a6-aa03-ce6e1578f3c1 对修复后的代码结论 OK，无新阻断。基于 94cb466..62017fc 的限域补丁已应用主仓库并复制四份独立数值结果；主仓库 bg_run b0f7f4214 exit0，51 项整数/几何/证书/运动全量回归和 `git diff --check` 通过。新增 `docs/numerical-motion-evaluator.md` 和 README/WORKSPACE/Keich 文档同步，浮点外包非严格的证据等级写明。PyPI CPython3.12 manylinux x86_64 wheel SHA256 d1f807e2b4760a8e5c6d6b4e8c1d71ef52b7fe1946ff088f4fa41e16a881a5ca，下载对照安装扩展字节相同；临时下载已移除。限域 diff 复读完毕；源码与测试暂存差异 SHA256 e4aee25955df982f790adb005d9f329497100fc9a09c214f559217fef4bb95bd。下一步提交本切片、清理自有工作树，随后实现 pivot/v2 适配；03 预算排名继续阻塞。
