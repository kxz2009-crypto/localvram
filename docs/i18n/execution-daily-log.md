# i18n Daily Execution Log

## 2026-03-02 (Done)

### Completed Today
1. Closed non-i18n risk item #1 (localized sitemap depth coverage):
   - Fixed sitemap localization matcher from shallow roots to deep route coverage.
   - Production now serves deep localized URLs in locale sitemaps.
2. Closed non-i18n risk item #2 (Cloudflare/routing drift guard):
   - Strengthened production verification checks (`/`, `/zh`, `/zh/*` variants).
   - Added scheduled GitHub Actions workflow: `Production Routing Guard` (every 6 hours).
3. Closed non-i18n risk item #3 (test/CI gap):
   - Added `scripts/smoke-tests.py`.
   - Added `npm run test:smoke` and wired it to CI.
4. Added i18n progress visibility tool:
   - `scripts/i18n-sitemap-section-report.py`
   - `npm run i18n:sitemap-report`
5. Completed blog route parity wave earlier than planned:
   - Added localized blog detail route: `/{locale}/blog/{slug}/` (10 locales, English slug preserved).
   - Upgraded localized blog index to list locale blog detail links (no forced jump to `/en`).
   - Updated sitemap localization coverage to include `/en/blog/*` for locale expansion.
   - Extended quality gate required pages with locale blog detail route.

### Evidence Snapshot (2026-03-02)
1. `npm run verify:prod:i18n`: all checks passed.
2. `npm run i18n:sitemap-report`:
   - `en_blog_detail_urls=22`
   - `es/pt/fr/de/ru/ja/ko/ar/hi/id blog_detail_urls=22`
   - `blog_parity_ratio_vs_en=1.0` for all 10 locales.
3. Local verification:
   - `npm run check:quality` passed.
   - `npm run build` passed.
   - `npm run test:smoke` passed.

## 2026-03-03 (Plan)

### Tomorrow Scope (single wave, no chaos)
1. Blog copy wave 1 (content quality, not routing):
   - Localize top 5 high-intent blog posts across 10 locales (title/description + key CTA lines).
   - Keep remaining blog detail pages in controlled fallback mode (no 404, no redirect loop).
2. Content policy:
   - Keep glossary terms locked and preserve model/version tokens.
   - Continue slug identity with English for all locales.
3. QA and release gate:
   - Run `npm run i18n:qa-copy`
   - Run `npm run check:quality`
   - Run `npm run build`
   - Run `npm run i18n:sitemap-report`
   - Run `npm run verify:prod:i18n` after deploy

### Exit Criteria for 2026-03-03
1. Blog route parity remains `1.0` in sitemap report.
2. At least 5 blog slugs have localized copy upgraded per locale wave.
3. `/zh*` redirect behavior and canonical/hreflang checks stay green.

## 2026-03-03 (Done)

### Completed Today
1. Finished blog copy wave 1 plus wave 2 step 1-2 (13 slugs total) across 10 locales:
   - Added localized `title` / `description` / `cta_line` in `src/data/i18n-blog-copy.json`.
   - Wave 1 slugs:
     - `best-24gb-vram-models-2026`
     - `rtx4090-vs-rtx3090-for-local-llm`
     - `cuda-out-of-memory-ollama-fixes-2026`
     - `llama-70b-on-rtx-3090-local-setup`
     - `model-qwen3-8b-local-benchmark`
   - Wave 2 step 1 slugs:
     - `model-qwen3-coder-30b-local-benchmark`
     - `best-local-rag-models-2026`
     - `local-vs-cloud-cost-decision-framework`
   - Wave 2 step 2 slugs:
     - `qwen35-35b-vram-requirements-guide`
     - `deepseek-r1-14b-3090-benchmark`
     - `deepseek-r1-32b-when-to-rent-cloud-gpu`
     - `model-qwen2-5-14b-benchmark-refresh`
     - `model-ministral-3-14b-benchmark-refresh`
2. Wired localized blog copy into locale routes:
   - `src/pages/[locale]/blog/[slug].astro`: localized title/description and localized CTA line with English fallback.
   - `src/pages/[locale]/blog/index.astro`: localized post cards for translated slugs and fallback for remaining slugs.
   - `src/lib/i18n-blog-copy.ts`: centralized blog copy resolver and fallback ratio output.
3. Enabled controlled fallback noindex behavior for locale blog pages:
   - Detail page noindex now considers both bridge-copy fallback and slug-localization fallback.
   - Blog index noindex now considers aggregate list fallback ratio.

### Evidence Snapshot (2026-03-03)
1. `npm run i18n:qa-copy`: passed (`issues=0`, `critical=0`, `high=0`).
2. `npm run check:quality`: passed (quality gate green, blog post count `27`).
3. `npm run i18n:sitemap-report`:
   - `en_blog_detail_urls=27`
   - all locales `blog_detail=27`, parity `1.0`.
4. `npm run build`: passed (static build complete).
5. `npm run verify:prod:i18n`: passed (`/zh*` redirect checks and hreflang checks all green).
