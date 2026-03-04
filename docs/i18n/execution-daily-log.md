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
10. Closed Week 1 non-blog hardware parity gap:
   - Added `src/pages/[locale]/hardware/index.astro` and `src/pages/[locale]/hardware/[slug].astro`.
   - Added hardware locale route files to `scripts/quality-gate.py` required page list (prevents regression).
   - Updated `scripts/build-sitemap.py` to include `/en/hardware/` in localizable prefixes so locale sitemaps include hardware index and tier routes.
11. Extended sitemap section observability:
   - `scripts/i18n-sitemap-section-report.py` now emits `key_section_parity_ratio_vs_en` for `home/tools/errors/status/guides/hardware/models`.
12. Added hard gate for key-section parity:
   - Added `scripts/check-i18n-section-parity.py` and npm script `i18n:check-section-parity`.
   - Wired `Weekly i18n Acceptance` to fail when any key section parity is not `1.0` for rollout locales.
13. Elevated key-section parity to daily quality gate:
   - `scripts/quality-gate.py` now runs `i18n-sitemap-section-report.py` and `check-i18n-section-parity.py`.
   - `npm run check:quality` now blocks merges when key section parity drifts.
14. Added diff-friendly parity artifact:
   - Added `scripts/export-i18n-section-parity-summary.py` and npm script `i18n:section-parity-summary`.
   - Workflow now uploads `dist/seo-audit/i18n-section-parity-summary.json` via existing `dist/seo-audit` artifact bundle.
15. Added automatic week-over-week parity drift diff:
   - Added `scripts/diff-i18n-section-parity.py` and npm script `i18n:section-parity-diff`.
   - `Weekly i18n Acceptance` now compares current summary with previous successful run artifact and emits `dist/seo-audit/i18n-section-parity-diff.json`.
   - Workflow summary now includes `section-parity-drift-detected: true|false`.
16. Hardened artifact persistence after build:
   - Workflow now copies parity JSONs to `logs/seo-audit/` before `build` so they are not lost when Astro rebuilds `dist/`.
   - Artifact upload now explicitly includes `logs/seo-audit/i18n-sitemap-section-report.json`, `i18n-section-parity-summary.json`, and `i18n-section-parity-diff.json`.
17. Added backward-compatible previous-artifact lookup:
   - Diff step now reads previous summary from `logs/seo-audit/i18n-section-parity-summary.json` first, with fallback to legacy `dist/seo-audit/...`.
18. Hardened failure-path observability in weekly acceptance:
   - Added explicit step `id` markers across i18n acceptance stages.
   - `Publish workflow summary` now runs with `if: always()` and reports each step `outcome` (`success`/`failure`/`skipped`).
   - `Upload acceptance artifacts` now runs with `if: always()` and `if-no-files-found: warn`.
   - `Preserve section parity artifacts` now runs with `if: always()` and uses guarded copy logic to avoid hiding root-cause failures.

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
12. `python scripts/build-sitemap.py`: locale sitemap counts increased from `627` to `632` after hardware locale route inclusion.
13. `python scripts/i18n-sitemap-section-report.py`: all locales show key parity `home/tools/errors/status/guides/hardware/models = 1.0`.
14. `python scripts/check-i18n-section-parity.py`: passed for 10 locales and 7 key sections.
15. `npm run check:quality`: passed with embedded sitemap section report + key section parity checks.
16. `python scripts/export-i18n-section-parity-summary.py`: generated summary JSON with `mismatch_count=0`.
17. `python scripts/diff-i18n-section-parity.py` (self-compare smoke): generated diff JSON with `has_drift=false`.
18. `npm run check:quality`: passed after workflow hardening update; parity checks and i18n coverage remain green.
19. GitHub Actions `Weekly i18n Acceptance` manual run `22634503056`: passed with all stages green; summary/artifact steps executed successfully.
20. Added failure alert loop for weekly acceptance:
   - Workflow now has `issues: write` permission.
   - On job failure, it auto-creates or updates issue `[i18n] Weekly acceptance failure tracker` with run URL and per-step outcomes.
21. GitHub Actions `Weekly i18n Acceptance` manual run `22635290030`: passed; failure-issue step was correctly skipped on success path.
22. Automated weekly rollback checkpoint tagging on acceptance success:
   - `Weekly i18n Acceptance` now creates/pushes `rollback-i18n-week-YYYYMMDD` tag on successful runs (idempotent).
   - Workflow summary now reports `rollback-checkpoint-tag` outcome; artifact bundle includes `logs/rollback-checkpoint-tag.log`.
23. GitHub Actions `Weekly i18n Acceptance` manual run `22635501319`: passed with `Create weekly rollback checkpoint tag = success`.
24. Verified remote tag exists: `rollback-i18n-week-20260303` on `origin`.
25. Hardened `Production Routing Guard` observability:
   - Standardized verify log output (`logs/verify-production-i18n.log`) with start/end and exit code.
   - Failure alert now reads `logs/failure-context.json` to include concrete exit-code detail in issue body.
   - Added always-on workflow summary and artifact upload (`production-routing-guard`).
26. GitHub Actions `Production Routing Guard` manual run `22635720599`: passed; `alert-issue` skipped on success path, summary/artifacts uploaded.
27. Hardened weekly i18n failure lifecycle:
   - Added success-path step `Resolve failure issue on recovery` to close open `[i18n] Weekly acceptance failure tracker`.
   - Reordered weekly summary/artifact steps after issue-sync logic so outcomes include `open-failure-issue` and `resolve-failure-issue`.
   - Added `logs/weekly-i18n-issue-sync.log` to acceptance artifacts for audit trace.
28. GitHub Actions `Weekly i18n Acceptance` manual run `22635918000`: passed; `resolve-failure-issue` executed successfully and issue-sync outcomes are now visible in summary.
29. Added parity-drift issue lifecycle automation:
   - New step `Sync parity drift issue` auto-opens/updates `[i18n] Weekly section parity drift tracker` when `has_drift=true`.
   - Automatically closes tracker when `has_drift=false` on successful weekly runs.
   - Added `logs/weekly-i18n-parity-drift.log` artifact and summary outcome `sync-parity-drift-issue`.
30. GitHub Actions `Weekly i18n Acceptance` manual run `22652502200`: passed; `sync-parity-drift-issue` executed successfully with no open drift tracker issue.
31. Added RTL manual acceptance system:
   - Added checklist doc `docs/i18n/rtl-visual-acceptance-checklist.md` (required URLs + visual checks + pass criteria).
   - Added signoff record file `docs/i18n/rtl-visual-signoff.json`.
   - Added gate script `scripts/check-rtl-visual-signoff.py` and npm command `i18n:check-rtl-signoff`.
   - Wired `Weekly i18n Acceptance` to enforce RTL signoff recency and publish `logs/i18n-rtl-signoff.log`.
32. GitHub Actions `Weekly i18n Acceptance` manual run `22652826579`: passed with `rtl-visual-signoff: success` and all other acceptance gates green.

## 2026-03-04 (Done)

### Completed Today
1. Enabled AI-assisted i18n QA using Gemini in weekly acceptance:
   - `scripts/audit-i18n-translation-quality.py` now supports `--ai-review` with Gemini API.
   - Added structured AI review output (`ai_review` summary + AI-origin issues in report JSON).
   - Added `.env.example` keys: `GEMINI_API_KEY`, `GEMINI_MODEL`.
2. Wired weekly workflow to execute AI QA:
   - `i18n translation QA` now runs with Gemini environment variables and `--ai-review`.
3. Hardened weekly parity-diff step against transient GitHub API failures:
   - Added retry wrapper for previous-run/artifact fetch and artifact-zip download.
   - Added graceful fallback to local-only diff when remote artifact fetch fails.
4. Enforced non-silent AI fallback behavior:
   - `Weekly i18n Acceptance` now runs `--ai-review --ai-required`.
   - If `GEMINI_API_KEY` is absent in Actions, the QA step fails instead of silently skipping AI.
5. Triggered and validated weekly acceptance runs:
   - Run `22665294185`: failed due to transient `gh api` HTTP 502 in parity-diff step (now fixed).
   - Run `22665392792`: passed after retry/fallback hardening.
   - Run `22667390778`: passed with Gemini secret present and AI review active.

### Evidence Snapshot (2026-03-04)
1. GitHub Actions `Weekly i18n Acceptance` run `22667390778`: passed (all critical gates green).
2. `i18n translation QA` logs on run `22667390778`:
   - `GEMINI_API_KEY: ***` (secret injected)
   - `ai_status=completed`
   - `ai_flagged=0`
3. Local gate check:
   - `npm run check:quality` passed with `i18n blog copy checks ok: localized=29/29 coverage=1.000`.
