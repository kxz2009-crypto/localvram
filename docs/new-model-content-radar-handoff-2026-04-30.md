# New Model Content Radar Handoff - 2026-04-30

This document records the LocalVRAM daily content and homepage work around new Ollama model traffic. It is meant as a restart point if the session is interrupted.

## Why This Exists

New Ollama model releases can create a short search window. LocalVRAM should capture that traffic only when the content has real value:

- Ollama library freshness says a model is newly updated or newly interesting.
- Runner `/api/tags` says whether the RTX 3090 machine actually has the model or family locally.
- Benchmark results say whether the model has measured RTX 3090 evidence.

The important distinction: Ollama freshness is an external market signal; runner inventory is the local truth.

## Completed Work

### 1. New Model Radar Uses Ollama Freshness

Commit: `4c41213 fix: use ollama library freshness for model radar`

Changed the new model watchlist so old benchmarked models are not mistaken for newly released models. The watchlist now checks Ollama library pages and uses labels such as `1 week ago`, `2 days ago`, or stale values to decide whether a candidate is fresh enough.

Main files:

- `scripts/build-new-model-watchlist.py`
- `tests/test_new_model_watchlist.py`
- `src/data/new-model-watchlist.json`

### 2. New Model Radar Combines Local Inventory

Commit: `db3972f feat: surface local model inventory in new model radar`

Added local inventory status to the watchlist. The data now separates:

- `ollama_library_freshness`: external update/download signal from Ollama.
- `local_inventory_status`: local availability from runner `/api/tags`, `runner-status.json`, `weekly-target-plan.json`, and benchmark evidence.
- `benchmark_status`: measured/pending/error status from `benchmark-results.json`.
- `traffic_priority`: `publish_now`, `benchmark_then_publish`, `watch`, or `backlog`.

Homepage ticker now shows the combined signal. Current example:

```text
Ollama 新模型: qwen3.6:35b（1 week ago） | 本地: 已下载 | RTX 3090: 已实测
```

Main files:

- `scripts/build-new-model-watchlist.py`
- `src/data/new-model-watchlist.json`
- `src/pages/en/index.astro`
- `src/pages/zh/index.astro`
- `src/pages/[locale]/index.astro`
- `tests/test_new_model_watchlist.py`

Validation:

- `python -m unittest tests\test_new_model_watchlist.py tests\test_content_strategy.py`
- `python -m unittest discover -s tests -p "test_*.py"`
- `npm.cmd run build`
- GitHub CI run `25158179035` passed.

### 3. Homepage Ticker Links to Model Landing Page

Commit: `10ce1fe feat: link new model ticker and cool repeated posts`

The model tag in the homepage ticker is now clickable. English links use the watchlist landing path directly; Chinese removes `/en` for the CN route; other locales use `withLocale`.

Main files:

- `src/pages/en/index.astro`
- `src/pages/zh/index.astro`
- `src/pages/[locale]/index.astro`

### 4. Daily Blog Avoids Repeating the Same Model

Commit: `10ce1fe feat: link new model ticker and cool repeated posts`

Daily content now records `model_tag` and `model_key` for new-model candidates and draft frontmatter. The generator blocks recently used model keys, so it should not keep writing the same model just because the title or slug changes.

Important behavior:

- Existing slug/topic duplicate protection still applies broadly.
- Model cooldown is windowed, currently via `collect_blocked_topics(today, lookback_days=30)`.
- Published posts now preserve `keyword` and `model_tag` in frontmatter for future filtering.

Main files:

- `scripts/daily-content-agent.py`
- `scripts/publish-content-queue.py`
- `tests/test_content_strategy.py`

Validation:

- `python -m unittest discover -s tests -p "test_*.py"` passed, 58 tests.
- `npm.cmd run build` passed, 8034 pages.
- GitHub CI run `25170277300` passed.

## Current Data Snapshot

As of the last generated watchlist in this work:

- Top item: `qwen3.6:35b`
- Ollama freshness: `1 week ago`
- Local inventory count: `44`
- Local status: `downloaded`
- Benchmark status: `measured`
- RTX 3090 result: about `39.6 tok/s`, latency about `3002 ms`
- Traffic priority: `publish_now`

The local status may come from exact runner tags, family availability, or benchmark evidence. At the time of this note, `qwen3.6:35b` was marked downloaded through benchmark evidence.

## Remaining Ideas / Roadmap

### High Priority

1. Make `traffic_priority` drive daily content more explicitly.

Current state: new-model watchlist candidates get high scores and enter the daily candidate pool.

Next step: use `traffic_priority` directly:

- `publish_now`: can become the lead daily draft.
- `benchmark_then_publish`: should create a benchmark request or pending setup page.
- `watch`: keep in queue but do not outrank measured content.
- `backlog`: ignore unless there are no stronger candidates.

2. Add cooldown exceptions for genuinely new evidence.

Current state: same model is blocked for the recent window.

Next step: allow an exception when:

- Ollama `updated_days` becomes newer than the previous published record.
- Benchmark `measured_at` is newer.
- Tokens/sec or latency changed meaningfully.
- Local inventory status moved from `not_seen_locally` to `downloaded` or `measured`.

3. Add a status page/table for the three signals.

Show the radar in a visible ops/status page:

- Model tag
- Ollama updated label/downloads
- Local inventory status
- Benchmark status
- Traffic priority
- Landing URL

This would make LocalVRAM feel more trustworthy because users can inspect the evidence chain.

### Medium Priority

4. Enrich generated new-model posts with evidence blocks.

The draft template should include:

- "Updated on Ollama: X"
- "Local inventory: downloaded/family available/not seen"
- "RTX 3090 benchmark: measured/pending"
- Exact `ollama run <tag>` command
- Link to model landing page and VRAM calculator

5. Add evergreen content pool for local inventory.

Not every useful article needs a new model. Use local inventory and benchmark data for evergreen pages such as:

- Best 14B models for RTX 3090
- Best 20B/30B local models for coding
- Qwen vs Mistral on 24GB VRAM
- Which local LLM fits RTX 3090?

This should be separate from the launch-window radar.

6. Add "new model opportunity" fields to publish logs.

Future publish records should include:

- `model_tag`
- `model_key`
- `ollama_updated_label`
- `benchmark_measured_at`
- `traffic_priority`

This will make cooldown exceptions and postmortems easier.

### Lower Priority

7. Localize the generic multilingual ticker labels.

English and Chinese homepage copy is explicit. The generic `[locale]` homepage currently uses English fallback labels for `New on Ollama`, `Local`, `downloaded`, and `pending`. It works, but true locale labels can be added later through i18n copy.

8. Add alerting when no local inventory is available.

If `runner-status.json` or `/api/tags` goes stale or reports zero models, the watchlist should mark local evidence as degraded and avoid claiming a model is locally available unless benchmark evidence exists.

## Useful Commands

Run focused tests:

```powershell
python -m unittest tests\test_new_model_watchlist.py tests\test_content_strategy.py
```

Run all tests:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Build site:

```powershell
npm.cmd run build
```

Regenerate watchlist:

```powershell
python scripts\build-new-model-watchlist.py
```

## Known Workspace Notes

During this work there were unrelated dirty and untracked files in the workspace. They were intentionally not staged or committed. Before future commits, check:

```powershell
git status --short
```

Expected relevant files for this initiative are mainly:

- `scripts/build-new-model-watchlist.py`
- `scripts/daily-content-agent.py`
- `scripts/publish-content-queue.py`
- `tests/test_new_model_watchlist.py`
- `tests/test_content_strategy.py`
- `src/data/new-model-watchlist.json`
- `src/pages/en/index.astro`
- `src/pages/zh/index.astro`
- `src/pages/[locale]/index.astro`

