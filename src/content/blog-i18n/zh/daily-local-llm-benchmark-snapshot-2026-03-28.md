<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-03-28.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 今日更新

本次更新整合了最新验证的本地推理测量结果，并将其转化为实用的部署决策。

## 已验证的基准锚点

- `gpt-oss:20b`: 166.0 tok/s | 延迟 1256 ms | 测试 2026-03-15T12:17:40Z
- `qwen3-coder:30b`: 159.9 tok/s | 延迟 999 ms | 测试 2026-03-11T04:17:51Z
- `qwen3:8b`: 137.2 tok/s | 延迟 1488 ms | 测试 2026-03-15T12:17:40Z
- `ministral-3:14b`: 89.3 tok/s | 延迟 2087 ms | 测试 2026-03-15T12:17:40Z
- `qwen2.5:14b`: 84.9 tok/s | 延迟 975 ms | 测试 2026-03-11T04:17:51Z

## 决策指南

1.  如果您的目标模型在 VRAM 中有足够的余量，请优先选择本地部署，以获得可预测的延迟和更低的长期成本。
2.  如果 p95 延迟或吞吐量未达到生产目标，请将本地部署作为基线，仅在高峰期突发至云端。
3.  如果故障率上升（OOM/重试次数激增），在横向扩展之前，请降低量化级别或减少并发负载。

## 操作清单

-   在代表性提示长度下验证 tokens/s 和延迟。
-   按模型和量化级别跟踪 OOM 和重试次数。
-   每周重新计算本地硬件与云租赁的盈亏平衡点。

## 后续行动

-   估算适配度：/en/tools/vram-calculator/
-   硬件路径：/en/affiliate/hardware-upgrade/
-   云端备用：/go/runpod 和 /go/vast

联盟披露：本文可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
