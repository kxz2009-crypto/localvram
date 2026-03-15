#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request

BAIDU_UA = "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)"


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def normalize_origin(origin: str) -> str:
    return str(origin).strip().rstrip("/")


def normalize_path(path: str) -> str:
    value = str(path or "/").strip() or "/"
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def request(
    url: str,
    *,
    allow_redirect: bool,
    timeout_s: int,
    user_agent: str,
) -> tuple[int, str, dict[str, str], str]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    opener = urllib.request.build_opener() if allow_redirect else urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(req, timeout=timeout_s) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return int(resp.status), resp.geturl(), headers, body
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            body = ""
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return int(exc.code), exc.geturl(), headers, body


def add_result(results: list[dict[str, str]], *, check: str, status: str, detail: str, ok: bool) -> None:
    results.append(
        {
            "check": check,
            "status": status,
            "detail": detail,
            "ok": "OK" if ok else "FAIL",
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Baidu crawler readiness for localvram CN migration.")
    parser.add_argument("--cn-domain", default="https://localvram.cn")
    parser.add_argument("--com-domain", default="https://localvram.com")
    parser.add_argument("--sitemap-url", default="https://localvram.cn/sitemap-cn.xml")
    parser.add_argument("--verify-path", default="", help="Optional Baidu verification file path, e.g. /baidu_verify_xxx.html")
    parser.add_argument("--timeout-s", type=int, default=20)
    args = parser.parse_args()

    cn_domain = normalize_origin(args.cn_domain)
    com_domain = normalize_origin(args.com_domain)
    sitemap_url = str(args.sitemap_url).strip()
    timeout_s = max(5, int(args.timeout_s))

    results: list[dict[str, str]] = []

    # CN core availability
    for path in ["/", "/tools/vram-calculator/", "/guides/best-coding-models/"]:
        url = f"{cn_domain}{path}"
        status, final_url, _, _ = request(url, allow_redirect=True, timeout_s=timeout_s, user_agent=BAIDU_UA)
        add_result(
            results,
            check=f"cn-page:{path}",
            status=str(status),
            detail=final_url,
            ok=status == 200,
        )

    # robots and sitemap
    robots_url = f"{cn_domain}/robots.txt"
    robots_status, robots_final, _, robots_body = request(
        robots_url,
        allow_redirect=True,
        timeout_s=timeout_s,
        user_agent=BAIDU_UA,
    )
    add_result(
        results,
        check="cn-robots:available",
        status=str(robots_status),
        detail=robots_final,
        ok=robots_status == 200,
    )
    expected_sitemap_line = f"Sitemap: {sitemap_url}"
    add_result(
        results,
        check="cn-robots:sitemap-line",
        status=str(robots_status),
        detail=expected_sitemap_line,
        ok=(robots_status == 200 and expected_sitemap_line in robots_body),
    )

    sitemap_status, sitemap_final, _, sitemap_body = request(
        sitemap_url,
        allow_redirect=True,
        timeout_s=timeout_s,
        user_agent=BAIDU_UA,
    )
    sitemap_xml_ok = ("<urlset" in sitemap_body) or ("<sitemapindex" in sitemap_body)
    add_result(
        results,
        check="cn-sitemap:accessible",
        status=str(sitemap_status),
        detail=sitemap_final,
        ok=(sitemap_status == 200 and sitemap_xml_ok),
    )

    alias_sitemap_url = f"{cn_domain}/sitemap.xml"
    alias_status, alias_final, _, alias_body = request(
        alias_sitemap_url,
        allow_redirect=True,
        timeout_s=timeout_s,
        user_agent=BAIDU_UA,
    )
    alias_xml_ok = ("<urlset" in alias_body) or ("<sitemapindex" in alias_body)
    add_result(
        results,
        check="cn-sitemap-alias:accessible",
        status=str(alias_status),
        detail=alias_final,
        ok=(alias_status == 200 and alias_xml_ok),
    )

    # Optional Baidu verify file check
    if args.verify_path.strip():
        verify_path = normalize_path(args.verify_path)
        verify_url = f"{cn_domain}{verify_path}"
        verify_status, verify_final, _, _ = request(
            verify_url,
            allow_redirect=True,
            timeout_s=timeout_s,
            user_agent=BAIDU_UA,
        )
        add_result(
            results,
            check=f"cn-verify-file:{verify_path}",
            status=str(verify_status),
            detail=verify_final,
            ok=verify_status == 200,
        )

    # COM -> CN redirect mapping checks
    legacy_redirects = [
        ("/zh", "/"),
        ("/zh/", "/"),
        ("/zh/tools/vram-calculator/?ref=qa", "/tools/vram-calculator/?ref=qa"),
    ]
    for source_path, target_path in legacy_redirects:
        source_url = f"{com_domain}{source_path}"
        status, _, headers, _ = request(
            source_url,
            allow_redirect=False,
            timeout_s=timeout_s,
            user_agent=BAIDU_UA,
        )
        expected_target = f"{cn_domain}{target_path}"
        actual_target = str(headers.get("location", "")).strip()
        ok = status == 301 and actual_target == expected_target
        add_result(
            results,
            check=f"com-zh-redirect:{source_path}",
            status=str(status),
            detail=f"{actual_target or '(missing location)'} expect={expected_target}",
            ok=ok,
        )

    print("baidu readiness verification")
    print(f"cn={cn_domain} com={com_domain}")
    print()
    print(f"{'check':45} {'status':8} {'ok':6} detail")
    print("-" * 110)
    for row in results:
        print(f"{row['check'][:45]:45} {row['status'][:8]:8} {row['ok'][:6]:6} {row['detail']}")

    failed = [row for row in results if row["ok"] != "OK"]
    if failed:
        print()
        print("FAILED checks:")
        for row in failed:
            print(f"- {row['check']}: status={row['status']} detail={row['detail']}")
        return 1

    print()
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
