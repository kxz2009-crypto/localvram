#!/usr/bin/env python3
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import urllib.error
import urllib.request

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
IMPORT_SCRIPT = ROOT / "scripts" / "import-affiliate-events.py"
BUILD_SCRIPT = ROOT / "scripts" / "build-conversion-funnel.py"
QUALITY_GATE = ROOT / "scripts" / "quality-gate.py"
AFFILIATE_LINKS_FILE = ROOT / "src" / "data" / "affiliate-links.json"
AFFILIATE_LIB_FILE = ROOT / "functions" / "_lib" / "affiliate.js"
LOGGER = configure_logging("refresh-affiliate-funnel")


def run_cmd(cmd: list[str], cwd: Path) -> None:
    LOGGER.info("+ %s", shlex.join(cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def load_affiliate_links(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise RuntimeError(f"invalid affiliate links payload: {path}")
    links: dict[str, str] = {}
    for key, value in data.items():
        name = str(key).strip()
        target = str(value).strip()
        if not name or not target:
            continue
        links[name] = target
    return links


def parse_supported_routes(affiliate_lib_path: Path) -> tuple[set[str], set[str]]:
    text = affiliate_lib_path.read_text(encoding="utf-8")
    provider_matches = re.findall(r'provider\s*===\s*"([a-z0-9_-]+)"', text)
    providers = {x.strip().lower() for x in provider_matches if x.strip()}

    object_match = re.search(
        r"const\s+AMAZON_RECOMMENDATIONS\s*=\s*\{(?P<body>.*?)\n\};",
        text,
        flags=re.DOTALL,
    )
    slugs: set[str] = set()
    if object_match:
        body = object_match.group("body")
        slug_matches = re.findall(r'["\']([a-z0-9-]+)["\']\s*:\s*\{', body)
        slugs = {x.strip().lower() for x in slug_matches if x.strip()}
    return providers, slugs


def validate_link_paths(
    links: dict[str, str],
    providers: set[str],
    slugs: set[str],
) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    for name, target in sorted(links.items(), key=lambda x: x[0]):
        if target.startswith("/go/"):
            provider = target.split("/", 3)[2].strip().lower() if target.count("/") >= 2 else ""
            if provider in providers:
                passed.append(f"{name}: {target} (provider={provider})")
            else:
                failed.append(f"{name}: unsupported /go provider '{provider}' for path {target}")
            continue
        if target.startswith("/recommends/"):
            slug = target.split("/", 3)[2].strip().lower() if target.count("/") >= 2 else ""
            if slug in slugs:
                passed.append(f"{name}: {target} (slug={slug})")
            else:
                failed.append(f"{name}: unsupported /recommends slug '{slug}' for path {target}")
            continue
        parsed = urlsplit(target)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            passed.append(f"{name}: {target} (absolute)")
            continue
        failed.append(f"{name}: invalid affiliate target '{target}'")
    return passed, failed


def check_redirect_response(url: str, timeout_s: int) -> tuple[bool, str]:
    opener = urllib.request.build_opener(NoRedirectHandler())
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LocalVRAM-AffiliateHealth/1.0)",
            "Accept": "text/html,*/*",
        },
    )
    try:
        with opener.open(req, timeout=max(1, int(timeout_s))) as resp:  # noqa: S310
            status = int(getattr(resp, "status", 0) or 0)
            location = str(resp.headers.get("Location", "")).strip()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        location = str(exc.headers.get("Location", "")).strip()
    except Exception as exc:  # noqa: BLE001
        return False, f"request_error={exc}"

    if status in {301, 302, 307, 308} and location:
        return True, f"status={status} location={location}"
    return False, f"status={status} location={location or '<none>'}"


def verify_affiliate_links(
    *,
    links_file: Path,
    affiliate_lib_file: Path,
    base_url: str,
    timeout_s: int,
) -> None:
    if not links_file.exists():
        raise SystemExit(f"verify-links failed: affiliate links file not found: {links_file}")
    if not affiliate_lib_file.exists():
        raise SystemExit(f"verify-links failed: affiliate library not found: {affiliate_lib_file}")

    links = load_affiliate_links(links_file)
    providers, slugs = parse_supported_routes(affiliate_lib_file)
    if not links:
        raise SystemExit("verify-links failed: no affiliate links configured")

    passed, failed = validate_link_paths(links, providers, slugs)
    for row in passed:
        LOGGER.info("affiliate_link_ok=%s", row)
    for row in failed:
        LOGGER.error("affiliate_link_error=%s", row)
    if failed:
        raise SystemExit(f"verify-links failed: invalid path mapping count={len(failed)}")

    base = str(base_url or "").strip().rstrip("/")
    if not base:
        LOGGER.info("verify-links skipped live redirect check: --verify-base-url not set")
        return

    live_failures: list[str] = []
    for name, target in sorted(links.items(), key=lambda x: x[0]):
        if not target.startswith("/"):
            continue
        probe_url = urljoin(base + "/", target.lstrip("/"))
        ok, detail = check_redirect_response(probe_url, timeout_s=timeout_s)
        if ok:
            LOGGER.info("affiliate_redirect_ok=%s url=%s %s", name, probe_url, detail)
        else:
            row = f"{name} url={probe_url} {detail}"
            LOGGER.error("affiliate_redirect_error=%s", row)
            live_failures.append(row)

    if live_failures:
        raise SystemExit(f"verify-links failed: live redirect check errors={len(live_failures)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot affiliate funnel refresh: import events -> rebuild funnel -> validate -> optional commit/push."
    )
    parser.add_argument("--source-file", default="", help="Raw affiliate export file (json/jsonl/ndjson)")
    parser.add_argument("--source-format", choices=["auto", "json", "jsonl"], default="auto")
    parser.add_argument("--source-label", default="cloudflare_kv_import")
    parser.add_argument("--max-age-days", type=int, default=45)
    parser.add_argument("--max-events", type=int, default=10000)
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument(
        "--affiliate-target-file",
        default=str(ROOT / "src" / "data" / "affiliate-click-events.json"),
        help="Target affiliate events JSON file path.",
    )
    parser.add_argument(
        "--funnel-output-file",
        default=str(ROOT / "src" / "data" / "conversion-funnel.json"),
        help="Output conversion funnel JSON file path.",
    )
    parser.add_argument(
        "--search-console-file",
        default=str(ROOT / "src" / "data" / "search-console-keywords.json"),
        help="Search Console keyword snapshot file path.",
    )
    parser.add_argument("--verify-links", action="store_true", help="Validate affiliate-links mapping and optional live redirects.")
    parser.add_argument("--verify-only", action="store_true", help="Only verify links, skip import/build/quality pipeline.")
    parser.add_argument("--verify-base-url", default="", help="Optional base URL for live redirect checks, e.g. https://localvram.com")
    parser.add_argument("--verify-timeout-s", type=int, default=15, help="Timeout for live redirect probes.")
    parser.add_argument("--skip-quality-gate", action="store_true")
    parser.add_argument("--git-commit", action="store_true", help="Commit changed funnel data files.")
    parser.add_argument("--git-push", action="store_true", help="Push after commit (requires --git-commit).")
    parser.add_argument(
        "--commit-message",
        default="data: refresh affiliate events and conversion funnel",
        help="Git commit message when --git-commit is set.",
    )
    args = parser.parse_args()

    if args.git_push and not args.git_commit:
        raise SystemExit("--git-push requires --git-commit")
    if args.verify_only and not args.verify_links:
        raise SystemExit("--verify-only requires --verify-links")
    if not args.verify_only and not str(args.source_file).strip():
        raise SystemExit("--source-file is required unless --verify-only is set")

    if args.verify_links:
        verify_affiliate_links(
            links_file=AFFILIATE_LINKS_FILE,
            affiliate_lib_file=AFFILIATE_LIB_FILE,
            base_url=str(args.verify_base_url),
            timeout_s=max(1, int(args.verify_timeout_s)),
        )
    if args.verify_only:
        LOGGER.info("verify_only=true")
        return

    source_file = Path(args.source_file)
    affiliate_target = Path(args.affiliate_target_file)
    funnel_output = Path(args.funnel_output_file)
    search_console_file = Path(args.search_console_file)

    run_cmd(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--source-file",
            str(source_file),
            "--target-file",
            str(affiliate_target),
            "--source-format",
            str(args.source_format),
            "--source-label",
            str(args.source_label),
            "--max-age-days",
            str(int(args.max_age_days)),
            "--max-events",
            str(int(args.max_events)),
        ],
        ROOT,
    )

    run_cmd(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--search-console-file",
            str(search_console_file),
            "--affiliate-events-file",
            str(affiliate_target),
            "--output-file",
            str(funnel_output),
            "--window-days",
            str(int(args.window_days)),
        ],
        ROOT,
    )

    if not args.skip_quality_gate:
        run_cmd([sys.executable, str(QUALITY_GATE)], ROOT)

    if args.git_commit:
        run_cmd(["git", "add", str(affiliate_target), str(funnel_output)], ROOT)
        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(ROOT),
            check=False,
        )
        if diff_check.returncode == 0:
            LOGGER.info("no staged changes for funnel data; skip commit")
        else:
            run_cmd(["git", "commit", "-m", str(args.commit_message)], ROOT)
            if args.git_push:
                run_cmd(["git", "push"], ROOT)

    LOGGER.info("refresh_affiliate_funnel=done")


if __name__ == "__main__":
    main()
