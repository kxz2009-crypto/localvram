#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
import re

from logging_utils import configure_logging


LOGGER = configure_logging("push-baidu-urls")
ROOT = Path(__file__).resolve().parents[1]
ZH_BLOG_DIR = ROOT / "src" / "content" / "blog-i18n" / "zh"
ZH_STUB_MARKER = "status: zh-stub (pending full translation)"
BLOG_PATH_RE = re.compile(r"^/blog/(?P<slug>[a-z0-9-]+)/?$")


def emit(message: str, *, level: str = "info", stderr: bool = False) -> None:
    if level == "error":
        LOGGER.error("%s", message)
    elif level == "warning":
        LOGGER.warning("%s", message)
    else:
        LOGGER.info("%s", message)


def parse_retry_delays(raw: str) -> list[int]:
    out: list[int] = []
    for piece in (raw or "").split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            out.append(max(0, int(piece)))
        except ValueError:
            continue
    return out or [5, 10, 20]


def parse_sitemap(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls: list[str] = []
    for loc in root.findall(".//sm:url/sm:loc", ns):
        if loc.text:
            urls.append(loc.text.strip())
    return urls


def fetch_text(url: str, timeout: int) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def read_urls_from_file(path: Path) -> list[str]:
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        urls.append(url)
    return urls


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def is_over_quota_error(status_code: int, body: str) -> bool:
    if status_code != 400:
        return False
    normalized = (body or "").lower()
    return "over quota" in normalized


def parse_csv_list(raw: str) -> list[str]:
    values: list[str] = []
    for piece in str(raw or "").split(","):
        item = piece.strip()
        if item:
            values.append(item)
    return values


def is_path_excluded(path: str, excluded_prefixes: list[str]) -> bool:
    normalized = str(path or "").strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    for prefix in excluded_prefixes:
        px = str(prefix or "").strip()
        if not px:
            continue
        if not px.startswith("/"):
            px = f"/{px}"
        # Match both exact path and nested path under this prefix.
        if normalized == px.rstrip("/"):
            return True
        if normalized.startswith(px.rstrip("/") + "/"):
            return True
    return False


def is_stub_blog_url(path: str) -> bool:
    match = BLOG_PATH_RE.match(path)
    if not match:
        return False
    slug = match.group("slug")
    zh_file = ZH_BLOG_DIR / f"{slug}.md"
    if not zh_file.exists():
        return True
    try:
        content = zh_file.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return True
    return ZH_STUB_MARKER in content


def post_with_retry(endpoint: str, payload_lines: list[str], retry_delays: list[int], timeout: int) -> str:
    data = ("\n".join(payload_lines) + "\n").encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, method="POST", headers={"Content-Type": "text/plain"})
    attempts = len(retry_delays) + 1
    last_error = ""
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                body = ""
            last_error = f"HTTP {exc.code} {exc.reason} {body}".strip()
            if is_over_quota_error(exc.code, body):
                emit(f"over_quota=true error={last_error}", level="warning")
                raise RuntimeError(last_error) from exc
            if i < len(retry_delays):
                emit(f"retry_http_error attempt={i + 1}/{attempts} delay_s={retry_delays[i]} error={last_error}", level="warning")
                time.sleep(retry_delays[i])
                continue
            raise RuntimeError(last_error) from exc
        except urllib.error.URLError as exc:
            last_error = f"URL error: {exc}"
            if i < len(retry_delays):
                emit(f"retry_url_error attempt={i + 1}/{attempts} delay_s={retry_delays[i]} error={last_error}", level="warning")
                time.sleep(retry_delays[i])
                continue
            raise RuntimeError(last_error) from exc
    raise RuntimeError(last_error or "unknown push error")


def main() -> int:
    parser = argparse.ArgumentParser(description="Push CN URLs to Baidu via ordinary push API.")
    parser.add_argument("--site", default="https://localvram.cn", help="Primary CN site URL (used for host filter).")
    parser.add_argument("--token", default="", help="Baidu push token. Can also be set by BAIDU_PUSH_TOKEN.")
    parser.add_argument("--sitemap-url", default="https://localvram.cn/sitemap-cn.xml")
    parser.add_argument("--urls-file", default="", help="Optional plain text URL list, one URL per line.")
    parser.add_argument("--limit", type=int, default=5000, help="Maximum URLs to push in this run.")
    parser.add_argument("--batch-size", type=int, default=500, help="URLs per POST request.")
    parser.add_argument("--retry-delays-s", default="5,10,20")
    parser.add_argument("--timeout-s", type=int, default=30)
    parser.add_argument(
        "--exclude-prefixes",
        default="/en,/zh,/api",
        help="Comma-separated URL path prefixes to exclude before pushing.",
    )
    parser.add_argument(
        "--include-blog-stub",
        action="store_true",
        help="Include blog URLs whose zh files are still stub placeholders.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print candidate URLs only, do not push.")
    args = parser.parse_args()

    token = args.token.strip() or os.environ.get("BAIDU_PUSH_TOKEN", "").strip()

    site = args.site.strip().rstrip("/")
    site_host = urllib.parse.urlsplit(site).netloc
    if not site_host:
        raise SystemExit("invalid --site")

    if args.urls_file:
        urls = read_urls_from_file(Path(args.urls_file))
    else:
        xml_text = fetch_text(args.sitemap_url, timeout=max(5, args.timeout_s))
        urls = parse_sitemap(xml_text)

    excluded_prefixes = parse_csv_list(args.exclude_prefixes)
    filtered: list[str] = []
    seen: set[str] = set()
    skipped_by_prefix = 0
    skipped_by_stub = 0
    for url in urls:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.netloc
        if host != site_host:
            continue
        path = parsed.path or "/"
        if is_path_excluded(path, excluded_prefixes):
            skipped_by_prefix += 1
            continue
        if not args.include_blog_stub and is_stub_blog_url(path):
            skipped_by_stub += 1
            continue
        if url in seen:
            continue
        seen.add(url)
        filtered.append(url)
    filtered = filtered[: max(0, args.limit)]

    emit(f"site_host={site_host}")
    emit(f"excluded_prefixes={excluded_prefixes}")
    emit(f"skipped_by_prefix={skipped_by_prefix}")
    emit(f"skipped_by_stub={skipped_by_stub}")
    emit(f"candidate_urls={len(filtered)}")
    if filtered:
        emit(f"first_url={filtered[0]}")
        emit(f"last_url={filtered[-1]}")

    if args.dry_run:
        emit("dry_run=true")
        return 0

    if not token:
        raise SystemExit("missing token: pass --token or set BAIDU_PUSH_TOKEN")
    if not filtered:
        emit("nothing_to_push=true")
        return 0

    endpoint = f"http://data.zz.baidu.com/urls?site={site_host}&token={token}"
    retry_delays = parse_retry_delays(args.retry_delays_s)
    batches = chunked(filtered, max(1, args.batch_size))
    emit(f"batch_count={len(batches)}")
    ok = 0
    for idx, batch in enumerate(batches, start=1):
        body = post_with_retry(endpoint, batch, retry_delays=retry_delays, timeout=max(5, args.timeout_s))
        ok += len(batch)
        emit(f"batch={idx}/{len(batches)} pushed={len(batch)} response={body}")
    emit(f"pushed_total={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
