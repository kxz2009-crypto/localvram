# SEO Multilingual Operations v1

Effective date: 2026-02-27

## Scope

- `localvram.com`:
  - Primary English (`/en/`)
  - Expansion locales: `/es/`, `/pt/`, `/fr/`, `/de/`, `/ru/`, `/ja/`, `/ko/`, `/ar/`, `/hi/`, `/id/`
- `localvram.cn`:
  - Chinese primary (`/zh/`)

## Operating model

1. Content topics can be reused across locales.
2. SEO execution is split by locale:
   - independent keyword pools
   - independent internal-link priorities
   - independent publish cadence
3. Operations are split by domain:
   - `.com` and `.cn` tracked separately
   - no mixed-domain indexing pushes

## Technical policy

1. Canonical:
   - `en/es/pt/fr/de/ru/ja/ko/ar/hi/id` canonical on `https://localvram.com`
   - `zh` canonical on `https://localvram.cn`
2. `hreflang`:
   - `en`, `es`, `pt`, `fr`, `de`, `ru`, `ja`, `ko`, `ar`, `hi`, `id`, `zh-CN`, `x-default`
3. Sitemap:
   - `https://localvram.com/sitemap.xml` contains `.com` locale URLs
   - `https://localvram.cn/sitemap-cn.xml` contains Chinese URLs only

## Weekly rhythm

1. Maintain one locale KPI row per day in `docs/seo-ops/locale-kpi-tracker.csv`.
2. Keep one content plan row per locale in `docs/seo-ops/locale-content-plan.csv`.
3. Review ranking/indexing regressions per locale; do not aggregate before diagnosis.
