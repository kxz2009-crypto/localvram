# i18n Translation Pack Workflow

Use this workflow to fill locale copy in controlled waves without changing rollout routing.

## 1) Export Phrase Template

```powershell
python scripts/export-i18n-translation-template.py --locale fr
```

Default output:

- `dist/seo-audit/i18n-template-fr.json`

Template includes all unique English phrases currently used by `src/data/i18n-copy.json`.

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

## 4) Validate

```powershell
python scripts/quality-gate.py
npm run i18n:readiness
npm run build
```

## 5) Rollout Rule

- Filling copy does **not** automatically enable indexability.
- Only locales listed in `src/data/i18n-rollout.json` are rollout locales.
- Non-rollout locales stay `noindex` by policy.
