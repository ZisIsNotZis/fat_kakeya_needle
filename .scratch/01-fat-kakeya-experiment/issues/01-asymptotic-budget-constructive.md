# 01 — 递推构造与预算—质量验证

Status: claimed
Need-review: yes
Need-test-cases: yes
Blocked by: none

## 问题与目标
用户于 2026-09-28 授权自主推进：寻找可随 ε 细化的运动构造或递推，检验小 ε 的理论对数阶，并在明确算力预算与已实现方法集合下作公平数值比较；失败时分析不可收敛、不稳定或给出可验证反例。目标不是声称有限数值证明真 minimum，亦不将有限范围的拟合冒充渐近定理。

## 验收
- 将几何运动的连续性、完整覆盖及面积评估误差分别验证；报告数值估计、经验上界、严格定理三个层次。
- 至少一个分辨率随 ε 增长的构造/递推和跨 ε 测试；若不可行，提供可复核的结构性阻碍并转向替代构造。
- 公平预算对照：事前固定核时或函数调用、硬件并发、随机种子、评估分辨率及比较方法；公布完整结果和命中率，不能断言覆盖一切未知方法。
- 对 ε=0.002 离群及证书机制单独审查；不把浮点 Shapely 计算称为数学严格证明。

## 执行序列
1. 独立核查文献可构造性与现有数字/证书的证据等级；查找有无理论上的固定光滑族渐近障碍。
2. 制定最小可复现实验及评分规则，再运行资源受限的基准；未有明确运行预算时先做短冒烟，不默认占用共享机器整夜。
3. 汇总证据，修正权威文档的矛盾，复核并提交；重大资源或目标取舍才向用户询问。

## Comments
- 2026-09-28 09:42 +08 (agent): 已读取 WORKSPACE.md、philosophy/findings/methodology/research-plan；初始 git master 干净。并行启动文献审查与本地证书/数据独立审查。当前旧记录对光滑族渐近常数的说法是待检验假说，不能直接当作收敛结论。
- 2026-09-28 09:44 +08 (agent): 并行工作流 0e8d0bc1-0d32-4a9d-ba1d-87120718cc9b 的 theory 子任务 99f4e78d-32f6-46f2-a7e1-9c7c36e22086 因 researcher 请求未加载的 web_search/fetch_content/get_search_content/source_check 而失败；按工作流故障规则停止，audit 子任务未完成。工作目录 /home/z/vibe/fat_kakeya_needle、master@19784d1、未启用 worktree。检查工作树发现 CLAUDE.md 符号链接删除（非本任务预期，来源未知），以及本票据未跟踪；未恢复或覆盖该外部变化。
- 2026-09-28 09:50 +08 (agent): 修正配置后的只读工作流 82e853e1-0043-470a-b16f-2319e1576889 成功完成 Designer 几何审查和 reviewer 证据审查。固定 K 枢转族零宽扇形解析下限 π/(8K)；原 pivot 证书映射不对、速度界不适用于非线性段、浮点几何未认证；旧 claimed 小于采样 lower，A_eff 的拟合式实际凹向下。修订文档提交 dcbd16d；用户确认统一 AGENTS.md 后 CLAUDE.md 删除提交 1e8a3b0。
- 2026-09-28 10:15 +08 (agent): 隔离 worker 提交 bf65cb6 经父会话 cherry-pick 成 6db7095；独立 reviewer 06fc75a4-4425-4891-bbe2-d917786f026b 审查已提交 diff，结论 OK with notes、无 P0/P1。父会话重跑 5 项单测与生成器 exit 0。其 P2（README/API 状态过时、缺少局部几何包含和全精度结果回归）已通过 README/docs 同步及 2 项新增测试处理，提交 8344dff；7 项单测通过。旧严格证书仍不可用，新结果为浮点数值包络。
- 2026-09-28 10:30 +08 (agent): 复评发现 GEOS 浮点并集对同一记录在 n_arc 40→80 从 0.3497321 假降至 0.3493582；输入角格点严格嵌套且矩形有效。fixed-grid overlay 后 40→80 为 0.3497321291→0.3497328727。独立 reviewer cc35d4ab-86d0-4a2a-b00e-4f21003c023d 结论 OK with notes；已按 P2 对镜像合并前两操作数贴合、显式 grid_size。8 项单测、生成器、diff check 通过。三次同解 n_arc80 墙钟（含启动）旧 1.37 秒/新 2.16 秒、用户 CPU 旧 2.07/新 2.84 秒；新稳定性约增 58% 墙钟成本，仅供本机局部参考，预算实验须记录实测核时。修复提交 3a97e8b。下一步：校验更广泛几何稳定性；完整递推与公平预算比较尚未做。
- 2026-09-28 10:40 +08 (agent): 直接访问 arXiv:math/0008098 摘要页 HTTP 200，标题为 From rotating needles to stability of waves，作者元数据为 Terence Tao；更正 findings 的 Bourgain 误署。摘要页不等于连续运动同阶证明；WORKSPACE 的旧理论条目改为待核验，提交 e5bab07。
- 2026-09-28 10:45 +08 (agent): 新增 `reevaluate_smooth.py` 对存档最好候选统一 n_sub=160，结果 `results/smooth_revaluation_0005_0002.json`。ε=0.005 的 v3 参数数值 [0.342648889,0.342962359]，优于 smooth_hr 参数 [0.349733275,0.350052995]；历史头条序列表遗漏了更低的旧候选，已修正文档。ε=0.002 参数数值 [0.337849741,0.338215044]，仍缺至少第 3 个 fresh seed。脚本无预算公平性数据，不能外推搜索方法排序，提交 8e3ebed。
- 2026-09-28 10:55 +08 (agent): `budget_pilot.py` 完成冒烟，15/30 核秒、两族×3 seed 的试验进程 exit 0，结果 `results/budget_pilot_0005_K32.json`。审查发现 12 次只有 2 次超过 DE 初始种群评估数（层次族 35、光滑族 65），因此 0.83423/0.82170 vs 1.07879 的最好浮点 upper 不构成方法排名。已补 `population_evals`、`search_started` 元数据；须升预算到至少完整初始种群＋若干代。接下来以 60/120 核秒预算同条件重跑 3 fresh seeds，预计 18 分钟单核 nice=10，逐 seed checkpoint；任何失败保留现有证据。
- 2026-09-28 10:01 +08 (worker): 在隔离分支 `pi-subagents/implementation-cb361d7-1701-s0-t0` 将泛用 strict_upper 改为拒绝，新增针对真实枢轴弧及完整段间滑移的数值包络；端点凸包按角步长和枢轴到角点最大半径加弧矢高，按浮点 Shapely 多边形算面积，绝不宣称数学证书。新增 5 个 unittest（含 K=1 解析圆盘、正负滑移、非中心弧及间断拒绝）；先复现 ImportError 再通过。实际 K=16 ε=.05 n_sub=300 新结果保存在 `results/pivot_numerical_enclosures.json`，lower=0.4722229811、upper=0.4723456522，旧 optimizer_area_estimate=0.471900813 小于 lower，故旧 results/certificates.json 保持未改且不能作为证书。`git diff --check` 通过；已自行重读限域 diff，未发现阻断项，仍待独立复核，不改变本票据整体 claimed 状态。
