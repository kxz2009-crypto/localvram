<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-04-06.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 今天有什么变化

本次更新整合了最新验证的本地推理测量结果，并将其转化为实际的部署决策。

## 验证基准锚点

- `qwen3-coder:30b`: 153.4 tok/s | 延迟 961 ms | 测试 2026-04-01T11:53:50Z
- `qwen3:8b`: 125.7 tok/s | 延迟 1554 ms | 测试 2026-04-01T11:53:50Z
- `ministral-3:14b`: 82.7 tok/s | 延迟 2390 ms | 测试 2026-04-01T11:53:50Z
- `deepseek-r1:14b`: 80.2 tok/s | 延迟 2027 ms | 测试 2026-04-01T11:53:50Z
- `qwen2.5:14b`: 77.7 tok/s | 延迟 1072 ms | 测试 2026-04-01T11:53:50Z

## 决策指南

1.  如果您的目标模型在 VRAM 中有足够的余量，优先选择本地部署以获得可预测的延迟和更低的长期成本。
2.  如果 p95 延迟或吞吐量未能达到生产目标，将本地部署作为基线，仅在高峰期才突发到云端。
3.  如果故障率上升（OOM/重试次数激增），在横向扩展之前，请降低量化级别或减少并发负载。

## 操作清单

- 在代表性提示长度下验证 tokens/s 和延迟。
- 按模型和量化级别跟踪 OOM 和重试次数。
- 每周重新计算本地硬件与云租赁的盈亏平衡点。

## 后续行动

- 估算适配性: /en/tools/vram-calculator/
- 硬件路径: /en/affiliate/hardware-upgrade/
- 云端备用: /go/runpod and /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
