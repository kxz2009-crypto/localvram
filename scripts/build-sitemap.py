#!/usr/bin/env python3
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
OUT_INDEX = PUBLIC_DIR / "sitemap-index.xml"
OUT_INDEX_ALIAS = PUBLIC_DIR / "sitemap.xml"
EN_PAGES_ROOT = ROOT / "src" / "pages" / "en"
ROLLOUT_CONFIG = ROOT / "src" / "data" / "i18n-rollout.json"
SITE_ORIGIN = "https://localvram.com"
APPLE_SILICON_SLUG = "apple-silicon-llm-guide"
COM_LOCALES = ["en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id"]
LOCALIZABLE_EN_PREFIXES = [
    "/en/guides/",
    "/en/status/",
    "/en/tools/",
    "/en/errors/",
    "/en/models/",
    "/en/matrix/",
    "/en/multimodal/",
    "/en/updates/",
]
LOCALIZABLE_EN_EXACT_PATHS = {
    "/en/",
    "/en/about/methodology/",
    "/en/affiliate/cloud-gpu/",
    "/en/benchmarks/changelog/",
    "/en/blog/",
    "/en/compare/qwen35-35b-q4-vs-llama31-70b-q4/",
    "/en/hardware/apple-silicon-llm-guide/",
    "/en/hardware/verified-3090/",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blog_slugs() -> list[str]:
    blog_dir = ROOT / "src" / "content" / "blog"
    return sorted([p.stem for p in blog_dir.glob("*.md")])


def en_static_paths() -> list[str]:
    paths: list[str] = []
    for file in EN_PAGES_ROOT.rglob("*.astro"):
        rel = file.relative_to(EN_PAGES_ROOT)
        parts = list(rel.parts)
        if any(("[" in part) or ("]" in part) for part in parts):
            continue
        if parts[-1] == "index.astro":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].removesuffix(".astro")
        path = "/en/" + "/".join(parts)
        if not path.endswith("/"):
            path += "/"
        path = path.replace("//", "/")
        paths.append(path)

    if "/en/" not in paths:
        paths.append("/en/")
    return sorted(set(paths))


def sanitize_rollout_locales(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return ["en"]
    sanitized = []
    for item in raw:
        value = str(item).strip().lower()
        if value in COM_LOCALES and value not in sanitized:
            sanitized.append(value)
    if "en" not in sanitized:
        sanitized.insert(0, "en")
    return sanitized or ["en"]


def load_rollout_locales() -> list[str]:
    data = load_json(ROLLOUT_CONFIG) if ROLLOUT_CONFIG.exists() else {}
    return sanitize_rollout_locales(data.get("sitemap_rollout_locales", ["en"]))


def write_urlset(out: Path, urls: list[str]) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in sorted(set(urls)):
        lines.extend(["  <url>", f"    <loc>{url}</loc>", "  </url>"])
    lines.append("</urlset>")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sitemap_index(out: Path, sitemap_urls: list[str]) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for sitemap_url in sitemap_urls:
        lines.extend(["  <sitemap>", f"    <loc>{sitemap_url}</loc>", "  </sitemap>"])
    lines.append("</sitemapindex>")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def replace_en_locale(url: str, locale: str) -> str:
    parts = urlsplit(url)
    localized_path = parts.path.replace("/en/", f"/{locale}/", 1)
    return urlunsplit((parts.scheme, parts.netloc, localized_path, parts.query, parts.fragment))


def is_localizable_en_url(url: str) -> bool:
    path = urlsplit(url).path
    if path in LOCALIZABLE_EN_EXACT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in LOCALIZABLE_EN_PREFIXES)


def cleanup_stale_locale_sitemaps(rollout_locales: list[str]) -> None:
    keep = {f"sitemap-{locale}.xml" for locale in rollout_locales}
    keep.update({"sitemap-index.xml", "sitemap.xml"})
    for file in PUBLIC_DIR.glob("sitemap-*.xml"):
        if file.name in keep:
            continue
        if re.match(r"^sitemap-[a-z]{2}\.xml$", file.name):
            file.unlink(missing_ok=True)


def build_en_urls() -> list[str]:
    error_data = load_json(ROOT / "src" / "data" / "errors.json")
    hardware_data = load_json(ROOT / "src" / "data" / "hardware-tiers.json")
    model_catalog = load_json(ROOT / "src" / "data" / "model-catalog.json")

    urls = [f"{SITE_ORIGIN}/legal/"]
    urls.extend([f"{SITE_ORIGIN}{path}" for path in en_static_paths()])

    for item in model_catalog.get("items", []):
        item_id = str(item.get("id", "")).strip()
        if item_id:
            urls.append(f"{SITE_ORIGIN}/en/models/{item_id}/")

    for group in model_catalog.get("group_definitions", []):
        group_id = str(group.get("id", "")).strip()
        if group_id:
            urls.append(f"{SITE_ORIGIN}/en/models/group/{group_id}/")

    for slug in blog_slugs():
        urls.append(f"{SITE_ORIGIN}/en/blog/{slug}/")

    for tier in hardware_data.get("tiers", []):
        urls.append(f"{SITE_ORIGIN}/en/hardware/{tier['vram_gb']}gb-vram-models/")
    urls.append(f"{SITE_ORIGIN}/en/hardware/{APPLE_SILICON_SLUG}/")

    for item in error_data.get("errors", []):
        urls.append(f"{SITE_ORIGIN}/en/errors/{item['id']}/")

    return sorted(set(urls))


def main() -> None:
    rollout_locales = load_rollout_locales()
    en_urls = build_en_urls()
    localizable_en_urls = [url for url in en_urls if is_localizable_en_url(url)]

    generated_sitemaps: list[str] = []
    for locale in rollout_locales:
        out_file = PUBLIC_DIR / f"sitemap-{locale}.xml"
        if locale == "en":
            locale_urls = en_urls
        else:
            locale_urls = [replace_en_locale(url, locale) for url in localizable_en_urls]
        write_urlset(out_file, locale_urls)
        generated_sitemaps.append(f"{SITE_ORIGIN}/{out_file.name}")

    cleanup_stale_locale_sitemaps(rollout_locales)
    write_sitemap_index(OUT_INDEX, generated_sitemaps)
    OUT_INDEX_ALIAS.write_text(OUT_INDEX.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"generated {OUT_INDEX} with {len(generated_sitemaps)} sitemap entries")
    print(f"generated {OUT_INDEX_ALIAS} (alias of sitemap-index.xml)")
    for locale in rollout_locales:
        file = PUBLIC_DIR / f"sitemap-{locale}.xml"
        count = file.read_text(encoding="utf-8").count("<url>")
        print(f"- {file.name}: {count} urls")


if __name__ == "__main__":
    main()
