# Retirement Runbook

This runbook covers the model retirement lifecycle in LocalVRAM:

- candidate generation
- proposal review
- optional semi-automatic apply
- post-apply validation and rollback

## Files

- `src/data/retired-models.json`: active retirement policy (source of truth)
- `src/data/retirement-candidates.json`: stale model candidates generated from benchmark history
- `src/data/retirement-proposal.json`: review output (auto-approved + manual-review split)
- `src/data/benchmark-results.json`: measured benchmark payload (pruned by retirement policy)

## Workflow Entry

Workflow: `Publish Benchmark Artifact`  
Manual dispatch inputs:

- `source_run_id` (required in manual mode)
- `apply_retirement_candidates` (`true`/`false`, default `false`)
- `retirement_min_stale_runs` (default `3`)
- `retirement_max_seen_ok_count` (default `2`)

Recommended default: start with `apply_retirement_candidates=false` for review-first.

## Standard Procedure

1. Trigger publish in review-only mode.
2. Wait for success.
3. Inspect `src/data/retirement-proposal.json`.
4. If proposal is acceptable, trigger publish with `apply_retirement_candidates=true`.
5. Verify `retired-models.json`, `benchmark-results.json`, and website status pages.

## Commands (PowerShell + gh)

Review-only run:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" workflow run "Publish Benchmark Artifact" `
  -R kxz2009-crypto/localvram `
  -f source_run_id=22405601903 `
  -f apply_retirement_candidates=false `
  -f retirement_min_stale_runs=3 `
  -f retirement_max_seen_ok_count=2
```

Apply run:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" workflow run "Publish Benchmark Artifact" `
  -R kxz2009-crypto/localvram `
  -f source_run_id=22405601903 `
  -f apply_retirement_candidates=true `
  -f retirement_min_stale_runs=3 `
  -f retirement_max_seen_ok_count=2
```

Watch latest run:

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run list `
  -R kxz2009-crypto/localvram `
  --workflow "Publish Benchmark Artifact" `
  --limit 1

& "C:\Program Files\GitHub CLI\gh.exe" run watch <RUN_ID> `
  -R kxz2009-crypto/localvram `
  --exit-status
```

## Validation Checklist

- Workflow run completed with `success`
- `src/data/retirement-proposal.json` exists and has fresh `generated_at`
- `src/data/retired-models.json` updated only when `apply_retirement_candidates=true`
- `src/data/benchmark-results.json` no longer contains newly retired tags
- `src/data/pipeline-status.json` keeps `failure_class=none` for publish run

## Failure Classes

Retirement-related publish failures:

- `retired_data_prune_failure`
- `retirement_candidates_failure`
- `retirement_review_failure`
- `retirement_apply_prune_failure`

Check logs/artifacts in the failed publish run for details.

## Rollback

If an apply run retires too aggressively:

1. Revert `src/data/retired-models.json` to previous commit.
2. Trigger publish with `apply_retirement_candidates=false`.
3. Confirm `benchmark-results.json` and proposal files are regenerated as expected.

Optional local rollback commands:

```powershell
git checkout <GOOD_COMMIT> -- src/data/retired-models.json
git commit -m "revert: rollback retirement policy"
git push
```

## Governance Notes

- Keep family-level retirement conservative; prefer tag-level retirement first.
- Treat proposal as advisory. Human review is required for business-critical families.
- Tune thresholds gradually:
  - increase `retirement_min_stale_runs` to be more conservative
  - decrease `retirement_max_seen_ok_count` to reduce auto-apply scope
