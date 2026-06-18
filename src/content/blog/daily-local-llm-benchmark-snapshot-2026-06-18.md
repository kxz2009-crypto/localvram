---
title: "Today's Local LLM Pick: ministral-3:14b on RTX 3090 (2026)"
description: "Daily 3090 recommendation for ministral-3:14b: moderate performer at 79.2 tok/s, RTX 3090 benchmark data, use-case fit, and local-vs-cloud decision guide."
keyword: "ministral-3:14b rtx 3090 ollama benchmark"
pubDate: 2026-06-18
updatedDate: 2026-06-18
tags: ["ollama", "benchmark", "vram", "latency", "moderate"]
lang: en
intent: benchmark
---

## Fast verdict

`ministral-3:14b` is a **moderate-speed** general-purpose model on a 24GB RTX 3090 (79.2 tok/s). It is worth testing locally for batch or offline workloads. For real-time interactive use, measure end-to-end latency with your typical prompt length before committing.

`ministral-3:14b` fits comfortably in 24GB at standard quantizations. Monitor VRAM usage if you push context beyond 8K tokens. It ranks **#6 of 18** in throughput among currently measured models on this RTX 3090. The next faster model is `qwen2.5:14b` (84.0 tok/s, 6% faster). The next slower model is `deepseek-r1:14b` (74.4 tok/s, 7% slower).

The daily goal is simple: help a 3090 owner decide what to download tonight, what to skip, and when a cloud fallback is the better use of time.

## Today's pick

- **Model:** `ministral-3:14b`
- **Category:** general-purpose
- **Size tier:** medium
- **Performance tier:** moderate
- **RTX 3090 speed:** 79.2 tok/s
- **Latency:** 2047 ms
- **Test time:** 2026-06-17T07:31:11Z
- **Baseline command:**

```bash
ollama run ministral-3:14b
```

## Who should try it

- RTX 3090 owners deciding whether to download `ministral-3:14b` tonight for local experimentation.
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
- `qwen3-coder:30b`: 140.5 tok/s | latency 935 ms | test 2026-06-17T07:31:11Z
- `qwen3:8b`: 121.7 tok/s | latency 1429 ms | test 2026-06-17T07:31:11Z
- `qwen2.5-coder:32b`: 92.2 tok/s | latency 1609 ms | test 2026-06-17T07:31:11Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z

## RTX 3090 decision guide

1. **Batch is the sweet spot**: ministral-3:14b is best for offline/batch jobs where throughput matters more than single-shot latency.
2. **Test at your context length**: moderate-speed models can slow significantly at longer contexts.
3. **Quantization choice matters**: stepping from Q8 to Q4 gains speed but test quality degradation first.
4. **Cloud fallback plan**: if local latency misses your target, use RunPod/Vast for time-sensitive runs.

## Comparisons to validate

- `ministral-3:14b` vs the next-fastest and next-slowest model in the benchmark feed.
- `ministral-3:14b` vs `qwen3:8b` — same size tier, 79 vs 122 tok/s.
- `ministral-3:14b` local power cost vs A100 rental for the same workload.

## Next actions

- Estimate VRAM fit: /en/tools/vram-calculator/
- Model page: /en/models/ministral-3-14b-q4/
- Benchmark changelog: /en/benchmarks/changelog/
- Local hardware path: /en/affiliate/hardware-upgrade/
- Cloud fallback: /go/runpod and /go/vast

Affiliate Disclosure: This post may include affiliate links. LocalVRAM may earn a commission at no extra cost.
