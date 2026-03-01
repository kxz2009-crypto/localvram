#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_EN = ROOT / "public" / "sitemap.xml"
EN_PAGES_ROOT = ROOT / "src" / "pages" / "en"
APPLE_SILICON_SLUG = "apple-silicon-llm-guide"


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


def write_sitemap(out: Path, urls: list[str]) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in sorted(set(urls)):
        lines.extend(["  <url>", f"    <loc>{url}</loc>", "  </url>"])
    lines.append("</urlset>")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    error_data = load_json(ROOT / "src" / "data" / "errors.json")
    hardware_data = load_json(ROOT / "src" / "data" / "hardware-tiers.json")
    model_catalog = load_json(ROOT / "src" / "data" / "model-catalog.json")

    urls = ["https://localvram.com/legal/"]
    urls.extend([f"https://localvram.com{path}" for path in en_static_paths()])

    for item in model_catalog.get("items", []):
        item_id = str(item.get("id", "")).strip()
        if item_id:
            urls.append(f"https://localvram.com/en/models/{item_id}/")

    for group in model_catalog.get("group_definitions", []):
        group_id = str(group.get("id", "")).strip()
        if group_id:
            urls.append(f"https://localvram.com/en/models/group/{group_id}/")

    for slug in blog_slugs():
        urls.append(f"https://localvram.com/en/blog/{slug}/")

    for tier in hardware_data.get("tiers", []):
        urls.append(f"https://localvram.com/en/hardware/{tier['vram_gb']}gb-vram-models/")
    urls.append(f"https://localvram.com/en/hardware/{APPLE_SILICON_SLUG}/")

    for item in error_data.get("errors", []):
        urls.append(f"https://localvram.com/en/errors/{item['id']}/")

    write_sitemap(OUT_EN, urls)
    print(f"generated {OUT_EN} with {len(sorted(set(urls)))} urls")


if __name__ == "__main__":
    main()
