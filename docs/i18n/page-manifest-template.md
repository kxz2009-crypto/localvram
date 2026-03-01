# i18n Page Manifest Template

## Purpose
This manifest is the single source of truth for page parity across:
- `en` (source locale)
- 10 standard i18n locales on `.com`: `es, pt, fr, de, ru, ja, ko, ar, hi, id`
- special `zh` policy on `.com`: redirect only to `.cn`, never render HTML

If any required locale mapping is missing, release must be blocked.

## Global Rules (Frozen)
1. English (`en`) is the content source of truth.
2. Slugs are identical across locales (no localized slugs).
3. Root path `/` must redirect to `/en/`.
4. `.com` must never serve `/zh` or `/zh/*` HTML.
5. `/zh` and `/zh/*` must 301 to `https://localvram.cn/zh/*` with path and query preserved.

## Manifest Schema
Store one row per English page (`page_id` unique).

| Field | Required | Example | Notes |
|---|---|---|---|
| `page_id` | yes | `models__detail__deepseek-r1` | Stable ID, never reused |
| `route_group` | yes | `models` | `home`, `models`, `guides`, `tools`, `errors`, `blog`, `status`, `hardware`, etc |
| `page_type` | yes | `dynamic` | `static` or `dynamic` |
| `en_path` | yes | `/en/models/deepseek-r1/` | Canonical source path |
| `data_source` | yes if dynamic | `src/data/model-catalog.json` | Primary source for generated pages |
| `locale_path_pattern` | yes | `/{locale}/models/deepseek-r1/` | Must preserve English slug |
| `required_locales` | yes | `es,pt,fr,de,ru,ja,ko,ar,hi,id` | Fixed 10 locales |
| `zh_policy` | yes | `redirect_to_cn` | Always `redirect_to_cn` on `.com` |
| `fallback_allowed` | yes | `true` | Field-level fallback to English allowed |
| `fallback_noindex_threshold_pct` | yes | `20` | If fallback ratio exceeds threshold, page must be `noindex` |
| `owner` | yes | `content-i18n` | Team/person responsible |
| `status` | yes | `ready` | `draft`, `ready`, `blocked`, `deprecated` |

## CSV Starter Template
Use this as the initial seed file (`docs/i18n/page-manifest.csv`).

```csv
page_id,route_group,page_type,en_path,data_source,locale_path_pattern,required_locales,zh_policy,fallback_allowed,fallback_noindex_threshold_pct,owner,status
home__index,home,static,/en/,,/{locale}/,es|pt|fr|de|ru|ja|ko|ar|hi|id,redirect_to_cn,true,20,content-i18n,ready
models__index,models,static,/en/models/,,/{locale}/models/,es|pt|fr|de|ru|ja|ko|ar|hi|id,redirect_to_cn,true,20,content-i18n,ready
models__detail__deepseek-r1,models,dynamic,/en/models/deepseek-r1/,src/data/model-catalog.json,/{locale}/models/deepseek-r1/,es|pt|fr|de|ru|ja|ko|ar|hi|id,redirect_to_cn,true,20,content-i18n,ready
guides__best-coding-models,guides,static,/en/guides/best-coding-models/,,/{locale}/guides/best-coding-models/,es|pt|fr|de|ru|ja|ko|ar|hi|id,redirect_to_cn,true,20,content-i18n,ready
```

## Completeness Gates
Release is blocked if any of these fail:
1. Missing locale mapping for any `page_id`.
2. `en_path` exists but any required locale path is missing.
3. Slug mismatch between English and locale path.
4. Any `.com` manifest entry that attempts to render `zh` content.

## Do-Not-Translate Glossary (Required Input)
Maintain a separate glossary file and enforce placeholder protection during translation.

Minimum protected token categories:
1. Model and product names: `DeepSeek-R1`, `Llama 3.3`, `Ollama`, `GGUF`.
2. Hardware names: `RTX 3090`, `A100`, `H100`.
3. Technical terms: `VRAM`, `tokens/s`, `Q4_K_M`.
4. All versions, numeric values, benchmark units.

## Suggested Ownership
1. `manifest-owner`: updates and validates manifest coverage.
2. `content-owner`: translation quality and glossary enforcement.
3. `release-owner`: gate checks and final go/no-go.

