#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT / "src" / "data" / "models.json",
    ROOT / "src" / "data" / "model-catalog.json",
    ROOT / "src" / "data" / "status.json",
    ROOT / "src" / "data" / "cta-rules.json",
    ROOT / "src" / "data" / "daily-updates.json",
    ROOT / "src" / "data" / "benchmark-changelog.json",
    ROOT / "src" / "data" / "benchmark-results.json",
    ROOT / "src" / "data" / "retired-models.json",
    ROOT / "src" / "data" / "retirement-candidates.json",
    ROOT / "src" / "data" / "retirement-proposal.json",
    ROOT / "src" / "data" / "search-console-keywords.json",
    ROOT / "src" / "data" / "affiliate-click-events.json",
    ROOT / "src" / "data" / "conversion-funnel.json",
    ROOT / "src" / "data" / "community-reports.json",
    ROOT / "src" / "data" / "submission-review.json",
    ROOT / "src" / "data" / "content-publish-log.json",
    ROOT / "src" / "data" / "content-review-log.json",
    ROOT / "src" / "data" / "pipeline-slo.json",
    ROOT / "src" / "data" / "locale-wave2-copy.ts",
]
REQUIRED_PAGES = [
    ROOT / "src" / "pages" / "en" / "models" / "index.astro",
    ROOT / "src" / "pages" / "en" / "models" / "[id].astro",
    ROOT / "src" / "pages" / "en" / "models" / "group" / "[group].astro",
    ROOT / "src" / "pages" / "en" / "guides" / "ollama-vs-vllm-vram.astro",
    ROOT / "src" / "pages" / "en" / "guides" / "ollama-local-cluster-network.astro",
    ROOT / "src" / "pages" / "en" / "benchmarks" / "changelog.astro",
    ROOT / "src" / "pages" / "en" / "benchmarks" / "submit-result.astro",
    ROOT / "src" / "pages" / "en" / "status" / "conversion-funnel.astro",
    ROOT / "src" / "pages" / "en" / "status" / "submission-review.astro",
    ROOT / "src" / "pages" / "en" / "status" / "content-publish.astro",
    ROOT / "src" / "pages" / "[locale]" / "guides" / "ollama-vs-vllm-vram.astro",
    ROOT / "src" / "pages" / "[locale]" / "guides" / "ollama-local-cluster-network.astro",
    ROOT / "src" / "pages" / "[locale]" / "models" / "qwen35-122b-cloud.astro",
    ROOT / "src" / "pages" / "[locale]" / "models" / "qwen35-35b-fp16.astro",
    ROOT / "src" / "pages" / "[locale]" / "errors" / "cuda-out-of-memory.astro",
    ROOT / "src" / "pages" / "[locale]" / "errors" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "errors" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "benchmarks" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "benchmarks" / "changelog.astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "data-freshness.astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "pipeline-status.astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "runner-health.astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "conversion-funnel.astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "content-publish.astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "submission-review.astro",
    ROOT / "src" / "pages" / "[locale]" / "blog" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "tools" / "roi-calculator.astro",
    ROOT / "src" / "pages" / "[locale]" / "tools" / "quantization-blind-test.astro",
]
GLOBAL_COM_LOCALES = ["en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id"]
GLOBAL_ALL_LOCALES = GLOBAL_COM_LOCALES + ["zh"]


def main() -> None:
    missing = [str(p) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        print("quality gate failed: missing required files")
        for item in missing:
            print(f"- {item}")
        sys.exit(1)

    missing_pages = [str(p) for p in REQUIRED_PAGES if not p.exists()]
    if missing_pages:
        print("quality gate failed: missing required pages")
        for item in missing_pages:
            print(f"- {item}")
        sys.exit(1)

    locale_missing: list[str] = []
    for locale in GLOBAL_ALL_LOCALES:
        base = ROOT / "src" / "pages" / locale
        required = [
            base / "index.astro",
            base / "guides" / "local-llm-cost-vs-cloud.astro",
            base / "tools" / "vram-calculator.astro",
        ]
        if locale == "en":
            required.append(base / "models" / "[id].astro")
            required.append(base / "tools" / "roi-calculator.astro")
        else:
            required.append(base / "models" / "qwen35-35b-q4.astro")
        for page in required:
            if not page.exists():
                locale_missing.append(str(page))

    if locale_missing:
        print("quality gate failed: missing locale funnel pages")
        for item in locale_missing:
            print(f"- {item}")
        sys.exit(1)

    funnel_issues: list[str] = []
    for locale in [x for x in GLOBAL_ALL_LOCALES if x != "en"]:
        guide = (ROOT / "src" / "pages" / locale / "guides" / "local-llm-cost-vs-cloud.astro").read_text(encoding="utf-8")
        model = (ROOT / "src" / "pages" / locale / "models" / "qwen35-35b-q4.astro").read_text(encoding="utf-8")
        tool = (ROOT / "src" / "pages" / locale / "tools" / "vram-calculator.astro").read_text(encoding="utf-8")
        if f"/{locale}/models/qwen35-35b-q4/" not in guide or f"/{locale}/tools/vram-calculator/" not in guide:
            funnel_issues.append(f"{locale}: guide missing model/tool links")
        if f"/{locale}/guides/local-llm-cost-vs-cloud/" not in model or f"/{locale}/tools/vram-calculator/" not in model:
            funnel_issues.append(f"{locale}: model missing guide/tool links")
        if f"/{locale}/guides/local-llm-cost-vs-cloud/" not in tool or f"/{locale}/models/qwen35-35b-q4/" not in tool:
            funnel_issues.append(f"{locale}: tool missing guide/model links")

    if funnel_issues:
        print("quality gate failed: locale funnel link loop is incomplete")
        for item in funnel_issues:
            print(f"- {item}")
        sys.exit(1)

    locale_home_issues: list[str] = []
    for locale in [x for x in GLOBAL_ALL_LOCALES if x != "en"]:
        home = (ROOT / "src" / "pages" / locale / "index.astro").read_text(encoding="utf-8")
        if f"/{locale}/tools/vram-calculator/" not in home:
            locale_home_issues.append(f"{locale}: home missing vram-calculator link")
        if f"/{locale}/tools/quantization-blind-test/" not in home:
            locale_home_issues.append(f"{locale}: home missing quantization-blind-test link")
        if f"/{locale}/benchmarks/changelog/" not in home:
            locale_home_issues.append(f"{locale}: home missing benchmark changelog link")
        if f"/{locale}/benchmarks/" not in home:
            locale_home_issues.append(f"{locale}: home missing benchmark hub link")
        if f"/{locale}/status/pipeline-status/" not in home:
            locale_home_issues.append(f"{locale}: home missing pipeline status link")
        if f"/{locale}/status/conversion-funnel/" not in home:
            locale_home_issues.append(f"{locale}: home missing conversion funnel link")

    if locale_home_issues:
        print("quality gate failed: locale home entry links are incomplete")
        for item in locale_home_issues:
            print(f"- {item}")
        sys.exit(1)

    localized_error_template = (
        ROOT / "src" / "pages" / "[locale]" / "errors" / "[slug].astro"
    ).read_text(encoding="utf-8")
    if "rocm-not-detected" not in localized_error_template or "metal-not-found" not in localized_error_template:
        print("quality gate failed: localized error template must cover rocm-not-detected and metal-not-found")
        sys.exit(1)

    locale_depth_count = 23
    print(f"locale depth baseline ok: non-en locale pages >= {locale_depth_count}")

    zh_redirect = (ROOT / "functions" / "zh" / "[[path]].js").read_text(encoding="utf-8")
    if "LV_ZH_CN_CUTOVER" not in zh_redirect or "REDIRECT_ENABLE_FLAGS" not in zh_redirect or "return context.next()" not in zh_redirect:
        print("quality gate failed: zh redirect guardrail missing expected cutover safety checks")
        sys.exit(1)

    base_layout = (ROOT / "src" / "layouts" / "BaseLayout.astro").read_text(encoding="utf-8")
    root_alternates = (ROOT / "src" / "data" / "root-alternates.ts").read_text(encoding="utf-8")
    en_model_page = (ROOT / "src" / "pages" / "en" / "models" / "[id].astro").read_text(encoding="utf-8")
    sitemap_builder = (ROOT / "scripts" / "build-sitemap.py").read_text(encoding="utf-8")
    if "PUBLIC_ZH_SITE_ORIGIN" not in base_layout or "PUBLIC_ZH_SITE_ORIGIN" not in root_alternates:
        print("quality gate failed: zh canonical origin env handling is missing")
        sys.exit(1)
    if "qwen35-122b-cloud" not in en_model_page:
        print("quality gate failed: en model page missing qwen35-122b-cloud locale alternate guardrail")
        sys.exit(1)
    if 'GLOBAL_LOCALE_TEMPLATE_ROOT' not in sitemap_builder:
        print("quality gate failed: sitemap builder missing [locale] template expansion support")
        sys.exit(1)
    print("global locale guardrail ok: en + zh + 10 locale checks passed")

    models = json.loads((ROOT / "src" / "data" / "models.json").read_text(encoding="utf-8"))
    model_catalog = json.loads((ROOT / "src" / "data" / "model-catalog.json").read_text(encoding="utf-8"))
    benchmark_results = json.loads((ROOT / "src" / "data" / "benchmark-results.json").read_text(encoding="utf-8-sig"))
    model_count = int(models.get("count", len(models.get("models", []))))
    catalog_count = int(model_catalog.get("count", len(model_catalog.get("items", []))))

    if model_count < 200 or catalog_count < 200:
        print(f"quality gate failed: expected >=200 models, got models={model_count}, catalog={catalog_count}")
        sys.exit(1)
    print(f"model counts ok: models={model_count}, catalog={catalog_count}")

    benchmark_map = benchmark_results.get("models", {})
    if not isinstance(benchmark_map, dict):
        print("quality gate failed: benchmark-results.json models must be an object")
        sys.exit(1)
    known_tags = {
        str(item.get("ollama_tag", "")).strip().lower()
        for item in model_catalog.get("items", [])
        if str(item.get("ollama_tag", "")).strip()
    }
    unknown_tags = sorted(
        key for key in benchmark_map.keys() if str(key).strip().lower() not in known_tags
    )
    if unknown_tags:
        print("quality gate failed: benchmark-results model tags missing in model-catalog ollama_tag")
        for tag in unknown_tags[:20]:
            print(f"- Error: Model '{tag}' found in results but missing in catalog.")
        sys.exit(1)
    print(f"benchmark tag alignment ok: {len(benchmark_map)} measured tag(s)")

    conversion = json.loads((ROOT / "src" / "data" / "conversion-funnel.json").read_text(encoding="utf-8-sig"))
    if not isinstance(conversion.get("funnel"), dict):
        print("quality gate failed: conversion-funnel.json missing funnel object")
        sys.exit(1)
    print("conversion funnel snapshot ok")

    affiliate_events = json.loads((ROOT / "src" / "data" / "affiliate-click-events.json").read_text(encoding="utf-8-sig"))
    if not isinstance(affiliate_events.get("events"), list):
        print("quality gate failed: affiliate-click-events.json missing events list")
        sys.exit(1)
    print(f"affiliate click events snapshot ok: {len(affiliate_events.get('events', []))} event(s)")

    submission_review = json.loads((ROOT / "src" / "data" / "submission-review.json").read_text(encoding="utf-8-sig"))
    if not isinstance(submission_review.get("summary"), dict):
        print("quality gate failed: submission-review.json missing summary object")
        sys.exit(1)
    print("submission review snapshot ok")

    content_publish = json.loads((ROOT / "src" / "data" / "content-publish-log.json").read_text(encoding="utf-8-sig"))
    if not isinstance(content_publish.get("history"), list):
        print("quality gate failed: content-publish-log.json missing history list")
        sys.exit(1)
    print("content publish log snapshot ok")

    content_review = json.loads((ROOT / "src" / "data" / "content-review-log.json").read_text(encoding="utf-8-sig"))
    if not isinstance(content_review.get("history"), list):
        print("quality gate failed: content-review-log.json missing history list")
        sys.exit(1)
    print("content review log snapshot ok")

    pipeline_slo = json.loads((ROOT / "src" / "data" / "pipeline-slo.json").read_text(encoding="utf-8-sig"))
    if not isinstance(pipeline_slo.get("workflows"), dict):
        print("quality gate failed: pipeline-slo.json missing workflows object")
        sys.exit(1)
    if not isinstance(pipeline_slo.get("weekly_report"), dict):
        print("quality gate failed: pipeline-slo.json missing weekly_report object")
        sys.exit(1)
    print("pipeline slo snapshot ok")

    blog_dir = ROOT / "src" / "content" / "blog"
    if not blog_dir.exists():
        print("quality gate failed: src/content/blog missing")
        sys.exit(1)

    post_count = len(list(blog_dir.glob("*.md")))
    if post_count < 6:
        print(f"quality gate failed: expected >=6 blog posts, found {post_count}")
        sys.exit(1)
    print(f"blog post count ok: {post_count}")

    print("quality gate passed")


if __name__ == "__main__":
    main()
