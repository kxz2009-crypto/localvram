# i18n Translation Pack Workflow

Use this workflow to fill locale copy in controlled waves without changing rollout routing.

## 1) Export Phrase Template

```powershell
python scripts/export-i18n-translation-template.py --locale fr
```

Or export all standard locales in one run:

```powershell
python scripts/export-i18n-translation-template.py --all
```

Default output:

- `dist/seo-audit/i18n-template-fr.json`

Template includes all unique English phrases currently used by `src/data/i18n-copy.json`.

For tracked wave files, use repo paths such as:

- `src/data/i18n-packs/wave2/i18n-template-fr.json`
- `src/data/i18n-packs/wave2/i18n-template-de.json`
- `src/data/i18n-packs/wave2/i18n-template-ru.json`

## 2) Fill Translations

Edit the exported file:

- keep `en` as source text
- set `translation` values
- preserve placeholders exactly, e.g. `{localeUpper}`, `{modelName}`

## 3) Apply Pack

```powershell
python scripts/apply-i18n-translation-pack.py --locale fr --pack dist/seo-audit/i18n-template-fr.json --strict
```

`--strict` requires every source phrase in pack to be translated.

Dry-run validation (no write):

```powershell
python scripts/apply-i18n-translation-pack.py --locale fr --pack src/data/i18n-packs/wave2/i18n-template-fr.json --strict --dry-run
```

Batch apply one wave directory:

```powershell
python scripts/apply-i18n-wave.py --wave-dir src/data/i18n-packs/wave2 --locales fr,de,ru --strict --dry-run
```

## 4) Validate

```powershell
python scripts/i18n-pack-status.py
python scripts/validate-i18n-packs.py
python scripts/quality-gate.py
npm run i18n:readiness
npm run build
```

## 5) Rollout Rule

- Filling copy does **not** automatically enable indexability.
- Only locales listed in `src/data/i18n-rollout.json` are rollout locales.
- Non-rollout locales stay `noindex` by policy.
- Readiness treats direct English copy as fallback (except placeholder-only tokens like `{itemDescription}`).
