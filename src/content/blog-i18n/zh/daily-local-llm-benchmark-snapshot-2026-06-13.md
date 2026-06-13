<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-06-13.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速评判

`nemotron-3-nano:30b` 是一个在 24GB RTX 3090 上运行的**中等速度**通用模型 (57.0 tok/s)。值得在本地测试，用于批处理或离线工作负载。对于实时交互使用，在投入使用前，请使用您典型的提示长度测量端到端延迟。

`nemotron-3-nano:30b` 在更高量化级别下接近 24GB 边界。如果您在 RTX 3090 上需要上下文余量，请考虑 Q4 或 Q5。在此 RTX 3090 上当前测量的模型中，其吞吐量排名**第 9 位（共 18 个）**。下一个更快的模型是 `mistral-small:22b` (57.4 tok/s，快 1%)。下一个更慢的模型是 `translategemma:27b` (41.3 tok/s，慢 38%)。

每日目标很简单：帮助 3090 拥有者决定今晚下载什么、跳过什么，以及何时云端备用是更好的时间利用方式。

## 今日精选

- **模型：** `nemotron-3-nano:30b`
- **类别：** 通用
- **大小级别：** 大型
- **性能级别：** 中等
- **RTX 3090 速度：** 57.0 tok/s
- **延迟：** 2468 毫秒
- **测试时间：** 2026-04-01T11:53:50Z
- **基准命令：**

```bash
ollama run nemotron-3-nano:30b
```

## 谁应该尝试

- 正在决定今晚是否下载 `nemotron-3-nano:30b` 进行本地实验的 RTX 3090 拥有者。
- 在确定工作流程之前，将本地推理速度与云租赁（RunPod, Vast）进行比较的用户。
- 任何正在构建本地 LLM 工具箱并希望获得此模型验证基准的用户。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载在并发下需要可预测的 p95 延迟的团队。
- 8GB/12GB GPU 拥有者，除非存在更小的量化变体。

## 注意事项

- **工作负载特定测试**：通用基准测试不能保证在您的特定用例中表现良好。
- **上下文长度**：在假定生产就绪之前，请务必在您的目标上下文长度下进行测试。
- **量化权衡**：较低的量化级别可以节省 VRAM，但可能会降低在细致任务上的输出质量。

## 验证基准锚点

- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3-coder:30b`: 144.7 tok/s | latency 936 ms | test 2026-06-10T06:45:58Z
- `qwen3:8b`: 124.6 tok/s | latency 1389 ms | test 2026-06-10T06:45:58Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z
- `ministral-3:14b`: 82.0 tok/s | latency 1960 ms | test 2026-06-10T06:45:58Z

## RTX 3090 决策指南

1.  **批处理是最佳选择**：nemotron-3-nano:30b 最适合离线/批处理作业，在这些作业中，吞吐量比单次延迟更重要。
2.  **在您的上下文长度下进行测试**：中等速度模型在较长的上下文下可能会显著变慢。
3.  **量化选择很重要**：从 Q8 切换到 Q4 可以提高速度，但请首先测试质量下降情况。
4.  **云端备用方案**：如果本地延迟未达到您的目标，请使用 RunPod/Vast 进行时间敏感的运行。

## 待验证比较

- `nemotron-3-nano:30b` 与基准测试源中下一个最快和下一个最慢的模型进行比较。
- `nemotron-3-nano:30b` 与 `gpt-oss:20b` — 相同大小级别，57 tok/s 对比 156 tok/s。
- `nemotron-3-nano:30b` 本地功耗成本与相同工作负载下 A100 租赁成本的比较。

## 后续行动

- 估算 VRAM 适配：/en/tools/vram-calculator/
- 模型页面：/en/models/nemotron-3-nano-30b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云端备用：/go/runpod 和 /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，而您无需支付额外费用。
