<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-06-26.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速评判

`qwen3.6:35b` 是一个在 24GB VRAM 上运行的**重型**模型 (10.6 tok/s)。它最适合离线批处理、概念验证或云端备用场景。在尝试交互式使用之前，请减少上下文或降低量化级别。

`qwen3.6:35b` 在较高量化级别下接近 24GB 边界。如果您需要在 RTX 3090 上获得上下文余量，请考虑 Q4 或 Q5。在此 RTX 3090 上当前测量的模型中，它的吞吐量排名**第 8 位（共 18 个）**。下一个更快的模型是 `glm-4.7-flash:bf16` (11.2 tok/s，快 6%)。下一个更慢的模型是 `qwen2.5-coder:32b` (9.0 tok/s，慢 18%)。

每日目标很简单：帮助 RTX 3090 用户决定今晚下载什么、跳过什么，以及何时云端备用是更好的时间利用方式。

## 今日推荐

-   **模型：** `qwen3.6:35b`
-   **类别：** 通用
-   **大小层级：** 大型
-   **性能层级：** 重型
-   **RTX 3090 速度：** 10.6 tok/s
-   **延迟：** 10242 毫秒
-   **测试时间：** 2026-06-24T06:22:37Z
-   **基准命令：**

```bash
ollama run qwen3.6:35b
```

## 谁应该尝试

-   正在决定今晚是否下载 `qwen3.6:35b` 进行本地实验的 RTX 3090 用户。
-   在确定工作流程之前，比较本地推理速度与云端租赁（RunPod, Vast）的用户。
-   任何正在构建本地 LLM 工具箱并希望获得此模型验证基准的用户。

## 谁应该跳过

-   在持续运行得到验证之前，需要长上下文生产稳定性的用户。
-   工作负载需要在并发下具有可预测的 p95 延迟的团队。
-   8GB/12GB GPU 用户，除非存在更小的量化变体。

## 注意事项

-   **工作负载特定测试**：通用基准测试不能保证在您的特定用例中表现良好。
-   **上下文长度**：在假设生产就绪之前，请务必在您的目标上下文长度下进行测试。
-   **量化权衡**：较低的量化级别可以节省 VRAM，但可能会降低在细致任务上的输出质量。

## 验证基准锚点

-   `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
-   `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z
-   `nemotron-3-nano:30b`: 57.0 tok/s | latency 2468 ms | test 2026-04-01T11:53:50Z
-   `translategemma:27b`: 41.3 tok/s | latency 3142 ms | test 2026-04-01T11:53:50Z
-   `qwen3-coder:30b`: 24.9 tok/s | latency 3724 ms | test 2026-06-24T06:22:37Z

## RTX 3090 决策指南

1.  **云端可能更优**：在 24GB 上以 10.6 tok/s 的速度运行，`qwen3.6:35b` 在 RunPod 或 Vast 上可能更具成本效益。
2.  **积极缩减**：降至 Q4 或 IQ4 并最小化上下文以适应 VRAM。
3.  **仅限离线**：不要依赖此模型进行交互式或实时本地工作负载。
4.  **硬件路径**：如果您每天运行此大小的模型，请考虑多 GPU 或云端作为永久解决方案。

## 待验证比较

-   `qwen3.6:35b` 与基准测试源中下一个最快和下一个最慢的模型进行比较。
-   `qwen3.6:35b` 与 `gpt-oss:20b` — 相同大小层级，11 vs 156 tok/s。
-   `qwen3.6:35b` 本地功耗成本与相同工作负载的 A100 租赁成本比较。

## 后续行动

-   估算 VRAM 适配：/en/tools/vram-calculator/
-   模型页面：/en/models/qwen36-35b-q4/
-   基准测试更新日志：/en/benchmarks/changelog/
-   本地硬件路径：/en/affiliate/hardware-upgrade/
-   云端备用：/go/runpod 和 /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，您无需支付额外费用。
