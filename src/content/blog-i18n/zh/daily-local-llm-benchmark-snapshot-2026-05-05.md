<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-05-05.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速结论

如果您想在24GB RTX 3090上获得一个快速的本地基准，请首先下载 `qwen3-coder:30b`。

每日目标很简单：帮助3090拥有者决定今晚下载什么、跳过什么，以及何时云端回退是更明智的时间利用。本页面不是一个通用的更新日志；它是一个基于最新验证的 LocalVRAM 基准测试反馈构建的实用决策说明。

## 今日精选

- 模型：`qwen3-coder:30b`
- RTX 3090 速度：160.0 tok/s
- 延迟：835 毫秒
- 测试时间：2026-04-29T05:39:58Z
- 基准命令：

```bash
ollama run qwen3-coder:30b
```

## 谁应该尝试

- 希望为 `qwen3-coder:30b` 获得全新 24GB RTX 3090 基准的开发者和本地 AI 用户。
- 在花费云积分之前，将本地速度与 RunPod/Vast 进行比较的读者。
- 任何决定新的 Ollama 模型是否值得在最初的 24-48 小时流量窗口内下载的人。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载需要在并发下具有可预测的 p95 延迟的团队；先在本地验证，然后突发到云端。
- 8GB/12GB GPU 拥有者，除非模型有更小的量化版本或精简版本。

## 验证过的基准锚点

- `qwen3-coder:30b`：160.0 tok/s | 延迟 835 毫秒 | 测试 2026-04-29T05:39:58Z
- `gpt-oss:20b`：156.1 tok/s | 延迟 1524 毫秒 | 测试 2026-04-29T05:39:58Z
- `qwen3:8b`：135.3 tok/s | 延迟 1270 毫秒 | 测试 2026-04-29T05:39:58Z
- `ministral-3:14b`：87.3 tok/s | 延迟 2253 毫秒 | 测试 2026-04-29T05:39:58Z
- `qwen2.5:14b`：84.0 tok/s | 延迟 946 毫秒 | 测试 2026-04-29T05:39:58Z

## 3090 决策指南

1.  如果模型适合 VRAM 且有余量，并且响应时间可接受，请首先在本地运行。
2.  如果它适合但未达到 p95 延迟，请保留本地机器进行验证，并在高峰期突发到云端。
3.  如果出现 OOMs，请在购买硬件之前减少上下文或量化。
4.  如果有新的 Ollama 版本正在流行，请提前发布预估页面，并在 24-48 小时内用验证过的 3090 数据更新它。

## 接下来要运行的比较提示

- `qwen3-coder:30b` 与当前编码基准的比较。
- `qwen3-coder:30b` 与最佳 14B/20B 快速本地模型的比较。
- `qwen3-coder:30b` 本地功耗成本与相同工作负载下 A100 租用成本的比较。

## 下一步行动

- 估算适配：/en/tools/vram-calculator/
- 模型页面：/en/models/qwen3-coder-30b-q4/
- 基准更新日志：/en/benchmarks/changelog/
- 硬件路径：/en/affiliate/hardware-upgrade/
- 云端回退：/go/runpod 和 /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM 可能会赚取佣金，而您无需支付额外费用。
