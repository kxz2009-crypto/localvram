# LocalVRAM

Production domain: `https://localvram.com`

Repository: `https://github.com/kxz2009-crypto/localvram/`

## Stack

- Static site: Astro
- Host/CDN: Cloudflare Pages
- Automation: GitHub Actions + Python scripts
- Benchmark runner: self-hosted label `3090-WSL2`

## Cloudflare Pages Setup

- Framework preset: `Astro`
- Build command: `npm run build`
- Build output directory: `dist`
- Root directory: `/`
- Environment variable: `NODE_VERSION=20`

## Affiliate Redirects (Cloudflare Workers on Pages Functions)

Affiliate URLs are routed through first-party short links to reduce ad-block loss:

- `/go/runpod` -> RunPod referral URL
- `/go/vast` -> Vast.ai referral URL
- `/recommends/rtx-3090-24gb` -> Amazon search + affiliate tag
- `/recommends/rtx-4090-24gb` -> Amazon search + affiliate tag

Configure in Cloudflare Pages:

- `AMAZON_TAG` (required for Amazon commissions)
- `RUNPOD_REF` (optional, default: `kzc9gtvv`)
- `VAST_REF_ID` (optional, default: `415258`)
- KV binding `AFFILIATE_EVENTS` (optional, stores click events for 30 days)

## Local run

```bash
npm install
npm run dev
```

## Data and automation

- Status freshness: `src/data/status.json`
- Content opportunities: `src/data/content-opportunities.json`
- Search Console backfeed: `src/data/search-console-keywords.json`
- CTA mapping: `src/data/cta-rules.json`
- Model catalog (200+): `src/data/model-catalog.json`
- Measured benchmark map: `src/data/benchmark-results.json` (keyed by `ollama_tag`)
- Public benchmark API endpoint: `/api/benchmark.json`
- Affiliate links: `src/data/affiliate-links.json` (replace placeholders)
- Affiliate redirect worker code: `functions/`
- GPU snapshots: `public/screenshots/`

## Scripts

- `python scripts/daily-content-agent.py`
- `python scripts/build-model-catalog.py`
- `python scripts/build-sitemap.py`
- `python scripts/quality-gate.py`
- `python scripts/weekly-benchmark.py`
- `python scripts/ollama-preflight.py`
- `python scripts/cluster-benchmark.py`
- `python scripts/report-data-freshness.py`

## Benchmark Runtime Controls

Weekly benchmark (`scripts/weekly-benchmark.py`):

- `LV_OLLAMA_ENDPOINT` (default: `http://127.0.0.1:11434`)
- `OLLAMA_HOST` (fallback when `LV_OLLAMA_ENDPOINT` is not set)
- `OLLAMA_MODELS` (runner/service-side Ollama model directory, for example `/mnt/d/Ollama`)
- `LV_WEEKLY_TARGETS` (default: `qwen3=128,deepseek-r1=128,qwen2.5=128,qwen3-coder=96,qwen3.5=96`; supports both family targets and explicit tags)
- `LV_FAMILY_TARGET_HINTS` (default: `qwen3=8,deepseek-r1=14,qwen2.5=14,qwen3-coder=30,qwen3.5=35,llama3.3=70`; preferred size hint when resolving family targets to a local installed tag)
- `LV_RUNS_PER_MODEL` (default: `2`)
- `LV_BENCHMARK_HISTORY_LIMIT` (default: `20`)
- `LV_BENCHMARK_NUM_CTX` (default: `4096`; fixed context window for apples-to-apples runs)
- `LV_PRE_COOLDOWN_S` (default: `5`; wait before baseline snapshot to reduce thermal bias)
- `LV_SIGNIFICANT_TPS_DELTA` (default: `0.5`; only write measured map when delta exceeds this)
- `LV_BENCHMARK_LOG_RETENTION_DAYS` (default: `30`)
- `LV_VERIFIED_TOOLTIP` (optional; tooltip text for measured hardware badges)
- `LV_AUTO_BACKFILL_TARGETS` (default: `true`; auto-add locally installed known model tags when runnable targets are below threshold)
- `LV_AUTO_BACKFILL_TARGETS_MAX` (default: `6`; cap for auto-added benchmark targets per run)
- `LV_AUTO_PRIORITY_TAGS` (default: `qwen3:8b,deepseek-r1:14b,qwen2.5:14b,qwen3-coder:30b,qwen3.5:35b`; preferred order for auto-added targets)
- `PUBLIC_AMAZON_PRICE_3090` (optional UI price label for local recommendation modules)
- `PUBLIC_RUNPOD_A100_PRICE` (optional UI price label for cloud recommendation modules)

Self-hosted runner preflight:

- `python scripts/ollama-preflight.py --required-targets "$LV_WEEKLY_TARGETS"`
- Validates `/api/tags` visibility before benchmark starts.
- When required targets are family names (for example `qwen3.5`), preflight treats any local tag in that family as runnable.
- Fails fast when no models or no runnable required targets are detected.
- In weekly workflow, preflight runs with `--restart-if-empty` to auto-recover `ollama serve` when model list is unexpectedly empty.

Cluster benchmark (`scripts/cluster-benchmark.py`):

- `LV_CLUSTER_ENDPOINTS` (comma-separated endpoints)
- `LV_CLUSTER_MODEL` (default: `qwen3:8b`)
- `LV_CLUSTER_NUM_CTX` (default: `4096`)
- `LV_CLUSTER_MAX_WORKERS` (default: `2`, use `1` for conservative power draw)
- `LV_CLUSTER_COOLDOWN_S` (default: `2.0`, delay between runs per endpoint)
- `LV_CLUSTER_POWER_LIMIT_W` (default: `0`, disabled; set >0 to enable local power guard)
- `LV_CLUSTER_LOG_RETENTION_DAYS` (default: `30`)

## Logo

Default connected set:

- `public/branding/logo.svg`
- `public/branding/logo-mark.svg`
- `public/favicon.svg`
- `public/branding/ollama-verified-pill.svg`

To switch logo direction, copy files from `branding/logo-options/*`.
