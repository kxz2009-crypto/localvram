<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-08-22.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速结论

`mistral-small:22b` 在 24GB RTX 3090 上是一个**中等速度**的通用模型 (59.0 tok/s)。对于批处理或离线工作负载，值得在本地进行测试。对于实时交互使用，在投入使用前，请使用您典型的提示长度测量端到端延迟。

`mistral-small:22b` 在更高量化级别下接近 24GB 边界。如果您在 RTX 3090 上需要上下文余量，请考虑 Q4 或 Q5。在目前测量的 RTX 3090 模型中，它的吞吐量排名**18 个模型中的第 7 位**。下一个更快的模型是 `deepseek-r1:14b` (78.9 tok/s，快 34%)。下一个更慢的模型是 `nemotron-3-nano:30b` (57.0 tok/s，慢 3%)。

每日目标很简单：帮助 3090 拥有者决定今晚下载什么、跳过什么，以及何时云端回退是更好的时间利用方式。

## 今日精选

- **模型：** `mistral-small:22b`
- **类别：** 通用
- **尺寸级别：** 大型
- **性能级别：** 中等
- **RTX 3090 速度：** 59.0 tok/s
- **延迟：** 1890 ms
- **测试时间：** 2026-08-19T03:08:42Z
- **基线命令：**

```bash
ollama run mistral-small:22b
```

## 谁应该尝试

- 正在决定今晚是否下载 `mistral-small:22b` 进行本地实验的 RTX 3090 拥有者。
- 在确定工作流程之前，比较本地推理速度与云租赁（RunPod, Vast）的用户。
- 任何正在构建本地 LLM 工具箱并希望获得此模型验证基线的用户。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载要求在并发下具有可预测的 p95 延迟的团队。
- 8GB/12GB GPU 拥有者，除非存在更小的量化变体。

## 注意事项

- **工作负载特定测试**：通用基准测试不能保证在您的特定用例上的性能。
- **上下文长度**：在假设生产就绪之前，务必在您的目标上下文长度下进行测试。
- **量化权衡**：较低的量化可节省 VRAM，但可能会降低细微任务的输出质量。

## 已验证的基准锚点

- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3-coder:30b`: 151.0 tok/s | latency 1003 ms | test 2026-08-19T03:08:42Z
- `qwen3:8b`: 128.3 tok/s | latency 1404 ms | test 2026-08-19T03:08:42Z
- `ministral-3:14b`: 85.6 tok/s | latency 1963 ms | test 2026-08-19T03:08:42Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z

## RTX 3090 决策指南

1.  **批处理是最佳选择**：`mistral-small:22b` 最适合离线/批处理作业，在这些作业中吞吐量比单次延迟更重要。
2.  **在您的上下文长度下进行测试**：中等速度的模型在较长的上下文中可能会显著变慢。
3.  **量化选择很重要**：从 Q8 切换到 Q4 可以提高速度，但请先测试质量下降情况。
4.  **云端回退计划**：如果本地延迟未达到您的目标，请使用 RunPod/Vast 进行时间敏感的运行。

## 待验证的比较

- `mistral-small:22b` 与基准测试源中下一个最快和下一个最慢的模型进行比较。
- `mistral-small:22b` 与 `gpt-oss:20b` — 相同尺寸级别，59 tok/s 对比 156 tok/s。
- `mistral-small:22b` 本地功耗成本与相同工作负载下 A100 租赁成本的比较。

## 下一步行动

- 估算 VRAM 适用性：/en/tools/vram-calculator/
- 模型页面：/en/models/mistral-small-22b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云端回退：/go/runpod and /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
