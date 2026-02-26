# Content Publish Runbook

This runbook covers auto-publishing queue drafts into live blog posts.

## 1) Source and output

- Queue source: `content-queue/<YYYY-MM-DD>/*.md`
- Blog output: `src/content/blog/*.md`
- Publish log: `src/data/content-publish-log.json`
- Review gate log: `src/data/content-review-log.json`
- Status page: `/en/status/content-publish/`

## 2) Review gate first (required)

```bash
python scripts/review-content-queue.py
```

The gate updates each draft `status`:

- `approved_auto`: safe to auto-publish
- `pending_manual_review`: needs human decision
- keeps manual terminal states: `approved_manual`, `rejected_manual`

Manual review actions:

```bash
python scripts/ops-review.py content --queue-date 2026-02-26 --slugs q4-vs-q8-quality-loss --action approve --reviewer ops
python scripts/ops-review.py content --queue-date 2026-02-26 --drafts 03-en-tools-quantization-blind-test.md --action reject --reviewer ops --note "low factual value"
```

Dry-run preview:

```bash
python scripts/ops-review.py content --queue-date 2026-02-26 --drafts 03-en-tools-quantization-blind-test.md --action reject --reviewer ops --note "low factual value" --dry-run
```

Optional one-shot commit/push:

```bash
python scripts/ops-review.py content --queue-date 2026-02-26 --drafts 03-en-tools-quantization-blind-test.md --action reject --reviewer ops --note "low factual value" --git-commit --git-push
```

Legacy direct command (still supported):

```bash
python scripts/review-content-drafts.py --queue-date 2026-02-26 --slugs q4-vs-q8-quality-loss --action approve --reviewer ops
```

## 3) Auto-publish command

```bash
python scripts/publish-content-queue.py
```

Optional controls:

```bash
python scripts/publish-content-queue.py --queue-date 2026-02-26 --max-publish 2 --min-score 120
```

Defaults:

- queue date: latest folder in `content-queue`
- max publish: `2` (`LV_CONTENT_AUTO_PUBLISH_MAX`)
- min score: `120` (`LV_CONTENT_AUTO_PUBLISH_MIN_SCORE`)

Only drafts in `approved_auto` / `approved_manual` status are publishable.

## 4) Dedupe behavior

Drafts are skipped when:

- slug already exists in `src/content/blog`
- topic key was already published in previous runs
- candidate topic is too similar to an existing post slug
- run already reached `--max-publish`

## 5) Validation

```bash
python scripts/build-sitemap.py
python scripts/quality-gate.py
```

## 6) CI integration

- `daily-content.yml` now runs: `daily-content-agent.py` -> `review-content-queue.py` -> `publish-content-queue.py`.
- same workflow commits:
  - draft status updates under `content-queue/`
  - `src/data/content-review-log.json`
  - new blog posts in `src/content/blog/`
  - `src/data/content-publish-log.json`
  - updated `src/data/daily-updates.json`

Manual one-shot trigger (CLI):

```powershell
python scripts/run-daily-content-workflow.py `
  --gh-path "C:\Program Files\GitHub CLI\gh.exe" `
  --repo kxz2009-crypto/localvram
```

