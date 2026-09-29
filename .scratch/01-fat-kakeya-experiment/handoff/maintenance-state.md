# 维护态交接（2026-09-29）

- 状态：v3 终局判定 2/3 达成，项目进入维护态（docs/philosophy.md §六）。
- 头条结论三层：
  1. 严格定理：自由连续运动 f(ε)=Θ(1/log(1/ε))（Keich 1999 + bridge）；固定剖面迁移规则不趋零（正下限定理）。
  2. 严格上界（可复算证书）：ε=.05→0.547974；ε=.002→0.321083；ε=.005 网格胜者→3203055/8388608≈0.381834。
  3. 数值估计：正式 48 格协议 A 标度律，smooth q∞=0.3442≈存档最优；B=480 族间差距 6.1%（未收敛信号）；票 04：理论转场在可计算尺度无增益（40/40 更差）。
- SSOT：docs/philosophy.md（目标）、docs/findings.md（结论）、docs/budget-quality-scaling.md（标度律）、docs/rational-pivot-certificate.md（证书）、docs/methodology.md（教训）。
- 重启条件：质疑任一证书，或决定做 ε 扫描（预算 5–10 倍本轮，约 10+ CPU 小时/格族）。
- 基础设施可复用：integer_motion_area.py（评估器）、budget_total_integer.py（协议 A runner）、aggregate_total_budget.py（聚合器，12 测试）、rational_pivot_certificate.py（证书）、run_budget_total_grid.sh（网格驱动）。
- 已知未决：四个 .pi-glla 文件的来源不明删除保持原状；两个旧 pi-subagents worktree（301a924、bf65cb6）未清理；票 01/02 已闭，03 已闭（条件 1 搁置项记录在案），04 已闭。
