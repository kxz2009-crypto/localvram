# i18n SEO Field Matrix

## Purpose
Define mandatory SEO fields per page for:
- `.com`: `en + 10 locales` (`es, pt, fr, de, ru, ja, ko, ar, hi, id`)
- `.cn`: `zh-CN` primary operation, and part of cross-domain hreflang mapping

## Hard SEO Rules
1. Canonical must be self-referential per locale page.
2. All `.com` locale variants of the same `page_id` must share one hreflang cluster.
3. `.com` hreflang cluster must include:
   - `en, es, pt, fr, de, ru, ja, ko, ar, hi, id`
   - `zh-CN` -> mapped `https://localvram.cn/*` URL
   - `x-default` -> English equivalent path
4. `.com` must publish cross-domain `zh-CN` hreflang entries pointing to `.cn`.
5. `/zh*` on `.com` must always return redirect response, never HTML content.
6. Trailing slash policy must be consistent in canonical and hreflang links.

## Per-Page SEO Matrix
Track this for each `page_id` and locale.

| Field | Required | Validation |
|---|---|---|
| `title` | yes | non-empty, locale language, no placeholder token |
| `meta_description` | yes | non-empty, locale language, no placeholder token |
| `canonical_url` | yes | equals current locale URL with canonical trailing slash |
| `robots` | yes | `index, follow` unless gated fallback over threshold |
| `og:title` | yes | aligned with title |
| `og:description` | yes | aligned with description |
| `og:url` | yes | equals canonical URL |
| `og:locale` | yes | valid locale mapping |
| `hreflang_set` | yes | exact `11 .com locales + zh-CN + x-default` |
| `structured_data_lang` | yes | locale-consistent schema language |
| `internal_links_locale` | yes | no accidental cross-locale links except language switcher |

## Locale Mapping for OG
Use this fixed mapping:

| Locale | og:locale |
|---|---|
| `en` | `en_US` |
| `es` | `es_ES` |
| `pt` | `pt_BR` |
| `fr` | `fr_FR` |
| `de` | `de_DE` |
| `ru` | `ru_RU` |
| `ja` | `ja_JP` |
| `ko` | `ko_KR` |
| `ar` | `ar_SA` |
| `hi` | `hi_IN` |
| `id` | `id_ID` |

## URL Examples by Page ID
Given `page_id = guides__best-coding-models`:
- English canonical: `https://localvram.com/en/guides/best-coding-models/`
- Japanese canonical: `https://localvram.com/ja/guides/best-coding-models/`
- x-default: `https://localvram.com/en/guides/best-coding-models/`

## Fallback and Indexing
Field-level fallback to English is allowed when translation fails, but:
1. Calculate fallback ratio by visible content fields.
2. If ratio exceeds threshold (recommended `20%`), force `noindex, follow`.
3. Remove `noindex` only after translation backfill is complete.

## Forbidden States (Release Blockers)
1. Canonical points to different locale path.
2. Missing any required hreflang variant in the cluster.
3. `x-default` points to non-English URL.
4. Any `.com` page misses `zh-CN` hreflang or points it to non-`.cn` URL.
5. Any `.com` page under `/zh*` renders HTML.
6. Broken trailing slash normalization causes duplicate canonical URLs.

## Suggested Artifact Files
1. `dist/seo-audit/pages.csv` (page-level SEO fields)
2. `dist/seo-audit/hreflang-clusters.csv` (cluster parity)
3. `dist/seo-audit/fallback-ratio.csv` (fallback gating)
