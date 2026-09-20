# Evidence and metrics repair

This change prevents family-level test results from being presented as proof for every quantization profile, and separates search-export totals from outbound request counts.

## Measurement identity

Profile pages, calculators, comparisons, recommendations and catalog counts use `getProfileBenchmark`. It requires matching `model_digest` (sha256-prefixed digest) and exact `quantization`, a successful finite-positive throughput result, a valid test time, context size and RTX 3090 hardware. A matching run proves only the reported throughput under its recorded conditions, not memory fit or output quality.

Historical rows lack these identity fields and therefore lose profile-level verification. They remain accessible as explicitly limited tag-level references in the hardware archive and changelog. Do not backfill digests or quantization by guessing from tag names or current downloads.

The weekly collector now reads Ollama `/api/tags` before and after each measured model run. It attaches identity only when both observations match, and records the Ollama version. The API provides digest and `details.quantization_level`: https://docs.ollama.com/api/tags . Collection errors retain the tag-level run without promoting its evidence level.

To restore a profile badge, pin the catalog entry to the actual measured digest and exact quantization, after checking that its displayed name and run command refer to that artifact. The current catalog generator does not automatically pin profiles; this change deliberately leaves legacy profiles unverified. A future catalog identity workflow must preserve reviewed pins when regenerating the catalog. Do not simply mark all Q4 variants as matching Q4_K_M.

## Metrics

- `search_to_affiliate_pct`, `search_to_cloud_pct`, and misleading `affiliate_to_cloud_pct` are null. Without linked sessions and provider orders, no conversion rate is available.
- `cloud_share_of_redirects_pct` is only a distribution within redirect requests. It is null without a denominator.
- The search export's own date range is retained and displayed separately from the redirect window.
- Invalid/future/out-of-window event times are excluded. Import no longer invents a current timestamp for undated activity.
- Referers from unrelated domains no longer masquerade as internal source pages. Decision-page classification includes other locales and root CN routes.
- New telemetry excludes non-GET requests, obvious crawler/check UAs, verified bots and prefetch. Redirect behavior still works. This is not proof that the remaining traffic is human, and historical data cannot be retroactively cleaned without the missing metadata.
- KPI fields `indexed_urls` and `index_rate_pct` become `visible_landing_urls` and `search_visibility_pct`. The refresher migrates old CSVs without dropping historical values. Both status pages can read old columns during transition. The metric counts unique landings with impressions, not indexed URLs. Landings may occur outside the sitemap, so counts must not be clamped to the sitemap size.

## Validation

Run `npm run test:unit`, `npm run check:quality`, `npm run build`, `node scripts/check-evidence-render.mjs`, and `npm run test:smoke`. CI now runs the rendered evidence check after its existing build step.

The Python regressions cover measurement identity, timestamp boundaries, external referers, channel separation and historical KPI migration. JavaScript tests cover quantization/digest isolation and tracking exclusions without breaking redirects. The rendered-page check verifies that unproven profiles do not acquire a hardware-verified badge and that unavailable conversion is visible in multiple locales.

## Remaining product work

This patch does not make the VRAM lookup an architecture-aware estimator, implement the ROI calculator, add session attribution/order reconciliation, or rerun GPU measurements. Those are separate follow-up features and need their own acceptance criteria. Revenue remains unverified until provider settlements and operating costs are reconciled.
