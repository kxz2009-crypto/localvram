---
title: "Today's Local LLM Pick: mistral-small:22b on RTX 3090 (2026)"
description: "Daily 3090 recommendation for mistral-small:22b: heavy performer at 5.5 tok/s, RTX 3090 benchmark data, use-case fit, and local-vs-cloud decision guide."
keyword: "mistral-small:22b rtx 3090 ollama benchmark"
pubDate: 2026-09-15
updatedDate: 2026-09-15
tags: ["ollama", "benchmark", "vram", "latency", "heavy"]
lang: en
intent: benchmark
---

## Fast verdict

`mistral-small:22b` is a **heavy** model on 24GB VRAM (5.5 tok/s). It is best suited for offline batch processing, proof-of-concept validation, or cloud fallback scenarios. Reduce context or step down quantization before attempting interactive use.

`mistral-small:22b` approaches the 24GB boundary at higher quantizations. Consider Q4 or Q5 if you need context headroom on the RTX 3090. It ranks **#14 of 18** in throughput among currently measured models on this RTX 3090. The next faster model is `gemma3:27b` (5.5 tok/s, 0% faster). The next slower model is `qwen3.5:122b` (4.9 tok/s, 11% slower).

The daily goal is simple: help a 3090 owner decide what to download tonight, what to skip, and when a cloud fallback is the better use of time.

## Today's pick

- **Model:** `mistral-small:22b`
- **Category:** general-purpose
- **Size tier:** large
- **Performance tier:** heavy
- **RTX 3090 speed:** 5.5 tok/s
- **Latency:** 16300 ms
- **Test time:** 2026-09-09T07:21:06Z
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
- `qwen3-coder:30b`: 84.4 tok/s | latency 7842 ms | test 2026-09-09T07:21:06Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z
- `nemotron-3-nano:30b`: 57.0 tok/s | latency 2468 ms | test 2026-04-01T11:53:50Z
- `deepseek-r1:14b`: 52.9 tok/s | latency 2724 ms | test 2026-09-09T07:21:06Z

## RTX 3090 decision guide

1. **Cloud may win**: at 5.5 tok/s on 24GB, mistral-small:22b may be more cost-effective on RunPod or Vast.
2. **Reduce aggressively**: step down to Q4 or IQ4 and minimize context to fit VRAM.
3. **Offline only**: do not rely on this model for interactive or real-time local workloads.
4. **Hardware path**: if you run models this size daily, consider multi-GPU or cloud as a permanent solution.

## Comparisons to validate

- `mistral-small:22b` vs the next-fastest and next-slowest model in the benchmark feed.
- `mistral-small:22b` vs `gpt-oss:20b` — same size tier, 5 vs 156 tok/s.
- `mistral-small:22b` local power cost vs A100 rental for the same workload.

## Next actions

- Estimate VRAM fit: /en/tools/vram-calculator/
- Model page: /en/models/mistral-small-22b-q4/
- Benchmark changelog: /en/benchmarks/changelog/
- Local hardware path: /en/affiliate/hardware-upgrade/
- Cloud fallback: /go/runpod and /go/vast

Affiliate Disclosure: This post may include affiliate links. LocalVRAM may earn a commission at no extra cost.
