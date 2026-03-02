#!/usr/bin/env python3
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
DIST_ROOT = ROOT / "dist"

NON_EN_LOCALES = ("es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id")
ALL_LOCALES = ("en",) + NON_EN_LOCALES + ("zh",)

ALLOW_ATTR_MARKERS = (
    "data-i18n-switcher",
    "data-language-switcher",
    "data-allow-cross-locale",
)
ALLOW_CLASS_MARKERS = (
    "lang-switcher",
    "language-switcher",
    "locale-switcher",
)

ANCHOR_TAG_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE | re.DOTALL)
HREF_LITERAL_RE = re.compile(r"""href\s*=\s*(["'])(?P<href>[^"']+)\1""", re.IGNORECASE)
HREF_EXPR_RE = re.compile(r"""href\s*=\s*\{(?P<expr>[^}]*)\}""", re.IGNORECASE | re.DOTALL)
CLASS_RE = re.compile(r"""class\s*=\s*(["'])(?P<className>[^"']+)\1""", re.IGNORECASE)


def is_locale_path(href: str, locale: str) -> bool:
    return (
        href == f"/{locale}"
        or href.startswith(f"/{locale}/")
        or href.startswith(f"/{locale}?")
        or href.startswith(f"/{locale}#")
    )


def is_allowed_anchor(tag: str) -> bool:
    tag_lower = tag.lower()
    if any(marker in tag_lower for marker in ALLOW_ATTR_MARKERS):
        return True
    class_match = CLASS_RE.search(tag)
    if not class_match:
        return False
    class_value = class_match.group("className").lower()
    return any(marker in class_value for marker in ALLOW_CLASS_MARKERS)


def line_number(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def detect_page_locale_from_dist(dist_file: Path) -> str | None:
    rel = dist_file.relative_to(DIST_ROOT)
    if not rel.parts:
        return None
    first = rel.parts[0].lower()
    if first in ALL_LOCALES:
        return first
    return None


def check_href_tokens(
    *,
    tag: str,
    source_label: str,
    path: Path,
    content: str,
    offset: int,
    page_locale: str | None,
    literal_href: str | None,
    dynamic_expr: str | None,
    violations: list[str],
) -> None:
    if is_allowed_anchor(tag):
        return

    line = line_number(content, offset)
    checks: list[tuple[str, str]] = []
    if literal_href is not None:
        href = literal_href.strip()
        checks.append(("literal", href))
    elif dynamic_expr is not None:
        checks.append(("dynamic", dynamic_expr.lower()))

    for mode, payload in checks:
        if mode == "literal":
            href = payload
            if not href.startswith("/"):
                continue
            if is_locale_path(href, "zh"):
                violations.append(
                    f"{source_label}:{path}:{line}: forbidden /zh anchor outside switcher (href={href})"
                )
                continue
            if page_locale == "en":
                for locale in NON_EN_LOCALES:
                    if is_locale_path(href, locale):
                        violations.append(
                            f"{source_label}:{path}:{line}: /en page links to /{locale} outside switcher (href={href})"
                        )
                        break
        else:
            expr = payload
            if '"/zh' in expr or "'/zh" in expr:
                violations.append(
                    f"{source_label}:{path}:{line}: forbidden /zh anchor expression outside switcher"
                )
                continue
            if page_locale == "en":
                for locale in NON_EN_LOCALES:
                    token_a = f'"/{locale}'
                    token_b = f"'/{locale}"
                    if token_a in expr or token_b in expr:
                        violations.append(
                            f"{source_label}:{path}:{line}: /en page links to /{locale} expression outside switcher"
                        )
                        break


def scan_content(
    *,
    source_label: str,
    path: Path,
    content: str,
    page_locale: str | None,
    violations: list[str],
) -> None:
    for match in ANCHOR_TAG_RE.finditer(content):
        tag = match.group(0)
        href_match = HREF_LITERAL_RE.search(tag)
        expr_match = HREF_EXPR_RE.search(tag)
        literal_href = href_match.group("href") if href_match else None
        dynamic_expr = expr_match.group("expr") if expr_match else None
        if literal_href is None and dynamic_expr is None:
            continue
        check_href_tokens(
            tag=tag,
            source_label=source_label,
            path=path,
            content=content,
            offset=match.start(),
            page_locale=page_locale,
            literal_href=literal_href,
            dynamic_expr=dynamic_expr,
            violations=violations,
        )


def main() -> None:
    violations: list[str] = []

    # Source checks: all astro pages for /zh anchor leaks,
    # and English pages for cross-locale links outside a language switcher.
    for src_file in sorted((SRC_ROOT / "pages").rglob("*.astro")):
        content = src_file.read_text(encoding="utf-8")
        rel = src_file.relative_to(SRC_ROOT)
        page_locale = "en" if rel.parts[:2] == ("pages", "en") else None
        scan_content(
            source_label="src",
            path=rel,
            content=content,
            page_locale=page_locale,
            violations=violations,
        )

    # Dist checks (if build artifacts exist) to catch generated HTML regressions.
    if DIST_ROOT.exists():
        for dist_file in sorted(DIST_ROOT.rglob("*.html")):
            content = dist_file.read_text(encoding="utf-8", errors="ignore")
            rel = dist_file.relative_to(ROOT)
            page_locale = detect_page_locale_from_dist(dist_file)
            scan_content(
                source_label="dist",
                path=rel,
                content=content,
                page_locale=page_locale,
                violations=violations,
            )

    if violations:
        print("locale link check failed: forbidden locale anchor patterns found")
        for item in violations[:80]:
            print(f"- {item}")
        if len(violations) > 80:
            print(f"- ... and {len(violations) - 80} more")
        sys.exit(1)

    print("locale link checks ok: no forbidden /zh anchors and no /en cross-locale leakage")


if __name__ == "__main__":
    main()
