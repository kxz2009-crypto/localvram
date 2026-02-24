# LocalVRAM

Production domain: `https://localvram.com`

Repository: `https://github.com/kxz2009-crypto/localvram/`

## Stack

- Static site: Astro
- Host/CDN: Cloudflare Pages
- Automation: GitHub Actions + Python scripts
- Benchmark runner: self-hosted label `3090-WSL2`

## Cloudflare Pages Setup

- Framework preset: `Astro`
- Build command: `npm run build`
- Build output directory: `dist`
- Root directory: `/`
- Environment variable: `NODE_VERSION=20`

## Affiliate Redirects (Cloudflare Workers on Pages Functions)

Affiliate URLs are routed through first-party short links to reduce ad-block loss:

- `/go/runpod` -> RunPod referral URL
- `/go/vast` -> Vast.ai referral URL
- `/recommends/rtx-3090-24gb` -> Amazon search + affiliate tag
- `/recommends/rtx-4090-24gb` -> Amazon search + affiliate tag

Configure in Cloudflare Pages:

- `AMAZON_TAG` (required for Amazon commissions)
- `RUNPOD_REF` (optional, default: `kzc9gtvv`)
- `VAST_REF_ID` (optional, default: `415258`)
- KV binding `AFFILIATE_EVENTS` (optional, stores click events for 30 days)

## Local run

```bash
npm install
npm run dev
```

## Data and automation

- Status freshness: `src/data/status.json`
- Content opportunities: `src/data/content-opportunities.json`
- Search Console backfeed: `src/data/search-console-keywords.json`
- CTA mapping: `src/data/cta-rules.json`
- Model catalog (200+): `src/data/model-catalog.json`
- Affiliate links: `src/data/affiliate-links.json` (replace placeholders)
- Affiliate redirect worker code: `functions/`

## Scripts

- `python scripts/daily-content-agent.py`
- `python scripts/build-model-catalog.py`
- `python scripts/build-sitemap.py`
- `python scripts/quality-gate.py`
- `python scripts/weekly-benchmark.py`
- `python scripts/cluster-benchmark.py`
- `python scripts/report-data-freshness.py`

## Logo

Default connected set:

- `public/branding/logo.svg`
- `public/branding/logo-mark.svg`
- `public/favicon.svg`
- `public/branding/ollama-verified-pill.svg`

To switch logo direction, copy files from `branding/logo-options/*`.
