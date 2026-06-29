<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-06-29.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速结论

`ministral-3:14b` 是一个在 24GB VRAM 上运行的**重量级**模型（7.4 tok/s）。它最适合离线批处理、概念验证或云端备用方案。在尝试交互式使用之前，请减少上下文或降低量化等级。

`ministral-3:14b` 在标准量化下可轻松适应 24GB VRAM。如果将上下文推至超过 8K tokens，请监控 VRAM 使用情况。在当前测量的 RTX 3090 模型中，其吞吐量排名**第 11 位（共 18 个）**。下一个更快的模型是 `deepseek-r1:14b`（7.5 tok/s，快 1%）。下一个更慢的模型是 `llama4:16x17b`（5.6 tok/s，慢 32%）。

日常目标很简单：帮助 RTX 3090 用户决定今晚下载什么、跳过什么，以及何时云端备用方案是更明智的时间利用方式。

## 今日推荐

- **模型：** `ministral-3:14b`
- **类别：** 通用型
- **大小层级：** 中等
- **性能层级：** 重量级
- **RTX 3090 速度：** 7.4 tok/s
- **延迟：** 18155 ms
- **测试时间：** 2026-06-24T06:22:37Z
- **基准命令：**

```bash
ollama run ministral-3:14b
```

## 谁应该尝试

- RTX 3090 用户，决定今晚是否下载 `ministral-3:14b` 进行本地实验。
- 用户在确定工作流程前，比较本地推理速度与云端租赁（RunPod, Vast）。
- 任何正在构建本地 LLM 工具箱，并希望获得此模型经过验证的基准的人。

## 谁应该跳过

- 需要长上下文生产稳定性，且尚未验证持续运行的用户。
- 工作负载要求在并发下具有可预测的 p95 延迟的团队。
- 8GB/12GB GPU 用户，除非存在更小的量化变体。

## 注意事项

- **工作负载特定测试**：通用基准测试不保证在您的特定用例上的性能。
- **上下文长度**：在假定可用于生产之前，始终在您的目标上下文长度下进行测试。
- **量化权衡**：较低的量化等级节省 VRAM，但可能会降低在细致任务上的输出质量。

## 已验证的基准锚点

- `gpt-oss:20b`: 156.1 tok/s | 延迟 1524 ms | 测试 2026-04-29T05:39:58Z
- `qwen2.5:14b`: 84.0 tok/s | 延迟 946 ms | 测试 2026-04-29T05:39:58Z
- `nemotron-3-nano:30b`: 57.0 tok/s | 延迟 2468 ms | 测试 2026-04-01T11:53:50Z
- `translategemma:27b`: 41.3 tok/s | 延迟 3142 ms | 测试 2026-04-01T11:53:50Z
- `qwen3-coder:30b`: 24.9 tok/s | 延迟 3724 ms | 测试 2026-06-24T06:22:37Z

## RTX 3090 决策指南

1.  **云端可能更优**：在 24GB 上以 7.4 tok/s 的速度运行，`ministral-3:14b` 在 RunPod 或 Vast 上可能更具成本效益。
2.  **积极降低**：降至 Q4 或 IQ4，并最小化上下文以适应 VRAM。
3.  **仅限离线使用**：不要依赖此模型进行交互式或实时本地工作负载。
4.  **硬件方案**：如果您每天运行此尺寸的模型，请考虑多 GPU 或云端作为永久解决方案。

## 待验证的比较

- `ministral-3:14b` 与基准测试源中下一个最快和下一个最慢的模型进行比较。
- `ministral-3:14b` 与 `qwen2.5:14b` — 相同大小层级，7 vs 84 tok/s。
- `ministral-3:14b` 本地功耗成本与 A100 租赁相同工作负载的比较。

## 后续操作

- 估算 VRAM 适应性：/en/tools/vram-calculator/
- 模型页面：/en/models/ministral-3-14b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件方案：/en/affiliate/hardware-upgrade/
- 云端备用：/go/runpod 和 /go/vast

联盟披露：此文章可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
