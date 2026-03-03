#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
LOGGER = configure_logging("quality-gate")
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
    ROOT / "src" / "data" / "i18n-blog-copy.json",
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
    ROOT / "src" / "pages" / "en" / "blog" / "index.astro",
    ROOT / "src" / "pages" / "en" / "blog" / "[slug].astro",
    ROOT / "src" / "pages" / "en" / "tools" / "vram-calculator.astro",
    ROOT / "src" / "pages" / "en" / "tools" / "roi-calculator.astro",
    ROOT / "src" / "pages" / "en" / "tools" / "quantization-blind-test.astro",
    ROOT / "src" / "pages" / "en" / "status" / "data-freshness.astro",
    ROOT / "src" / "pages" / "en" / "status" / "pipeline-status.astro",
    ROOT / "src" / "pages" / "en" / "status" / "runner-health.astro",
    ROOT / "src" / "pages" / "en" / "status" / "conversion-funnel.astro",
    ROOT / "src" / "pages" / "en" / "status" / "content-publish.astro",
    ROOT / "src" / "pages" / "en" / "status" / "submission-review.astro",
    ROOT / "src" / "pages" / "en" / "hardware" / "index.astro",
    ROOT / "src" / "pages" / "en" / "hardware" / "[slug].astro",
    ROOT / "src" / "pages" / "en" / "hardware" / "verified-3090.astro",
    ROOT / "src" / "pages" / "en" / "hardware" / "apple-silicon-llm-guide.astro",
    ROOT / "src" / "pages" / "[locale]" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "guides" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "guides" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "status" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "tools" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "tools" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "errors" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "errors" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "hardware" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "hardware" / "[slug].astro",
    ROOT / "src" / "pages" / "[locale]" / "hardware" / "verified-3090.astro",
    ROOT / "src" / "pages" / "[locale]" / "hardware" / "apple-silicon-llm-guide.astro",
    ROOT / "src" / "pages" / "[locale]" / "models" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "models" / "[id].astro",
    ROOT / "src" / "pages" / "[locale]" / "models" / "group" / "[group].astro",
    ROOT / "src" / "pages" / "[locale]" / "blog" / "index.astro",
    ROOT / "src" / "pages" / "[locale]" / "blog" / "[slug].astro",
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
PLACEHOLDER_ONLY_RE = re.compile(r"^\{[a-zA-Z0-9_]+\}$")
FORBIDDEN_I18N_FRAGMENTS = {
    "fr": ["Erreur Ko", "Ko d'erreur", "Pomme Silicium", "Démarrer VRAM Calculatrice"],
    "ko": ["RTX 3090에 확인됨", "공개 비교", "애플실리콘"],
    "ar": ["خطأ بالكيلو بايت", "خطأ كيلو بايت", "مراكز الملاحة", "اختبار أعمى الكمي", "أبل السيليكون"],
}
REQUIRED_I18N_BLOG_COPY_FIELDS = {"title", "description", "cta_line"}
MIN_I18N_BLOG_COPY_COVERAGE_RATIO = 0.9


def _log_print(*values: object, sep: str = " ", end: str = "\n", flush: bool = False) -> None:  # noqa: ARG001
    message = sep.join(str(v) for v in values)
    if not message:
        return
    if message.startswith("quality gate failed") or message.startswith("- Error:"):
        LOGGER.error("%s", message)
    else:
        LOGGER.info("%s", message)


log_line = _log_print


def is_effective_fallback(en_value: object, localized_value: object) -> bool:
    if not isinstance(localized_value, str) or not localized_value.strip():
        return True
    en_text = str(en_value).strip()
    localized_text = localized_value.strip()
    if localized_text != en_text:
        return False
    # Identical placeholder-only tokens are expected to stay unchanged.
    return not bool(PLACEHOLDER_ONLY_RE.fullmatch(en_text))


def main() -> None:
    missing = [str(p) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        log_line("quality gate failed: missing required files")
        for item in missing:
            log_line(f"- {item}")
        sys.exit(1)

    missing_pages = [str(p) for p in REQUIRED_PAGES if not p.exists()]
    if missing_pages:
        log_line("quality gate failed: missing required pages")
        for item in missing_pages:
            log_line(f"- {item}")
        sys.exit(1)

    page_dirs = [p.name for p in (ROOT / "src" / "pages").iterdir() if p.is_dir()]
    unexpected_locale_dirs = sorted(
        x
        for x in page_dirs
        if len(x) == 2 and x.isalpha() and x not in EXPECTED_COM_LOCALES
    )
    if unexpected_locale_dirs:
        log_line("quality gate failed: unexpected locale directories found")
        for item in unexpected_locale_dirs:
            log_line(f"- src/pages/{item}")
        sys.exit(1)

    i18n_config_path = ROOT / "src" / "config" / "i18n.ts"
    if not i18n_config_path.exists():
        log_line("quality gate failed: missing src/config/i18n.ts")
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
            log_line(f"quality gate failed: i18n config missing token {token}")
            sys.exit(1)

    rollout_config = json.loads((ROOT / "src" / "data" / "i18n-rollout.json").read_text(encoding="utf-8"))
    rollout_locale_sets: dict[str, set[str]] = {}
    for key in ("hreflang_rollout_locales", "sitemap_rollout_locales"):
        raw = rollout_config.get(key)
        if not isinstance(raw, list) or not raw:
            log_line(f"quality gate failed: i18n-rollout.json {key} must be a non-empty array")
            sys.exit(1)
        values = [str(x).strip().lower() for x in raw if str(x).strip()]
        if "en" not in values:
            log_line(f"quality gate failed: i18n-rollout.json {key} must include 'en'")
            sys.exit(1)
        unknown = sorted(x for x in values if x not in EXPECTED_COM_LOCALES)
        if unknown:
            log_line(f"quality gate failed: i18n-rollout.json {key} contains unknown locales")
            for item in unknown:
                log_line(f"- {item}")
            sys.exit(1)
        rollout_locale_sets[key] = set(values)

    base_layout = (ROOT / "src" / "layouts" / "BaseLayout.astro").read_text(encoding="utf-8")
    if "OG_LOCALE_BY_LANG" not in base_layout or "isRtlLocale" not in base_layout:
        log_line("quality gate failed: BaseLayout missing i18n locale metadata support")
        sys.exit(1)
    if 'dir={htmlDir}' not in base_layout:
        log_line("quality gate failed: BaseLayout missing rtl/ltr html direction binding")
        sys.exit(1)
    for token in ["ZH_SITE_URL", "zhSwitchHref", "locale-switcher"]:
        if token not in base_layout:
            log_line(f"quality gate failed: BaseLayout missing locale switch token {token}")
            sys.exit(1)

    i18n_copy_lib = (ROOT / "src" / "lib" / "i18n-copy.ts").read_text(encoding="utf-8")
    for token in ["HREFLANG_ROLLOUT_LOCALES", "hreflangRolloutLocaleSet.has(locale)"]:
        if token not in i18n_copy_lib:
            log_line(f"quality gate failed: i18n noindex rollout guard missing token {token}")
            sys.exit(1)

    redirects_file = ROOT / "public" / "_redirects"
    if not redirects_file.exists():
        log_line("quality gate failed: public/_redirects missing")
        sys.exit(1)
    redirects_text = redirects_file.read_text(encoding="utf-8")
    required_redirect_lines = [
        "/ /en/ 301",
        "/zh https://localvram.cn/zh/ 301",
        "/zh/* https://localvram.cn/zh/:splat 301",
    ]
    for line in required_redirect_lines:
        if line not in redirects_text:
            log_line(f"quality gate failed: missing redirect rule '{line}'")
            sys.exit(1)
    log_line("i18n baseline checks ok: locale config + layout + zh redirect rules")

    locale_link_checker = ROOT / "scripts" / "check-locale-links.py"
    if not locale_link_checker.exists():
        log_line("quality gate failed: missing scripts/check-locale-links.py")
        sys.exit(1)
    locale_link_cmd = [sys.executable, str(locale_link_checker)]
    locale_link_result = subprocess.run(locale_link_cmd, cwd=ROOT)
    if locale_link_result.returncode != 0:
        log_line("quality gate failed: locale link checks failed")
        sys.exit(locale_link_result.returncode)

    pack_validator = ROOT / "scripts" / "validate-i18n-packs.py"
    if not pack_validator.exists():
        log_line("quality gate failed: missing scripts/validate-i18n-packs.py")
        sys.exit(1)
    pack_validate_cmd = [sys.executable, str(pack_validator)]
    pack_validate_result = subprocess.run(pack_validate_cmd, cwd=ROOT)
    if pack_validate_result.returncode != 0:
        log_line("quality gate failed: i18n pack validation failed")
        sys.exit(pack_validate_result.returncode)

    sitemap_section_reporter = ROOT / "scripts" / "i18n-sitemap-section-report.py"
    if not sitemap_section_reporter.exists():
        log_line("quality gate failed: missing scripts/i18n-sitemap-section-report.py")
        sys.exit(1)
    sitemap_report_cmd = [sys.executable, str(sitemap_section_reporter)]
    sitemap_report_result = subprocess.run(sitemap_report_cmd, cwd=ROOT)
    if sitemap_report_result.returncode != 0:
        log_line("quality gate failed: i18n sitemap section report failed")
        sys.exit(sitemap_report_result.returncode)

    section_parity_checker = ROOT / "scripts" / "check-i18n-section-parity.py"
    if not section_parity_checker.exists():
        log_line("quality gate failed: missing scripts/check-i18n-section-parity.py")
        sys.exit(1)
    section_parity_cmd = [sys.executable, str(section_parity_checker)]
    section_parity_result = subprocess.run(section_parity_cmd, cwd=ROOT)
    if section_parity_result.returncode != 0:
        log_line("quality gate failed: i18n key section parity check failed")
        sys.exit(section_parity_result.returncode)

    i18n_copy = json.loads((ROOT / "src" / "data" / "i18n-copy.json").read_text(encoding="utf-8"))
    i18n_glossary = json.loads((ROOT / "src" / "data" / "i18n-glossary.json").read_text(encoding="utf-8"))
    threshold = i18n_copy.get("fallback_noindex_threshold")
    if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
        log_line("quality gate failed: i18n-copy.json fallback_noindex_threshold must be between 0 and 1")
        sys.exit(1)

    required_locales = set(i18n_copy.get("required_locales", []))
    if required_locales != EXPECTED_STANDARD_LOCALES:
        log_line("quality gate failed: i18n-copy.json required_locales must exactly match standard locales")
        log_line(f"- expected: {sorted(EXPECTED_STANDARD_LOCALES)}")
        log_line(f"- actual: {sorted(required_locales)}")
        sys.exit(1)

    pages = i18n_copy.get("pages")
    if not isinstance(pages, dict):
        log_line("quality gate failed: i18n-copy.json pages must be an object")
        sys.exit(1)

    missing_copy_pages = sorted(REQUIRED_I18N_COPY_PAGES - set(pages.keys()))
    if missing_copy_pages:
        log_line("quality gate failed: i18n-copy.json missing required page ids")
        for item in missing_copy_pages:
            log_line(f"- {item}")
        sys.exit(1)

    protected_terms = i18n_glossary.get("protected_terms", [])
    if not isinstance(protected_terms, list) or not protected_terms:
        log_line("quality gate failed: i18n-glossary.json protected_terms must be a non-empty list")
        sys.exit(1)
    protected_terms = [str(x).strip() for x in protected_terms if str(x).strip()]
    if not protected_terms:
        log_line("quality gate failed: i18n-glossary.json protected_terms must include non-empty strings")
        sys.exit(1)

    for page_id in sorted(REQUIRED_I18N_COPY_PAGES):
        page_entry = pages.get(page_id, {})
        en_fields = page_entry.get("en")
        if not isinstance(en_fields, dict) or not en_fields:
            log_line(f"quality gate failed: i18n-copy.json page '{page_id}' missing non-empty en fields")
            sys.exit(1)
        if "meta_title" not in en_fields or "meta_description" not in en_fields:
            log_line(f"quality gate failed: i18n-copy.json page '{page_id}' missing meta_title/meta_description")
            sys.exit(1)

        locales = page_entry.get("locales")
        if not isinstance(locales, dict):
            log_line(f"quality gate failed: i18n-copy.json page '{page_id}' locales must be an object")
            sys.exit(1)
        locale_keys = set(locales.keys())
        if locale_keys != EXPECTED_STANDARD_LOCALES:
            log_line(f"quality gate failed: i18n-copy.json page '{page_id}' locales must include exact 10 standard locales")
            log_line(f"- expected: {sorted(EXPECTED_STANDARD_LOCALES)}")
            log_line(f"- actual: {sorted(locale_keys)}")
            sys.exit(1)

        for locale_key, localized_fields in locales.items():
            if not isinstance(localized_fields, dict):
                log_line(
                    f"quality gate failed: i18n-copy.json page '{page_id}' locale '{locale_key}' must be an object"
                )
                sys.exit(1)
            for field_name, field_value in localized_fields.items():
                if not isinstance(field_value, str):
                    log_line(
                        f"quality gate failed: i18n-copy.json page '{page_id}' locale '{locale_key}' field '{field_name}' must be string"
                    )
                    sys.exit(1)
                if field_name not in en_fields:
                    log_line(
                        f"quality gate failed: i18n-copy.json page '{page_id}' locale '{locale_key}' has unknown field '{field_name}'"
                    )
                    sys.exit(1)
                if not field_value.strip():
                    continue
                en_text = str(en_fields.get(field_name, ""))
                for term in protected_terms:
                    if term in en_text and term not in field_value:
                        log_line(
                            f"quality gate failed: i18n glossary lock broken on page '{page_id}' locale '{locale_key}' field '{field_name}' for term '{term}'"
                        )
                        sys.exit(1)
                for bad_fragment in FORBIDDEN_I18N_FRAGMENTS.get(locale_key, []):
                    if bad_fragment in field_value:
                        log_line(
                            f"quality gate failed: forbidden i18n fragment '{bad_fragment}' found on page '{page_id}' locale '{locale_key}' field '{field_name}'"
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
                if is_effective_fallback(en_fields.get(key), val):
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
            log_line(f"quality gate failed: {rollout_key} contains locales not ready for index")
            log_line(f"- ready locales: {sorted(ready_locales) if ready_locales else '(none)'}")
            for item in disallowed:
                log_line(f"- {item}")
            sys.exit(1)

    log_line(
        f"i18n copy checks ok: pages={len(REQUIRED_I18N_COPY_PAGES)} locales={len(EXPECTED_STANDARD_LOCALES)} threshold={threshold}"
    )
    log_line(f"i18n readiness ok: ready locales = {sorted(ready_locales) if ready_locales else '(none)'}")

    models = json.loads((ROOT / "src" / "data" / "models.json").read_text(encoding="utf-8"))
    model_catalog = json.loads((ROOT / "src" / "data" / "model-catalog.json").read_text(encoding="utf-8"))
    benchmark_results = json.loads((ROOT / "src" / "data" / "benchmark-results.json").read_text(encoding="utf-8-sig"))
    model_count = int(models.get("count", len(models.get("models", []))))
    catalog_count = int(model_catalog.get("count", len(model_catalog.get("items", []))))

    if model_count < 200 or catalog_count < 200:
        log_line(f"quality gate failed: expected >=200 models, got models={model_count}, catalog={catalog_count}")
        sys.exit(1)
    log_line(f"model counts ok: models={model_count}, catalog={catalog_count}")

    benchmark_map = benchmark_results.get("models", {})
    if not isinstance(benchmark_map, dict):
        log_line("quality gate failed: benchmark-results.json models must be an object")
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
        log_line("quality gate failed: benchmark-results model tags missing in model-catalog ollama_tag")
        for tag in unknown_tags[:20]:
            log_line(f"- Error: Model '{tag}' found in results but missing in catalog.")
        sys.exit(1)
    log_line(f"benchmark tag alignment ok: {len(benchmark_map)} measured tag(s)")

    conversion = json.loads((ROOT / "src" / "data" / "conversion-funnel.json").read_text(encoding="utf-8-sig"))
    if not isinstance(conversion.get("funnel"), dict):
        log_line("quality gate failed: conversion-funnel.json missing funnel object")
        sys.exit(1)
    log_line("conversion funnel snapshot ok")

    affiliate_events = json.loads((ROOT / "src" / "data" / "affiliate-click-events.json").read_text(encoding="utf-8-sig"))
    if not isinstance(affiliate_events.get("events"), list):
        log_line("quality gate failed: affiliate-click-events.json missing events list")
        sys.exit(1)
    log_line(f"affiliate click events snapshot ok: {len(affiliate_events.get('events', []))} event(s)")

    submission_review = json.loads((ROOT / "src" / "data" / "submission-review.json").read_text(encoding="utf-8-sig"))
    if not isinstance(submission_review.get("summary"), dict):
        log_line("quality gate failed: submission-review.json missing summary object")
        sys.exit(1)
    log_line("submission review snapshot ok")

    content_publish = json.loads((ROOT / "src" / "data" / "content-publish-log.json").read_text(encoding="utf-8-sig"))
    if not isinstance(content_publish.get("history"), list):
        log_line("quality gate failed: content-publish-log.json missing history list")
        sys.exit(1)
    log_line("content publish log snapshot ok")

    content_review = json.loads((ROOT / "src" / "data" / "content-review-log.json").read_text(encoding="utf-8-sig"))
    if not isinstance(content_review.get("history"), list):
        log_line("quality gate failed: content-review-log.json missing history list")
        sys.exit(1)
    log_line("content review log snapshot ok")

    pipeline_slo = json.loads((ROOT / "src" / "data" / "pipeline-slo.json").read_text(encoding="utf-8-sig"))
    if not isinstance(pipeline_slo.get("workflows"), dict):
        log_line("quality gate failed: pipeline-slo.json missing workflows object")
        sys.exit(1)
    if not isinstance(pipeline_slo.get("weekly_report"), dict):
        log_line("quality gate failed: pipeline-slo.json missing weekly_report object")
        sys.exit(1)
    log_line("pipeline slo snapshot ok")

    blog_dir = ROOT / "src" / "content" / "blog"
    if not blog_dir.exists():
        log_line("quality gate failed: src/content/blog missing")
        sys.exit(1)

    post_count = len(list(blog_dir.glob("*.md")))
    if post_count < 6:
        log_line(f"quality gate failed: expected >=6 blog posts, found {post_count}")
        sys.exit(1)
    log_line(f"blog post count ok: {post_count}")
    blog_slugs = {p.stem for p in blog_dir.glob("*.md")}

    i18n_blog_copy = json.loads((ROOT / "src" / "data" / "i18n-blog-copy.json").read_text(encoding="utf-8"))
    blog_copy_slugs = i18n_blog_copy.get("slugs")
    if not isinstance(blog_copy_slugs, dict):
        log_line("quality gate failed: i18n-blog-copy.json slugs must be an object")
        sys.exit(1)

    for slug, entry in blog_copy_slugs.items():
        if not isinstance(entry, dict):
            log_line(f"quality gate failed: i18n-blog-copy.json slug '{slug}' must map to an object")
            sys.exit(1)
        en_entry = entry.get("en")
        if not isinstance(en_entry, dict):
            log_line(f"quality gate failed: i18n-blog-copy.json slug '{slug}' missing en object")
            sys.exit(1)
        for field_name in REQUIRED_I18N_BLOG_COPY_FIELDS:
            field_value = en_entry.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                log_line(
                    f"quality gate failed: i18n-blog-copy.json slug '{slug}' en field '{field_name}' must be non-empty string"
                )
                sys.exit(1)

        locale_entries = entry.get("locales")
        if not isinstance(locale_entries, dict):
            log_line(f"quality gate failed: i18n-blog-copy.json slug '{slug}' locales must be an object")
            sys.exit(1)
        locale_keys = set(locale_entries.keys())
        if locale_keys != EXPECTED_STANDARD_LOCALES:
            log_line(f"quality gate failed: i18n-blog-copy.json slug '{slug}' locales must include exact 10 standard locales")
            log_line(f"- expected: {sorted(EXPECTED_STANDARD_LOCALES)}")
            log_line(f"- actual: {sorted(locale_keys)}")
            sys.exit(1)

        for locale_key in EXPECTED_STANDARD_LOCALES:
            locale_fields = locale_entries.get(locale_key)
            if not isinstance(locale_fields, dict):
                log_line(
                    f"quality gate failed: i18n-blog-copy.json slug '{slug}' locale '{locale_key}' must be an object"
                )
                sys.exit(1)
            for field_name in REQUIRED_I18N_BLOG_COPY_FIELDS:
                field_value = locale_fields.get(field_name)
                if not isinstance(field_value, str) or not field_value.strip():
                    log_line(
                        f"quality gate failed: i18n-blog-copy.json slug '{slug}' locale '{locale_key}' field '{field_name}' must be non-empty string"
                    )
                    sys.exit(1)

    localized_slugs = set(blog_copy_slugs.keys()) & blog_slugs
    coverage_ratio = len(localized_slugs) / len(blog_slugs) if blog_slugs else 1.0
    if coverage_ratio < MIN_I18N_BLOG_COPY_COVERAGE_RATIO:
        missing_blog_copy = sorted(blog_slugs - set(blog_copy_slugs.keys()))
        log_line(
            "quality gate failed: i18n blog copy coverage below threshold "
            f"({coverage_ratio:.3f} < {MIN_I18N_BLOG_COPY_COVERAGE_RATIO:.3f})"
        )
        for slug in missing_blog_copy[:20]:
            log_line(f"- missing blog copy slug: {slug}")
        sys.exit(1)
    log_line(
        "i18n blog copy checks ok: "
        f"localized={len(localized_slugs)}/{len(blog_slugs)} coverage={coverage_ratio:.3f}"
    )

    log_line("quality gate passed")


if __name__ == "__main__":
    main()

