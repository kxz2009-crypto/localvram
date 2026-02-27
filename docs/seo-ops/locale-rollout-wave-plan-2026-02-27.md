# Locale Rollout Wave Plan (2026-02-27)

## Objective

Start multilingual execution by locale using one fixed funnel:

1. Topic page
2. Model page
3. CTA conversion page

## Wave schedule

- Wave 1 start: 2026-03-02
- Wave 2 start: 2026-03-16
- Wave 3 start: 2026-03-30
- Wave 4 start: 2026-04-13

## Wave 1 (2026-03-02)

- `es`: `/es/guides/local-llm-cost-vs-cloud/` -> `/es/models/qwen35-35b-q4/` -> `/es/tools/vram-calculator/`
- `pt`: `/pt/guides/local-llm-cost-vs-cloud/` -> `/pt/models/qwen35-35b-q4/` -> `/pt/tools/vram-calculator/`
- `ja`: `/ja/guides/local-llm-cost-vs-cloud/` -> `/ja/models/qwen35-35b-q4/` -> `/ja/tools/vram-calculator/`

## Wave 2 (2026-03-16)

- `fr`: `/fr/guides/local-llm-cost-vs-cloud/` -> `/fr/models/qwen35-35b-q4/` -> `/fr/tools/vram-calculator/`
- `de`: `/de/guides/local-llm-cost-vs-cloud/` -> `/de/models/qwen35-35b-q4/` -> `/de/tools/vram-calculator/`
- `ko`: `/ko/guides/local-llm-cost-vs-cloud/` -> `/ko/models/qwen35-35b-q4/` -> `/ko/tools/vram-calculator/`

## Wave 3 (2026-03-30)

- `ru`: `/ru/guides/local-llm-cost-vs-cloud/` -> `/ru/models/qwen35-35b-q4/` -> `/ru/tools/vram-calculator/`
- `id`: `/id/guides/local-llm-cost-vs-cloud/` -> `/id/models/qwen35-35b-q4/` -> `/id/tools/vram-calculator/`
- `hi`: `/hi/guides/local-llm-cost-vs-cloud/` -> `/hi/models/qwen35-35b-q4/` -> `/hi/tools/vram-calculator/`

## Wave 4 (2026-04-13)

- `ar`: `/ar/guides/local-llm-cost-vs-cloud/` -> `/ar/models/qwen35-35b-q4/` -> `/ar/tools/vram-calculator/`
- `zh-CN`: `https://localvram.cn/zh/guides/local-llm-cost-vs-cloud/` -> `https://localvram.cn/zh/models/qwen35-35b-q4/` -> `https://localvram.cn/zh/tools/vram-calculator/`

## Acceptance per locale

1. All 3 URLs return `200` and are present in locale sitemap.
2. Internal links form one closed loop: topic -> model -> CTA -> topic.
3. `canonical` and `hreflang` are correct for locale cluster.
4. KPI tracker row is updated 72 hours after publish.
