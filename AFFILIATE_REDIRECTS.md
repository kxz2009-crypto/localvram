# Affiliate Redirects on Cloudflare

This project uses Cloudflare Pages Functions as first-party redirect routes.

## Why

- Reduces ad-block filtering of direct affiliate links.
- Keeps URLs clean: `localvram.com/go/*` and `localvram.com/recommends/*`.
- Centralized link maintenance and click logging.

## Routes

- `GET /go/runpod`
- `GET /go/vast`
- `GET /recommends/rtx-3090-24gb`
- `GET /recommends/rtx-4090-24gb`
- `GET /recommends/atx3-1000w-psu`
- `GET /recommends/high-airflow-case`

Source files:

- `functions/go/[provider].js`
- `functions/recommends/[slug].js`
- `functions/_lib/affiliate.js`

## Cloudflare Pages Configuration

Add environment variables in Pages project settings:

- `AMAZON_TAG` (required for Amazon commissions)
- `RUNPOD_REF` (optional, default `kzc9gtvv`)
- `VAST_REF_ID` (optional, default `415258`)
- `AMAZON_3090_URL` (optional override for `/recommends/rtx-3090-24gb`)
- `AMAZON_4090_URL` (optional override for `/recommends/rtx-4090-24gb`)
- `AMAZON_PSU_URL` (optional override for `/recommends/atx3-1000w-psu`)
- `AMAZON_CASE_URL` (optional override for `/recommends/high-airflow-case`)

Optional KV binding for click events:

- Binding name: `AFFILIATE_EVENTS`
- Namespace type: KV
- TTL: managed in code (30 days)

## Click Tracking

Every redirect logs a structured event via `console.log`.
If `AFFILIATE_EVENTS` is bound, events are also persisted in KV with 30-day TTL.

## Adding More Affiliate Platforms

1. Open `functions/_lib/affiliate.js`.
2. Extend `buildProviderTarget()` for provider routes (`/go/*`) or
   `AMAZON_RECOMMENDATIONS` for product routes (`/recommends/*`).
3. Add a short link in `src/data/affiliate-links.json`.
4. Update page CTAs to use the short link.
