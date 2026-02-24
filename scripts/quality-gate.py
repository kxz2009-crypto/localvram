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
    ROOT / "src" / "data" / "search-console-keywords.json",
]
REQUIRED_PAGES = [
    ROOT / "src" / "pages" / "en" / "models" / "index.astro",
    ROOT / "src" / "pages" / "en" / "models" / "[id].astro",
    ROOT / "src" / "pages" / "en" / "models" / "group" / "[group].astro",
    ROOT / "src" / "pages" / "en" / "benchmarks" / "changelog.astro",
    ROOT / "src" / "pages" / "en" / "benchmarks" / "submit-result.astro",
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
    model_count = int(models.get("count", len(models.get("models", []))))
    catalog_count = int(model_catalog.get("count", len(model_catalog.get("items", []))))

    if model_count < 200 or catalog_count < 200:
        print(f"quality gate failed: expected >=200 models, got models={model_count}, catalog={catalog_count}")
        sys.exit(1)
    print(f"model counts ok: models={model_count}, catalog={catalog_count}")

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
