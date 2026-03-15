#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from logging_utils import configure_logging


LOGGER = configure_logging("build-cn-changed-urls")
SKIP_HTML_PATHS = {"/404.html", "/403.html", "/500.html"}


def parse_csv_list(raw: str) -> list[str]:
    values: list[str] = []
    for piece in str(raw or "").split(","):
        item = piece.strip()
        if item:
            values.append(item)
    return values


def normalize_prefix(prefix: str) -> str:
    text = str(prefix or "").strip()
    if not text:
        return ""
    if not text.startswith("/"):
        text = f"/{text}"
    return text.rstrip("/")


def is_path_excluded(path: str, excluded_prefixes: list[str]) -> bool:
    normalized = str(path or "").strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    for prefix in excluded_prefixes:
        px = normalize_prefix(prefix)
        if not px:
            continue
        if normalized == px:
            return True
        if normalized.startswith(px + "/"):
            return True
    return False


def to_url_path(relative_html_path: Path) -> str:
    rel = relative_html_path.as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return f"/{rel[:-len('index.html')]}"
    return f"/{rel}"


def compute_manifest(dist_dir: Path, site_origin: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for html_file in sorted(dist_dir.rglob("*.html")):
        rel = html_file.relative_to(dist_dir)
        path = to_url_path(rel)
        if path in SKIP_HTML_PATHS:
            continue
        digest = hashlib.sha256(html_file.read_bytes()).hexdigest()
        manifest[f"{site_origin}{path}"] = digest
    return manifest


def load_manifest(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        LOGGER.warning("baseline manifest is not valid json: %s", path)
        return {}
    if not isinstance(payload, dict):
        LOGGER.warning("baseline manifest is not an object: %s", path)
        return {}
    out: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, str):
            out[key] = value
    return out


def write_manifest(path: Path, manifest: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_urls(path: Path, urls: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(urls)
    if body:
        body += "\n"
    path.write_text(body, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build changed CN URL list by comparing dist-cn html hash manifest.")
    parser.add_argument("--dist-dir", default="dist-cn")
    parser.add_argument("--site", default="https://localvram.cn")
    parser.add_argument("--baseline-manifest", default="logs/cn-url-manifest-baseline.json")
    parser.add_argument("--output-manifest", default="logs/cn-url-manifest-current.json")
    parser.add_argument("--output-urls", default="logs/baidu-changed-urls.txt")
    parser.add_argument(
        "--exclude-prefixes",
        default="/en,/zh,/api",
        help="Comma-separated URL path prefixes to exclude from changed URL output.",
    )
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir).resolve()
    if not dist_dir.exists():
        raise SystemExit(f"dist dir does not exist: {dist_dir}")
    if not dist_dir.is_dir():
        raise SystemExit(f"dist path is not a directory: {dist_dir}")

    site_origin = args.site.strip().rstrip("/")
    site_host = urlsplit(site_origin).netloc
    if not site_host:
        raise SystemExit(f"invalid --site: {args.site}")

    baseline_path = Path(args.baseline_manifest)
    output_manifest_path = Path(args.output_manifest)
    output_urls_path = Path(args.output_urls)
    excluded_prefixes = parse_csv_list(args.exclude_prefixes)

    baseline_manifest = load_manifest(baseline_path)
    current_manifest = compute_manifest(dist_dir, site_origin)

    changed_urls: list[str] = []
    skipped_by_prefix = 0
    for url, digest in sorted(current_manifest.items()):
        old_digest = baseline_manifest.get(url, "")
        if old_digest == digest:
            continue
        path = urlsplit(url).path
        if is_path_excluded(path, excluded_prefixes):
            skipped_by_prefix += 1
            continue
        changed_urls.append(url)

    write_manifest(output_manifest_path, current_manifest)
    write_urls(output_urls_path, changed_urls)

    LOGGER.info("site_host=%s", site_host)
    LOGGER.info("baseline_entries=%d", len(baseline_manifest))
    LOGGER.info("current_entries=%d", len(current_manifest))
    LOGGER.info("excluded_prefixes=%s", excluded_prefixes)
    LOGGER.info("skipped_by_prefix=%d", skipped_by_prefix)
    LOGGER.info("changed_urls=%d", len(changed_urls))
    if changed_urls:
        LOGGER.info("first_changed_url=%s", changed_urls[0])
        LOGGER.info("last_changed_url=%s", changed_urls[-1])
    LOGGER.info("output_manifest=%s", output_manifest_path.as_posix())
    LOGGER.info("output_urls=%s", output_urls_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
