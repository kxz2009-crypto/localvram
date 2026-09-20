# Homepage models and cost calculator

Homepage selection lives in `src/data/homepage-models.json`, independently of the short-lived new-model queue. Preserve exact Ollama tags, canonical official source URLs, observed download sizes, exact quantization, review date and display priority. Download size is not runtime VRAM. Metadata was checked on 2026-09-20 against:

- https://ollama.com/library/qwen3.8:27b
- https://ollama.com/library/gemma4:26b
- https://ollama.com/library/qwen3.6:27b

This is a dated editorial selection, not an exhaustive latest-release feed. Recheck every 30 days; a later site build marks overdue entries for review. To change the selection, update the registry and rerun tests/builds. The static site must be rebuilt to refresh date-based labels.

Local inventory labels describe the saved runner sample, never live availability. Sample absence remains unknown. A model is measured only when the exact digest, quantization and required hardware/context metadata match the evidence resolver. New cards intentionally remain unverified until such evidence exists.

The ROI tool compares equivalent work using editable assumptions in a single user-chosen currency. It includes whole-system active and idle electricity, maintenance, cloud storage/transfer/operations, relative cloud execution time, and purchase/resale where applicable. Default values are examples, not quotes. Existing hardware excludes sunk purchase costs; new hardware subtracts resale only at the chosen horizon. Cash payback uses gross purchase divided by monthly operating savings, without counting future resale early. It does not model financing, taxes, downtime, or opportunity cost of keeping owned hardware; include relevant labor in maintenance. Confirm workload quality and model fit separately.

Validation: `npm run test:unit`, `npm run build`, `node scripts/check-evidence-render.mjs`, `node scripts/check-homepage-render.mjs`, `npm run build:cn`, `node scripts/check-homepage-render.mjs --cn`.
