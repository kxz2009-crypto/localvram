<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-06-22.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速结论

`nemotron-3-nano:30b` 在 24GB RTX 3090 上是一个**中等速度**的通用模型（57.0 tok/s）。值得在本地测试，适用于批处理或离线工作负载。对于实时交互使用，在投入使用前，请测量您典型提示长度的端到端延迟。

`nemotron-3-nano:30b` 在更高的量化级别下接近 24GB 边界。如果您在 RTX 3090 上需要上下文余量，请考虑 Q4 或 Q5。在当前测量的 RTX 3090 模型中，它在吞吐量方面排名**18个模型中的第8位**。下一个更快的模型是 `deepseek-r1:14b` (74.4 tok/s，快30%)。下一个更慢的模型是 `mistral-small:22b` (54.8 tok/s，慢4%)。

每日目标很简单：帮助 RTX 3090 用户决定今晚下载什么、跳过什么，以及何时使用云端备用方案能更好地利用时间。

## 今日精选

- **模型：** `nemotron-3-nano:30b`
- **类别：** 通用
- **尺寸级别：** 大型
- **性能级别：** 中等
- **RTX 3090 速度：** 57.0 tok/s
- **延迟：** 2468 毫秒
- **测试时间：** 2026-04-01T11:53:50Z
- **基准命令：**

```bash
ollama run nemotron-3-nano:30b
```

## 谁应该尝试

- RTX 3090 用户决定今晚是否下载 `nemotron-3-nano:30b` 进行本地实验。
- 在确定工作流程之前，将本地推理速度与云租赁（RunPod, Vast）进行比较的用户。
- 任何构建本地 LLM 工具箱并希望获得此模型验证基准的用户。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载要求在并发下具有可预测的 p95 延迟的团队。
- 8GB/12GB GPU 用户，除非存在更小的量化变体。

## 注意事项

- **工作负载特定测试**：通用基准测试不能保证在您的特定用例中表现良好。
- **上下文长度**：在假定生产就绪之前，请务必在目标上下文长度下进行测试。
- **量化权衡**：较低的量化级别可以节省 VRAM，但可能会降低细微任务的输出质量。

## 已验证的基准锚点

- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3-coder:30b`: 140.5 tok/s | latency 935 ms | test 2026-06-17T07:31:11Z
- `qwen3:8b`: 121.7 tok/s | latency 1429 ms | test 2026-06-17T07:31:11Z
- `qwen2.5-coder:32b`: 92.2 tok/s | latency 1609 ms | test 2026-06-17T07:31:11Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z

## RTX 3090 决策指南

1.  **批处理是最佳选择**：nemotron-3-nano:30b 最适合离线/批处理作业，在这些作业中，吞吐量比单次延迟更重要。
2.  **在您的上下文长度下进行测试**：中等速度模型在较长的上下文下可能会显著变慢。
3.  **量化选择很重要**：从 Q8 切换到 Q4 可以提高速度，但请首先测试质量下降情况。
4.  **云端备用方案**：如果本地延迟未达到您的目标，请使用 RunPod/Vast 进行时间敏感的运行。

## 待验证的比较

- `nemotron-3-nano:30b` 与基准测试中下一个最快和下一个最慢的模型进行比较。
- `nemotron-3-nano:30b` 与 `gpt-oss:20b` — 相同尺寸级别，57 tok/s 对比 156 tok/s。
- `nemotron-3-nano:30b` 的本地功耗成本与 A100 租赁相同工作负载的成本进行比较。

## 下一步行动

- 估算 VRAM 适用性：/en/tools/vram-calculator/
- 模型页面：/en/models/nemotron-3-nano-30b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云端备用：/go/runpod and /go/vast

联盟披露：本文可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
