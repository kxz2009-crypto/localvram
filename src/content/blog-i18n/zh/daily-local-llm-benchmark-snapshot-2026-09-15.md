<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-09-15.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速判断

`mistral-small:22b` 是一个在 24GB VRAM 上运行的**重型**模型 (5.5 tok/s)。它最适合离线批处理、概念验证或云回退场景。在尝试交互式使用之前，请减少上下文或降低量化级别。

`mistral-small:22b` 在更高量化级别下接近 24GB 边界。如果您在 RTX 3090 上需要上下文余量，请考虑 Q4 或 Q5。在目前测量的 RTX 3090 模型中，其吞吐量排名**18个模型中的第14位**。下一个更快的模型是 `gemma3:27b` (5.5 tok/s，快 0%)。下一个更慢的模型是 `qwen3.5:122b` (4.9 tok/s，慢 11%)。

日常目标很简单：帮助 3090 拥有者决定今晚下载什么、跳过什么，以及何时云回退是更好的时间利用方式。

## 今日精选

- **模型：** `mistral-small:22b`
- **类别：** 通用
- **大小级别：** 大型
- **性能级别：** 重型
- **RTX 3090 速度：** 5.5 tok/s
- **延迟：** 16300 毫秒
- **测试时间：** 2026-09-09T07:21:06Z
- **基准命令：**

```bash
ollama run mistral-small:22b
```

## 谁应该尝试

- 正在决定今晚是否下载 `mistral-small:22b` 进行本地实验的 RTX 3090 拥有者。
- 在确定工作流程之前，将本地推理速度与云租赁（RunPod, Vast）进行比较的用户。
- 任何正在构建本地 LLM 工具箱并希望获得此模型验证基准的用户。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载要求在并发下具有可预测的 p95 延迟的团队。
- 8GB/12GB GPU 拥有者，除非存在更小量化变体。

## 注意事项

- **工作负载特定测试**：通用基准测试不能保证在您的特定用例中表现良好。
- **上下文长度**：在假定生产就绪之前，请务必在您的目标上下文长度下进行测试。
- **量化权衡**：较低的量化级别可以节省 VRAM，但可能会降低在细致任务上的输出质量。

## 验证基准锚点

- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3-coder:30b`: 84.4 tok/s | latency 7842 ms | test 2026-09-09T07:21:06Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z
- `nemotron-3-nano:30b`: 57.0 tok/s | latency 2468 ms | test 2026-04-01T11:53:50Z
- `deepseek-r1:14b`: 52.9 tok/s | latency 2724 ms | test 2026-09-09T07:21:06Z

## RTX 3090 决策指南

1.  **云服务可能更优**：在 24GB 上以 5.5 tok/s 的速度运行，`mistral-small:22b` 在 RunPod 或 Vast 上可能更具成本效益。
2.  **积极缩减**：降至 Q4 或 IQ4 并最小化上下文以适应 VRAM。
3.  **仅限离线**：不要依赖此模型进行交互式或实时本地工作负载。
4.  **硬件路径**：如果您每天运行此大小的模型，请考虑多 GPU 或云作为永久解决方案。

## 待验证的比较

- `mistral-small:22b` 与基准测试源中下一个最快和下一个最慢的模型进行比较。
- `mistral-small:22b` 与 `gpt-oss:20b` — 相同大小级别，5 tok/s 对比 156 tok/s。
- `mistral-small:22b` 的本地功耗成本与相同工作负载下 A100 租赁成本的比较。

## 后续行动

- 估算 VRAM 适用性：/en/tools/vram-calculator/
- 模型页面：/en/models/mistral-small-22b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云回退：/go/runpod and /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，而您无需支付额外费用。
