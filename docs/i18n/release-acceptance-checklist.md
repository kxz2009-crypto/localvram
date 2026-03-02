# i18n Release Acceptance Checklist

## Scope
This checklist is for releasing:
- `.com`: `en + es, pt, fr, de, ru, ja, ko, ar, hi, id`
- `.cn`: independent `zh` operation
- `.com /zh*`: redirect only

## Fixed Rollback Point
Current rollback baseline:
- commit: `82e8c3e`
- tag: `rollback-i18n-20260301-c22`
- branch: `main` (tagged checkpoint)

If release goes wrong, rollback to the tag above.

## Phase 0: Pre-Deploy Gate
0. Run readiness audit:
   - `python scripts/i18n-readiness.py`
1. `Page Manifest` coverage is complete for all `page_id`.
2. English-to-10-locale page parity check passes.
3. `zh_policy` is `redirect_to_cn` for all `.com` pages.
4. SEO matrix checks all pass:
   - canonical self-reference
   - hreflang cluster completeness
   - `x-default` to English path
5. Fallback ratio check passes per locale threshold.
6. Internal link scanner finds no forbidden cross-locale links:
   - `python scripts/check-locale-links.py`
7. Translation quality report is generated and reviewed:
   - `npm run i18n:qa-copy`
   - review `dist/seo-audit/i18n-translation-qa.json` (`top_review_queue`, `manual_review_queue`)
8. RTL validation (`ar`) is visually accepted.
9. Non-rollout locales are forced `noindex` even when copy is prefilled.

## Phase 1: Cloudflare Rules (Simple + Stable)
Keep only durable rules:
1. `/zh` -> `https://localvram.cn/zh/` (`301`)
2. `/zh/*` -> `https://localvram.cn/zh/:splat` (`301`, preserve query)
3. Root `/` -> `/en/` (canonical root redirect)

Do not rely on temporary emergency rules long-term.

## Phase 2: Deploy Sequence
1. Deploy target commit to Cloudflare Pages production.
2. Confirm deployment status is `Success` and `Active`.
3. Purge cache for `localvram.com` zone (`Purge Everything`).

## Phase 3: Route + SEO Verification (PowerShell)
Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify-production-i18n.ps1
```

Optional custom domains:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify-production-i18n.ps1 -ComDomain "https://localvram.com" -CnDomain "https://localvram.cn"
```

Expected:
1. 11 locale roots on `.com` behave as planned (normally 200).
2. `/zh/` and `/zh/*` always 301 to `https://localvram.cn/zh/*` with query preserved.
3. `/en/` hreflang cluster includes `en + 10 locales + x-default` and excludes `zh-CN`.

## Phase 5: Post-Release Monitoring (7-14 days)
1. Monitor Cloudflare 404 logs by locale.
2. Monitor redirect hit volume for `/zh*`.
3. Monitor GSC/Bing for:
   - hreflang conflicts
   - duplicate canonical
   - excluded by noindex spikes

## Emergency Rollback
Use only if release causes SEO or routing instability.

1. In Cloudflare Pages, redeploy the rollback tag commit (`rollback-i18n-20260301-c22`) to production.
2. Purge cache for `localvram.com` zone (`Purge Everything`).
3. Re-run `scripts/verify-production-i18n.ps1` and confirm all checks pass.
