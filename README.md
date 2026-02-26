# LocalVRAM

Production domain: `https://localvram.com`

Repository: `https://github.com/kxz2009-crypto/localvram/`

Operations runbooks:

- `docs/retirement-runbook.md`
- `docs/conversion-funnel-runbook.md`
- `docs/submission-review-runbook.md`
- `docs/content-publish-runbook.md`
- `docs/pipeline-slo-runbook.md`
- `docs/ops-review-runbook.md`

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
- Affiliate click export (sanitized): `src/data/affiliate-click-events.json`
- Conversion funnel snapshot: `src/data/conversion-funnel.json`
- Community submissions: `src/data/community-reports.json`
- Submission review snapshot: `src/data/submission-review.json`
- Content publish log: `src/data/content-publish-log.json`
- Content review log: `src/data/content-review-log.json`
- Pipeline SLO snapshot: `src/data/pipeline-slo.json`
- CTA mapping: `src/data/cta-rules.json`
- Model catalog (200+): `src/data/model-catalog.json`
- Measured benchmark map: `src/data/benchmark-results.json` (keyed by `ollama_tag`)
- Retirement policy: `src/data/retired-models.json` (retired families/tags)
- Retirement candidates: `src/data/retirement-candidates.json` (auto-generated stale model suggestions)
- Retirement proposal: `src/data/retirement-proposal.json` (auto-review result for optional apply)
- Public benchmark API endpoint: `/api/benchmark.json`
- Affiliate links: `src/data/affiliate-links.json` (replace placeholders)
- Affiliate redirect worker code: `functions/`
- GPU snapshots: `public/screenshots/`

## Scripts

- `python scripts/daily-content-agent.py`
- `python scripts/build-model-catalog.py`
- `python scripts/build-sitemap.py`
- `python scripts/build-conversion-funnel.py`
- `python scripts/import-affiliate-events.py --source-file <raw-export.jsonl>`
- `python scripts/refresh-affiliate-funnel.py --source-file <raw-export.jsonl>`
- `python scripts/build-submission-review.py`
- `python scripts/review-content-queue.py`
- `python scripts/review-content-drafts.py --queue-date <YYYY-MM-DD> --slugs <slug1,slug2> --action approve|reject|needs_info`
- `python scripts/ops-review.py content --action approve|reject|needs_info --drafts <draft1.md,draft2.md> --reviewer ops [--git-commit --git-push]`
- `python scripts/publish-content-queue.py`
- `python scripts/build-pipeline-slo.py`
- `python scripts/quality-gate.py`
- `python scripts/weekly-benchmark.py`
- `python scripts/resolve-weekly-targets.py`
- `python scripts/ollama-preflight.py`
- `python scripts/prune-retired-benchmark-data.py`
- `python scripts/generate-retirement-candidates.py`
- `python scripts/review-retirement-candidates.py`
- `python scripts/runner-diagnostics.py`
- `python scripts/validate-benchmark-artifact.py --source-dir <artifact-dir>`
- `python scripts/update-pipeline-status.py --workflow-key <key> --run-id <id> --run-url <url>`
- `python scripts/cluster-benchmark.py`
- `python scripts/report-data-freshness.py`
- `python scripts/score-user-submission.py`
- `python scripts/review-community-submissions.py --submission-ids <id1,id2> --action approve|reject|needs_info`
- `python scripts/ops-review.py submission --submission-ids <id1,id2> --action approve|reject|needs_info --reviewer ops [--git-commit --git-push]`
- `python scripts/run-publish-workflow.py --gh-path "<gh.exe path>"`

## Benchmark Runtime Controls

Weekly benchmark (`scripts/weekly-benchmark.py`):

- `LV_OLLAMA_ENDPOINT` (default: `http://127.0.0.1:11434`)
- `OLLAMA_HOST` (fallback when `LV_OLLAMA_ENDPOINT` is not set)
- `OLLAMA_MODELS` (runner/service-side Ollama model directory, for example `/mnt/d/Ollama`)
- `LV_WEEKLY_TARGETS` (default: `qwen3=128,deepseek-r1=128,qwen2.5=128,qwen3-coder=96,qwen3.5=96`; supports both family targets and explicit tags)
- `LV_FAMILY_TARGET_HINTS` (default: `qwen3=8,deepseek-r1=14,qwen2.5=14,qwen3-coder=30,qwen3.5=35,llama3.3=70`; preferred size hint when resolving family targets to a local installed tag)
- `LV_NETWORK_RETRY_DELAYS_S` (default: `5,10,20`; transient network retry backoff for Ollama API requests)
- `LV_RETIRED_POLICY_FILE` (default: `src/data/retired-models.json`; excludes retired families/tags from targets and auto-backfill)
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

- `python scripts/ollama-preflight.py --required-targets "$LV_WEEKLY_TARGETS" --require-local-process`
- Validates `/api/tags` visibility before benchmark starts.
- When required targets are family names (for example `qwen3.5`), preflight treats any local tag in that family as runnable.
- Uses `LV_NETWORK_RETRY_DELAYS_S` retry backoff (default `5,10,20`) before failing on transient connection issues.
- Fails fast when no models or no runnable required targets are detected.
- In weekly workflow, preflight runs with `--restart-if-empty` to auto-recover `ollama serve` when model list is unexpectedly empty.
- Single-instance governance checks classify runner-side ownership problems: `ollama_multi_instance`, `ollama_port_conflict`, `ollama_instance_unmanaged`.
- Failure classes in logs: `checkout_network_failure`, `ollama_not_visible`, `model_missing`, `ollama_multi_instance`, `ollama_port_conflict`, `ollama_instance_unmanaged`, `benchmark_threshold_not_met`, `source_run_discovery_failure`, `source_run_metadata_failure`, `source_run_not_publishable`, `artifact_download_rate_limited`, `publish_push_rate_limited`, `retired_data_prune_failure`, `retirement_candidates_failure`, `retirement_review_failure`, `retirement_apply_prune_failure`.
- Failure alerts: `Weekly Benchmark` and `Publish Benchmark Artifact` auto-create or update GitHub Issues with title `[OPS-ALERT] <workflow>: <failure_class>`.
- Recovery handling: when workflow returns to success, open `[OPS-ALERT]` issues for that workflow are auto-commented and closed.
- Model retirement: update `src/data/retired-models.json` to phase out old families/tags so they stop entering weekly targets and auto-backfill.

Smoke check workflow:

- GitHub Actions workflow: `Runner Smoke Check` (manual trigger).
- Runs quick diagnostics + preflight only (no full benchmark), useful after runner/Ollama upgrades.
- Scheduled and manual runs normalize missing inputs to defaults, then auto-resolve runnable families from local `/api/tags`.
- Scheduled daily at `01:40 UTC` (US evening window).

Weekly collect/publish split:

- `Weekly Benchmark` now runs only on self-hosted runner and uploads a `benchmark-collection` artifact.
- Weekly target resolver writes `src/data/weekly-target-plan.json` and includes it in the benchmark artifact/publish sync.
- Weekly target plan records retirement impact (`dropped_base_targets`, retired local sample) for auditability.
- Publish workflow prunes retired models from `src/data/benchmark-results.json` before catalog/sitemap build.
- Publish workflow generates `src/data/retirement-candidates.json` from benchmark history to assist next retirement batch review.
- Publish manual dispatch supports semi-auto apply:
  - `apply_retirement_candidates=true` to append auto-approved tags into `retired-models.json`
  - `retirement_min_stale_runs` and `retirement_max_seen_ok_count` to tune review strictness
- Weekly benchmark schedule: `02:10 UTC every Wednesday` (US Tuesday evening window).
- `Publish Benchmark Artifact` (workflow_run/manual) downloads that artifact, validates JSON payloads, rebuilds catalog/sitemap, and pushes with retry backoff (`5,10,20` default) + 429-aware wait (`rate_limit_delay_s`, default `60`) + jitter.
- Manual `Publish Benchmark Artifact` dispatch can leave `source_run_id` empty; workflow auto-resolves the latest successful `weekly-benchmark.yml` run ID.
- Invalid/manual `source_run_id` is guarded: publish now verifies source run is `Weekly Benchmark` + `completed/success`, and auto-falls back to latest successful weekly run when needed.
- Publish workflow performs a follow-up lightweight commit for `src/data/pipeline-status.json` so the publish run conclusion is persisted even when the main publish commit has already been pushed.
- Drill workflow: `Publish Fallback Drill` (manual) dispatches publish with invalid `source_run_id` and asserts fallback evidence in logs.
- Recommended manual dispatch wrapper: `scripts/run-publish-workflow.py` (auto-resolves latest successful weekly run ID, dispatches publish with retry, and watches run result).
- Runner health status page: `/en/status/runner-health/` (source file `src/data/runner-status.json` from diagnostics snapshot).
- Pipeline status page: `/en/status/pipeline-status/` (source file `src/data/pipeline-status.json`).
- Conversion funnel page: `/en/status/conversion-funnel/` (source file `src/data/conversion-funnel.json`).
- Submission review page: `/en/status/submission-review/` (source file `src/data/submission-review.json`).
- Content publish status page: `/en/status/content-publish/` (source file `src/data/content-publish-log.json`).

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
