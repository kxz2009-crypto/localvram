# SEO Adoption Log (2026-02-26)

Source input: `d:\Downloads\localvramSEO.txt`

## Adopted now

- Canonical and metadata framework upgrade in `BaseLayout`:
  - explicit `canonicalPath`
  - optional `alternates` (`hreflang`)
  - `robots`, Twitter card, OG locale/site name
  - reusable JSON-LD injection
- Home `/en/` and `/zh/` now use explicit `hreflang` (`en`, `zh`, `x-default`).
- Added structured data for high-value pages:
  - `VRAM Calculator`: `SoftwareApplication` + `HowTo` + `FAQPage`
  - `Quantization Blind Test`: `Dataset` + `FAQPage`
  - `Benchmark Changelog`: `Dataset`
  - `Error KB index`: `FAQPage`
  - `Error KB detail`: `HowTo` + `FAQPage` + `TechArticle` + `BreadcrumbList`
  - `Blog detail`: `BlogPosting` + `BreadcrumbList`
  - `Model detail`: `TechArticle` + `BreadcrumbList`
  - `Model index`: `CollectionPage`
  - `ROI Calculator`: `SoftwareApplication` + `FAQPage`
  - `Cloud GPU page`: `FAQPage`
- Added trust/methodology page:
  - `/en/about/methodology/`
  - linked in global footer
- Added Apple Silicon SEO landing page:
  - `/en/hardware/apple-silicon-llm-guide/`
  - linked from hardware index and home
- Added backend comparison SEO landing page:
  - `/en/guides/ollama-vs-vllm-vram/`
  - linked from home
- Added `404` page with recovery links to model catalog and VRAM calculator.
- Updated sitemap generation to include new pages and rebuilt `public/sitemap.xml`.
- Quality gate validation passed after changes.

## Not adopted now (with reasons)

- Google Indexing API for all model pages:
  - Reason: official support is limited (primarily job posting/live stream content). Using it for all standard content pages is not a stable/official long-term SEO strategy.
  - Alternative used: improved sitemap, stronger internal linking, richer schema, and freshness updates.
- Dynamic OG image generation via server runtime (`@vercel/og`) right now:
  - Reason: current deployment is static-first pipeline; server runtime dependency and image route infra were not yet validated in this environment.
  - Follow-up: can adopt pre-rendered OG generation in build pipeline or add runtime OG after hosting capability validation.
- Newsletter capture component immediate release:
  - Reason: requires privacy/compliance copy, subscription provider integration, and anti-spam handling. Launching a placeholder form without backend would create UX/compliance risk.
  - Follow-up: add provider-backed form in a dedicated small rollout.
- Full Apple Silicon calculator logic in VRAM tool:
  - Reason: requires a validated formula/model matrix for unified memory behavior before exposing production calculations.
  - What we did now: shipped dedicated Apple Silicon guide page as SEO and intent capture entry.

## Next recommended implementation batch

- Add static/build-time OG image generation for model pages and top tools.
- Add dead-link checker script to weekly pipeline and emit report artifact.
- Add newsletter with legal-safe flow (double opt-in + disclosure).

