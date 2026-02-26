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

## 4) Preconditions

- `gh auth status -h github.com` is healthy.
- token has workflow dispatch permission for this repo.
- local network can reach `api.github.com`.

## 5) Failure handling

- If weekly run fails, publish stage is blocked by design.
- Re-run after fixing runner/Ollama issue:
  - `Runner Smoke Check`
  - `Weekly Benchmark`
  - then this script again.
