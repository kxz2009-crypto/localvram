#!/usr/bin/env python3
import argparse
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
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
STANDARD_I18N_LOCALES = ("es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id", "zh")
TRANSLATOR_TARGET_BY_LOCALE = {
    "es": "es",
    "pt": "pt",
    "fr": "fr",
    "de": "de",
    "ru": "ru",
    "ja": "ja",
    "ko": "ko",
    "ar": "ar",
    "hi": "hi",
    "id": "id",
    "zh": "zh-CN",
}
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")
FRONTMATTER_TITLE_RE = re.compile(r'(?m)^title:\s*(?P<value>".+?"|\'.+?\'|.+?)\s*$')
FRONTMATTER_FIELD_RE = re.compile(r"(?m)^(?P<key>[A-Za-z0-9_]+):\s*(?P<value>.+?)\s*$")
INTERNAL_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])/(?:en|es|pt|fr|de|ru|ja|ko|ar|hi|id|zh|go|recommends)"
    r"(?:/[A-Za-z0-9._~!$&'()*+,;=:@%-]+)+/?"
)
LOGGER = configure_logging("auto-fill-i18n-blog-body")
DEFAULT_TRANSLATE_TIMEOUT_S = float(os.environ.get("I18N_TRANSLATE_TIMEOUT_S", "12"))
DEFAULT_GEMINI_MODEL = str(os.environ.get("I18N_GEMINI_MODEL", "gemini-2.5-flash")).strip() or "gemini-2.5-flash"
DEFAULT_GEMINI_TIMEOUT_S = float(os.environ.get("I18N_GEMINI_TIMEOUT_S", "45"))
GEMINI_API_BASE = str(os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")).strip()
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
INTENT_LABEL_ZH = {
    "troubleshooting": "故障排查",
    "hardware": "硬件选型",
    "benchmark": "性能基准",
    "guide": "实操指南",
    "cost": "成本决策",
}


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
        INTERNAL_PATH_RE,  # bare internal route paths
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


def _gemini_extract_text(payload: dict) -> str:
    candidates = payload.get("candidates", [])
    if not isinstance(candidates, list):
        return ""
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content", {})
        if not isinstance(content, dict):
            continue
        parts = content.get("parts", [])
        if not isinstance(parts, list):
            continue
        text_chunks = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = str(part.get("text", "")).strip()
            if text:
                text_chunks.append(text)
        if text_chunks:
            return "\n".join(text_chunks).strip()
    return ""


def call_gemini(prompt: str, *, api_key: str, model: str, timeout_s: float) -> str:
    if not api_key:
        raise RuntimeError("missing GEMINI_API_KEY")
    model_name = str(model or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    url = f"{GEMINI_API_BASE}/models/{model_name}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.9,
            "maxOutputTokens": 8192,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(1.0, float(timeout_s))) as response:  # noqa: S310
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:  # pragma: no cover - network/runtime guard
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            detail = ""
        raise RuntimeError(f"gemini http error {exc.code}: {detail}") from exc
    except Exception as exc:  # pragma: no cover - network/runtime guard
        raise RuntimeError(f"gemini request failed: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("gemini returned non-json response") from exc

    text = _gemini_extract_text(payload)
    if not text:
        raise RuntimeError("gemini response missing text candidate")
    return text


def translate_text_with_gemini(text: str, *, api_key: str, model: str, timeout_s: float, protected_terms: list[str]) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    terms = ", ".join(protected_terms[:60]) if protected_terms else "None"
    prompt = (
        "Translate the following English title to Simplified Chinese (zh-CN).\n"
        "Rules:\n"
        "1) Keep model names and protected terms unchanged.\n"
        "2) Keep punctuation concise and natural for Chinese readers.\n"
        "3) Return only the translated title line.\n"
        f"Protected terms: {terms}\n"
        f"Title: {raw}"
    )
    translated = call_gemini(prompt, api_key=api_key, model=model, timeout_s=timeout_s).strip()
    return translated or raw


def translate_markdown_with_gemini(
    markdown: str,
    *,
    api_key: str,
    model: str,
    timeout_s: float,
    protected_terms: list[str],
) -> str:
    source = str(markdown or "").strip()
    if not source:
        return "\n"
    terms = ", ".join(protected_terms[:120]) if protected_terms else "None"
    prompt = (
        "Translate the Markdown document below from English to Simplified Chinese (zh-CN).\n"
        "Hard requirements:\n"
        "1) Preserve Markdown structure exactly: headings, lists, tables, blockquotes, and spacing.\n"
        "2) Do NOT translate code fences, inline code, URLs, or route paths like /en/blog/slug/.\n"
        "3) Keep model names, product names, and protected terms unchanged.\n"
        "4) Translate all prose fully; no summary and no omission.\n"
        "5) Return only translated Markdown, without extra comments.\n"
        f"Protected terms: {terms}\n\n"
        "Markdown input:\n"
        f"{source}"
    )
    translated = call_gemini(prompt, api_key=api_key, model=model, timeout_s=timeout_s).strip()
    if not translated:
        raise RuntimeError("gemini returned empty markdown translation")
    return translated + "\n"


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


def _translate_batch(contents: list[str], translator: GoogleTranslator, batch_size: int = 20) -> list[str]:
    if not contents:
        return []
    translated: list[str] = []
    for start in range(0, len(contents), batch_size):
        chunk = contents[start : start + batch_size]
        chunk_translated: list[str] | None = None
        try:
            candidate = translator.translate_batch(chunk)
            if isinstance(candidate, list) and len(candidate) == len(chunk):
                chunk_translated = [str(item or "") for item in candidate]
        except Exception:
            chunk_translated = None

        if chunk_translated is None:
            # Fallback to per-line translation when batch fails.
            chunk_translated = []
            for item in chunk:
                try:
                    chunk_translated.append(str(translator.translate(item) or ""))
                except Exception:
                    chunk_translated.append("")

        translated.extend(chunk_translated)
        time.sleep(0.15)
    return translated


def translate_markdown(markdown: str, translator: GoogleTranslator, protected_terms: list[str]) -> tuple[str, int]:
    lines = markdown.splitlines()
    translated_lines: list[str] = []
    in_code_fence = False
    failures = 0
    pending_indices: list[int] = []
    pending_prefixes: list[str] = []
    pending_source_contents: list[str] = []
    pending_contents: list[str] = []
    pending_token_maps: list[dict[str, str]] = []

    def flush_pending() -> None:
        nonlocal failures
        if not pending_contents:
            return
        translated_batch = _translate_batch(pending_contents, translator)
        for idx, prefix, source, token_map, translated in zip(
            pending_indices,
            pending_prefixes,
            pending_source_contents,
            pending_token_maps,
            translated_batch,
        ):
            text = unmask_text(str(translated or "").strip(), token_map)
            if not text:
                failures += 1
                text = source
            translated_lines[idx] = f"{prefix}{text}" if prefix else text
        pending_indices.clear()
        pending_prefixes.clear()
        pending_source_contents.clear()
        pending_contents.clear()
        pending_token_maps.clear()

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_pending()
            in_code_fence = not in_code_fence
            translated_lines.append(line)
            continue

        if in_code_fence or not stripped:
            flush_pending()
            translated_lines.append(line)
            continue

        prefix, content = split_markdown_prefix(line)
        masked_content, token_map = mask_text(content, protected_terms)
        translated_lines.append(line)
        pending_indices.append(len(translated_lines) - 1)
        pending_prefixes.append(prefix)
        pending_source_contents.append(content)
        pending_contents.append(masked_content)
        pending_token_maps.append(token_map)

    flush_pending()

    return "\n".join(translated_lines).strip() + "\n", failures


def split_frontmatter(markdown: str) -> tuple[str, str]:
    normalized = markdown.lstrip("\ufeff")
    if not normalized.startswith("---"):
        return "", normalized
    match = re.match(r"^---\s*\r?\n[\s\S]*?\r?\n---\s*(\r?\n)?", normalized)
    if not match:
        return "", normalized
    return match.group(0), normalized[match.end() :]


def extract_frontmatter_title(frontmatter: str) -> str:
    if not frontmatter:
        return ""
    match = FRONTMATTER_TITLE_RE.search(frontmatter)
    if not match:
        return ""
    raw_value = str(match.group("value") or "").strip()
    return raw_value.strip('"').strip("'").strip()


def parse_frontmatter_fields(frontmatter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    if not frontmatter:
        return fields
    for match in FRONTMATTER_FIELD_RE.finditer(frontmatter):
        key = str(match.group("key") or "").strip()
        value = str(match.group("value") or "").strip()
        if not key:
            continue
        fields[key] = value
    return fields


def parse_frontmatter_tags(raw: str) -> list[str]:
    value = str(raw or "").strip()
    if not value:
        return []
    if not (value.startswith("[") and value.endswith("]")):
        return [value.strip('"').strip("'").strip()] if value else []
    body = value[1:-1].strip()
    if not body:
        return []
    tags: list[str] = []
    for item in body.split(","):
        tag = item.strip().strip('"').strip("'").strip()
        if tag:
            tags.append(tag)
    return tags


def normalize_frontmatter_value(raw: str) -> str:
    return str(raw or "").strip().strip('"').strip("'").strip()


def normalize_date_value(raw: str) -> str:
    value = normalize_frontmatter_value(raw)
    if "T" in value:
        value = value.split("T", 1)[0]
    if " " in value:
        value = value.split(" ", 1)[0]
    return value


def extract_summary_snippet(source_body: str, fallback: str) -> str:
    if source_body.strip():
        blocks = [x.strip() for x in re.split(r"\r?\n\s*\r?\n", source_body.strip()) if x.strip()]
        for block in blocks:
            if block.startswith("#"):
                continue
            plain = " ".join(line.strip() for line in block.splitlines() if line.strip())
            if plain:
                return plain[:260]
    return str(fallback or "").strip()[:260]


def build_zh_stub_markdown(slug: str, frontmatter: str, source_body: str) -> str:
    fields = parse_frontmatter_fields(frontmatter)
    title = normalize_frontmatter_value(fields.get("title", "")) or slug.replace("-", " ")
    description = normalize_frontmatter_value(fields.get("description", ""))
    pub_date = normalize_date_value(fields.get("pubDate", ""))
    intent = normalize_frontmatter_value(fields.get("intent", "guide")).lower()
    intent_label = INTENT_LABEL_ZH.get(intent, "实操指南")
    tags = parse_frontmatter_tags(fields.get("tags", ""))
    tag_text = "、".join(tags) if tags else "待补充"
    summary = extract_summary_snippet(source_body, description or title)

    lines = [
        f"# {title}（中文整理中）",
        "",
        "## 中文速览（待人工校对）",
        "",
        "该文章已在英文站发布。为保证中文站与英文站每日同步，先提供关键上下文，完整中文版本会在术语统一与技术校对后补齐。",
        "",
        f"- 发布日期：{pub_date or '待补充'}",
        f"- 文章类型：{intent_label}",
        f"- 标签：{tag_text}",
        f"- 英文原文：/en/blog/{slug}/",
        "",
        "## 英文摘要（原文引用）",
        "",
        f"> {summary}",
        "",
        "## 当前建议",
        "",
        "1. 如果要立即落地，请优先参考英文原文中的命令、参数与版本说明。",
        "2. 中文完整版上线后，会补充本地化术语、流程图与常见误区说明。",
        "",
    ]
    return "\n".join(lines)


def prepend_heading_if_missing(markdown: str, heading: str) -> str:
    content = str(markdown or "").lstrip()
    title = str(heading or "").strip()
    if not title:
        return markdown
    if re.match(r"^\s*#{1,6}\s+", content):
        return markdown
    return f"# {title}\n\n{content}" if content else f"# {title}\n"


def count_cjk_chars(text: str) -> int:
    return len(CJK_RE.findall(str(text or "")))


def probe_translator(translator: GoogleTranslator, locale: str) -> None:
    try:
        probe = str(translator.translate("translation probe") or "").strip()
    except Exception as exc:  # pragma: no cover - network/runtime guard
        raise SystemExit(
            "auto-fill failed: translator probe failed for locale="
            f"{locale} ({exc}). Check network access to translate.google.com "
            "or run this step in an environment with outbound access."
        ) from exc
    if not probe:
        raise SystemExit(
            f"auto-fill failed: translator probe returned empty output for locale={locale}. "
            "Check translator availability before retry."
        )


def build_header(slug: str, locale: str, status: str = "machine-translated (human review recommended)") -> str:
    return (
        "<!--\n"
        f"auto-translated from src/content/blog/{slug}.md\n"
        f"target-locale: {locale}\n"
        f"status: {status}\n"
        "-->\n\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fill localized blog body markdown files from English sources.")
    parser.add_argument("--locales", help="Comma-separated locale list. Default: all supported locales.")
    parser.add_argument("--slugs", help="Comma-separated slug list. Default: all blog slugs.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of slugs to process.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing localized markdown files.")
    parser.add_argument(
        "--overwrite-stub-only",
        action="store_true",
        help="When overwriting, only replace files containing the zh-stub status marker.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show planned writes without writing files.")
    parser.add_argument(
        "--fallback-mode",
        choices=("none", "stub"),
        default="none",
        help=(
            "Fallback behavior when machine translation is unavailable. "
            "'stub' only applies to zh locale and writes Chinese placeholder drafts."
        ),
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=DEFAULT_TRANSLATE_TIMEOUT_S,
        help="Network timeout in seconds for translator requests (default from I18N_TRANSLATE_TIMEOUT_S or 12).",
    )
    parser.add_argument(
        "--zh-provider",
        choices=("auto", "google", "gemini"),
        default=str(os.environ.get("I18N_ZH_PROVIDER", "auto")).strip().lower() or "auto",
        help="zh translator provider selection. auto=prefer gemini when GEMINI_API_KEY exists, else google.",
    )
    parser.add_argument(
        "--gemini-model",
        default=DEFAULT_GEMINI_MODEL,
        help=f"Gemini model for zh translation (default: {DEFAULT_GEMINI_MODEL}).",
    )
    parser.add_argument(
        "--gemini-timeout-s",
        type=float,
        default=DEFAULT_GEMINI_TIMEOUT_S,
        help="HTTP timeout in seconds for each Gemini request.",
    )
    parser.add_argument(
        "--min-zh-cjk",
        type=int,
        default=24,
        help="Minimum number of CJK characters required for zh output validation.",
    )
    args = parser.parse_args()
    if args.timeout_s > 0:
        socket.setdefaulttimeout(args.timeout_s)

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
    gemini_api_key = str(os.environ.get("GEMINI_API_KEY", "")).strip()

    for locale in locales:
        locale_provider = "google"
        if locale == "zh":
            if args.zh_provider == "gemini":
                if not gemini_api_key:
                    raise SystemExit(
                        "auto-fill failed: --zh-provider gemini requires GEMINI_API_KEY environment variable."
                    )
                locale_provider = "gemini"
            elif args.zh_provider == "auto" and gemini_api_key:
                locale_provider = "gemini"

        translator = None
        if locale_provider == "google":
            translator = GoogleTranslator(source="en", target=TRANSLATOR_TARGET_BY_LOCALE.get(locale, locale))
        use_stub_fallback = False
        if translator is not None:
            try:
                probe_translator(translator, locale)
            except SystemExit:
                if args.fallback_mode == "stub" and locale == "zh":
                    use_stub_fallback = True
                    LOGGER.warning(
                        "translator unavailable for locale=%s; fallback=stub enabled, writing zh placeholder drafts",
                        locale,
                    )
                else:
                    raise
        elif locale_provider == "gemini":
            LOGGER.info("locale=%s translation provider=gemini model=%s", locale, args.gemini_model)

        locale_out_dir = OUT_DIR / locale
        if not args.dry_run:
            locale_out_dir.mkdir(parents=True, exist_ok=True)

        for blog_file in blog_files:
            slug = blog_file.stem
            out_file = locale_out_dir / f"{slug}.md"
            existing_text = out_file.read_text(encoding="utf-8") if out_file.exists() else ""
            existing_is_stub = "status: zh-stub (pending full translation)" in existing_text
            if out_file.exists() and not args.overwrite:
                LOGGER.info("skip existing: locale=%s slug=%s file=%s", locale, slug, out_file)
                continue
            if out_file.exists() and args.overwrite_stub_only and not existing_is_stub:
                LOGGER.info("skip non-stub existing file: locale=%s slug=%s file=%s", locale, slug, out_file)
                continue

            source_markdown = blog_file.read_text(encoding="utf-8")
            frontmatter, source_body = split_frontmatter(source_markdown)
            header_status = f"machine-translated via {locale_provider} (human review recommended)"
            if use_stub_fallback:
                translated_markdown = build_zh_stub_markdown(slug, frontmatter, source_body)
                failed_lines = 0
                header_status = "zh-stub (pending full translation)"
            elif locale_provider == "gemini":
                try:
                    translated_markdown = translate_markdown_with_gemini(
                        source_body,
                        api_key=gemini_api_key,
                        model=args.gemini_model,
                        timeout_s=args.gemini_timeout_s,
                        protected_terms=protected_terms,
                    )
                except Exception as exc:
                    if args.fallback_mode == "stub" and locale == "zh":
                        translated_markdown = build_zh_stub_markdown(slug, frontmatter, source_body)
                        failed_lines = 0
                        header_status = "zh-stub (pending full translation)"
                        LOGGER.warning(
                            "gemini translation failed locale=%s slug=%s; fallback=stub enabled (%s)",
                            locale,
                            slug,
                            exc,
                        )
                    else:
                        raise SystemExit(
                            f"auto-fill failed: gemini translation failed for locale={locale} slug={slug}: {exc}"
                        ) from exc
                else:
                    failed_lines = 0
                    source_title = extract_frontmatter_title(frontmatter)
                    if source_title:
                        try:
                            translated_title = translate_text_with_gemini(
                                source_title,
                                api_key=gemini_api_key,
                                model=args.gemini_model,
                                timeout_s=args.gemini_timeout_s,
                                protected_terms=protected_terms,
                            )
                        except Exception:
                            translated_title = source_title
                        translated_markdown = prepend_heading_if_missing(
                            translated_markdown,
                            translated_title or source_title,
                        )
            else:
                if translator is None:
                    raise SystemExit(f"auto-fill failed: translator not initialized for locale={locale}")
                translated_markdown, failed_lines = translate_markdown(source_body, translator, protected_terms)
                source_title = extract_frontmatter_title(frontmatter)
                if source_title:
                    translated_title = translate_text(source_title, translator, protected_terms)
                    translated_markdown = prepend_heading_if_missing(translated_markdown, translated_title or source_title)
            total_failed_lines += failed_lines

            if locale == "zh" and header_status != "zh-stub (pending full translation)":
                cjk_chars = count_cjk_chars(translated_markdown)
                if cjk_chars < int(args.min_zh_cjk):
                    raise SystemExit(
                        "auto-fill failed: zh translation quality check failed "
                        f"(slug={slug}, cjk_chars={cjk_chars}, required>={args.min_zh_cjk})"
                    )

            payload = build_header(slug, locale, header_status) + translated_markdown
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
