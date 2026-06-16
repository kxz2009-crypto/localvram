#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "src" / "data" / "search-console-keywords.json"
LOGGER = configure_logging("import-gsc-performance-export")


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_number(value: str) -> float:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0.0
    return float(text)


def parse_percent(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    if text.endswith("%"):
        return round(parse_number(text[:-1]) / 100.0, 4)
    parsed = parse_number(text)
    return round(parsed / 100.0 if parsed > 1 else parsed, 4)


def normalize_landing(page: str) -> str:
    value = str(page or "").strip()
    if not value:
        return "/"
    if value.startswith("/"):
        path = value
    else:
        parsed = urlsplit(value)
        path = parsed.path or "/"
    return path if path.startswith("/") else f"/{path}"


def extract_locale_from_landing(landing: str) -> str:
    match = re.match(r"^/([a-z]{2})(/|$)", str(landing or "").strip())
    return match.group(1).lower() if match else ""


def keyword_from_landing(landing: str) -> str:
    path = normalize_landing(landing).strip("/")
    parts = [part for part in path.split("/") if part]
    if parts and re.fullmatch(r"[a-z]{2}", parts[0]):
        parts = parts[1:]
    section = parts[0] if parts else ""
    if parts and section in {"blog", "models", "tools", "affiliate", "compare", "use-cases"} and len(parts) > 1:
        parts = parts[1:]
    slug = parts[-1] if parts else "home"
    words = re.sub(r"[^a-zA-Z0-9]+", " ", slug).strip().lower()
    return words or "home"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else (ROOT / path).resolve()


def read_csv_from_export(zip_path: Path, filename: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as archive:
        candidates = [name for name in archive.namelist() if Path(name).name == filename]
        if not candidates:
            return []
        with archive.open(candidates[0]) as handle:
            text = handle.read().decode("utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def read_filter_value(zip_path: Path, key: str) -> str:
    rows = read_csv_from_export(zip_path, "过滤器.csv")
    for row in rows:
        if not row:
            continue
        values = list(row.values())
        if len(values) >= 2 and str(values[0]).strip() == key:
            return str(values[1]).strip()
    return ""


def convert_query_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for row in rows:
        query = str(row.get("热门查询", "")).strip()
        if not query:
            continue
        items.append(
            {
                "keyword": query,
                "query": query,
                "clicks": int(round(parse_number(row.get("点击次数", "0")))),
                "impressions": int(round(parse_number(row.get("展示", "0")))),
                "ctr": parse_percent(row.get("点击率", "0")),
                "position": round(parse_number(row.get("排名", "0")), 2),
                "source_row_type": "query",
            }
        )
    items.sort(key=lambda item: (-int(item["impressions"]), -int(item["clicks"]), str(item["query"])))
    return items


def convert_page_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for row in rows:
        page = str(row.get("排名靠前的网页", "")).strip()
        if not page:
            continue
        landing = normalize_landing(page)
        items.append(
            {
                "keyword": keyword_from_landing(landing),
                "query": keyword_from_landing(landing),
                "page": page,
                "clicks": int(round(parse_number(row.get("点击次数", "0")))),
                "impressions": int(round(parse_number(row.get("展示", "0")))),
                "ctr": parse_percent(row.get("点击率", "0")),
                "position": round(parse_number(row.get("排名", "0")), 2),
                "landing": landing,
                "locale": extract_locale_from_landing(landing),
                "source_row_type": "page",
            }
        )
    items.sort(key=lambda item: (-int(item["impressions"]), -int(item["clicks"]), str(item["landing"])))
    return items


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def import_gsc_export(zip_path: Path, output_path: Path, imported_at: str | None = None) -> dict[str, object]:
    zip_path = resolve_path(Path(zip_path))
    output_path = resolve_path(Path(output_path))
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    query_items = convert_query_rows(read_csv_from_export(zip_path, "查询数.csv"))
    page_items = convert_page_rows(read_csv_from_export(zip_path, "网页.csv"))
    if not query_items and not page_items:
        raise ValueError("GSC export did not contain query or page rows")

    payload: dict[str, object] = {
        "updated_at": imported_at or utc_now_iso(),
        "source": "google-search-console-ui-export",
        "date_range_label": read_filter_value(zip_path, "日期"),
        "note": "Google Search Console UI exports query and page tables separately; items are page-level rows, not invented query-page pairs.",
        "items": page_items,
        "page_items": page_items,
        "query_items": query_items,
    }
    write_json(output_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a Google Search Console Performance UI export zip.")
    parser.add_argument("zip_path", help="Path to localvram.com-Performance-on-Search-*.zip")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON file")
    parser.add_argument("--imported-at", default="", help="Override imported timestamp for tests")
    args = parser.parse_args()

    payload = import_gsc_export(
        zip_path=Path(args.zip_path),
        output_path=Path(args.output),
        imported_at=str(args.imported_at or "").strip() or None,
    )
    LOGGER.info("gsc_export_source=google-search-console-ui-export")
    LOGGER.info("gsc_query_items=%s", len(payload.get("query_items", [])))
    LOGGER.info("gsc_page_items=%s", len(payload.get("page_items", [])))
    LOGGER.info("gsc_output=%s", resolve_path(Path(args.output)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
