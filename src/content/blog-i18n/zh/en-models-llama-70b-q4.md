<!--
auto-translated from src/content/blog/en-models-llama-70b-q4.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 决策背景

本草稿旨在解决查询 "llama 70b on 3090"，并应帮助读者今天做出具体的部署或扩展决策。

## 测量锚点数据

- `qwen3-coder:30b`: 153.4 tok/s (延迟 961 ms, 测试 2026-04-01T11:53:50Z)
- `qwen3:8b`: 125.7 tok/s (延迟 1554 ms, 测试 2026-04-01T11:53:50Z)
- `ministral-3:14b`: 82.7 tok/s (延迟 2390 ms, 测试 2026-04-01T11:53:50Z)

## 本文必须回答的问题

- 提供一个可重现的设置路径，并附带验证检查点。
- 定义故障边界（VRAM 限制、延迟目标或稳定性阈值）。
- 包含一个经过验证的本地路径和一个云备用路径。
- 最后根据工作负载大小给出可操作的建议。

## 编辑大纲（草稿）

1. 问题框架和目标工作负载。
2. 基准测试证据和解释。
3. 本地和云选项的成本/风险比较。
4. 最终建议和下一步清单。

## 需包含的内部链接

- VRAM 计算器：/en/tools/vram-calculator/
- 相关着陆页：/en/models/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云备用方案：/go/runpod 和 /go/vast

## 盈利放置（合规）

- 联盟披露：本草稿可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
- 将披露声明放在 CTA 模块附近。
- 使用一个本地推荐 CTA 和一个云备用 CTA。
- 保持措辞事实：测量值与估计值必须明确。
