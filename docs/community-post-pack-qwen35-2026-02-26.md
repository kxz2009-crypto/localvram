# Community Post Pack: Qwen3.5 on RTX 3090 (2026-02-26)

Use this pack for 6 communities:

- X (Twitter)
- Reddit
- Hugging Face
- GitHub Discussions
- Discord
- Hacker News

This version is **no-link first** (account warm-up friendly).

## Facts to keep consistent

- Date of measured snapshot: **2026-02-26T19:19:16Z**
- Hardware: **RTX 3090 24GB (WSL2)**
- Ollama: **0.17.1**
- Qwen3.5 35B measured: **35.885 tok/s**
- Qwen3.5 122B measured: **4.931 tok/s**
- 122B required high swap headroom in our setup (we used **160GiB swap**).

---

## 1) X (Twitter)

### Post (no link)

We just finished a fresh LocalVRAM run on RTX 3090 (24GB, WSL2) for the latest Qwen3.5 line.

- Qwen3.5 35B: 35.885 tok/s (measured)
- Qwen3.5 122B: 4.931 tok/s (measured)
- Both are now reproducible on 3090 with the right setup

Main takeaway: 35B is practical for daily local use; 122B is possible but needs serious system memory/swap headroom.

If you run Qwen3.5 on 3090/4090/A100, share your numbers and config.

#LLM #Ollama #Qwen #RTX3090 #LocalAI

### Optional link suffix (use later)

Data + methodology on LocalVRAM (models + benchmark changelog).

---

## 2) Reddit (r/LocalLLaMA / r/ollama)

### Title

Measured on RTX 3090: Qwen3.5 35B and 122B both run locally (35.885 tok/s / 4.931 tok/s)

### Body (no link)

Ran a new benchmark pass on RTX 3090 24GB (WSL2, Ollama 0.17.1).

Results:
- Qwen3.5 35B: 35.885 tok/s
- Qwen3.5 122B: 4.931 tok/s

What mattered most:
- 35B was straightforward after upgrade and clean pull.
- 122B needed large system memory headroom and high swap (we used 160GiB) to avoid loader/runtime failures.

Practical conclusion:
- 35B = daily driver tier on 3090
- 122B = technically runnable, but higher latency + heavier memory pressure

Happy to compare with Linux bare-metal / dual GPU / 4090 runs if others share configs.

---

## 3) Hugging Face (Discussion / Community post)

### Post (no link)

Benchmark update from LocalVRAM (2026-02-26):

- Model family: Qwen3.5 (latest line)
- GPU: RTX 3090 24GB
- Runtime: Ollama 0.17.1
- Measured:
  - Qwen3.5 35B -> 35.885 tok/s
  - Qwen3.5 122B -> 4.931 tok/s

Important runtime note:
122B required much larger memory headroom (160GiB swap in our test host) to pass from "can pull" to "stable run".

If you have a reproducible 122B setup on 3090/4090, we want to compare:
- tok/s
- num_ctx
- prompt length
- total RAM + swap

---

## 4) GitHub Discussions (localvram repo)

### Title

Qwen3.5 benchmark update: 35B + 122B measured on RTX 3090

### Body

Latest pipeline update is live.

Measured on RTX 3090 (24GB, WSL2, Ollama 0.17.1):
- qwen3.5:35b -> 35.885 tok/s
- qwen3.5:122b -> 4.931 tok/s

Operational notes:
- 122B is now runnable in our environment after memory/swap tuning (160GiB swap).
- Weekly -> Publish pipeline completed successfully for this batch.

If anyone wants us to publish per-model config deltas (ctx, timeout, swap profile) as a dedicated runbook appendix, reply here.

---

## 5) Discord (server update)

### Post (no link)

Quick benchmark update from LocalVRAM:

**Qwen3.5 on RTX 3090 (24GB) is now fully measured**
- 35B: **35.885 tok/s**
- 122B: **4.931 tok/s**

Env:
- WSL2
- Ollama 0.17.1
- 122B needed high memory/swap headroom (160GiB swap in our run)

Bottom line:
- 35B is production-friendly on 3090
- 122B is possible, but slower + memory sensitive

If you want, we can post a clean config template for reproducing 122B runs.

---

## 6) Hacker News ("Show HN" style text)

### Title

Show HN: Reproducible Qwen3.5 35B and 122B runs on a single RTX 3090

### Body (no link)

We maintain a benchmark pipeline for local LLM deployment decisions.

Latest measured run (2026-02-26):
- GPU: RTX 3090 24GB
- Runtime: Ollama 0.17.1
- Qwen3.5 35B: 35.885 tok/s
- Qwen3.5 122B: 4.931 tok/s

What was interesting:
- 35B was straightforward once runtime version matched model requirements.
- 122B initially failed due to memory limits, then became stable after increasing swap headroom.

If people are interested, we can share an anonymized benchmark matrix (3090 vs 4090 vs cloud fallback) in a follow-up.

---

## Posting sequence (recommended)

1. X
2. Reddit
3. Discord
4. Hugging Face
5. GitHub Discussions
6. Hacker News

Tip: post text-first, no external links for new accounts. Add links in replies only after initial engagement starts.
