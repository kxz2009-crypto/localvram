<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-08-11.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速评判

`ministral-3:14b` 是一个在 24GB RTX 3090 上运行的**中等速度**通用模型 (79.7 tok/s)。值得在本地测试，适用于批处理或离线工作负载。对于实时交互使用，在投入使用前，请使用您典型的提示长度测量端到端延迟。

`ministral-3:14b` 在标准量化下可轻松适应 24GB VRAM。如果您将上下文推至超过 8K tokens，请监控 VRAM 使用情况。在此 RTX 3090 上当前测量的模型中，其吞吐量排名**18 个模型中的第 5 位**。下一个更快的模型是 `qwen2.5:14b` (84.0 tok/s，快 5%)。下一个更慢的模型是 `deepseek-r1:14b` (74.1 tok/s，慢 8%)。

每日目标很简单：帮助 RTX 3090 用户决定今晚下载什么、跳过什么，以及何时云端备用方案是更好的时间利用方式。

## 今日之选

- **模型：** `ministral-3:14b`
- **类别：** 通用
- **大小级别：** 中等
- **性能级别：** 中等
- **RTX 3090 速度：** 79.7 tok/s
- **延迟：** 2084 毫秒
- **测试时间：** 2026-08-05T05:23:10Z
- **基准命令：**

```bash
ollama run ministral-3:14b
```

## 谁应该尝试

- 正在决定今晚是否下载 `ministral-3:14b` 进行本地实验的 RTX 3090 用户。
- 在确定工作流程之前，将本地推理速度与云租赁（RunPod, Vast）进行比较的用户。
- 任何正在构建本地 LLM 工具箱并希望获得此模型经过验证的基准的用户。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载在并发下需要可预测的 p95 延迟的团队。
- 8GB/12GB GPU 用户，除非存在更小的量化变体。

## 注意事项

- **工作负载特定测试**：通用基准测试不能保证在您的特定用例上的性能。
- **上下文长度**：在假设生产就绪之前，请务必在您的目标上下文长度下进行测试。
- **量化权衡**：较低的量化可节省 VRAM，但可能会降低细致任务的输出质量。

## 经验证的基准锚点

- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3-coder:30b`: 140.1 tok/s | latency 1039 ms | test 2026-08-05T05:23:10Z
- `qwen3:8b`: 120.9 tok/s | latency 1485 ms | test 2026-08-05T05:23:10Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z
- `ministral-3:14b`: 79.7 tok/s | latency 2084 ms | test 2026-08-05T05:23:10Z

## RTX 3090 决策指南

1.  **批处理是最佳选择**：`ministral-3:14b` 最适合离线/批处理作业，在这些作业中，吞吐量比单次延迟更重要。
2.  **在您的上下文长度下进行测试**：中等速度模型在较长的上下文中可能会显著变慢。
3.  **量化选择很重要**：从 Q8 切换到 Q4 可以提高速度，但请首先测试质量下降情况。
4.  **云端备用方案**：如果本地延迟未达到您的目标，请使用 RunPod/Vast 进行时间敏感的运行。

## 待验证的比较

- `ministral-3:14b` 与基准测试源中下一个最快和下一个最慢的模型进行比较。
- `ministral-3:14b` 与 `qwen3:8b` — 相同大小级别，80 tok/s 对比 121 tok/s。
- `ministral-3:14b` 本地功耗成本与相同工作负载的 A100 租赁成本进行比较。

## 后续行动

- 估算 VRAM 适应性：/en/tools/vram-calculator/
- 模型页面：/en/models/ministral-3-14b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云端备用：/go/runpod 和 /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
