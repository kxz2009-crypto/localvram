#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "sitemap.xml"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blog_slugs() -> list[str]:
    blog_dir = ROOT / "src" / "content" / "blog"
    return sorted([p.stem for p in blog_dir.glob("*.md")])


def main() -> None:
    error_data = load_json(ROOT / "src" / "data" / "errors.json")
    hardware_data = load_json(ROOT / "src" / "data" / "hardware-tiers.json")
    model_catalog = load_json(ROOT / "src" / "data" / "model-catalog.json")

    base_urls = [
        "https://localvram.com/en/",
        "https://localvram.com/zh/",
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
        base_urls.append(f"https://localvram.com/en/errors/{item['id']}/")

    for tier in hardware_data.get("tiers", []):
        base_urls.append(f"https://localvram.com/en/hardware/{tier['vram_gb']}gb-vram-models/")

    for slug in blog_slugs():
        base_urls.append(f"https://localvram.com/en/blog/{slug}/")

    for group in model_catalog.get("group_definitions", []):
        base_urls.append(f"https://localvram.com/en/models/group/{group['id']}/")

    for item in model_catalog.get("items", []):
        base_urls.append(f"https://localvram.com/en/models/{item['id']}/")

    urls = sorted(set(base_urls))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        lines.extend(["  <url>", f"    <loc>{url}</loc>", "  </url>"])
    lines.append("</urlset>")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"generated {OUT} with {len(urls)} urls")


if __name__ == "__main__":
    main()
