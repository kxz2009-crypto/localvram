<!--
auto-translated from src/content/blog/daily-local-llm-benchmark-snapshot-2026-05-24.md
target-locale: zh
status: machine-translated via gemini (human review recommended)
-->

## 快速结论

如果您想在24GB RTX 3090上获得快速的本地基准，请首先下载`qwen3-coder:30b`。

每日目标很简单：帮助3090拥有者决定今晚下载什么、跳过什么，以及何时云端回退是更明智的时间利用。本页面不是一个通用的更新日志；它是一份基于最新验证的LocalVRAM基准测试反馈构建的实用决策说明。

## 今日精选

- 模型：`qwen3-coder:30b`
- RTX 3090 速度：157.8 tok/s
- 延迟：845 ms
- 测试时间：2026-05-20T06:24:07Z
- 基准命令：

```bash
ollama run qwen3-coder:30b
```

## 谁应该尝试

- 希望为`qwen3-coder:30b`获得全新24GB RTX 3090基准的开发者和本地AI用户。
- 在花费云积分之前，将本地速度与RunPod/Vast进行比较的读者。
- 任何决定新的Ollama模型是否值得在最初的24-48小时流量窗口内下载的人。

## 谁应该跳过

- 在持续运行得到验证之前，需要长上下文生产稳定性的用户。
- 工作负载要求并发下可预测的p95延迟的团队；先在本地验证，然后爆发到云端。
- 8GB/12GB GPU拥有者，除非模型有更小的量化或蒸馏变体。

## 已验证的基准锚点

- `qwen3-coder:30b`: 157.8 tok/s | 延迟 845 ms | 测试 2026-05-20T06:24:07Z
- `gpt-oss:20b`: 156.1 tok/s | 延迟 1524 ms | 测试 2026-04-29T05:39:58Z
- `qwen3:8b`: 133.3 tok/s | 延迟 1306 ms | 测试 2026-05-20T06:24:07Z
- `qwen2.5-coder:32b`: 98.5 tok/s | 延迟 1532 ms | 测试 2026-05-20T06:24:07Z
- `ministral-3:14b`: 85.9 tok/s | 延迟 1892 ms | 测试 2026-05-20T06:24:07Z

## 3090 决策指南

1.  如果模型在VRAM中有余量且响应时间可接受，请首先在本地运行它。
2.  如果它能适应但未能达到p95延迟，请保留本地机器进行验证，并在高峰期爆发到云端。
3.  如果出现OOMs，请在购买硬件之前减少上下文或量化。
4.  如果新的Ollama版本正在流行，请尽早发布预估页面，并在24-48小时内用验证过的3090数据更新它。

## 接下来要运行的比较提示

- `qwen3-coder:30b` 与当前编码基准的比较。
- `qwen3-coder:30b` 与最佳14B/20B快速本地模型的比较。
- `qwen3-coder:30b` 本地功耗成本与相同工作负载下A100租赁成本的比较。

## 后续行动

- 估算适配：/en/tools/vram-calculator/
- 模型页面：/en/models/qwen3-coder-30b-q4/
- 基准更新日志：/en/benchmarks/changelog/
- 硬件路径：/en/affiliate/hardware-upgrade/
- 云端回退：/go/runpod 和 /go/vast

联盟披露：此帖子可能包含联盟链接。LocalVRAM可能会赚取佣金，而您无需支付额外费用。
