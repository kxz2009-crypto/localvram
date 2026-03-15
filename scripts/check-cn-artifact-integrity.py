#!/usr/bin/env python3
import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from logging_utils import configure_logging


LOGGER = configure_logging("check-cn-artifact-integrity")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEY_PATHS = ["/", "/tools/", "/tools/vram-calculator/", "/guides/", "/guides/best-coding-models/"]
COM_SITE_ORIGIN = "https://localvram.com"
SHARED_COM_PATHS = {"/legal/"}
CANONICAL_RE = re.compile(
    r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\'](?P<href>[^"\'>]+)["\']',
    re.IGNORECASE,
)
LOC_RE = re.compile(r"<loc>(?P<loc>[^<]+)</loc>", re.IGNORECASE)
EN_INTERNAL_PATH_RE = re.compile(r'(["\'])/en(?=/|["\'#?])')
ALTERNATE_TAG_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
HREFLANG_RE = re.compile(r'\bhreflang=["\'](?P<value>[^"\']+)["\']', re.IGNORECASE)
HREF_RE = re.compile(r'\bhref=["\'](?P<value>[^"\']+)["\']', re.IGNORECASE)
REL_ALTERNATE_RE = re.compile(r'\brel=["\']alternate["\']', re.IGNORECASE)
ALTERNATE_COM_LINK_RE = re.compile(
    r'<link\b(?=[^>]*\brel=["\']alternate["\'])(?=[^>]*\bhref=["\']https://localvram\.com[^"\']*["\'])[^>]*>',
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate dist-cn artifact integrity.")
    parser.add_argument("--dist", default="dist-cn", help="CN artifact directory")
    parser.add_argument("--site-origin", default="https://localvram.cn", help="Expected CN origin")
    parser.add_argument("--key-path", action="append", dest="key_paths", help="Key root path to validate")
    parser.add_argument(
        "--required-icp-number",
        default=str(os.environ.get("CN_ICP_NUMBER", "京ICP备2026009936号")).strip(),
        help="Required ICP number expected in CN index html",
    )
    parser.add_argument(
        "--required-icp-url",
        default=str(os.environ.get("CN_ICP_URL", "")).strip(),
        help="Required ICP URL expected in CN index html",
    )
    parser.add_argument(
        "--required-public-security-record",
        default=str(os.environ.get("CN_PUBLIC_SECURITY_RECORD", "公安备案办理中")).strip(),
        help="Required public security record text expected in CN pages",
    )
    parser.add_argument(
        "--required-public-security-status",
        default=str(os.environ.get("CN_PUBLIC_SECURITY_STATUS", "pending")).strip().lower(),
        help="Expected public security record status (pending|active)",
    )
    parser.add_argument(
        "--required-public-security-url",
        default=str(os.environ.get("CN_PUBLIC_SECURITY_URL", "")).strip(),
        help="Required public security record URL expected in CN pages (optional)",
    )
    return parser.parse_args()


def normalize_origin(origin: str) -> str:
    return str(origin).strip().rstrip("/")


def normalize_path(path: str) -> str:
    text = str(path or "/").strip() or "/"
    if not text.startswith("/"):
        text = f"/{text}"
    if text != "/" and not text.endswith("/"):
        text = f"{text}/"
    return text


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_canonical_href(html: str) -> str:
    match = CANONICAL_RE.search(html)
    return match.group("href").strip() if match else ""


def extract_alternates(html: str) -> dict[str, str]:
    alternates: dict[str, str] = {}
    for tag in ALTERNATE_TAG_RE.finditer(html):
        raw_tag = tag.group(0)
        if not REL_ALTERNATE_RE.search(raw_tag):
            continue
        lang_match = HREFLANG_RE.search(raw_tag)
        href_match = HREF_RE.search(raw_tag)
        if not lang_match or not href_match:
            continue
        hreflang = lang_match.group("value").strip().lower()
        href = href_match.group("value").strip()
        if hreflang and href:
            alternates[hreflang] = href
    return alternates


def expected_com_en_href(path: str) -> str:
    normalized = normalize_path(path)
    if normalized == "/":
        return f"{COM_SITE_ORIGIN}/en/"
    if normalized in SHARED_COM_PATHS:
        return f"{COM_SITE_ORIGIN}{normalized}"
    return f"{COM_SITE_ORIGIN}/en{normalized}"


def strip_expected_com_references(html: str) -> str:
    # Cross-domain hreflang links to localvram.com are expected on CN pages.
    return ALTERNATE_COM_LINK_RE.sub("", html)


def expected_source_candidates(dist_dir: Path, root_path: str) -> list[Path]:
    normalized = normalize_path(root_path)
    candidates: list[Path] = []
    if normalized == "/":
        candidates.append(dist_dir / "en" / "index.html")
        candidates.append(dist_dir / "index.html")
        return candidates

    tail = normalized.lstrip("/")
    candidates.append(dist_dir / tail / "index.html")
    candidates.append(dist_dir / "en" / tail / "index.html")
    return candidates


def expected_root_source(dist_dir: Path, root_path: str) -> Path:
    normalized = normalize_path(root_path)
    if normalized == "/":
        return dist_dir / "index.html"
    tail = normalized.lstrip("/")
    return dist_dir / tail / "index.html"


def resolve_source_html(dist_dir: Path, root_path: str, allow_en_fallback: bool = True) -> Path | None:
    candidates = expected_source_candidates(dist_dir, root_path)
    if not allow_en_fallback:
        candidates = candidates[:1]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_sitemap_locs(sitemap_path: Path) -> list[str]:
    text = read_text(sitemap_path)
    return [m.group("loc").strip() for m in LOC_RE.finditer(text) if m.group("loc").strip()]


def validate_canonical(
    dist_dir: Path,
    site_origin: str,
    root_path: str,
    errors: list[str],
    allow_en_fallback: bool = True,
) -> None:
    source = resolve_source_html(dist_dir, root_path, allow_en_fallback=allow_en_fallback)
    if source is None:
        errors.append(f"missing source html for key path {normalize_path(root_path)}")
        return
    html = read_text(source)
    canonical = extract_canonical_href(html)
    expected = f"{site_origin}{normalize_path(root_path)}"
    if canonical != expected:
        errors.append(
            "canonical mismatch "
            f"(path={normalize_path(root_path)} source={source} expected={expected} actual={canonical or '(missing)'})"
        )


def main() -> None:
    args = parse_args()
    dist_dir = (ROOT / args.dist).resolve()
    site_origin = normalize_origin(args.site_origin)
    key_paths = args.key_paths if args.key_paths else DEFAULT_KEY_PATHS
    required_icp_number = str(args.required_icp_number or "").strip()
    required_icp_url = str(args.required_icp_url or "").strip()
    required_public_security_record = str(args.required_public_security_record or "").strip()
    required_public_security_status = str(args.required_public_security_status or "pending").strip().lower()
    required_public_security_url = str(args.required_public_security_url or "").strip()

    errors: list[str] = []

    if not dist_dir.exists():
        errors.append(f"dist directory missing: {dist_dir}")
    else:
        astro_dir = dist_dir / "_astro"
        if not astro_dir.exists() or not astro_dir.is_dir():
            errors.append(f"_astro directory missing: {astro_dir}")
        else:
            has_assets = any(astro_dir.iterdir())
            if not has_assets:
                errors.append(f"_astro directory is empty: {astro_dir}")

        robots_path = dist_dir / "robots.txt"
        sitemap_cn_path = dist_dir / "sitemap-cn.xml"
        sitemap_alias_path = dist_dir / "sitemap.xml"
        redirects_path = dist_dir / "_redirects"

        for required in [robots_path, sitemap_cn_path, sitemap_alias_path, redirects_path]:
            if not required.exists():
                errors.append(f"required file missing: {required}")

        if robots_path.exists():
            robots_text = read_text(robots_path)
            expected_robots_line = f"Sitemap: {site_origin}/sitemap-cn.xml"
            if expected_robots_line not in robots_text:
                errors.append(f"robots sitemap line mismatch: expected '{expected_robots_line}'")

        sitemap_locs: list[str] = []
        if sitemap_cn_path.exists():
            sitemap_locs = load_sitemap_locs(sitemap_cn_path)
            if not sitemap_locs:
                errors.append(f"sitemap-cn has no <loc> entries: {sitemap_cn_path}")
            for loc in sitemap_locs:
                if not loc.startswith(f"{site_origin}/"):
                    errors.append(f"sitemap loc not under cn origin: {loc}")
                loc_path = normalize_path(urlsplit(loc).path)
                if loc_path.startswith("/zh/") or loc_path == "/zh/":
                    errors.append(f"sitemap-cn contains legacy /zh path: {loc}")

        if redirects_path.exists():
            redirects_text = read_text(redirects_path)
            required_redirect_lines = [
                "/zh https://localvram.cn/ 301",
                "/zh/ https://localvram.cn/ 301",
                "/zh/* https://localvram.cn/:splat 301",
                "/en / 301",
                "/en/ / 301",
                "/en/* /:splat 301",
            ]
            for line in required_redirect_lines:
                if line not in redirects_text:
                    errors.append(f"cn artifact missing redirect rule: {line}")
            if "/ /en/ 301" in redirects_text:
                errors.append("cn artifact contains legacy root redirect '/ /en/ 301'")

        for path in key_paths:
            validate_canonical(dist_dir, site_origin, path, errors, allow_en_fallback=False)

        key_sources: dict[str, Path] = {}
        for path in key_paths:
            source = resolve_source_html(dist_dir, path, allow_en_fallback=False)
            if source is not None:
                key_sources[normalize_path(path)] = source
            else:
                errors.append(
                    "missing root html for key path (cn root strategy requires materialized page): "
                    f"path={normalize_path(path)} expected={expected_root_source(dist_dir, path)}"
                )

        if (required_icp_number or required_icp_url) and not key_sources:
            errors.append("unable to resolve key source html files for icp validation")
        if required_public_security_status not in {"pending", "active"}:
            errors.append(f"invalid required public security status: {required_public_security_status}")

        for key_path, source in key_sources.items():
            source_text = read_text(source)
            alternates = extract_alternates(source_text)
            if required_icp_number and required_icp_number not in source_text:
                errors.append(f"key source missing required icp number: path={key_path} source={source}")
            if required_icp_url and required_icp_url not in source_text:
                errors.append(f"key source missing required icp url: path={key_path} source={source}")
            if required_public_security_record and required_public_security_record not in source_text:
                errors.append(
                    "key source missing required public security record text: "
                    f"path={key_path} source={source} expected={required_public_security_record}"
                )
            if required_public_security_url and required_public_security_url not in source_text:
                errors.append(
                    "key source missing required public security record url: "
                    f"path={key_path} source={source} expected={required_public_security_url}"
                )
            if required_public_security_status == "active" and "公安备案办理中" in source_text:
                errors.append(
                    "key source still shows pending public security text while status is active: "
                    f"path={key_path} source={source}"
                )
            if "© 2026 localvram.com" in source_text.lower():
                errors.append(f"key source copyright still references localvram.com: path={key_path} source={source}")
            if EN_INTERNAL_PATH_RE.search(source_text):
                errors.append(
                    "key source still contains internal /en path links under cn root strategy: "
                    f"path={key_path} source={source}"
                )
            expected_zh = f"{site_origin}{normalize_path(key_path)}"
            if alternates.get("zh-cn") != expected_zh:
                errors.append(
                    "key source alternate zh-cn mismatch: "
                    f"path={key_path} source={source} expected={expected_zh} actual={alternates.get('zh-cn') or '(missing)'}"
                )
            expected_en = expected_com_en_href(key_path)
            if alternates.get("en") != expected_en:
                errors.append(
                    "key source alternate en mismatch: "
                    f"path={key_path} source={source} expected={expected_en} actual={alternates.get('en') or '(missing)'}"
                )
            if alternates.get("x-default") != expected_en:
                errors.append(
                    "key source alternate x-default mismatch: "
                    f"path={key_path} source={source} expected={expected_en} actual={alternates.get('x-default') or '(missing)'}"
                )
            if key_path == "/" and ("Redirecting to: /en/" in source_text or "url=/en/" in source_text):
                errors.append(f"cn root index still redirects to /en: source={source}")

        # Sample a few sitemap urls and ensure source html exists in root or /en fallback.
        if sitemap_locs:
            for loc in sitemap_locs[:50]:
                loc_path = normalize_path(urlsplit(loc).path)
                source = resolve_source_html(dist_dir, loc_path, allow_en_fallback=False)
                if source is None:
                    errors.append(f"sitemap url has no source html in artifact: {loc}")

    if errors:
        LOGGER.error("CN artifact integrity check failed with %s issue(s)", len(errors))
        for err in errors:
            LOGGER.error("- %s", err)
        sys.exit(1)

    com_reference_files: list[str] = []
    for html_file in dist_dir.rglob("*.html"):
        text = read_text(html_file)
        sanitized = strip_expected_com_references(text)
        if "https://localvram.com" in sanitized:
            rel = html_file.relative_to(dist_dir).as_posix()
            com_reference_files.append(rel)
    if com_reference_files:
        LOGGER.warning(
            "CN artifact warning: found %s html file(s) with unexpected https://localvram.com references (e.g. %s)",
            len(com_reference_files),
            ", ".join(com_reference_files[:5]),
        )

    LOGGER.info("CN artifact integrity check passed: dist=%s site_origin=%s", dist_dir, site_origin)


if __name__ == "__main__":
    main()
