<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-06-18.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速评判

`ministral-3:14b` 是一个在 24GB RTX 3090 上运行的**中等速度**通用模型（79.2 tok/s）。对于批处理或离线工作负载，它值得在本地进行测试。对于实时交互使用，在投入使用前，请使用您典型的提示长度测量端到端延迟。

`ministral-3:14b` 在标准量化下可轻松适应 24GB 显存。如果您将上下文推至 8K tokens 以上，请监控 VRAM 使用情况。在当前测量的 RTX 3090 模型中，它的吞吐量排名**18个模型中的第6位**。下一个更快的模型是 `qwen2.5:14b`（84.0 tok/s，快 6%）。下一个更慢的模型是 `deepseek-r1:14b`（74.4 tok/s，慢 7%）。

日常目标很简单：帮助 3090 拥有者决定今晚下载什么，哪些可以跳过，以及何时云端备用方案能更好地利用时间。

## 今日精选

- **模型：** `ministral-3:14b`
- **类别：** 通用
- **尺寸级别：** 中等
- **性能级别：** 中等
- **RTX 3090 速度：** 79.2 tok/s
- **延迟：** 2047 毫秒
- **测试时间：** 2026-06-17T07:31:11Z
- **基准命令：**

```bash
ollama run ministral-3:14b
```

## 谁应该尝试

- RTX 3090 拥有者，决定今晚是否下载 `ministral-3:14b` 进行本地实验。
- 在确定工作流程之前，比较本地推理速度与云租赁（RunPod, Vast）的用户。
- 任何正在构建本地 LLM 工具箱，并希望获得该模型经过验证的基准的人。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载需要在并发情况下具有可预测的 p95 延迟的团队。
- 8GB/12GB GPU 拥有者，除非存在更小的量化变体。

## 注意事项

- **工作负载特定测试**：通用基准测试不能保证在您的特定用例中表现良好。
- **上下文长度**：在假设生产就绪之前，请务必在目标上下文长度下进行测试。
- **量化权衡**：较低的量化可节省 VRAM，但可能会降低细微任务的输出质量。

## 经验证的基准锚点

- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3-coder:30b`: 140.5 tok/s | latency 935 ms | test 2026-06-17T07:31:11Z
- `qwen3:8b`: 121.7 tok/s | latency 1429 ms | test 2026-06-17T07:31:11Z
- `qwen2.5-coder:32b`: 92.2 tok/s | latency 1609 ms | test 2026-06-17T07:31:11Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z

## RTX 3090 决策指南

1.  **批处理是最佳选择**：`ministral-3:14b` 最适合离线/批处理作业，在这些作业中，吞吐量比单次延迟更重要。
2.  **在您的上下文长度下进行测试**：中等速度模型在较长上下文下可能会显著变慢。
3.  **量化选择很重要**：从 Q8 切换到 Q4 可以提高速度，但请首先测试质量下降情况。
4.  **云端备用计划**：如果本地延迟未达到您的目标，请使用 RunPod/Vast 进行时间敏感的运行。

## 待验证的比较

- `ministral-3:14b` 与基准测试源中下一个最快和下一个最慢的模型进行比较。
- `ministral-3:14b` 与 `qwen3:8b` — 相同尺寸级别，79 对 122 tok/s。
- `ministral-3:14b` 本地功耗成本与相同工作负载的 A100 租赁成本进行比较。

## 后续行动

- 估算 VRAM 适应性：/en/tools/vram-calculator/
- 模型页面：/en/models/ministral-3-14b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云端备用：/go/runpod 和 /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，而您无需支付额外费用。
