# Submission Review Runbook

This runbook covers community benchmark submission intake and queue review.

## 1) Source files

- Submission raw queue: `src/data/community-reports.json`
- Review snapshot: `src/data/submission-review.json`
- Status page: `/en/status/submission-review/`

## 2) Intake command (submitter-side precheck)

```bash
python scripts/score-user-submission.py \
  --model-id llama-70b-q4 \
  --hardware "RTX 4090 24GB + WSL2" \
  --score 0.91 \
  --submitter-id github:your-id \
  --issue-url "https://github.com/kxz2009-crypto/localvram/issues/123"
```

Default safeguards:

- max `3` submissions per submitter per UTC day (`rejected_rate_limited`)
- duplicate window `48h` for same submitter + model + hardware (`pending_duplicate_review`)
- low score flag if `<0.70` (`low_precheck_score`)
- missing issue link flag (`missing_issue_url`)

## 3) Build review snapshot

```bash
python scripts/build-submission-review.py
```

Optional tighter stale threshold:

```bash
python scripts/build-submission-review.py --stale-days 5
```

## 4) Validate

```bash
python scripts/quality-gate.py
```

Checks include:

- `src/data/community-reports.json` exists
- `src/data/submission-review.json` exists
- `summary` object exists in `submission-review.json`
- `/en/status/submission-review/` page exists

## 5) CI integration

- `daily-content.yml` rebuilds submission review snapshot daily.
- `publish-benchmark-artifact.yml` rebuilds submission review snapshot during publish pipeline.

## 6) Review actions (approve/reject/needs info)

Approve one or more pending submissions:

```bash
python scripts/ops-review.py submission \
  --submission-ids f9ba21e73260,4d9248019034 \
  --action approve \
  --reviewer ops:gao20 \
  --note "validated logs and reproducibility"
```

Dry-run preview:

```bash
python scripts/ops-review.py submission \
  --submission-ids f9ba21e73260,4d9248019034 \
  --action approve \
  --reviewer ops:gao20 \
  --note "validated logs and reproducibility" \
  --dry-run
```

Optional one-shot commit/push:

```bash
python scripts/ops-review.py submission \
  --submission-ids f9ba21e73260,4d9248019034 \
  --action approve \
  --reviewer ops:gao20 \
  --note "validated logs and reproducibility" \
  --git-commit \
  --git-push
```

Reject pending submissions:

```bash
python scripts/ops-review.py submission \
  --submission-ids a1d1d3edd2dd \
  --action reject \
  --reviewer ops:gao20 \
  --note "missing reproducible logs"
```

Ask for more information:

```bash
python scripts/ops-review.py submission \
  --submission-ids dca6301c40c8 \
  --action needs_info \
  --reviewer ops:gao20 \
  --note "please attach exact prompt/context and raw run logs"
```

After any review action:

```bash
python scripts/quality-gate.py
```

`ops-review.py submission` refreshes `submission-review.json` by default.  
Use `--skip-snapshot-refresh` only when you explicitly want to defer snapshot update.
