---
title: "Today's Local LLM Pick: mistral-small:22b on RTX 3090 (2026)"
description: "Daily 3090 recommendation for mistral-small:22b: moderate performer at 57.9 tok/s, RTX 3090 benchmark data, use-case fit, and local-vs-cloud decision guide."
keyword: "mistral-small:22b rtx 3090 ollama benchmark"
pubDate: 2026-07-12
updatedDate: 2026-07-12
tags: ["ollama", "benchmark", "vram", "latency", "moderate"]
lang: en
intent: benchmark
---

## Fast verdict

`mistral-small:22b` is a **moderate-speed** general-purpose model on a 24GB RTX 3090 (57.9 tok/s). It is worth testing locally for batch or offline workloads. For real-time interactive use, measure end-to-end latency with your typical prompt length before committing.

`mistral-small:22b` approaches the 24GB boundary at higher quantizations. Consider Q4 or Q5 if you need context headroom on the RTX 3090. It ranks **#7 of 18** in throughput among currently measured models on this RTX 3090. The next faster model is `deepseek-r1:14b` (76.6 tok/s, 32% faster). The next slower model is `nemotron-3-nano:30b` (57.0 tok/s, 1% slower).

The daily goal is simple: help a 3090 owner decide what to download tonight, what to skip, and when a cloud fallback is the better use of time.

## Today's pick

- **Model:** `mistral-small:22b`
- **Category:** general-purpose
- **Size tier:** large
- **Performance tier:** moderate
- **RTX 3090 speed:** 57.9 tok/s
- **Latency:** 1841 ms
- **Test time:** 2026-07-08T15:58:01Z
- **Baseline command:**

```bash
ollama run mistral-small:22b
```

## Who should try it

- RTX 3090 owners deciding whether to download `mistral-small:22b` tonight for local experimentation.
- Users comparing local inference speed against cloud rental (RunPod, Vast) before committing to a workflow.
- Anyone building a local LLM toolbox who wants a verified baseline for this model.

## Who should skip it

- Users who need long-context production stability before a sustained run has been verified.
- Teams whose workload requires predictable p95 latency under concurrency.
- 8GB/12GB GPU owners unless a smaller quantized variant exists.
## Watch points

- **Workload-specific testing**: generic benchmarks do not guarantee performance on your particular use case.
- **Context length**: always test at your target context length before assuming production readiness.
- **Quantization trade-off**: lower quantization saves VRAM but may reduce output quality on nuanced tasks.

## Verified benchmark anchors

- `gpt-oss:20b`: 156.1 tok/s | latency 1524 ms | test 2026-04-29T05:39:58Z
- `qwen3-coder:30b`: 149.8 tok/s | latency 897 ms | test 2026-07-08T15:58:01Z
- `qwen3:8b`: 112.7 tok/s | latency 1536 ms | test 2026-07-08T15:58:01Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z
- `ministral-3:14b`: 80.7 tok/s | latency 2003 ms | test 2026-07-08T15:58:01Z

## RTX 3090 decision guide

1. **Batch is the sweet spot**: mistral-small:22b is best for offline/batch jobs where throughput matters more than single-shot latency.
2. **Test at your context length**: moderate-speed models can slow significantly at longer contexts.
3. **Quantization choice matters**: stepping from Q8 to Q4 gains speed but test quality degradation first.
4. **Cloud fallback plan**: if local latency misses your target, use RunPod/Vast for time-sensitive runs.

## Comparisons to validate

- `mistral-small:22b` vs the next-fastest and next-slowest model in the benchmark feed.
- `mistral-small:22b` vs `gpt-oss:20b` — same size tier, 58 vs 156 tok/s.
- `mistral-small:22b` local power cost vs A100 rental for the same workload.

## Next actions

- Estimate VRAM fit: /en/tools/vram-calculator/
- Model page: /en/models/mistral-small-22b-q4/
- Benchmark changelog: /en/benchmarks/changelog/
- Local hardware path: /en/affiliate/hardware-upgrade/
- Cloud fallback: /go/runpod and /go/vast

Affiliate Disclosure: This post may include affiliate links. LocalVRAM may earn a commission at no extra cost.
