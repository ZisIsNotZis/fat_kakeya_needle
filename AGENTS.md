# AGENTS.md — fat_kakeya_needle 项目约定

## 语言

- 与用户对话、报告、总结一律使用**简体中文**。
- 代码、代码注释、commit message、results/ 里的 JSON 字段保持英文
  （机器消费 + 通用惯例）；面向用户的文档（README、docs/）用中文。

## 等待策略（autonomous 模式）

- 自动唤醒（bg_run watcher 通知）不可靠，多次失败。自主研究等待长任务
  （>30min）时，用**前台 `sleep N` 轮询**（如 `sleep 3600 && tail log`），
  这是唯一可靠的等待方式。轮询间隔 = 任务预期时长 / 3，单次 bash 调用
  带 timeout 参数覆盖 sleep+检查。等待前先把状态写进 docs（SSOT），
  确保任何中断后可从文档恢复。

## 项目性质

数值实验项目：研究 1×ε 细长矩形针在完全自由平面运动（平移+旋转）
下旋转 180° 的最小扫掠面积 f(ε)。详见 docs/findings.md。

## 项目哲学

目标与哲学的 SSOT 在 docs/philosophy.md（v3：不证明也不寻找真
minimum，只论证"按此方法能找到"——budget→quality 标度关系）。
报告数值时必须区分三层：数值估计 / 经验上界 / 严格定理。
