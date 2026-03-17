<!--
auto-translated from src/content/blog/model-qwen3-5-122b-benchmark-refresh.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 决策背景

本草案旨在解决查询 "qwen3.5:122b local inference benchmark update"，并应帮助读者今天做出具体的部署或扩展决策。

## 测量的锚定数据

- `gpt-oss:20b`: 166.0 tok/s (延迟 1256 ms, 测试 2026-03-15T12:17:40Z)
- `qwen3-coder:30b`: 159.9 tok/s (延迟 999 ms, 测试 2026-03-11T04:17:51Z)
- `qwen3:8b`: 137.2 tok/s (延迟 1488 ms, 测试 2026-03-15T12:17:40Z)

## 本文必须回答的问题

- 首先报告测量的吞吐量/延迟，然后解释硬件瓶颈。
- 定义故障边界（VRAM 限制、延迟目标或稳定性阈值）。
- 包括一个经过验证的本地路径和一个云备用路径。
- 最后根据工作负载大小提出可操作的建议。

## 编辑大纲（草案）

1. 问题框架和目标工作负载。
2. 基准证据和解释。
3. 本地和云选项的成本/风险比较。
4. 最终建议及后续步骤清单。

## 要包含的内部链接

- VRAM 计算器: /en/tools/vram-calculator/
- 相关着陆页: /en/models/
- 本地硬件路径: /en/affiliate/hardware-upgrade/
- 云备用: /go/runpod 和 /go/vast

## 变现位置（合规）

- 联盟披露：本草案可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
- 将披露声明放在 CTA 模块附近。
- 使用一个本地推荐 CTA 和一个云备用 CTA。
- 保持措辞事实性：测量值与估计值必须明确。
