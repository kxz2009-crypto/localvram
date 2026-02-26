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
]
REQUIRED_PAGES = [
    ROOT / "src" / "pages" / "en" / "models" / "index.astro",
    ROOT / "src" / "pages" / "en" / "models" / "[id].astro",
    ROOT / "src" / "pages" / "en" / "models" / "group" / "[group].astro",
    ROOT / "src" / "pages" / "en" / "benchmarks" / "changelog.astro",
    ROOT / "src" / "pages" / "en" / "benchmarks" / "submit-result.astro",
    ROOT / "src" / "pages" / "en" / "status" / "conversion-funnel.astro",
    ROOT / "src" / "pages" / "en" / "status" / "submission-review.astro",
    ROOT / "src" / "pages" / "en" / "status" / "content-publish.astro",
]


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
