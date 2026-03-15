#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from logging_utils import configure_logging


LOGGER = configure_logging("push-baidu-urls-2day")
ROOT = Path(__file__).resolve().parents[1]
ZH_BLOG_DIR = ROOT / "src" / "content" / "blog-i18n" / "zh"
ZH_STUB_MARKER = "status: zh-stub (pending full translation)"
BLOG_PATH_RE = re.compile(r"^/blog/(?P<slug>[a-z0-9-]+)/?$")


def emit(message: str, *, level: str = "info") -> None:
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


def parse_csv_list(raw: str) -> list[str]:
    values: list[str] = []
    for piece in str(raw or "").split(","):
        item = piece.strip()
        if item:
            values.append(item)
    return values


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


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


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
            if i < len(retry_delays):
                emit(
                    f"retry_http_error attempt={i + 1}/{attempts} delay_s={retry_delays[i]} error={last_error}",
                    level="warning",
                )
                time.sleep(retry_delays[i])
                continue
            raise RuntimeError(last_error) from exc
        except urllib.error.URLError as exc:
            last_error = f"URL error: {exc}"
            if i < len(retry_delays):
                emit(
                    f"retry_url_error attempt={i + 1}/{attempts} delay_s={retry_delays[i]} error={last_error}",
                    level="warning",
                )
                time.sleep(retry_delays[i])
                continue
            raise RuntimeError(last_error) from exc
    raise RuntimeError(last_error or "unknown push error")


def split_urls(urls: list[str], *, day: int, total_days: int) -> list[str]:
    # Round-robin split keeps each day mixed across sections instead of front-loading one section.
    return [url for idx, url in enumerate(urls) if idx % total_days == (day - 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Push CN URLs to Baidu by day-batch (day 1 / day 2).")
    parser.add_argument("--site", default="https://localvram.cn", help="Primary CN site URL (used for host filter).")
    parser.add_argument("--token", default="", help="Baidu push token. Can also be set by BAIDU_PUSH_TOKEN.")
    parser.add_argument("--sitemap-url", default="https://localvram.cn/sitemap-cn.xml")
    parser.add_argument("--day", type=int, choices=[1, 2], required=True, help="Day batch index (1 or 2).")
    parser.add_argument("--total-days", type=int, default=2, help="Total split day count. Default: 2.")
    parser.add_argument("--limit", type=int, default=5000, help="Maximum URLs to consider before splitting.")
    parser.add_argument("--batch-size", type=int, default=200, help="URLs per POST request.")
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
    parser.add_argument("--out-file", default="", help="Optional output file to save selected URLs.")
    parser.add_argument("--dry-run", action="store_true", help="Print candidate URLs only, do not push.")
    args = parser.parse_args()

    if args.total_days < 1:
        raise SystemExit("--total-days must be >= 1")
    if args.day > args.total_days:
        raise SystemExit("--day must be <= --total-days")

    token = args.token.strip() or os.environ.get("BAIDU_PUSH_TOKEN", "").strip()
    site = args.site.strip().rstrip("/")
    site_host = urllib.parse.urlsplit(site).netloc
    if not site_host:
        raise SystemExit("invalid --site")

    xml_text = fetch_text(args.sitemap_url, timeout=max(5, args.timeout_s))
    urls = parse_sitemap(xml_text)

    excluded_prefixes = parse_csv_list(args.exclude_prefixes)
    filtered: list[str] = []
    seen: set[str] = set()
    skipped_by_prefix = 0
    skipped_by_stub = 0
    for url in urls:
        parsed = urllib.parse.urlsplit(url)
        if parsed.netloc != site_host:
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
    selected = split_urls(filtered, day=args.day, total_days=args.total_days)

    emit(f"site_host={site_host}")
    emit(f"day={args.day}/{args.total_days}")
    emit(f"excluded_prefixes={excluded_prefixes}")
    emit(f"skipped_by_prefix={skipped_by_prefix}")
    emit(f"skipped_by_stub={skipped_by_stub}")
    emit(f"candidate_urls={len(filtered)}")
    emit(f"selected_urls={len(selected)}")
    if selected:
        emit(f"first_url={selected[0]}")
        emit(f"last_url={selected[-1]}")

    if args.out_file:
        out_path = Path(args.out_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")
        emit(f"wrote_file={out_path}")

    if args.dry_run:
        emit("dry_run=true")
        return 0

    if not token:
        raise SystemExit("missing token: pass --token or set BAIDU_PUSH_TOKEN")
    if not selected:
        emit("nothing_to_push=true")
        return 0

    endpoint = f"http://data.zz.baidu.com/urls?site={site_host}&token={token}"
    retry_delays = parse_retry_delays(args.retry_delays_s)
    batches = chunked(selected, max(1, args.batch_size))
    emit(f"batch_count={len(batches)}")
    pushed = 0
    for idx, batch in enumerate(batches, start=1):
        body = post_with_retry(endpoint, batch, retry_delays=retry_delays, timeout=max(5, args.timeout_s))
        pushed += len(batch)
        emit(f"batch={idx}/{len(batches)} pushed={len(batch)} response={body}")
    emit(f"pushed_total={pushed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
