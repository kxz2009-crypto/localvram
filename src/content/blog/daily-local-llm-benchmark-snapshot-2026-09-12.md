---
title: "Today's Local LLM Pick: ministral-3:14b on RTX 3090 (2026)"
description: "Daily 3090 recommendation for ministral-3:14b: deliberate performer at 15.4 tok/s, RTX 3090 benchmark data, use-case fit, and local-vs-cloud decision guide."
keyword: "ministral-3:14b rtx 3090 ollama benchmark"
pubDate: 2026-09-12
updatedDate: 2026-09-12
tags: ["ollama", "benchmark", "vram", "latency", "deliberate"]
lang: en
intent: benchmark
---

## Fast verdict

`ministral-3:14b` runs at **15.4 tok/s** on a 24GB RTX 3090 — in the deliberate range. This model prioritizes quality or parameter count over raw speed. Test it on offline or background tasks first, and consider a smaller quantization if interactive response time matters.

`ministral-3:14b` fits comfortably in 24GB at standard quantizations. Monitor VRAM usage if you push context beyond 8K tokens. It ranks **#9 of 18** in throughput among currently measured models on this RTX 3090. The next faster model is `qwq:32b` (26.1 tok/s, 70% faster). The next slower model is `glm-4.7-flash:bf16` (11.2 tok/s, 37% slower).

The daily goal is simple: help a 3090 owner decide what to download tonight, what to skip, and when a cloud fallback is the better use of time.

## Today's pick

- **Model:** `ministral-3:14b`
- **Category:** general-purpose
- **Size tier:** medium
- **Performance tier:** deliberate
- **RTX 3090 speed:** 15.4 tok/s
- **Latency:** 8563 ms
- **Test time:** 2026-09-09T07:21:06Z
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
- `qwen3-coder:30b`: 84.4 tok/s | latency 7842 ms | test 2026-09-09T07:21:06Z
- `qwen2.5:14b`: 84.0 tok/s | latency 946 ms | test 2026-04-29T05:39:58Z
- `nemotron-3-nano:30b`: 57.0 tok/s | latency 2468 ms | test 2026-04-01T11:53:50Z
- `deepseek-r1:14b`: 52.9 tok/s | latency 2724 ms | test 2026-09-09T07:21:06Z

## RTX 3090 decision guide

1. **Offline first**: prioritize ministral-3:14b for scheduled batch inference, research, or validation workflows.
2. **Context is the bottleneck**: reduce context to the minimum viable length for your task.
3. **Quantize before you buy hardware**: Q4 or Q5 may make this viable on 24GB where Q8 is not.
4. **Cloud for interactive**: if real-time response is required, treat ministral-3:14b as a cloud-fallback candidate.

## Comparisons to validate

- `ministral-3:14b` vs the next-fastest and next-slowest model in the benchmark feed.
- `ministral-3:14b` vs `qwen2.5:14b` — same size tier, 15 vs 84 tok/s.
- `ministral-3:14b` local power cost vs A100 rental for the same workload.

## Next actions

- Estimate VRAM fit: /en/tools/vram-calculator/
- Model page: /en/models/ministral-3-14b-q4/
- Benchmark changelog: /en/benchmarks/changelog/
- Local hardware path: /en/affiliate/hardware-upgrade/
- Cloud fallback: /go/runpod and /go/vast

Affiliate Disclosure: This post may include affiliate links. LocalVRAM may earn a commission at no extra cost.
