# Weekly Publish Runbook

This runbook describes one-shot orchestration for weekly benchmark collection and publish.

Script: `python scripts/run-weekly-publish-pipeline.py`

## 1) Standard run (recommended)

```powershell
python scripts/run-weekly-publish-pipeline.py `
  --gh-path "C:\Program Files\GitHub CLI\gh.exe" `
  --repo kxz2009-crypto/localvram
```

What it does:

1. Dispatches `weekly-benchmark.yml`.
2. Watches run until completion.
3. Requires weekly result to be `success`.
4. Dispatches publish via `run-publish-workflow.py` using that weekly run id.

## 2) Weekly only (no publish)

```powershell
python scripts/run-weekly-publish-pipeline.py `
  --gh-path "C:\Program Files\GitHub CLI\gh.exe" `
  --repo kxz2009-crypto/localvram `
  --skip-publish
```

## 3) Optional controls

- `--include-heavy-targets`: passes `include_heavy_targets=true` to weekly workflow.
- `--extra-targets "<csv>"`: passes extra target CSV to weekly workflow.
- `--benchmark-timeout-s <seconds>`: sets weekly benchmark timeout input.
- `--retry-delays-s "5,10,20"`: network retry backoff for `gh` calls.
- `--apply-retirement-candidates true|false`: forwarded to publish stage.
- `--retirement-min-stale-runs <n>` / `--retirement-max-seen-ok-count <n>`: forwarded to publish stage.
- `--run-smoke-on-weekly-failure true|false`: when weekly fails, auto-dispatch `Runner Smoke Check` (default `true`).
- `--smoke-workflow runner-smoke-check.yml`: smoke workflow id/name for dispatch.
- `--smoke-endpoint http://127.0.0.1:11434`: smoke check endpoint input.
- `--smoke-required-targets "<csv>"`: optional smoke required target override.
- `--smoke-restart-if-empty true|false`: forwarded to smoke input (default `true`).
- `--smoke-retry-delays-s "5,10,20"`: smoke input retry CSV (defaults to `--retry-delays-s` when empty).

## 4) Preconditions

- `gh auth status -h github.com` is healthy.
- token has workflow dispatch permission for this repo.
- local network can reach `api.github.com`.

## 5) Failure handling

- If weekly run fails, publish stage is blocked by design.
- Script now prints `weekly_failure_class` / `weekly_failure_detail` and a short failed-log excerpt when available.
- By default it also dispatches `Runner Smoke Check` and prints `smoke_run_id`, `smoke_run_url`, and `smoke_conclusion`.
- If smoke also fails, script prints `smoke_failure_class` / `smoke_failure_detail` and log hint command.
- Re-run after fixing runner/Ollama issue:
  - `Weekly Benchmark`
  - then this script again.
