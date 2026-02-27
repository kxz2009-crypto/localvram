#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_EN = ROOT / "public" / "sitemap.xml"
OUT_CN = ROOT / "public" / "sitemap-cn.xml"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blog_slugs() -> list[str]:
    blog_dir = ROOT / "src" / "content" / "blog"
    return sorted([p.stem for p in blog_dir.glob("*.md")])


def zh_static_paths() -> list[str]:
    pages_root = ROOT / "src" / "pages" / "zh"
    if not pages_root.exists():
        return []
    paths: list[str] = []
    for file in pages_root.rglob("*.astro"):
        rel = file.relative_to(pages_root)
        parts = list(rel.parts)
        if any(("[" in part) or ("]" in part) for part in parts):
            continue
        if parts[-1] == "index.astro":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].removesuffix(".astro")
        path = "/zh/" + "/".join(parts)
        if not path.endswith("/"):
            path += "/"
        path = path.replace("//", "/")
        paths.append(path)
    if "/zh/" not in paths:
        paths.append("/zh/")
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

    base_urls_en = [
        "https://localvram.com/en/",
        "https://localvram.com/legal/",
        "https://localvram.com/en/blog/",
        "https://localvram.com/en/updates/",
        "https://localvram.com/en/about/methodology/",
        "https://localvram.com/en/status/data-freshness/",
        "https://localvram.com/en/status/runner-health/",
        "https://localvram.com/en/status/pipeline-status/",
        "https://localvram.com/en/status/conversion-funnel/",
        "https://localvram.com/en/status/submission-review/",
        "https://localvram.com/en/status/content-publish/",
        "https://localvram.com/en/errors/",
        "https://localvram.com/en/hardware/",
        "https://localvram.com/en/hardware/apple-silicon-llm-guide/",
        "https://localvram.com/en/models/",
        "https://localvram.com/en/benchmarks/",
        "https://localvram.com/en/benchmarks/changelog/",
        "https://localvram.com/en/benchmarks/submit-result/",
        "https://localvram.com/en/tools/vram-calculator/",
        "https://localvram.com/en/tools/roi-calculator/",
        "https://localvram.com/en/tools/quantization-blind-test/",
        "https://localvram.com/en/affiliate/cloud-gpu/",
        "https://localvram.com/en/affiliate/hardware-upgrade/",
        "https://localvram.com/en/guides/ollama-local-cluster-network/",
        "https://localvram.com/en/guides/ollama-vs-vllm-vram/",
    ]

    for item in error_data.get("errors", []):
        base_urls_en.append(f"https://localvram.com/en/errors/{item['id']}/")

    for tier in hardware_data.get("tiers", []):
        base_urls_en.append(f"https://localvram.com/en/hardware/{tier['vram_gb']}gb-vram-models/")

    for slug in blog_slugs():
        base_urls_en.append(f"https://localvram.com/en/blog/{slug}/")

    for group in model_catalog.get("group_definitions", []):
        base_urls_en.append(f"https://localvram.com/en/models/group/{group['id']}/")

    for item in model_catalog.get("items", []):
        base_urls_en.append(f"https://localvram.com/en/models/{item['id']}/")

    zh_paths = zh_static_paths()
    base_urls_cn = [f"https://localvram.cn{path}" for path in zh_paths]

    write_sitemap(OUT_EN, base_urls_en)
    write_sitemap(OUT_CN, base_urls_cn)
    print(f"generated {OUT_EN} with {len(sorted(set(base_urls_en)))} urls")
    print(f"generated {OUT_CN} with {len(sorted(set(base_urls_cn)))} urls")


if __name__ == "__main__":
    main()
