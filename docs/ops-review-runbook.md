# Ops Review Runbook

This runbook defines the unified manual-review entrypoint for LocalVRAM:

- content draft manual decisions
- community submission manual decisions

Script: `python scripts/ops-review.py`

## 1) Content manual review

Approve by slug:

```bash
python scripts/ops-review.py content \
  --queue-date 2026-02-26 \
  --slugs q4-vs-q8-quality-loss \
  --action approve \
  --reviewer ops
```

Reject by draft file:

```bash
python scripts/ops-review.py content \
  --queue-date 2026-02-26 \
  --drafts 03-en-tools-quantization-blind-test.md \
  --action reject \
  --reviewer ops \
  --note "existing slug/topic duplicate"
```

Optional: include `--quality-gate` to run `scripts/quality-gate.py` after the action.

Dry-run preview (no file write):

```bash
python scripts/ops-review.py content \
  --queue-date 2026-02-26 \
  --drafts 03-en-tools-quantization-blind-test.md \
  --action reject \
  --reviewer ops \
  --note "existing slug/topic duplicate" \
  --dry-run
```

Auto commit + push (optional):

```bash
python scripts/ops-review.py content \
  --queue-date 2026-02-26 \
  --drafts 03-en-tools-quantization-blind-test.md \
  --action reject \
  --reviewer ops \
  --note "existing slug/topic duplicate" \
  --git-commit \
  --git-push
```

## 2) Submission manual review

Approve/reject/needs info:

```bash
python scripts/ops-review.py submission \
  --submission-ids f9ba21e73260,4d9248019034 \
  --action approve \
  --reviewer ops:gao20 \
  --note "validated logs and reproducibility"
```

By default this command automatically refreshes `src/data/submission-review.json`.

Optional flags:

- `--skip-snapshot-refresh`: skip `build-submission-review.py`
- `--allow-non-pending`: allow re-reviewing non-pending rows
- `--quality-gate`: run `scripts/quality-gate.py` at end
- `--dry-run`: preview only; no file writes (and no snapshot refresh)
- `--git-commit`: stage only review-related files and commit
- `--git-push`: push after commit (requires `--git-commit`)
- `--git-commit-message`: custom commit message
- `--allow-prestaged`: allow committing even if staged files already exist

## 3) Notes

- Legacy scripts remain supported:
  - `scripts/review-content-drafts.py`
  - `scripts/review-community-submissions.py`
- Use `ops-review.py` as the default operator command to reduce manual mistakes and command drift.
- Safety default: auto-commit mode refuses to run when pre-staged files exist, to avoid accidental mixed commits.
- Safety rule: `--dry-run` cannot be combined with `--git-commit`/`--git-push`.
