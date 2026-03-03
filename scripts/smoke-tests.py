#!/usr/bin/env python3
import importlib.util
import re
import sys
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
SITEMAP_LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
LOGGER = configure_logging("smoke-tests")


def load_build_sitemap_module():
    module_path = ROOT / "scripts" / "build-sitemap.py"
    spec = importlib.util.spec_from_file_location("build_sitemap", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module spec: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_sitemap_urls(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return {m.group(1).strip() for m in SITEMAP_LOC_RE.finditer(text)}


def fail(message: str) -> None:
    LOGGER.error("smoke tests failed: %s", message)
    sys.exit(1)


def main() -> None:
    build_sitemap = load_build_sitemap_module()
    rollout_locales = build_sitemap.load_rollout_locales()
    en_urls = build_sitemap.build_en_urls()
    localizable_en_urls = [u for u in en_urls if build_sitemap.is_localizable_en_url(u)]

    if not rollout_locales:
        fail("rollout locales are empty")

    for locale in rollout_locales:
        sitemap_file = PUBLIC_DIR / f"sitemap-{locale}.xml"
        if not sitemap_file.exists():
            fail(f"missing sitemap file: {sitemap_file}")

        actual_urls = read_sitemap_urls(sitemap_file)
        if locale == "en":
            expected_urls = set(en_urls)
        else:
            expected_urls = {build_sitemap.replace_en_locale(u, locale) for u in localizable_en_urls}

        if actual_urls != expected_urls:
            missing = sorted(expected_urls - actual_urls)[:10]
            extra = sorted(actual_urls - expected_urls)[:10]
            LOGGER.error("locale=%s expected=%d actual=%d", locale, len(expected_urls), len(actual_urls))
            if missing:
                LOGGER.error("missing samples:")
                for item in missing:
                    LOGGER.error("- %s", item)
            if extra:
                LOGGER.error("extra samples:")
                for item in extra:
                    LOGGER.error("- %s", item)
            fail(f"sitemap mismatch for locale={locale}")

        # Safety floor to catch accidental regressions such as 3-url locale sitemaps.
        minimum_expected = 100 if locale != "en" else 500
        if len(actual_urls) < minimum_expected:
            fail(
                f"unexpectedly low sitemap coverage for locale={locale}: "
                f"{len(actual_urls)} < {minimum_expected}"
            )

        LOGGER.info("sitemap ok: locale=%s urls=%d", locale, len(actual_urls))

    LOGGER.info("smoke tests passed")


if __name__ == "__main__":
    main()
