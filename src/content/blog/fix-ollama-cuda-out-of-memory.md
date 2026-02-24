---
title: "Fix Ollama CUDA Out of Memory in 5 Minutes"
description: "Terminal-first quick fix path for the most common Ollama runtime failure."
pubDate: 2026-02-24
updatedDate: 2026-02-24
tags: ["error-kb", "cuda", "oom"]
lang: en
intent: troubleshooting
---

`CUDA out of memory` is usually not a single problem. It is a budget mismatch between model size, context window, and runtime overhead.

## Fast fix order

1. Lower quantization
2. Reduce context size
3. Reduce GPU layers
4. Retry with smaller output length

## Why this works

Each step reduces memory pressure from a different axis. Most users only change one variable and stop too early.

## Prevent repeated OOM

- Keep a per-model context cap
- Save known-good launch commands
- Use a fit calculator before pulling new large models

The fastest stable workflow is: estimate -> verify -> lock known-safe parameters.
