# i18n Translation Quality Review

Use this after translation packs are applied and before production rollout changes.

## 1) Generate QA Report

```powershell
npm run i18n:qa-copy
```

Output:

- `dist/seo-audit/i18n-translation-qa.json`

Optional export to checklist CSV:

```powershell
npm run i18n:export-review-csv
```

- output: `dist/seo-audit/i18n-manual-review-checklist.csv`

## 2) Read Two Queues

1. `top_review_queue`
   - Auto-detected risk items (`critical/high/medium`).
   - If non-empty, fix these first.
2. `manual_review_queue`
   - Fixed high-priority manual sampling list across locales/pages.
   - Use this even when auto issues are zero.

## 3) Manual Review Rule (Simple)

For each sampled row, verify:

1. Meaning is correct and complete.
2. Placeholder variables are preserved exactly (`{localeUpper}`, `{itemTitle}`, etc.).
3. Protected terms are preserved (VRAM, Ollama, CUDA, ROCm, model names).
4. No token artifacts or garbled text.
5. CTA labels and SEO fields (`meta_title`, `meta_description`) are natural.

## 4) Escalation

If major quality problems are found:

1. Fix affected locale entries in `src/data/i18n-copy.json`.
2. Re-run:
   - `npm run i18n:qa-copy`
   - `python scripts/quality-gate.py`
   - `npm run build`
