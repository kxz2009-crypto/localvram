<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-07-05.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速评判

`qwen2.5-coder:32b` 在 24GB RTX 3090 上以 **38.9 tok/s** 的速度运行——处于审慎范围。该模型优先考虑质量或参数数量，而非原始速度。请先在离线或后台任务中测试它，如果交互响应时间很重要，请考虑使用更小的量化版本。

`qwen2.5-coder:32b` 在更高的量化版本下接近 24GB 边界。如果您在 RTX 3090 上需要上下文余量，请考虑 Q4 或 Q5。在目前于此 RTX 3090 上测量的模型中，其吞吐量排名**18个中的第11位**。下一个更快的模型是 `translategemma:27b` (41.3 tok/s，快6%)。下一个更慢的模型是 `qwen3.6:35b` (34.6 tok/s，慢12%)。

每日目标很简单：帮助 RTX 3090 用户决定今晚下载什么、跳过什么，以及何时云端回退是更好的时间利用方式。

## 今日精选

- **模型：** `qwen2.5-coder:32b`
- **类别：** 编码
- **尺寸级别：** 大型
- **性能级别：** 审慎
- **RTX 3090 速度：** 38.9 tok/s
- **延迟：** 3061 毫秒
- **测试时间：** 2026-07-01T06:49:08Z
- **基准命令：**

```bash
ollama run qwen2.5-coder:32b
```

## 适用人群

- 在本地 RTX 3090 上评估 `qwen2.5-coder:32b` 进行代码补全、重构或智能体编码的开发者。
- 希望拥有私有、离线编码助手，而无需将源代码发送到云 API 的团队。
- 任何将 `qwen2.5-coder:32b` 与 Copilot 或云端编码智能体在延迟和吞吐量方面进行比较的人。

## 不适用人群

- 主要工作负载是长上下文聊天或文档分析而非代码的用户。
- 需要特定编程语言上保证性能的团队；请先使用自己的基准进行测试。
- 8GB/12GB GPU 用户，除非有更小的量化版本可用。

## 注意事项

- **输出质量因语言而异**：在依赖 `qwen2.5-coder:32b` 之前，请先用您的主要语言进行测试。
- **温度敏感性**：编码任务通常在温度为0时表现最佳；更高的值可能会引入错误。
- **上下文窗口**：验证模型在您所需的上下文长度下保持指令遵循的稳定性。

## 已验证的基准锚点

- `qwen3-coder:30b`: 157.6 tok/s | latency 853 ms | test 2026-07-01T06:49:08Z
- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3:8b`: 136.4 tok/s | latency 1281 ms | test 2026-07-01T06:49:08Z
- `ministral-3:14b`: 88.1 tok/s | latency 1860 ms | test 2026-07-01T06:49:08Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z

## RTX 3090 决策指南

1.  **离线优先**：优先将 `qwen2.5-coder:32b` 用于计划的批量推理、研究或验证工作流程。
2.  **上下文是瓶颈**：将上下文减少到任务所需的最小可行长度。
3.  **购买硬件前先量化**：Q4 或 Q5 可能使其在 24GB 上可行，而 Q8 则不可行。
4.  **交互式任务使用云端**：如果需要实时响应，请将 `qwen2.5-coder:32b` 视为云端回退的备选方案。

## 待验证的比较

- `qwen2.5-coder:32b` 与基准测试源中下一个最快和下一个最慢的模型进行比较。
- `qwen2.5-coder:32b` 与 `qwen3-coder:30b` — 相同尺寸级别，39 tok/s 对比 158 tok/s。
- `qwen2.5-coder:32b` 的本地功耗成本与 A100 租用相同工作负载的成本比较。

## 后续操作

- 估算 VRAM 适配：/en/tools/vram-calculator/
- 模型页面：/en/models/qwen25-coder-32b-q4/
- 基准测试更新日志：/en/benchmarks/changelog/
- 本地硬件路径：/en/affiliate/hardware-upgrade/
- 云端回退：/go/runpod and /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，而您无需支付额外费用。
