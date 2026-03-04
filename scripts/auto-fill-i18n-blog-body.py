#!/usr/bin/env python3
import argparse
import json
import re
import time
from pathlib import Path

from logging_utils import configure_logging

try:
    from deep_translator import GoogleTranslator
except Exception as exc:  # pragma: no cover - runtime import guard
    raise SystemExit(
        f"auto-fill failed: deep-translator is required ({exc}). Install via: python -m pip install deep-translator"
    )


ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "src" / "content" / "blog"
OUT_DIR = ROOT / "src" / "content" / "blog-i18n"
GLOSSARY_PATH = ROOT / "src" / "data" / "i18n-glossary.json"
STANDARD_I18N_LOCALES = ("es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id")
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")
LOGGER = configure_logging("auto-fill-i18n-blog-body")


def load_protected_terms() -> list[str]:
    if not GLOSSARY_PATH.exists():
        return []
    payload = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    terms = payload.get("protected_terms", [])
    if not isinstance(terms, list):
        return []
    return [str(t).strip() for t in terms if str(t).strip()]


def mask_text(text: str, protected_terms: list[str]) -> tuple[str, dict[str, str]]:
    masked = text
    token_map: dict[str, str] = {}
    token_idx = 0

    patterns = [
        re.compile(r"`[^`]+`"),  # inline code
        re.compile(r"\[[^\]]+\]\([^)]+\)"),  # markdown links
        re.compile(r"https?://\S+"),  # urls
        PLACEHOLDER_RE,
    ]

    for pattern in patterns:
        for match in sorted(set(pattern.findall(masked)), key=len, reverse=True):
            token = f"@@{token_idx}@@"
            token_idx += 1
            masked = masked.replace(match, token)
            token_map[token] = match

    for term in sorted(protected_terms, key=len, reverse=True):
        if term not in masked:
            continue
        token = f"##{token_idx}##"
        token_idx += 1
        masked = masked.replace(term, token)
        token_map[token] = term

    return masked, token_map


def unmask_text(text: str, token_map: dict[str, str]) -> str:
    restored = text
    for token, original in token_map.items():
        restored = restored.replace(token, original)
    return restored


def translate_text(text: str, translator: GoogleTranslator, protected_terms: list[str]) -> str:
    stripped = text.strip()
    if not stripped:
        return text
    masked, token_map = mask_text(text, protected_terms)
    translated = str(translator.translate(masked) or "").strip()
    if not translated:
        return text
    return unmask_text(translated, token_map)


def split_markdown_prefix(line: str) -> tuple[str, str]:
    patterns = [
        re.compile(r"^(\s{0,3}#{1,6}\s+)(.*)$"),  # headings
        re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)(.*)$"),  # lists
        re.compile(r"^(\s*>\s+)(.*)$"),  # blockquotes
    ]
    for pattern in patterns:
        match = pattern.match(line)
        if match:
            return match.group(1), match.group(2)
    return "", line


def translate_markdown(markdown: str, translator: GoogleTranslator, protected_terms: list[str]) -> tuple[str, int]:
    lines = markdown.splitlines()
    translated_lines: list[str] = []
    in_code_fence = False
    failures = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            translated_lines.append(line)
            continue

        if in_code_fence or not stripped:
            translated_lines.append(line)
            continue

        prefix, content = split_markdown_prefix(line)
        try:
            translated_content = translate_text(content, translator, protected_terms)
            translated_lines.append(f"{prefix}{translated_content}" if prefix else translated_content)
        except Exception:
            failures += 1
            translated_lines.append(line)
        time.sleep(0.03)

    return "\n".join(translated_lines).strip() + "\n", failures


def build_header(slug: str, locale: str) -> str:
    return (
        "<!--\n"
        f"auto-translated from src/content/blog/{slug}.md\n"
        f"target-locale: {locale}\n"
        "status: machine-translated (human review recommended)\n"
        "-->\n\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fill localized blog body markdown files from English sources.")
    parser.add_argument("--locales", help="Comma-separated locale list. Default: all 10 standard locales.")
    parser.add_argument("--slugs", help="Comma-separated slug list. Default: all blog slugs.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of slugs to process.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing localized markdown files.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned writes without writing files.")
    args = parser.parse_args()

    locales = STANDARD_I18N_LOCALES
    if args.locales:
        requested = [x.strip().lower() for x in args.locales.split(",") if x.strip()]
        unknown = [x for x in requested if x not in STANDARD_I18N_LOCALES]
        if unknown:
            raise SystemExit(f"auto-fill failed: unknown locales: {','.join(unknown)}")
        locales = tuple(requested)

    blog_files = sorted(BLOG_DIR.glob("*.md"))
    if args.slugs:
        wanted = {x.strip() for x in args.slugs.split(",") if x.strip()}
        blog_files = [p for p in blog_files if p.stem in wanted]
    if args.limit > 0:
        blog_files = blog_files[: args.limit]

    if not blog_files:
        raise SystemExit("auto-fill failed: no blog markdown files selected")

    protected_terms = load_protected_terms()
    total_written = 0
    total_failed_lines = 0

    for locale in locales:
        translator = GoogleTranslator(source="en", target=locale)
        locale_out_dir = OUT_DIR / locale
        if not args.dry_run:
            locale_out_dir.mkdir(parents=True, exist_ok=True)

        for blog_file in blog_files:
            slug = blog_file.stem
            out_file = locale_out_dir / f"{slug}.md"
            if out_file.exists() and not args.overwrite:
                LOGGER.info("skip existing: locale=%s slug=%s file=%s", locale, slug, out_file)
                continue

            source_markdown = blog_file.read_text(encoding="utf-8")
            translated_markdown, failed_lines = translate_markdown(source_markdown, translator, protected_terms)
            total_failed_lines += failed_lines

            payload = build_header(slug, locale) + translated_markdown
            if args.dry_run:
                LOGGER.info("dry-run write: locale=%s slug=%s file=%s", locale, slug, out_file)
            else:
                out_file.write_text(payload, encoding="utf-8")
                LOGGER.info(
                    "wrote localized body: locale=%s slug=%s failed_lines=%s file=%s",
                    locale,
                    slug,
                    failed_lines,
                    out_file,
                )
            total_written += 1

    LOGGER.info(
        "auto-fill complete: locales=%s files=%s failed_lines=%s",
        len(locales),
        total_written,
        total_failed_lines,
    )


if __name__ == "__main__":
    main()
