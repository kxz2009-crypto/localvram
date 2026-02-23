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

## Local run

```bash
npm install
npm run dev
```

## Data and automation

- Status freshness: `src/data/status.json`
- Content opportunities: `src/data/content-opportunities.json`
- CTA mapping: `src/data/cta-rules.json`
- Affiliate links: `src/data/affiliate-links.json` (replace placeholders)

## Scripts

- `python scripts/daily-content-agent.py`
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
