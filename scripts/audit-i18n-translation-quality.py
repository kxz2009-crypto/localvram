#!/usr/bin/env python3
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
COPY_PATH = ROOT / "src" / "data" / "i18n-copy.json"
GLOSSARY_PATH = ROOT / "src" / "data" / "i18n-glossary.json"
OUT_PATH = ROOT / "dist" / "seo-audit" / "i18n-translation-qa.json"

PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")
PLACEHOLDER_ONLY_RE = re.compile(r"^\{[a-zA-Z0-9_]+\}$")
TOKEN_ARTIFACT_RE = re.compile(r"(LVPH|LVPT|@@\d+@@|##\d+##|TOKEN)", re.IGNORECASE)
ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
NON_ASCII_LETTER_RE = re.compile(r"[^\x00-\x7F]")

LOCALE_SCRIPT_HINTS = {
    "ru": re.compile(r"[\u0400-\u04FF]"),
    "ja": re.compile(r"[\u3040-\u30FF\u31F0-\u31FF\u4E00-\u9FFF]"),
    "ko": re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]"),
    "ar": re.compile(r"[\u0600-\u06FF]"),
    "hi": re.compile(r"[\u0900-\u097F]"),
}

PAGE_PRIORITY = {
    "locale-home": 100,
    "models-index": 95,
    "models-detail": 90,
    "models-group": 88,
    "guides-index": 86,
    "guides-detail": 84,
    "tools-index": 82,
    "tools-detail": 80,
    "status-index": 78,
    "status-detail": 76,
    "errors-index": 70,
    "errors-detail": 68,
}

SEVERITY_WEIGHT = {"critical": 60, "high": 35, "medium": 15}
REVIEW_PAGE_IDS = [
    "locale-home",
    "models-index",
    "models-detail",
    "guides-index",
    "guides-detail",
    "tools-detail",
    "status-detail",
]
REVIEW_FIELD_CANDIDATES = ["meta_title", "meta_description", "hero_title", "hero_intro"]
LOGGER = configure_logging("audit-i18n-translation-quality")


def extract_placeholders(text: str) -> list[str]:
    return sorted(set(PLACEHOLDER_RE.findall(text)))


def likely_strong_fallback(en_text: str, localized_text: str) -> bool:
    en_clean = en_text.strip()
    loc_clean = localized_text.strip()
    if not en_clean or not loc_clean:
        return False
    if en_clean != loc_clean:
        return False
    if PLACEHOLDER_ONLY_RE.fullmatch(en_clean):
        return False
    literal_source = PLACEHOLDER_RE.sub(" ", en_clean)
    words = re.findall(r"[A-Za-z]{2,}", literal_source)
    if len(words) <= 2:
        # Template-like titles such as "{itemTitle} ({localeUpper}) | LocalVRAM"
        # are expected to keep a large shared literal segment.
        return False
    return len(en_clean) >= 20 and len(words) >= 4


def has_locale_script(locale: str, text: str) -> bool:
    pattern = LOCALE_SCRIPT_HINTS.get(locale)
    if not pattern:
        return True
    return bool(pattern.search(text))


def ascii_ratio(text: str) -> float:
    alpha_total = 0
    ascii_alpha = 0
    for ch in text:
        if ch.isalpha():
            alpha_total += 1
            if ord(ch) < 128:
                ascii_alpha += 1
    return (ascii_alpha / alpha_total) if alpha_total else 0.0


def detect_issues(
    page_id: str,
    field_name: str,
    locale: str,
    en_text: str,
    localized_text: str,
    protected_terms: list[str],
) -> list[dict]:
    issues: list[dict] = []
    value = localized_text.strip()

    if not value:
        issues.append(
            {
                "severity": "high",
                "code": "empty_translation",
                "message": "Translation is empty.",
            }
        )
        return issues

    if TOKEN_ARTIFACT_RE.search(value):
        issues.append(
            {
                "severity": "critical",
                "code": "token_artifact",
                "message": "Found translation token artifact from auto-fill masking.",
            }
        )

    src_placeholders = extract_placeholders(en_text)
    dst_placeholders = extract_placeholders(value)
    if src_placeholders != dst_placeholders:
        issues.append(
            {
                "severity": "high",
                "code": "placeholder_mismatch",
                "message": f"Placeholder mismatch: src={src_placeholders} dst={dst_placeholders}",
            }
        )

    if likely_strong_fallback(en_text, value):
        issues.append(
            {
                "severity": "high",
                "code": "english_fallback",
                "message": "Locale text equals English source on a long phrase.",
            }
        )

    for term in protected_terms:
        if term in en_text and term not in value:
            issues.append(
                {
                    "severity": "high",
                    "code": "protected_term_missing",
                    "message": f"Protected term missing: '{term}'",
                }
            )
            break

    if locale in LOCALE_SCRIPT_HINTS:
        en_len = len(en_text.strip())
        literal_source = PLACEHOLDER_RE.sub(" ", en_text)
        literal_words = re.findall(r"[A-Za-z]{2,}", literal_source)
        ratio = ascii_ratio(value)
        if en_len >= 24 and len(literal_words) >= 4 and ratio >= 0.85 and not has_locale_script(locale, value):
            issues.append(
                {
                    "severity": "medium",
                    "code": "missing_locale_script",
                    "message": f"Text is mostly ASCII and lacks expected script for locale '{locale}'.",
                }
            )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit i18n translation quality and build a manual review queue.")
    parser.add_argument("--out", default=str(OUT_PATH), help="Output report path.")
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Max items printed to stdout from top review queue.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when any critical/high issue is found.",
    )
    args = parser.parse_args()

    copy_data = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    glossary_data = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    protected_terms = [str(x).strip() for x in glossary_data.get("protected_terms", []) if str(x).strip()]
    pages = copy_data.get("pages", {})

    issues: list[dict] = []
    locale_summary: dict[str, dict] = {}

    for page_id, page_entry in pages.items():
        if not isinstance(page_entry, dict):
            continue
        en_fields = page_entry.get("en", {})
        locale_fields = page_entry.get("locales", {})
        if not isinstance(en_fields, dict) or not isinstance(locale_fields, dict):
            continue
        for locale, translated_map in locale_fields.items():
            if not isinstance(translated_map, dict):
                continue
            summary = locale_summary.setdefault(
                locale,
                {"critical": 0, "high": 0, "medium": 0, "issues": 0, "fields_checked": 0},
            )
            for field_name, en_value in en_fields.items():
                en_text = str(en_value)
                localized_text = str(translated_map.get(field_name, ""))
                summary["fields_checked"] += 1
                field_issues = detect_issues(
                    page_id=page_id,
                    field_name=field_name,
                    locale=locale,
                    en_text=en_text,
                    localized_text=localized_text,
                    protected_terms=protected_terms,
                )
                for item in field_issues:
                    severity = item["severity"]
                    summary[severity] += 1
                    summary["issues"] += 1
                    priority = PAGE_PRIORITY.get(page_id, 50) + SEVERITY_WEIGHT.get(severity, 0)
                    issues.append(
                        {
                            "locale": locale,
                            "page_id": page_id,
                            "field": field_name,
                            "severity": severity,
                            "code": item["code"],
                            "message": item["message"],
                            "priority": priority,
                            "en": en_text,
                            "translation": localized_text,
                        }
                    )

    issues.sort(key=lambda x: (-x["priority"], x["locale"], x["page_id"], x["field"], x["code"]))

    manual_review_queue: list[dict] = []
    for locale in sorted(locale_summary.keys()):
        for page_id in REVIEW_PAGE_IDS:
            page_entry = pages.get(page_id, {})
            if not isinstance(page_entry, dict):
                continue
            en_fields = page_entry.get("en", {})
            localized_map = page_entry.get("locales", {}).get(locale, {})
            if not isinstance(en_fields, dict) or not isinstance(localized_map, dict):
                continue
            for field_name in REVIEW_FIELD_CANDIDATES:
                if field_name not in en_fields:
                    continue
                manual_review_queue.append(
                    {
                        "locale": locale,
                        "page_id": page_id,
                        "field": field_name,
                        "priority": PAGE_PRIORITY.get(page_id, 50),
                        "en": str(en_fields.get(field_name, "")),
                        "translation": str(localized_map.get(field_name, "")),
                    }
                )
    manual_review_queue.sort(key=lambda x: (-x["priority"], x["locale"], x["page_id"], x["field"]))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "locales": locale_summary,
            "total_issues": len(issues),
            "critical": sum(x.get("critical", 0) for x in locale_summary.values()),
            "high": sum(x.get("high", 0) for x in locale_summary.values()),
            "medium": sum(x.get("medium", 0) for x in locale_summary.values()),
        },
        "top_review_queue": issues[:200],
        "manual_review_queue": manual_review_queue[:300],
        "issues": issues,
    }

    out_file = Path(args.out)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    LOGGER.info(
        "i18n translation qa report: "
        f"issues={report['summary']['total_issues']} "
        f"critical={report['summary']['critical']} "
        f"high={report['summary']['high']} "
        f"medium={report['summary']['medium']} "
        f"manual_queue={len(report['manual_review_queue'])} "
        f"report={out_file}"
    )
    if issues:
        LOGGER.info("top review queue:")
        for item in issues[: max(args.limit, 0)]:
            LOGGER.info(
                f"- [{item['severity']}] {item['locale']} {item['page_id']}.{item['field']} "
                f"({item['code']})"
            )

    if args.strict:
        blocking = [x for x in issues if x["severity"] in {"critical", "high"}]
        if blocking:
            LOGGER.error("i18n translation qa failed: blocking issues=%s", len(blocking))
            sys.exit(1)


if __name__ == "__main__":
    main()
