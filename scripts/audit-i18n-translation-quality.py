#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
COPY_PATH = ROOT / "src" / "data" / "i18n-copy.json"
GLOSSARY_PATH = ROOT / "src" / "data" / "i18n-glossary.json"
OUT_PATH = ROOT / "dist" / "seo-audit" / "i18n-translation-qa.json"
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
GEMINI_MODEL_DEFAULT = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

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


def extract_json_payload(text: str) -> dict | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def call_gemini_batch(items: list[dict], api_key: str, model: str, timeout_s: int) -> list[dict]:
    compact_items = [
        {
            "index": idx,
            "locale": item.get("locale"),
            "page_id": item.get("page_id"),
            "field": item.get("field"),
            "en": item.get("en", ""),
            "translation": item.get("translation", ""),
        }
        for idx, item in enumerate(items)
    ]
    prompt = (
        "You are a strict i18n QA reviewer.\n"
        "For each item, evaluate whether translation quality is acceptable for production.\n"
        "Focus on semantic correctness, fluency, and preserving technical meaning.\n"
        "Do not require literal translation. Placeholders must remain unchanged if present.\n"
        "Return ONLY JSON object with key `results`.\n"
        "Each result item must include: index (int), severity (none|medium|high|critical), code, message, confidence (0..1).\n"
        "Use severity=none if acceptable.\n\n"
        f"Items:\n{json.dumps(compact_items, ensure_ascii=False)}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        GEMINI_API_ENDPOINT.format(model=model, api_key=api_key),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        data = json.loads(response.read().decode("utf-8"))

    raw_text = ""
    for candidate in data.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                raw_text = text.strip()
                break
        if raw_text:
            break

    parsed = extract_json_payload(raw_text)
    if not parsed or not isinstance(parsed.get("results"), list):
        raise RuntimeError("gemini response does not contain valid JSON results")
    return parsed["results"]


def run_ai_review_queue(
    queue: list[dict],
    api_key: str,
    model: str,
    max_items: int,
    batch_size: int,
    timeout_s: int,
    retries: int,
    retry_backoff_s: int,
) -> tuple[list[dict], dict]:
    metadata = {
        "enabled": True,
        "model": model,
        "max_items": max_items,
        "batch_size": batch_size,
        "items_selected": 0,
        "batches": 0,
        "successful_batches": 0,
        "reviewed_items": 0,
        "coverage": 0.0,
        "flagged": 0,
        "errors": 0,
    }
    selected = queue[: max(max_items, 0)]
    metadata["items_selected"] = len(selected)
    if not selected:
        metadata["status"] = "skipped_no_items"
        return [], metadata

    ai_issues: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    effective_batch_size = max(batch_size, 1)

    for start in range(0, len(selected), effective_batch_size):
        batch = selected[start : start + effective_batch_size]
        metadata["batches"] += 1
        reviews: list[dict] = []
        attempts = max(retries, 1)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                reviews = call_gemini_batch(batch, api_key=api_key, model=model, timeout_s=timeout_s)
                last_error = None
                break
            except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(max(retry_backoff_s, 1) * attempt)
        if last_error is not None:
            metadata["errors"] += 1
            LOGGER.warning("gemini review batch failed after retries: %s", last_error)
            continue

        covered_indices: set[int] = set()

        for review in reviews:
            try:
                idx = int(review.get("index"))
            except (TypeError, ValueError):
                continue
            if idx < 0 or idx >= len(batch):
                continue
            severity = str(review.get("severity", "none")).lower().strip()
            if severity not in {"none", "medium", "high", "critical"}:
                severity = "none"
            covered_indices.add(idx)
            if severity == "none":
                continue

            item = batch[idx]
            key = (
                str(item.get("locale", "")),
                str(item.get("page_id", "")),
                str(item.get("field", "")),
                str(review.get("code", "ai_quality_issue")),
            )
            if key in seen:
                continue
            seen.add(key)
            confidence_raw = review.get("confidence", 0.0)
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.0

            metadata["flagged"] += 1
            ai_issues.append(
                {
                    "locale": item.get("locale"),
                    "page_id": item.get("page_id"),
                    "field": item.get("field"),
                    "severity": severity,
                    "code": str(review.get("code", "ai_quality_issue")),
                    "message": str(review.get("message", "AI reviewer flagged translation quality risk.")),
                    "priority": int(item.get("priority", 50)) + SEVERITY_WEIGHT.get(severity, 0),
                    "en": str(item.get("en", "")),
                    "translation": str(item.get("translation", "")),
                    "source": "gemini",
                    "confidence": confidence,
                }
            )

        if covered_indices:
            metadata["successful_batches"] += 1
            metadata["reviewed_items"] += len(covered_indices)
        else:
            metadata["errors"] += 1
            LOGGER.warning("gemini review batch returned no valid index coverage")

    if metadata["items_selected"] > 0:
        metadata["coverage"] = round(float(metadata["reviewed_items"]) / float(metadata["items_selected"]), 4)
    if metadata["successful_batches"] == 0 and metadata["items_selected"] > 0:
        metadata["status"] = "no_successful_batches"
    elif metadata["errors"] > 0:
        metadata["status"] = "completed_with_errors"
    else:
        metadata["status"] = "completed"
    return ai_issues, metadata


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
    parser.add_argument(
        "--ai-review",
        action="store_true",
        help="Enable Gemini-based semantic QA on the manual review queue.",
    )
    parser.add_argument(
        "--ai-required",
        action="store_true",
        help="Fail if --ai-review is enabled but GEMINI_API_KEY is missing.",
    )
    parser.add_argument(
        "--ai-model",
        default=GEMINI_MODEL_DEFAULT,
        help=f"Gemini model name. Default: {GEMINI_MODEL_DEFAULT}",
    )
    parser.add_argument(
        "--ai-max-items",
        type=int,
        default=300,
        help="Maximum queue items sent to AI review.",
    )
    parser.add_argument(
        "--ai-batch-size",
        type=int,
        default=25,
        help="How many items to include per Gemini request.",
    )
    parser.add_argument(
        "--ai-timeout-s",
        type=int,
        default=45,
        help="HTTP timeout in seconds for each Gemini request.",
    )
    parser.add_argument(
        "--ai-retries",
        type=int,
        default=3,
        help="Retry count per Gemini batch request.",
    )
    parser.add_argument(
        "--ai-retry-backoff-s",
        type=int,
        default=2,
        help="Base backoff seconds for Gemini request retries.",
    )
    parser.add_argument(
        "--ai-min-coverage",
        type=float,
        default=0.9,
        help="Minimum AI-reviewed item coverage ratio required when AI review is enabled.",
    )
    parser.add_argument(
        "--ai-fail-on-errors",
        action="store_true",
        help="Fail when any Gemini batch still fails after retries.",
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

    ai_summary: dict = {
        "enabled": bool(args.ai_review),
        "status": "disabled",
        "model": args.ai_model,
        "max_items": args.ai_max_items,
        "batch_size": args.ai_batch_size,
        "items_selected": 0,
        "batches": 0,
        "successful_batches": 0,
        "reviewed_items": 0,
        "coverage": 0.0,
        "flagged": 0,
        "errors": 0,
    }
    if args.ai_review:
        gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not gemini_api_key:
            ai_summary["status"] = "missing_api_key"
            message = "GEMINI_API_KEY is missing; skipped AI review."
            if args.ai_required:
                LOGGER.error("i18n translation qa failed: %s", message)
                sys.exit(1)
            LOGGER.warning("%s", message)
        else:
            ai_issues, ai_summary = run_ai_review_queue(
                queue=manual_review_queue,
                api_key=gemini_api_key,
                model=args.ai_model,
                max_items=args.ai_max_items,
                batch_size=args.ai_batch_size,
                timeout_s=args.ai_timeout_s,
                retries=args.ai_retries,
                retry_backoff_s=args.ai_retry_backoff_s,
            )
            for item in ai_issues:
                locale = str(item.get("locale", ""))
                if not locale:
                    continue
                summary = locale_summary.setdefault(
                    locale,
                    {"critical": 0, "high": 0, "medium": 0, "issues": 0, "fields_checked": 0},
                )
                severity = str(item.get("severity", "medium"))
                if severity in {"critical", "high", "medium"}:
                    summary[severity] += 1
                summary["issues"] += 1
                issues.append(item)
            issues.sort(key=lambda x: (-x["priority"], x["locale"], x["page_id"], x["field"], x["code"]))
            if args.ai_required and ai_summary.get("status") == "no_successful_batches":
                LOGGER.error("i18n translation qa failed: no successful Gemini review batches")
                sys.exit(1)
            if args.ai_required and float(ai_summary.get("coverage", 0.0)) < float(args.ai_min_coverage):
                LOGGER.error(
                    "i18n translation qa failed: ai coverage %.4f below required %.4f",
                    float(ai_summary.get("coverage", 0.0)),
                    float(args.ai_min_coverage),
                )
                sys.exit(1)
            if args.ai_fail_on_errors and int(ai_summary.get("errors", 0)) > 0:
                LOGGER.error(
                    "i18n translation qa failed: ai review had %s failed batch(es)",
                    int(ai_summary.get("errors", 0)),
                )
                sys.exit(1)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "locales": locale_summary,
            "total_issues": len(issues),
            "critical": sum(x.get("critical", 0) for x in locale_summary.values()),
            "high": sum(x.get("high", 0) for x in locale_summary.values()),
            "medium": sum(x.get("medium", 0) for x in locale_summary.values()),
        },
        "ai_review": ai_summary,
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
        f"ai_status={report['ai_review']['status']} "
        f"ai_flagged={report['ai_review']['flagged']} "
        f"ai_coverage={report['ai_review']['coverage']} "
        f"ai_errors={report['ai_review']['errors']} "
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
