<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-09-12.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速评判

`ministral-3:14b` 在 24GB RTX 3090 上以 **15.4 tok/s** 的速度运行 — 属于“审慎”范围。该模型优先考虑质量或参数数量而非原始速度。建议首先在离线或后台任务中测试它，如果交互响应时间很重要，请考虑使用更小的量化版本。

`ministral-3:14b` 在标准量化下可轻松适应 24GB 显存。如果您将上下文推至 8K tokens 以上，请监控 VRAM 使用情况。在此 RTX 3090 上当前测量的模型中，它的吞吐量排名 **18 个模型中的第 9 位**。下一个更快的模型是 `qwq:32b` (26.1 tok/s，快 70%)。下一个更慢的模型是 `glm-4.7-flash:bf16` (11.2 tok/s，慢 37%)。

每日目标很简单：帮助 3090 显卡用户决定今晚下载什么、跳过什么，以及何时云端回退是更好的时间利用方式。

## 今日之选

- **模型：** `ministral-3:14b`
- **类别：** 通用
- **大小层级：** 中等
- **性能层级：** 审慎
- **RTX 3090 速度：** 15.4 tok/s
- **延迟：** 8563 毫秒
- **测试时间：** 2026-09-09T07:21:06Z
- **基准命令：**

```bash
ollama run ministral-3:14b
```

## 谁应该尝试

- 正在决定今晚是否下载 `ministral-3:14b` 进行本地实验的 RTX 3090 用户。
- 在确定工作流程之前，将本地推理速度与云租赁（RunPod, Vast）进行比较的用户。
- 任何正在构建本地 LLM 工具箱并希望获得该模型验证基准的用户。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载要求在并发下具有可预测的 p95 延迟的团队。
- 8GB/12GB GPU 用户，除非存在更小的量化版本。
## 注意事项

- **工作负载特定测试**：通用基准测试不能保证在您的特定用例中表现良好。
- **上下文长度**：在假定生产就绪之前，务必在您的目标上下文长度下进行测试。
- **量化权衡**：较低的量化可节省 VRAM，但可能会降低在细致任务上的输出质量。

## 已验证的基准锚点

- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3-coder:30b`: 84.4 tok/s | latency 7842 ms | test 2026-09-09T07:21:06Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z
- `nemotron-3-nano:30b`: 57.0 tok/s | latency 2468 ms | test 2026-04-01T11:53:50Z
- `deepseek-r1:14b`: 52.9 tok/s | latency 2724 ms | test 2026-09-09T07:21:06Z

## RTX 3090 决策指南

1.  **离线优先**：将 `ministral-3:14b` 优先用于计划的批量推理、研究或验证工作流程。
2.  **上下文是瓶颈**：将上下文长度缩减到任务所需的最小可行长度。
3.  **购买硬件前先量化**：Q4 或 Q5 可能使其在 24GB 上可行，而 Q8 则不可行。
4.  **交互式任务选择云端**：如果需要实时响应，请将 `ministral-3:14b` 视为云端回退的备选方案。

## 待验证的比较

- `ministral-3:14b` 与基准测试中下一个最快和下一个最慢的模型进行比较。
- `ministral-3:14b` 与 `qwen2.5:14b` — 相同大小层级，15 tok/s 对比 84 tok/s。
- `ministral-3:14b` 本地功耗成本与相同工作负载下 A100 租赁成本的比较。

## 后续操作

- 估算 VRAM 适配：/en/tools/vram-calculator/
- 模型页面：/en/models/ministral-3-14b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云端回退：/go/runpod 和 /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，而您无需支付额外费用。
