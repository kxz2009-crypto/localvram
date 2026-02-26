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

```bash
python scripts/build-conversion-funnel.py
```

Optional window override:

```bash
python scripts/build-conversion-funnel.py --window-days 14
```

## 4) Validation

```bash
python scripts/quality-gate.py
```

Checks include:

- `src/data/conversion-funnel.json` exists
- `funnel` object exists in the generated snapshot
- `/en/status/conversion-funnel/` page exists

## 5) CI integration

- `daily-content.yml` rebuilds conversion funnel snapshot daily.
- `publish-benchmark-artifact.yml` rebuilds conversion funnel snapshot before quality gate and publish commit.

