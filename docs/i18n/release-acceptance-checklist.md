# i18n Release Acceptance Checklist

## Scope
This checklist is for releasing:
- `.com`: `en + es, pt, fr, de, ru, ja, ko, ar, hi, id`
- `.cn`: independent `zh` operation
- `.com /zh*`: redirect only

## Fixed Rollback Point
Current rollback baseline:
- commit: `ff67f00`
- tag: `rollback-i18n-20260301-c4`
- branch: `main` (tagged checkpoint)

If release goes wrong, rollback to the tag above.

## Phase 0: Pre-Deploy Gate
1. `Page Manifest` coverage is complete for all `page_id`.
2. English-to-10-locale page parity check passes.
3. `zh_policy` is `redirect_to_cn` for all `.com` pages.
4. SEO matrix checks all pass:
   - canonical self-reference
   - hreflang cluster completeness
   - `x-default` to English path
5. Fallback ratio check passes per locale threshold.
6. Internal link scanner finds no forbidden cross-locale links.
7. RTL validation (`ar`) is visually accepted.

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

## Phase 3: Route Verification (PowerShell)
Run from repo root:

```powershell
$domain='https://localvram.com'
$locales=@('en','es','pt','fr','de','ru','ja','ko','ar','hi','id')

Write-Host "== Locale roots =="
foreach($l in $locales){
  $url="$domain/$l/"
  $resp = curl.exe -s -I $url
  $status = (($resp | Select-String '^HTTP/1.1 ') | Select-Object -Last 1).Line
  $loc = (($resp | Select-String '^Location:' | Select-Object -First 1).Line)
  if(-not $loc){$loc='Location: (none)'}
  "$l`t$status`t$loc"
}

Write-Host "`n== zh redirect behavior =="
curl.exe -I "$domain/zh/"
curl.exe -I "$domain/zh/test-path?utm_source=check"
```

Expected:
1. 11 locale roots on `.com` behave as planned (normally 200).
2. `/zh/` and `/zh/*` always 301 to `https://localvram.cn/zh/*` with query preserved.

## Phase 4: SEO Verification (PowerShell)
```powershell
$domain='https://localvram.com'
curl.exe -s "$domain/sitemap-index.xml" | Select-String -Pattern 'sitemap-en.xml|sitemap-es.xml|sitemap-ja.xml|sitemap-ko.xml'
curl.exe -s "$domain/sitemap-en.xml" | Select-String -Pattern '/zh/|/en/'
curl.exe -s "$domain/sitemap.xml" | Select-String -Pattern 'sitemap-en.xml'
curl.exe -s "$domain/en/" | Select-String -Pattern 'canonical|hreflang|x-default'
curl.exe -s "$domain/ja/" | Select-String -Pattern 'canonical|hreflang|x-default'
```

Expected:
1. Sitemap index lists only currently rollout-enabled locale sitemaps.
2. No `.com` sitemap entries under `/zh/`.
3. Canonical and hreflang tags are present and consistent.

## Phase 5: Post-Release Monitoring (7-14 days)
1. Monitor Cloudflare 404 logs by locale.
2. Monitor redirect hit volume for `/zh*`.
3. Monitor GSC/Bing for:
   - hreflang conflicts
   - duplicate canonical
   - excluded by noindex spikes

## Emergency Rollback
Use only if release causes SEO or routing instability.

```powershell
git checkout main
git reset --hard rollback-i18n-baseline-20260301
git push --force-with-lease origin main
```

Then redeploy Pages and purge cache.
