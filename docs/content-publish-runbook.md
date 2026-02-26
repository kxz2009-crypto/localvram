# Content Publish Runbook

This runbook covers auto-publishing queue drafts into live blog posts.

## 1) Source and output

- Queue source: `content-queue/<YYYY-MM-DD>/*.md`
- Blog output: `src/content/blog/*.md`
- Publish log: `src/data/content-publish-log.json`
- Status page: `/en/status/content-publish/`

## 2) Auto-publish command

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

## 3) Dedupe behavior

Drafts are skipped when:

- slug already exists in `src/content/blog`
- topic key was already published in previous runs
- candidate topic is too similar to an existing post slug
- run already reached `--max-publish`

## 4) Validation

```bash
python scripts/build-sitemap.py
python scripts/quality-gate.py
```

## 5) CI integration

- `daily-content.yml` runs `publish-content-queue.py` after draft generation.
- same workflow commits:
  - new blog posts in `src/content/blog/`
  - `src/data/content-publish-log.json`
  - updated `src/data/daily-updates.json`

