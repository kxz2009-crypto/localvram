#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit, urlunsplit

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
EN_PAGES_ROOT = ROOT / "src" / "pages" / "en"
ROLLOUT_CONFIG = ROOT / "src" / "data" / "i18n-rollout.json"
COM_SITE_ORIGIN = "https://localvram.com"
CN_SITE_ORIGIN = "https://localvram.cn"
APPLE_SILICON_SLUG = "apple-silicon-llm-guide"
COM_LOCALES = ["en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id"]
LOCALIZABLE_EN_PREFIXES = [
    "/en/guides/",
    "/en/status/",
    "/en/tools/",
    "/en/errors/",
    "/en/hardware/",
    "/en/models/",
    "/en/blog/",
    "/en/matrix/",
    "/en/multimodal/",
    "/en/updates/",
]
LOCALIZABLE_EN_EXACT_PATHS = {
    "/en/",
    "/en/about/methodology/",
    "/en/affiliate/cloud-gpu/",
    "/en/affiliate/hardware-upgrade/",
    "/en/benchmarks/",
    "/en/benchmarks/changelog/",
    "/en/benchmarks/submit-result/",
    "/en/compare/qwen35-35b-q4-vs-llama31-70b-q4/",
    "/en/hardware/apple-silicon-llm-guide/",
    "/en/hardware/verified-3090/",
}
LOGGER = configure_logging("build-sitemap")
FRONTMATTER_RE = re.compile(r"^\ufeff?---\s*\r?\n(?P<frontmatter>[\s\S]*?)\r?\n---\s*(\r?\n)?")
FRONTMATTER_FIELD_RE = re.compile(r"(?m)^(?P<key>[A-Za-z][A-Za-z0-9_-]*):\s*(?P<value>.+?)\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SitemapEntry(TypedDict, total=False):
    loc: str
    lastmod: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build sitemap and robots artifacts for COM/CN targets.")
    parser.add_argument(
        "--target",
        choices=["auto", "com", "cn"],
        default="auto",
        help="Build target. 'auto' uses BUILD_TARGET env.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(PUBLIC_DIR),
        help="Output directory for generated sitemap and robots files.",
    )
    return parser.parse_args()


def resolve_target(raw_target: str) -> str:
    if raw_target in {"com", "cn"}:
        return raw_target
    build_target = str(os.environ.get("BUILD_TARGET", "")).strip().lower()
    return "cn" if build_target == "cn" else "com"


def resolve_site_origin(target: str) -> str:
    env_site = str(os.environ.get("SITE_URL", "")).strip().rstrip("/")
    if env_site:
        return env_site
    return CN_SITE_ORIGIN if target == "cn" else COM_SITE_ORIGIN


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blog_slugs() -> list[str]:
    blog_dir = ROOT / "src" / "content" / "blog"
    return sorted([p.stem for p in blog_dir.glob("*.md")])


def parse_frontmatter_fields(markdown: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for item in FRONTMATTER_FIELD_RE.finditer(match.group("frontmatter")):
        fields[item.group("key")] = item.group("value").strip().strip('"').strip("'")
    return fields


def normalize_lastmod(value: object) -> str:
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        return ""
    date_part = text.split("T", 1)[0].strip()
    return date_part if DATE_RE.match(date_part) else ""


def blog_lastmod_by_slug() -> dict[str, str]:
    blog_dir = ROOT / "src" / "content" / "blog"
    lastmods: dict[str, str] = {}
    for path in blog_dir.glob("*.md"):
        fields = parse_frontmatter_fields(path.read_text(encoding="utf-8"))
        lastmod = normalize_lastmod(fields.get("updatedDate") or fields.get("pubDate"))
        if lastmod:
            lastmods[path.stem] = lastmod
    return lastmods


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


def write_urlset(out: Path, entries: list[SitemapEntry] | list[str]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    normalized_entries = normalize_sitemap_entries(entries)
    for entry in sorted(normalized_entries, key=lambda item: item["loc"]):
        lines.extend(["  <url>", f"    <loc>{entry['loc']}</loc>"])
        if entry.get("lastmod"):
            lines.append(f"    <lastmod>{entry['lastmod']}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_sitemap_entries(entries: list[SitemapEntry] | list[str]) -> list[SitemapEntry]:
    deduped: dict[str, SitemapEntry] = {}
    for item in entries:
        if isinstance(item, str):
            entry: SitemapEntry = {"loc": item}
        else:
            entry = {"loc": str(item.get("loc", "")).strip()}
            lastmod = normalize_lastmod(item.get("lastmod"))
            if lastmod:
                entry["lastmod"] = lastmod
        if entry["loc"]:
            existing = deduped.get(entry["loc"])
            if existing is None or (entry.get("lastmod") and not existing.get("lastmod")):
                deduped[entry["loc"]] = entry
    return list(deduped.values())


def write_sitemap_index(out: Path, sitemap_urls: list[str]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for sitemap_url in sitemap_urls:
        lines.extend(["  <sitemap>", f"    <loc>{sitemap_url}</loc>", "  </sitemap>"])
    lines.append("</sitemapindex>")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_robots(out_dir: Path, sitemap_url: str) -> None:
    robots_path = out_dir / "robots.txt"
    robots_path.write_text(
        "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                "Disallow: /go/",
                "Disallow: /recommends/",
                "",
                f"Sitemap: {sitemap_url}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def replace_en_locale(url: str, locale: str) -> str:
    parts = urlsplit(url)
    localized_path = parts.path.replace("/en/", f"/{locale}/", 1)
    return urlunsplit((parts.scheme, parts.netloc, localized_path, parts.query, parts.fragment))


def to_cn_root_path(url: str, cn_origin: str) -> str:
    parts = urlsplit(url)
    path = parts.path
    if path == "/en/":
        path = "/"
    elif path.startswith("/en/"):
        path = "/" + path[len("/en/") :]
    target = urlsplit(cn_origin)
    return urlunsplit((target.scheme, target.netloc, path, parts.query, parts.fragment))


def replace_entry_en_locale(entry: SitemapEntry, locale: str) -> SitemapEntry:
    localized: SitemapEntry = {"loc": replace_en_locale(entry["loc"], locale)}
    if entry.get("lastmod"):
        localized["lastmod"] = entry["lastmod"]
    return localized


def to_cn_root_entry(entry: SitemapEntry, cn_origin: str) -> SitemapEntry:
    localized: SitemapEntry = {"loc": to_cn_root_path(entry["loc"], cn_origin)}
    if entry.get("lastmod"):
        localized["lastmod"] = entry["lastmod"]
    return localized


def is_localizable_en_url(url: str) -> bool:
    path = urlsplit(url).path
    if path in LOCALIZABLE_EN_EXACT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in LOCALIZABLE_EN_PREFIXES)


def cleanup_stale_com_locale_sitemaps(out_dir: Path, rollout_locales: list[str]) -> None:
    keep = {f"sitemap-{locale}.xml" for locale in rollout_locales}
    keep.update({"sitemap-index.xml", "sitemap.xml"})
    for file in out_dir.glob("sitemap-*.xml"):
        if file.name in keep:
            continue
        if re.match(r"^sitemap-[a-z]{2}\.xml$", file.name):
            file.unlink(missing_ok=True)


def cleanup_stale_cn_locale_sitemaps(out_dir: Path) -> None:
    keep = {"sitemap-cn.xml", "sitemap-index.xml", "sitemap.xml"}
    for file in out_dir.glob("sitemap-*.xml"):
        if file.name in keep:
            continue
        if re.match(r"^sitemap-[a-z]{2}\.xml$", file.name):
            file.unlink(missing_ok=True)


def build_en_url_entries(site_origin: str) -> list[SitemapEntry]:
    error_data = load_json(ROOT / "src" / "data" / "errors.json")
    hardware_data = load_json(ROOT / "src" / "data" / "hardware-tiers.json")
    model_catalog = load_json(ROOT / "src" / "data" / "model-catalog.json")
    blog_lastmods = blog_lastmod_by_slug()

    entries: list[SitemapEntry] = [{"loc": f"{site_origin}/legal/"}]
    entries.extend({"loc": f"{site_origin}{path}"} for path in en_static_paths())

    for item in model_catalog.get("items", []):
        item_id = str(item.get("id", "")).strip()
        if item_id:
            entries.append({"loc": f"{site_origin}/en/models/{item_id}/"})

    for group in model_catalog.get("group_definitions", []):
        group_id = str(group.get("id", "")).strip()
        if group_id:
            entries.append({"loc": f"{site_origin}/en/models/group/{group_id}/"})

    for slug in blog_slugs():
        entry: SitemapEntry = {"loc": f"{site_origin}/en/blog/{slug}/"}
        if blog_lastmods.get(slug):
            entry["lastmod"] = blog_lastmods[slug]
        entries.append(entry)

    for tier in hardware_data.get("tiers", []):
        entries.append({"loc": f"{site_origin}/en/hardware/{tier['vram_gb']}gb-vram-models/"})
    entries.append({"loc": f"{site_origin}/en/hardware/{APPLE_SILICON_SLUG}/"})

    for item in error_data.get("errors", []):
        entries.append({"loc": f"{site_origin}/en/errors/{item['id']}/"})

    return normalize_sitemap_entries(entries)


def build_en_urls(site_origin: str) -> list[str]:
    return sorted(entry["loc"] for entry in build_en_url_entries(site_origin))


def build_com_artifacts(out_dir: Path, site_origin: str) -> None:
    rollout_locales = load_rollout_locales()
    en_entries = build_en_url_entries(site_origin)
    en_urls = [entry["loc"] for entry in en_entries]
    localizable_en_urls = [url for url in en_urls if is_localizable_en_url(url)]
    localizable_en_entries = [entry for entry in en_entries if is_localizable_en_url(entry["loc"])]

    generated_sitemaps: list[str] = []
    for locale in rollout_locales:
        out_file = out_dir / f"sitemap-{locale}.xml"
        if locale == "en":
            locale_entries = en_entries
        else:
            locale_entries = [replace_entry_en_locale(entry, locale) for entry in localizable_en_entries]
        write_urlset(out_file, locale_entries)
        generated_sitemaps.append(f"{site_origin}/{out_file.name}")

    cleanup_stale_com_locale_sitemaps(out_dir, rollout_locales)
    out_index = out_dir / "sitemap-index.xml"
    out_alias = out_dir / "sitemap.xml"
    write_sitemap_index(out_index, generated_sitemaps)
    out_alias.write_text(out_index.read_text(encoding="utf-8"), encoding="utf-8")
    write_robots(out_dir, f"{site_origin}/sitemap.xml")

    LOGGER.info("target=com out_dir=%s", out_dir)
    LOGGER.info("generated %s with %s sitemap entries", out_index, len(generated_sitemaps))
    LOGGER.info("generated %s (alias of sitemap-index.xml)", out_alias)
    for locale in rollout_locales:
        file = out_dir / f"sitemap-{locale}.xml"
        count = file.read_text(encoding="utf-8").count("<url>")
        LOGGER.info("- %s: %s urls", file.name, count)


def build_cn_artifacts(out_dir: Path, site_origin: str) -> None:
    en_entries = build_en_url_entries(site_origin)
    cn_entries = [to_cn_root_entry(entry, site_origin) for entry in en_entries if is_localizable_en_url(entry["loc"])]

    cleanup_stale_cn_locale_sitemaps(out_dir)
    cn_sitemap = out_dir / "sitemap-cn.xml"
    out_index = out_dir / "sitemap-index.xml"
    out_alias = out_dir / "sitemap.xml"

    write_urlset(cn_sitemap, cn_entries)
    write_sitemap_index(out_index, [f"{site_origin}/sitemap-cn.xml"])
    out_alias.write_text(cn_sitemap.read_text(encoding="utf-8"), encoding="utf-8")
    write_robots(out_dir, f"{site_origin}/sitemap-cn.xml")

    LOGGER.info("target=cn out_dir=%s", out_dir)
    LOGGER.info("generated %s with %s urls", cn_sitemap, cn_sitemap.read_text(encoding="utf-8").count("<url>"))
    LOGGER.info("generated %s with 1 sitemap entry", out_index)
    LOGGER.info("generated %s (alias of sitemap-cn.xml)", out_alias)


def main() -> None:
    args = parse_args()
    target = resolve_target(args.target)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    site_origin = resolve_site_origin(target)

    if target == "cn":
        build_cn_artifacts(out_dir, site_origin)
    else:
        build_com_artifacts(out_dir, site_origin)


if __name__ == "__main__":
    main()
