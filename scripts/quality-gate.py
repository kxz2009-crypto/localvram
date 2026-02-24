#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT / "src" / "data" / "models.json",
    ROOT / "src" / "data" / "status.json",
    ROOT / "src" / "data" / "cta-rules.json",
    ROOT / "src" / "data" / "daily-updates.json",
]


def main() -> None:
    missing = [str(p) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        print("quality gate failed: missing required files")
        for item in missing:
            print(f"- {item}")
        sys.exit(1)

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
