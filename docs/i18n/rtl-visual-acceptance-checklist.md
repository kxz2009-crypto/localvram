# RTL Visual Acceptance Checklist (Arabic `ar`)

## Goal
Use this checklist to manually verify RTL rendering quality after i18n updates.

## Required URLs (production)
1. `https://localvram.com/ar/`
2. `https://localvram.com/ar/tools/`
3. `https://localvram.com/ar/errors/`
4. `https://localvram.com/ar/status/`
5. `https://localvram.com/ar/guides/`
6. `https://localvram.com/ar/hardware/`
7. `https://localvram.com/ar/models/`
8. `https://localvram.com/ar/blog/`
9. `https://localvram.com/ar/models/llama-70b-q4/`
10. `https://localvram.com/ar/tools/quantization-blind-test/`
11. `https://localvram.com/ar/blog/best-24gb-vram-models-2026/`

## Visual Checks
1. Direction and alignment:
   - Page root uses RTL direction (`dir="rtl"`).
   - Headings, body text, bullets, and card content are right-aligned by default.
2. Overflow and clipping:
   - No clipped Arabic text in cards, buttons, badges, nav items, and footer.
   - No horizontal page overflow at 1280px, 768px, and 390px widths.
3. Navigation and switcher:
   - Locale switcher renders correctly and keeps `ZH-CN` link visible.
   - Tab order is logical with keyboard navigation (Tab/Shift+Tab).
4. Components and interaction:
   - CTA buttons, tables/charts blocks, and model cards keep spacing and readability.
   - Hover/focus states do not shift layout or hide text.
5. SEO shell consistency:
   - Canonical/hreflang tags exist and match routed locale page.
   - No unexpected `/en/` content leakage inside visible body text.

## Pass Criteria
1. All required URLs load successfully.
2. All visual checks pass with no critical or high severity issues.
3. Any medium issues are documented with owner and fix ETA.

## Signoff Process
1. Complete the checks above.
2. Update `docs/i18n/rtl-visual-signoff.json` with a new pass entry:
   - `date` in `YYYY-MM-DD` (UTC date).
   - `reviewer` short identifier.
   - `status` set to `pass`.
   - `run_id` set to the related weekly workflow run id.
   - `notes` with concise evidence.
3. Run:
   - `npm run i18n:check-rtl-signoff`
4. Commit the updated signoff file in the same change set as i18n rollout updates.

