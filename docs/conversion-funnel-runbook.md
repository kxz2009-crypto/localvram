# Conversion Funnel Runbook

This runbook explains how to keep `Conversion Funnel` data updated in LocalVRAM.

## 1) Data sources

- Search intent: `src/data/search-console-keywords.json`
- Affiliate click export (sanitized): `src/data/affiliate-click-events.json`
- Generated snapshot: `src/data/conversion-funnel.json`

`Conversion Funnel` page:

- `/en/status/conversion-funnel/`

## 2) Affiliate click export format

Use this JSON structure in `src/data/affiliate-click-events.json`:

```json
{
  "updated_at": "2026-02-26T00:00:00Z",
  "source": "cloudflare_kv_export_sanitized",
  "events": [
    {
      "ts": "2026-02-25T23:40:20Z",
      "provider": "runpod",
      "route": "/go/runpod",
      "destination": "https://runpod.io?ref=...",
      "referer": "https://localvram.com/en/models/qwen3-8b-q4/"
    }
  ]
}
```

Recommended: exclude IP/user-agent fields from committed snapshots.

## 3) Build conversion snapshot

If you have a fresh raw export (JSON/JSONL/NDJSON), import it first:

```bash
python scripts/import-affiliate-events.py --source-file logs/affiliate-events-export.jsonl --source-label "cloudflare-kv-2026-02-26"
```

Then build conversion snapshot:

```bash
python scripts/build-conversion-funnel.py
```

Optional window override:

```bash
python scripts/build-conversion-funnel.py --window-days 14
```

Cloudflare KV direct export (recommended for automation):

```bash
python scripts/export-affiliate-kv-events.py \
  --account-id "$CF_ACCOUNT_ID" \
  --api-token "$CF_API_TOKEN" \
  --namespace-id "$CF_AFFILIATE_EVENTS_NAMESPACE_ID" \
  --output-file logs/affiliate-events-export.json
```

## 3.1) One-shot refresh (import -> build -> validate -> optional commit/push)

Use the helper script to run the full pipeline in one command:

```bash
python scripts/refresh-affiliate-funnel.py --source-file logs/affiliate-events-export.jsonl
```

Include commit + push after a successful refresh:

```bash
python scripts/refresh-affiliate-funnel.py --source-file logs/affiliate-events-export.jsonl --git-commit --git-push
```

Useful options:

- `--source-format auto|json|jsonl`
- `--source-label <label>`
- `--window-days 30`
- `--skip-quality-gate`
- `--commit-message "data: refresh affiliate events and conversion funnel"`

## 4) Validation

```bash
python scripts/quality-gate.py
```

Checks include:

- `src/data/affiliate-click-events.json` exists with an `events` array
- `src/data/conversion-funnel.json` exists
- `funnel` object exists in the generated snapshot
- `/en/status/conversion-funnel/` page exists

Optional strict health check:

```bash
python scripts/check-affiliate-funnel-health.py
```

## 5) CI integration

- `daily-content.yml` rebuilds conversion funnel snapshot daily.
- `daily-content.yml` optionally syncs Cloudflare KV affiliate events before rebuilding funnel snapshot.
- `publish-benchmark-artifact.yml` rebuilds conversion funnel snapshot before quality gate and publish commit.
- `affiliate-health-check.yml` validates route mapping + live redirects and enforces funnel health.
