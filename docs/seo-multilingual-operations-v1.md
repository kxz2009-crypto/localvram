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

## Mandatory change checklist (all issues)

Every fix/update must be reviewed from all three dimensions:

1. English (`/en/` on `localvram.com`)
2. Chinese (`/zh/`, with `.com` to `.cn` cutover safety)
3. Other 10 locales (`es/pt/fr/de/ru/ja/ko/ar/hi/id`)

Minimum acceptance before merge:

1. Route/funnel completeness: index + topic + model + CTA pages are present for affected locale(s).
2. Internal funnel loop: topic -> model -> CTA -> topic links are intact for locale pages.
3. CN guardrail: `LV_ZH_CN_CUTOVER` and `PUBLIC_ZH_SITE_ORIGIN` behavior remains safe.
4. CI gate: `scripts/quality-gate.py` passes (includes global locale guardrail checks).

## Weekly rhythm

1. Maintain one locale KPI row per day in `docs/seo-ops/locale-kpi-tracker.csv`.
2. Keep one content plan row per locale in `docs/seo-ops/locale-content-plan.csv`.
3. Review ranking/indexing regressions per locale; do not aggregate before diagnosis.
