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
1. Finished blog copy wave 1 plus wave 2 step 1-5 (27 slugs total) across 10 locales:
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
   - Wave 2 step 3 slugs:
     - `deepseek-r1-on-rtx-3090-what-works`
     - `qwen35-122b-cloud-vs-local-cost`
     - `q4-vs-q8-quality-loss-ollama`
     - `24gb-vram-models-that-actually-run`
     - `best-local-rag-models-under-24gb-vram`
   - Wave 2 step 4 slugs:
     - `16gb-vram-model-selection-guide`
     - `llama4-local-inference-feasibility-check`
     - `qwen25-coder-32b-self-host-guide`
     - `ollama-local-cluster-network-checklist`
   - Wave 2 step 5 slugs:
     - `en-tools-quantization-blind-test`
     - `fix-ollama-cuda-out-of-memory`
     - `local-llm-customer-support-rag-stack`
     - `still-the-vram-king-rtx-3090-2026`
     - `weekly-verified-models-2026-02-24`
2. Wired localized blog copy into locale routes:
   - `src/pages/[locale]/blog/[slug].astro`: localized title/description and localized CTA line with English fallback.
   - `src/pages/[locale]/blog/index.astro`: localized post cards for translated slugs and fallback for remaining slugs.
   - `src/lib/i18n-blog-copy.ts`: centralized blog copy resolver and fallback ratio output.
3. Enabled controlled fallback noindex behavior for locale blog pages:
   - Detail page noindex now considers both bridge-copy fallback and slug-localization fallback.
   - Blog index noindex now considers aggregate list fallback ratio.
4. Reduced i18n core copy fallback debt to zero:
   - Filled remaining locale fallback fields in `src/data/i18n-copy.json` (ticker labels, locale meta titles, and page labels).
   - `i18n-readiness` summary now reports `fallback_ratio=0.0` across all tracked pages/locales.
5. Added anti-regression quality gate for blog localization coverage:
   - `scripts/quality-gate.py` now requires `src/data/i18n-blog-copy.json`.
   - Gate validates non-empty localized fields and enforces minimum blog-copy coverage ratio.
6. Completed translation-pack fill for tracked wave locales:
   - Filled all remaining empty `translation` rows in wave packs by syncing from current `i18n-copy.json` locale fields.
   - Updated packs: `wave2/{fr,de,ru}` and `wave3/{ar,hi,id,ko}` to full phrase coverage.
7. Added missing translation-pack files for core rollout locales:
   - Created `wave1/{es,pt,ja}` pack files with full `131/131` phrase coverage.
   - Pack-level coverage now spans all 10 standard locales.
8. Hardened pack validation rule:
   - `scripts/validate-i18n-packs.py` now fails when any standard locale pack is missing.
   - Also fails when duplicate pack files exist for the same locale.
9. Added weekly acceptance automation for i18n:
   - Added workflow `.github/workflows/weekly-i18n-acceptance.yml` (runs every Monday and supports manual dispatch).
   - Workflow executes readiness, locale-link checks, translation QA, sitemap parity, quality gate, build, and production verify.

### Evidence Snapshot (2026-03-03)
1. `npm run i18n:qa-copy`: passed (`issues=0`, `critical=0`, `high=0`).
2. `npm run check:quality`: passed (quality gate green, blog post count `27`).
3. `npm run i18n:sitemap-report`:
   - `en_blog_detail_urls=27`
   - all locales `blog_detail=27`, parity `1.0`.
4. `npm run build`: passed (static build complete).
5. `npm run verify:prod:i18n`: passed (`/zh*` redirect checks and hreflang checks all green).
6. `npm run i18n:readiness`: passed, all locales ready and no fallback fields remaining in tracked pages.
7. `npm run check:quality`: passed with i18n blog copy coverage check (`localized=27/27`, `coverage=1.000`).
8. `python scripts/i18n-pack-status.py`: all tracked packs now `131/131` (`100.0%`).
9. `python scripts/validate-i18n-packs.py`: passes with `packs=10`, `source_phrases=131`.
10. `npm run check:quality`: confirms strict locale-pack validation passes in gate path.
11. Weekly acceptance automation is available in Actions as `Weekly i18n Acceptance`.
