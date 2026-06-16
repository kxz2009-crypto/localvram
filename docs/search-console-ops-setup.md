# Search Console Ops Setup

LocalVRAM uses Google Search Console data to refresh locale KPI rows and keep the affiliate funnel snapshot tied to real landing-page demand.

## Required GitHub configuration

Set one repository variable:

```text
GSC_SITE_URL=sc-domain:localvram.com
```

Set one repository secret:

```text
GSC_SERVICE_ACCOUNT_JSON=<full Google service account JSON>
```

GitHub path:

```text
Settings -> Secrets and variables -> Actions
```

Use `Variables` for `GSC_SITE_URL` and `Secrets` for `GSC_SERVICE_ACCOUNT_JSON`.

## Google Search Console access

1. In Google Cloud, create a service account for Search Console automation.
2. Create a JSON key for that service account.
3. In Google Search Console, open the `localvram.com` domain property.
4. Add the service account email as a user with restricted access or higher.
5. Store the complete JSON key in the GitHub secret `GSC_SERVICE_ACCOUNT_JSON`.

## Validation

After the secret is saved, run:

```text
Actions -> Locale KPI Refresh -> Run workflow
```

The workflow should no longer emit `SearchConsoleSyncSkipped`. It should run:

```text
Sync Search Console keywords snapshot
Validate Search Console coverage
Refresh locale KPI rows
```

For affiliate funnel health, run:

```text
Actions -> Affiliate Health Check -> Run workflow
```

The workflow should no longer emit `GSCFreshnessRelaxed`.
