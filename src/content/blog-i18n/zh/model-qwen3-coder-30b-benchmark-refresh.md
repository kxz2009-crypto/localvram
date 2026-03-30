<!--
auto-translated from src/content/blog/model-qwen3-coder-30b-benchmark-refresh.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 决策背景

本草稿旨在解决查询 "qwen3-coder:30b local inference benchmark update"，并应帮助读者今天做出具体的部署或扩展决策。

## 测量的锚定数据

- `gpt-oss:20b`: 166.0 tok/s (延迟 1256 ms, 测试 2026-03-15T12:17:40Z)
- `qwen3-coder:30b`: 159.9 tok/s (延迟 999 ms, 测试 2026-03-11T04:17:51Z)
- `qwen3:8b`: 137.2 tok/s (延迟 1488 ms, 测试 2026-03-15T12:17:40Z)

## 本文必须回答的问题

- 首先报告测量的吞吐量/延迟，然后解释硬件瓶颈。
- 定义故障边界 (VRAM 限制、延迟目标或稳定性阈值)。
- 包含一个经过验证的本地路径和一个云备用路径。
- 最后提出按工作负载大小的可操作建议。

## 编辑大纲 (草稿)

1. 问题框架和目标工作负载。
2. 基准证据和解释。
3. 本地和云选项之间的成本/风险比较。
4. 最终建议附带下一步清单。

## 需包含的内部链接

- VRAM calculator: /en/tools/vram-calculator/
- 相关着陆页: /en/models/
- 本地硬件路径: /en/affiliate/hardware-upgrade/
- 云备用方案: /go/runpod and /go/vast

## 变现位置 (合规)

- 联盟披露: 本草稿可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
- 将披露行放置在 CTA 模块附近。
- 使用一个本地推荐 CTA 和一个云备用 CTA。
- 保持措辞事实性：测量值与估计值必须明确区分。
