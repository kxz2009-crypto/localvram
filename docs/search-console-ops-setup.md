# Search Console Ops Setup

LocalVRAM uses Google Search Console data to refresh locale KPI rows and keep the affiliate funnel snapshot tied to real landing-page demand.

## Required GitHub configuration

Set one repository variable:

```text
GSC_SITE_URL=sc-domain:localvram.com
```

Set two repository variables for keyless Google auth:

```text
GCP_SERVICE_ACCOUNT=localvram-gsc-reader@project-654db07a-7d13-4204-abd.iam.gserviceaccount.com
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/<project-number>/locations/global/workloadIdentityPools/localvram-github/providers/github
```

JSON-key fallback is still supported, but avoid it when the Google Cloud organization blocks key creation:

```text
GSC_SERVICE_ACCOUNT_JSON=<full Google service account JSON>
```

GitHub path:

```text
Settings -> Secrets and variables -> Actions
```

Use `Variables` for `GSC_SITE_URL`, `GCP_SERVICE_ACCOUNT`, and `GCP_WORKLOAD_IDENTITY_PROVIDER`. Use `Secrets` only for the fallback `GSC_SERVICE_ACCOUNT_JSON`.

## Google Search Console access

1. In Google Cloud, keep the service account `localvram-gsc-reader@project-654db07a-7d13-4204-abd.iam.gserviceaccount.com`.
2. In Google Search Console, open the `localvram.com` domain property.
3. Add the service account email as a user with restricted access or higher.
4. Create a Workload Identity Pool and GitHub provider.
5. Allow `kxz2009-crypto/localvram` GitHub Actions runs to impersonate the service account.

## Workload Identity setup

Run these commands in Google Cloud Shell:

```bash
PROJECT_ID="project-654db07a-7d13-4204-abd"
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")"
SERVICE_ACCOUNT="localvram-gsc-reader@${PROJECT_ID}.iam.gserviceaccount.com"
POOL_ID="localvram-github"
PROVIDER_ID="github"
REPO="kxz2009-crypto/localvram"

gcloud services enable iamcredentials.googleapis.com searchconsole.googleapis.com --project="${PROJECT_ID}"

gcloud iam workload-identity-pools create "${POOL_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="LocalVRAM GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" \
  --display-name="GitHub Actions" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository == '${REPO}'"

gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"
```

Then set GitHub repository variables:

```text
GCP_SERVICE_ACCOUNT=localvram-gsc-reader@project-654db07a-7d13-4204-abd.iam.gserviceaccount.com
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/<project-number>/locations/global/workloadIdentityPools/localvram-github/providers/github
```

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
