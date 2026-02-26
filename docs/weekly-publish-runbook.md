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
4. Waits for auto `workflow_run` publish and watches it (`--publish-mode auto` default).
5. Falls back to manual publish only when requested (`--publish-mode auto-then-manual` or `manual`).

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
- `--retry-weekly-after-smoke true|false`: when `weekly` fails but `smoke` succeeds, auto-dispatch one retry weekly run (default `false`).
- `--publish-mode auto|manual|auto-then-manual`:
  - `auto` (default): wait and watch auto `workflow_run` publish only.
  - `manual`: always dispatch `run-publish-workflow.py`.
  - `auto-then-manual`: try auto publish first, dispatch manual publish only if auto run is not available/successful.
- `--publish-workflow publish-benchmark-artifact.yml`: publish workflow file id/name to watch/dispatch.

## 4) Preconditions

- `gh auth status -h github.com` is healthy.
- token has workflow dispatch permission for this repo.
- local network can reach `api.github.com`.

## 5) Failure handling

- If weekly run fails, publish stage is blocked by design.
- Script now prints `weekly_failure_class` / `weekly_failure_detail` and a short failed-log excerpt when available.
- By default it also dispatches `Runner Smoke Check` and prints `smoke_run_id`, `smoke_run_url`, and `smoke_conclusion`.
- If smoke also fails, script prints `smoke_failure_class` / `smoke_failure_detail` and log hint command.
- Optional auto-retry: set `--retry-weekly-after-smoke true` to run one extra weekly attempt after a successful smoke run.
- Re-run after fixing runner/Ollama issue:
  - `Weekly Benchmark`
  - then this script again.

## 6) Known publish quality-gate mismatch

Symptom in `Publish Benchmark Artifact` logs:

- `quality gate failed: benchmark-results model tags missing in model-catalog ollama_tag`
- Example: `Model 'ministral-3:14b' found in results but missing in catalog.`

Meaning:

- Weekly artifact contains a measured model tag that catalog did not include.

Current fix (already in `main`):

- `scripts/build-model-catalog.py` auto-discovers missing measured tags from `src/data/benchmark-results.json` and adds catalog entries before quality gate.

Operator action:

1. `git pull` to ensure runner/workflow uses latest `main`.
2. Re-run `Publish Benchmark Artifact` (or rerun full weekly->publish).
3. If still failing, fetch failed logs with retry backoff and check exact missing tags:

```powershell
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$repo = "kxz2009-crypto/localvram"
$pubId = & $gh run list -R $repo --workflow "Publish Benchmark Artifact" --json databaseId -L 1 --jq '.[0].databaseId'
$delays = @(5,10,20,30)
$ok = $false
for ($i=0; $i -le $delays.Count; $i++) {
  $log = & $gh run view $pubId -R $repo --log-failed 2>&1
  if ($LASTEXITCODE -eq 0) { $ok = $true; break }
  if ($i -lt $delays.Count) { Start-Sleep -Seconds $delays[$i] }
}
if (-not $ok) { throw "failed to fetch logs for run $pubId" }
$log | Select-String -Pattern "quality gate failed|missing in catalog|benchmark-results model tags"
```

## 7) Known qwen3.5 runtime incompatibility (412/500)

Symptom:

- `ollama pull qwen3.5:35b` => `412 ... requires a newer version of Ollama`
- `ollama run qwen3.5:35b` => `500 ... unable to load model ... sha256-...`

Action:

- Follow [Ollama Upgrade Runbook](/docs/ollama-upgrade-runbook.md) first.
- Re-run smoke, then weekly->publish.
