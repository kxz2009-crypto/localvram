#!/usr/bin/env python3
import json
import subprocess
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
    ROOT / "src" / "data" / "i18n-copy.json",
    ROOT / "src" / "data" / "i18n-glossary.json",
    ROOT / "src" / "data" / "i18n-rollout.json",
]
REQUIRED_PAGES = [
    ROOT / "src" / "pages" / "index.astro",
    ROOT / "src" / "pages" / "legal.astro",
    ROOT / "src" / "pages" / "404.astro",
    ROOT / "src" / "pages" / "en" / "index.astro",
    ROOT / "src" / "pages" / "en" / "models" / "index.astro",
    ROOT / "src" / "pages" / "en" / "models" / "[id].astro",
    ROOT / "src" / "pages" / "en" / "models" / "group" / "[group].astro",
    ROOT / "src" / "pages" / "en" / "guides" / "local-llm-cost-vs-cloud.astro",
    ROOT / "src" / "pages" / "en" / "guides" / "ollama-vs-vllm-vram.astro",
    ROOT / "src" / "pages" / "en" / "guides" / "ollama-local-cluster-network.astro",
    ROOT / "src" / "pages" / "en" / "tools" / "vram-calculator.astro",
    ROOT / "src" / "pages" / "en" / "tools" / "roi-calculator.astro",
    ROOT / "src" / "pages" / "en" / "tools" / "quantization-blind-test.astro",
    ROOT / "src" / "pages" / "en" / "status" / "data-freshness.astro",
    ROOT / "src" / "pages" / "en" / "status" / "pipeline-status.astro",
    ROOT / "src" / "pages" / "en" / "status" / "runner-health.astro",
    ROOT / "src" / "pages" / "en" / "status" / "conversion-funnel.astro",
    ROOT / "src" / "pages" / "en" / "status" / "content-publish.astro",
    ROOT / "src" / "pages" / "en" / "status" / "submission-review.astro",
    ROOT / "src" / "pages" / "[locale]" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "guides" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "guides" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "tools" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "tools" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "errors" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "errors" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "models" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "models" / "[id].astro",
    ROOT / "src" / "pages" / "[locale]" / "models" / "group" / "[group].astro",
]
EXPECTED_COM_LOCALES = {"en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id"}
EXPECTED_STANDARD_LOCALES = EXPECTED_COM_LOCALES - {"en"}
REQUIRED_I18N_COPY_PAGES = {
    "locale-home",
    "guides-index",
    "guides-detail",
    "status-index",
    "status-detail",
    "tools-index",
    "tools-detail",
    "errors-index",
    "errors-detail",
    "models-index",
    "models-detail",
    "models-group",
}


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

    page_dirs = [p.name for p in (ROOT / "src" / "pages").iterdir() if p.is_dir()]
    unexpected_locale_dirs = sorted(
        x
        for x in page_dirs
        if len(x) == 2 and x.isalpha() and x not in EXPECTED_COM_LOCALES
    )
    if unexpected_locale_dirs:
        print("quality gate failed: unexpected locale directories found")
        for item in unexpected_locale_dirs:
            print(f"- src/pages/{item}")
        sys.exit(1)

    i18n_config_path = ROOT / "src" / "config" / "i18n.ts"
    if not i18n_config_path.exists():
        print("quality gate failed: missing src/config/i18n.ts")
        sys.exit(1)
    i18n_config = i18n_config_path.read_text(encoding="utf-8")
    for token in [
        'DEFAULT_LOCALE = "en"',
        "STANDARD_I18N_LOCALES",
        "HREFLANG_ROLLOUT_LOCALES",
        "SITEMAP_ROLLOUT_LOCALES",
        '"ko"',
        '"ar"',
        '"id"',
    ]:
        if token not in i18n_config:
            print(f"quality gate failed: i18n config missing token {token}")
            sys.exit(1)

    rollout_config = json.loads((ROOT / "src" / "data" / "i18n-rollout.json").read_text(encoding="utf-8"))
    rollout_locale_sets: dict[str, set[str]] = {}
    for key in ("hreflang_rollout_locales", "sitemap_rollout_locales"):
        raw = rollout_config.get(key)
        if not isinstance(raw, list) or not raw:
            print(f"quality gate failed: i18n-rollout.json {key} must be a non-empty array")
            sys.exit(1)
        values = [str(x).strip().lower() for x in raw if str(x).strip()]
        if "en" not in values:
            print(f"quality gate failed: i18n-rollout.json {key} must include 'en'")
            sys.exit(1)
        unknown = sorted(x for x in values if x not in EXPECTED_COM_LOCALES)
        if unknown:
            print(f"quality gate failed: i18n-rollout.json {key} contains unknown locales")
            for item in unknown:
                print(f"- {item}")
            sys.exit(1)
        rollout_locale_sets[key] = set(values)

    base_layout = (ROOT / "src" / "layouts" / "BaseLayout.astro").read_text(encoding="utf-8")
    if "OG_LOCALE_BY_LANG" not in base_layout or "isRtlLocale" not in base_layout:
        print("quality gate failed: BaseLayout missing i18n locale metadata support")
        sys.exit(1)
    if 'dir={htmlDir}' not in base_layout:
        print("quality gate failed: BaseLayout missing rtl/ltr html direction binding")
        sys.exit(1)

    i18n_copy_lib = (ROOT / "src" / "lib" / "i18n-copy.ts").read_text(encoding="utf-8")
    for token in ["HREFLANG_ROLLOUT_LOCALES", "hreflangRolloutLocaleSet.has(locale)"]:
        if token not in i18n_copy_lib:
            print(f"quality gate failed: i18n noindex rollout guard missing token {token}")
            sys.exit(1)

    redirects_file = ROOT / "public" / "_redirects"
    if not redirects_file.exists():
        print("quality gate failed: public/_redirects missing")
        sys.exit(1)
    redirects_text = redirects_file.read_text(encoding="utf-8")
    required_redirect_lines = [
        "/ /en/ 301",
        "/zh https://localvram.cn/zh/ 301",
        "/zh/* https://localvram.cn/zh/:splat 301",
    ]
    for line in required_redirect_lines:
        if line not in redirects_text:
            print(f"quality gate failed: missing redirect rule '{line}'")
            sys.exit(1)
    print("i18n baseline checks ok: locale config + layout + zh redirect rules")

    locale_link_checker = ROOT / "scripts" / "check-locale-links.py"
    if not locale_link_checker.exists():
        print("quality gate failed: missing scripts/check-locale-links.py")
        sys.exit(1)
    locale_link_cmd = [sys.executable, str(locale_link_checker)]
    locale_link_result = subprocess.run(locale_link_cmd, cwd=ROOT)
    if locale_link_result.returncode != 0:
        print("quality gate failed: locale link checks failed")
        sys.exit(locale_link_result.returncode)

    i18n_copy = json.loads((ROOT / "src" / "data" / "i18n-copy.json").read_text(encoding="utf-8"))
    i18n_glossary = json.loads((ROOT / "src" / "data" / "i18n-glossary.json").read_text(encoding="utf-8"))
    threshold = i18n_copy.get("fallback_noindex_threshold")
    if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
        print("quality gate failed: i18n-copy.json fallback_noindex_threshold must be between 0 and 1")
        sys.exit(1)

    required_locales = set(i18n_copy.get("required_locales", []))
    if required_locales != EXPECTED_STANDARD_LOCALES:
        print("quality gate failed: i18n-copy.json required_locales must exactly match standard locales")
        print(f"- expected: {sorted(EXPECTED_STANDARD_LOCALES)}")
        print(f"- actual: {sorted(required_locales)}")
        sys.exit(1)

    pages = i18n_copy.get("pages")
    if not isinstance(pages, dict):
        print("quality gate failed: i18n-copy.json pages must be an object")
        sys.exit(1)

    missing_copy_pages = sorted(REQUIRED_I18N_COPY_PAGES - set(pages.keys()))
    if missing_copy_pages:
        print("quality gate failed: i18n-copy.json missing required page ids")
        for item in missing_copy_pages:
            print(f"- {item}")
        sys.exit(1)

    protected_terms = i18n_glossary.get("protected_terms", [])
    if not isinstance(protected_terms, list) or not protected_terms:
        print("quality gate failed: i18n-glossary.json protected_terms must be a non-empty list")
        sys.exit(1)
    protected_terms = [str(x).strip() for x in protected_terms if str(x).strip()]
    if not protected_terms:
        print("quality gate failed: i18n-glossary.json protected_terms must include non-empty strings")
        sys.exit(1)

    for page_id in sorted(REQUIRED_I18N_COPY_PAGES):
        page_entry = pages.get(page_id, {})
        en_fields = page_entry.get("en")
        if not isinstance(en_fields, dict) or not en_fields:
            print(f"quality gate failed: i18n-copy.json page '{page_id}' missing non-empty en fields")
            sys.exit(1)
        if "meta_title" not in en_fields or "meta_description" not in en_fields:
            print(f"quality gate failed: i18n-copy.json page '{page_id}' missing meta_title/meta_description")
            sys.exit(1)

        locales = page_entry.get("locales")
        if not isinstance(locales, dict):
            print(f"quality gate failed: i18n-copy.json page '{page_id}' locales must be an object")
            sys.exit(1)
        locale_keys = set(locales.keys())
        if locale_keys != EXPECTED_STANDARD_LOCALES:
            print(f"quality gate failed: i18n-copy.json page '{page_id}' locales must include exact 10 standard locales")
            print(f"- expected: {sorted(EXPECTED_STANDARD_LOCALES)}")
            print(f"- actual: {sorted(locale_keys)}")
            sys.exit(1)

        for locale_key, localized_fields in locales.items():
            if not isinstance(localized_fields, dict):
                print(
                    f"quality gate failed: i18n-copy.json page '{page_id}' locale '{locale_key}' must be an object"
                )
                sys.exit(1)
            for field_name, field_value in localized_fields.items():
                if not isinstance(field_value, str):
                    print(
                        f"quality gate failed: i18n-copy.json page '{page_id}' locale '{locale_key}' field '{field_name}' must be string"
                    )
                    sys.exit(1)
                if field_name not in en_fields:
                    print(
                        f"quality gate failed: i18n-copy.json page '{page_id}' locale '{locale_key}' has unknown field '{field_name}'"
                    )
                    sys.exit(1)
                if not field_value.strip():
                    continue
                en_text = str(en_fields.get(field_name, ""))
                for term in protected_terms:
                    if term in en_text and term not in field_value:
                        print(
                            f"quality gate failed: i18n glossary lock broken on page '{page_id}' locale '{locale_key}' field '{field_name}' for term '{term}'"
                        )
                        sys.exit(1)

    ready_locales: set[str] = set()
    for locale_key in EXPECTED_STANDARD_LOCALES:
        locale_ready = True
        for page_id in REQUIRED_I18N_COPY_PAGES:
            page_entry = pages.get(page_id, {})
            en_fields = page_entry.get("en", {}) if isinstance(page_entry, dict) else {}
            locale_fields = page_entry.get("locales", {}).get(locale_key, {}) if isinstance(page_entry, dict) else {}
            keys = list(en_fields.keys()) if isinstance(en_fields, dict) else []
            if not keys:
                continue
            fallback_count = 0
            for key in keys:
                val = locale_fields.get(key) if isinstance(locale_fields, dict) else None
                if not isinstance(val, str) or not val.strip():
                    fallback_count += 1
            fallback_ratio = fallback_count / len(keys)
            if fallback_ratio > threshold:
                locale_ready = False
                break
        if locale_ready:
            ready_locales.add(locale_key)

    for rollout_key in ("hreflang_rollout_locales", "sitemap_rollout_locales"):
        disallowed = sorted(x for x in rollout_locale_sets.get(rollout_key, set()) if x != "en" and x not in ready_locales)
        if disallowed:
            print(f"quality gate failed: {rollout_key} contains locales not ready for index")
            print(f"- ready locales: {sorted(ready_locales) if ready_locales else '(none)'}")
            for item in disallowed:
                print(f"- {item}")
            sys.exit(1)

    print(
        f"i18n copy checks ok: pages={len(REQUIRED_I18N_COPY_PAGES)} locales={len(EXPECTED_STANDARD_LOCALES)} threshold={threshold}"
    )
    print(f"i18n readiness ok: ready locales = {sorted(ready_locales) if ready_locales else '(none)'}")

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
